import json, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

from vectolith_runtime import distillation_training as dt

SHA = 'a' * 40

def rows_for(prompts, teachers=('t1', 't2')):
    rows = []
    for i, prompt in enumerate(prompts):
        rows.append({'prompt': prompt, 'response': 'answer %d' % i, 'teacher_id': teachers[i % len(teachers)]})
    return rows

class FakeTokenizer:
    chat_template = None
    eos_token = '</s>'

    def __call__(self, text, add_special_tokens=True, truncation=False, max_length=None):
        ids = list(range(1, len(text.split()) + 1))
        if truncation and max_length is not None:
            ids = ids[:max_length]
        return {'input_ids': ids}

class ChatTokenizer(FakeTokenizer):
    chat_template = '<template>'

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        return ' | '.join('<%s>%s</%s>' % (m['role'], m['content'], m['role']) for m in messages)

class SplitTests(unittest.TestCase):
    def test_split_is_deterministic_and_disjoint(self):
        rows = rows_for(['p1', 'p2', 'p3', 'p4'])
        train_a, val_a, meta_a = dt.split_dataset_by_prompt_group(rows, validation_fraction=0.25, seed=7)
        train_b, val_b, meta_b = dt.split_dataset_by_prompt_group(rows, validation_fraction=0.25, seed=7)
        self.assertEqual(meta_a['validation_prompt_sha256'], meta_b['validation_prompt_sha256'])
        self.assertEqual(len(train_a) + len(val_a), len(rows))
        self.assertFalse(set(meta_a['training_prompt_sha256']) & set(meta_a['validation_prompt_sha256']))
        self.assertGreaterEqual(meta_a['validation_prompt_groups'], 2)
        self.assertEqual(set(meta_a['teacher_ids_in_training']), {'t1', 't2'})
        self.assertEqual(meta_a['schema_version'], 'vectolith-training-data-split/1.0')

    def test_duplicate_prompt_rows_stay_on_one_side(self):
        rows = rows_for(['p1', 'p2', 'p3', 'p4'])
        rows.append({'prompt': 'p1', 'response': 'second answer', 'teacher_id': 't2'})
        train, val, meta = dt.split_dataset_by_prompt_group(rows, validation_fraction=0.2)
        train_prompts = {r['prompt'] for r in train}
        val_prompts = {r['prompt'] for r in val}
        self.assertFalse(train_prompts & val_prompts)
        self.assertEqual(len(train) + len(val), len(rows))

    def test_seed_changes_selection(self):
        rows = rows_for(['p%d' % i for i in range(12)], teachers=('t1', 't2', 't3'))
        _, _, meta1 = dt.split_dataset_by_prompt_group(rows, validation_fraction=0.25, seed=1)
        _, _, meta2 = dt.split_dataset_by_prompt_group(rows, validation_fraction=0.25, seed=99)
        self.assertNotEqual(meta1['validation_prompt_sha256'], meta2['validation_prompt_sha256'])

    def test_rejects_bad_fraction_seed_and_group_floor(self):
        rows = rows_for(['p1', 'p2', 'p3'])
        with self.assertRaises(ValueError):
            dt.split_dataset_by_prompt_group(rows, validation_fraction=0.5)
        with self.assertRaises(ValueError):
            dt.split_dataset_by_prompt_group(rows, seed=True)
        with self.assertRaises(ValueError):
            dt.split_dataset_by_prompt_group(rows, minimum_validation_groups=0)
        with self.assertRaises(ValueError):
            dt.split_dataset_by_prompt_group(rows_for(['only']), minimum_validation_groups=2)

    def test_rejects_incomplete_rows(self):
        good = rows_for(['p1', 'p2', 'p3'])
        for bad in ({'prompt': '', 'response': 'x', 'teacher_id': 't1'},
                    {'prompt': 'p', 'response': '  ', 'teacher_id': 't1'},
                    {'prompt': 'p', 'response': 'x', 'teacher_id': ''},
                    {'prompt': 'p', 'response': 'x'}):
            with self.assertRaises(ValueError):
                dt.split_dataset_by_prompt_group(good + [bad])

    def test_rejects_when_validation_would_remove_a_teacher(self):
        rows = [
            {'prompt': 'a', 'response': 'x', 'teacher_id': 't1'},
            {'prompt': 'b', 'response': 'x', 'teacher_id': 't1'},
            {'prompt': 'c', 'response': 'x', 'teacher_id': 't2'},
        ]
        with self.assertRaises(ValueError) as ctx:
            dt.split_dataset_by_prompt_group(rows, validation_fraction=0.3, minimum_validation_groups=2)
        self.assertIn('collect more independent prompts', str(ctx.exception))

class TokenizeTests(unittest.TestCase):
    def test_masks_prompt_tokens_in_labels(self):
        batch = dt._tokenize_batch({'prompt': ['hello there'], 'response': ['yes indeed']}, FakeTokenizer(), 64)
        input_ids, labels = batch['input_ids'][0], batch['labels'][0]
        self.assertEqual(batch['attention_mask'][0], [1] * len(input_ids))
        self.assertEqual(input_ids[:6], [1, 2, 3, 4, 5, 6])
        self.assertEqual(labels[:6], [-100] * 6)
        prompt_tokens = len('### Instruction hello there ### Response'.split())
        self.assertEqual(labels[prompt_tokens:], input_ids[prompt_tokens:])
        self.assertEqual(len(labels), len(input_ids))

    def test_chat_template_path_masks_prompt(self):
        batch = dt._tokenize_batch({'prompt': ['hey'], 'response': ['yo']}, ChatTokenizer(), 64)
        labels = batch['labels'][0]
        self.assertEqual(labels[:1], [-100])
        self.assertTrue(all(label != -100 for label in labels[1:]))
        self.assertEqual(len(labels), 3)

    def test_raises_when_response_truncated(self):
        with self.assertRaises(ValueError) as ctx:
            dt._tokenize_batch({'prompt': ['a b c d'], 'response': ['e f g h']}, FakeTokenizer(), 4)
        self.assertIn('strict prefix', str(ctx.exception))

PREFLIGHT = {
    'foundation_selection_sha256': 'f' * 64,
    'dataset_sha256': 'd' * 64,
    'teacher_manifest_sha256': 't' * 64,
    'protected_holdout_deployment_sha256': 'h' * 64,
    'training_execution_manifest_sha256': 'e' * 64,
    'training_run_id': 'run-1',
}

def call_train_student(**overrides):
    kwargs = dict(
        foundation_model='org/model',
        foundation_revision=SHA,
        dataset_path='dataset.jsonl',
        output_dir=tempfile.mkdtemp(),
        foundation_selection_manifest='fs.json',
        teacher_qualification_manifest_dir='teachers',
        holdout_deployment_manifest='holdout.json',
        holdout_evaluation_results_dir='results',
        training_execution_manifest='exec.json',
        training_code_revision=SHA,
    )
    kwargs.update(overrides)
    return dt.train_student(**kwargs)

class TrainStudentTests(unittest.TestCase):
    def test_rejects_mutable_revisions(self):
        with self.assertRaises(ValueError):
            call_train_student(training_code_revision='main')
        with self.assertRaises(ValueError):
            call_train_student(foundation_revision='v1.0')

    def test_rejects_unusable_configuration(self):
        for bad in (dict(max_seq_length=16), dict(epochs=0), dict(learning_rate=0), dict(per_device_batch_size=0), dict(gradient_accumulation_steps=0)):
            with self.assertRaises(ValueError):
                call_train_student(**bad)

    def test_refuses_non_empty_output_dir(self):
        out = tempfile.mkdtemp()
        Path(out, 'leftover.txt').write_text('x')
        with mock.patch.object(dt, 'validate_training_preflight', return_value=(rows_for(['p1', 'p2', 'p3', 'p4']), PREFLIGHT)):
            with self.assertRaises(FileExistsError):
                call_train_student(output_dir=out)

    def test_records_failed_manifest_when_dependencies_missing(self):
        out = tempfile.mkdtemp()
        with mock.patch.object(dt, 'validate_training_preflight', return_value=(rows_for(['p1', 'p2', 'p3', 'p4']), PREFLIGHT)), \
             mock.patch.dict(sys.modules, {'datasets': None}):
            with self.assertRaises(RuntimeError) as ctx:
                call_train_student(output_dir=out)
        self.assertIn('training dependencies missing', str(ctx.exception))
        manifest = json.loads(Path(out, 'training-run-manifest.json').read_text())
        self.assertEqual(manifest['status'], 'failed')
        self.assertEqual(manifest['failure']['exception_type'], 'RuntimeError')
        self.assertEqual(manifest['training_run_id'], 'run-1')
        self.assertEqual(manifest['schema_version'], 'vectolith-training-run/1.0')
        self.assertTrue(Path(out, 'training-preflight.json').exists())

if __name__ == '__main__':
    unittest.main()