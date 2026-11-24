
"""CPU-only verification of training/kaggle/kernel.py.

The kernel itself needs a GPU, torch and transformers, but its curriculum
handling, teacher-record validation, dataset assembly, config parsing and
output paths are all pure Python. This suite stubs torch/transformers so those
stages can be verified on any CPU machine (and in CI) before a Kaggle session
is spent.

Run: python3 -m unittest training/kaggle/test_kernel_cpu.py -v
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
KERNEL = HERE / "kernel.py"


def _stub_dependencies() -> None:
    """Install the smallest possible torch/transformers stand-ins."""

    class _NoOp:
        def __init__(self, *args, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def __getattr__(self, name):
            return _NoOp()

        def eval(self):
            return self

        def to(self, *args, **kwargs):
            return self

    torch = types.ModuleType("torch")
    torch.float16 = "float16"
    torch.inference_mode = lambda: (lambda fn: fn)
    torch.manual_seed = lambda seed: None
    torch.__version__ = "stub"
    torch.cuda = types.SimpleNamespace(
        empty_cache=lambda: None,
        is_available=lambda: False,
        device_count=lambda: 0,
        get_device_name=lambda index=0: "stub",
    )
    transformers = types.ModuleType("transformers")
    for name in (
        "AutoModelForCausalLM",
        "AutoTokenizer",
        "BitsAndBytesConfig",
        "Trainer",
        "TrainingArguments",
    ):
        setattr(transformers, name, _NoOp)
    sys.modules.setdefault("torch", torch)
    sys.modules.setdefault("transformers", transformers)


def load_kernel(working_dir: str):
    _stub_dependencies()
    os.environ["KAGGLE_WORKING_DIR"] = working_dir
    spec = importlib.util.spec_from_file_location("kaggle_kernel", KERNEL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class KernelCpuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.kernel = load_kernel(cls.tmp.name)
        cls.working = Path(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # -- config parsing / metadata ------------------------------------------
    def test_metadata(self):
        metadata = json.loads((HERE / "kernel-metadata.json").read_text(encoding="utf-8"))
        owner, _, slug = metadata["id"].partition("/")
        self.assertEqual(owner, "vectolith", "metadata id must belong to the repo owner")
        self.assertTrue(slug, "metadata id must be <owner>/<slug>")
        self.assertEqual(metadata["code_file"], "kernel.py")
        self.assertTrue((HERE / metadata["code_file"]).is_file())
        self.assertEqual(metadata["language"], "python")
        self.assertIn(metadata["kernel_type"], ("script", "notebook"))
        self.assertTrue(metadata["is_private"], "the training run must not be public")
        self.assertTrue(metadata["enable_gpu"], "the kernel needs a GPU")
        self.assertTrue(metadata["enable_internet"], "weights are pulled from the Hub")
        for key in ("dataset_sources", "competition_sources", "kernel_sources", "model_sources"):
            self.assertIn(key, metadata)

    def test_output_paths(self):
        self.kernel.prepare_paths()
        self.assertTrue(self.kernel.OUT.is_dir())
        self.assertTrue(self.kernel.CORPUS.is_dir())
        self.assertEqual(self.kernel.OUT.parent, self.working)

    # -- curriculum ----------------------------------------------------------
    def test_curriculum_schema_and_coverage(self):
        competencies = {
            competency
            for spec in self.kernel.TEACHERS.values()
            for competency in spec["competencies"]
        }
        tasks = [
            json.loads(line)
            for line in (
                REPO / "training" / "curriculum" / "tasks-v1.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertGreater(len(tasks), 0)
        ids = set()
        for task in tasks:
            self.kernel.validate_task(task, competencies)
            self.assertNotIn(task["id"], ids, "duplicate curriculum task id")
            ids.add(task["id"])
        covered = {task["competency"] for task in tasks}
        self.assertEqual(covered - competencies, set(), "uncovered competencies")
        # every teacher must own at least one competency in the curriculum
        for name, spec in self.kernel.TEACHERS.items():
            assigned = [task for task in tasks if task["competency"] in spec["competencies"]]
            self.assertGreater(len(assigned), 0, f"{name} has no curriculum tasks")

    def test_unknown_competency_rejected(self):
        with self.assertRaises(ValueError):
            self.kernel.validate_task(
                {"id": "x", "competency": "not-a-thing", "system": "s", "prompt": "p"},
                {"reasoning"},
            )
        with self.assertRaises(ValueError):
            self.kernel.validate_task({"id": "y", "competency": "reasoning"}, {"reasoning"})

    # -- reproducibility -----------------------------------------------------
    def test_seed_is_content_derived(self):
        expected = int(hashlib.sha256(b"granite-4.2-8b").hexdigest()[:8], 16) % 10000
        self.assertEqual(self.kernel.seed_for("granite-4.2-8b"), expected)
        self.assertEqual(
            self.kernel.seed_for("granite-4.2-8b"), self.kernel.seed_for("granite-4.2-8b")
        )

    def test_seed_stable_across_hash_randomisation(self):
        script = (
            "import hashlib;"
            "print(int(hashlib.sha256(b'qwen3-4b-instruct').hexdigest()[:8],16)%10000,"
            "hash('qwen3-4b-instruct'))"
        )
        seeds = set()
        for hashseed in ("1", "2", "3"):
            env = dict(os.environ, PYTHONHASHSEED=hashseed)
            out = subprocess.run(
                [sys.executable, "-c", script], capture_output=True, text=True, env=env, check=True
            )
            seeds.add(out.stdout.split()[0])
        self.assertEqual(len(seeds), 1, "seed changed with PYTHONHASHSEED")

    # -- teacher records -----------------------------------------------------
    def _record(self, **overrides):
        text = overrides.pop("text", "A reasonably long and specific answer. " * 4)
        record = {
            "task_id": "cap-1",
            "competency": "reasoning",
            "prompt": "why",
            "system": "you are",
            "teacher": "granite-4.2-8b",
            "teacher_model": "ibm-granite/granite-4.2-8b",
            "teacher_revision": "a7042144125ce5ae64f89610e8289647fc000b9a",
            "teacher_license": "apache-2.0",
            "response": text,
            "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "checks": {"accepted": True, "reasons": []},
        }
        record.update(overrides)
        return record

    def test_corpus_row_validation(self):
        self.kernel.validate_corpus_row(self._record())
        broken = self._record()
        broken.pop("teacher_revision")
        with self.assertRaises(ValueError):
            self.kernel.validate_corpus_row(broken)
        tampered = self._record(response_sha256="0" * 64)
        with self.assertRaises(ValueError):
            self.kernel.validate_corpus_row(tampered)

    def test_deterministic_checks(self):
        fence = chr(96) * 3
        task = {"competency": "coding"}
        good = (
            "Here is a function.\n\n"
            + fence
            + "python\ndef add(a, b):\n    return a + b\n"
            + fence
            + "\nIt returns the sum of both arguments."
        )
        self.assertTrue(self.kernel.deterministic_checks(task, good)["accepted"])
        self.assertIn("too_short", self.kernel.deterministic_checks(task, "short")["reasons"])
        refusal = "As an AI language model, I cannot help with that request at all, sorry friend."
        self.assertIn(
            "boilerplate_refusal", self.kernel.deterministic_checks(task, refusal)["reasons"]
        )
        bad_python = (
            "Sure.\n\n"
            + fence
            + "python\ndef add(a, b)\n    return a + b\n"
            + fence
            + "\nThat should do what you asked for."
        )
        self.assertIn(
            "python_syntax_error", self.kernel.deterministic_checks(task, bad_python)["reasons"]
        )

    # -- dataset assembly ----------------------------------------------------
    def test_build_dataset_filters_and_is_stable(self):
        accepted = self._record(task_id="cap-1")
        rejected = self._record(task_id="cap-2", checks={"accepted": False, "reasons": ["too_short"]})
        other = self._record(task_id="cap-3", teacher="qwen3-4b-instruct")
        corpus = {
            "granite-4.2-8b": [accepted, rejected],
            "qwen3-4b-instruct": [other],
            "qwen2.5-coder-7b": [],
        }
        panel = ["granite-4.2-8b", "qwen3-4b-instruct"]
        rows = self.kernel.build_dataset(corpus, panel, seed=11)
        self.assertEqual(sorted(row["task_id"] for row in rows), ["cap-1", "cap-3"])
        for row in rows:
            self.assertIn(row["teacher_revision"], (
                accepted["teacher_revision"],
                other["teacher_revision"],
            ))
        self.assertEqual(
            {row["teacher_revision"] for row in rows}, {accepted["teacher_revision"]}
        )
        self.assertEqual(rows, self.kernel.build_dataset(corpus, panel, seed=11))
        only_panel = self.kernel.build_dataset(corpus, ["qwen3-4b-instruct"], seed=11)
        self.assertEqual([row["teacher"] for row in only_panel], ["qwen3-4b-instruct"])

    def test_generate_corpus_end_to_end(self):
        """Exercise the full generate -> validate -> write path with a fake teacher."""
        from unittest import mock

        tasks = [
            {
                "id": "cap-a",
                "competency": "reasoning",
                "system": "you are",
                "prompt": "why",
            },
            {
                "id": "cap-b",
                "competency": "conversation",
                "system": "you are",
                "prompt": "hello",
            },
            {
                "id": "cap-c",
                "competency": "coding",
                "system": "you are",
                "prompt": "write code",
            },
        ]

        class _FakeConfig:
            _commit_hash = "deadbeef00000000000000000000000000000000"

        class _FakeModel:
            config = _FakeConfig()

        def fake_load_teacher(name, spec):
            # mirror load_teacher(): record the immutable revision it saw
            self.kernel.REVISIONS[name] = _FakeConfig._commit_hash
            return object(), _FakeModel()

        def fake_answer(tokenizer, model, subset, seed):
            self.assertIsInstance(seed, int)
            return [
                {"task": task, "text": f"{task['id']} answer. " * 6}
                for task in subset
            ]

        self.kernel.prepare_paths()
        with mock.patch.object(self.kernel, "load_teacher", fake_load_teacher), mock.patch.object(
            self.kernel, "answer_tasks", fake_answer
        ):
            corpus = self.kernel.generate_corpus(tasks)

        self.assertEqual(set(corpus), set(self.kernel.TEACHERS))
        written = 0
        for name in corpus:
            path = self.kernel.CORPUS / f"teacher-{name}.jsonl"
            self.assertTrue(path.is_file(), path)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            for row in rows:
                self.kernel.validate_corpus_row(row)
                self.assertEqual(row["teacher"], name)
                self.assertEqual(row["teacher_revision"], "deadbeef" + "0" * 32)
                self.assertEqual(self.kernel.REVISIONS[name], "deadbeef" + "0" * 32)
            written += len(rows)
        self.assertEqual(written, len(tasks), "every task answered by exactly one teacher")
        for student in self.kernel.STUDENTS.values():
            rows = self.kernel.build_dataset(corpus, student["panel"], student["seed"])
            self.assertGreater(len(rows), 0)

    def test_student_panels_reference_known_teachers(self):
        for name, spec in self.kernel.STUDENTS.items():
            for teacher in spec["panel"]:
                self.assertIn(teacher, self.kernel.TEACHERS, f"{name} panel names {teacher}")
            self.assertNotEqual(
                spec["model_id"],
                self.kernel.STUDENTS[
                    "fyr-prima" if name == "ash-prime" else "ash-prime"
                ]["model_id"],
                "students must not share a foundation",
            )


class GradedCorpusTests(unittest.TestCase):
    """The graded-corpus path must train only on all-criteria-passed rows."""

    def setUp(self):
        import hashlib as _hashlib, json as _json
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.kernel = load_kernel(self.dir.as_posix() + "/work")
        self.kernel.prepare_paths()
        self.kernel.GRADED_CORPUS_DIR = self.dir

    def tearDown(self):
        self.tmp.cleanup()

    def _row(self, case_id, teacher, response, accepted=True, reason=None):
        import hashlib as _hashlib
        return {
            "schema_version": "vectolith-ash-prime-graded-training-corpus/1.0",
            "case_id": case_id,
            "teacher": teacher,
            "teacher_revision": "a" * 40,
            "source_artifact_sha256": "b" * 64,
            "system": "sys-" + case_id,
            "prompt": "ask-" + case_id,
            "response": response,
            "response_sha256": _hashlib.sha256(response.encode()).hexdigest(),
            "grade": {"passed": 4, "failed": 0, "unscored": 0, "total": 4},
            "accepted": accepted,
            "rejection_reason": reason,
        }

    def _write(self, rows):
        import hashlib as _hashlib, json as _json
        path = self.dir / self.kernel.GRADED_CORPUS_FILE
        payload = b"".join(
            _json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + bytes([10])
            for row in rows
        )
        path.write_bytes(payload)
        (self.dir / self.kernel.GRADED_CORPUS_MANIFEST).write_text(
            _json.dumps({"corpus_sha256": _hashlib.sha256(payload).hexdigest()}), encoding="utf-8"
        )

    def test_missing_corpus_falls_back_to_generation(self):
        self.assertEqual(self.kernel.load_graded_corpus(), [])

    def test_rejected_rows_are_never_loaded(self):
        self._write([
            self._row("case-a", "granite-4.2-3b", "good"),
            self._row("case-b", "granite-4.2-3b", "bad", accepted=False, reason="failed_criteria"),
        ])
        rows = self.kernel.load_graded_corpus()
        self.assertEqual([row["case_id"] for row in rows], ["case-a"])

    def test_tampered_corpus_is_rejected(self):
        self._write([self._row("case-a", "granite-4.2-3b", "good")])
        path = self.dir / self.kernel.GRADED_CORPUS_FILE
        path.write_text(path.read_text(encoding="utf-8").replace("good", "evil"), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            self.kernel.load_graded_corpus()

    def test_unhashed_response_is_rejected(self):
        row = self._row("case-a", "granite-4.2-3b", "good")
        row["response"] = "tampered"
        self._write([row])
        with self.assertRaises(ValueError):
            self.kernel.load_graded_corpus()

    def test_unknown_teacher_is_rejected(self):
        self._write([self._row("case-a", "mystery-model", "good")])
        with self.assertRaises(ValueError):
            self.kernel.load_graded_corpus()

    def test_graded_dataset_respects_panels_and_licences(self):
        self._write([
            self._row("case-a", "granite-4.2-3b", "good a"),
            self._row("case-b", "phi-4-mini-instruct", "good b"),
            self._row("case-c", "lfm2.5-2.6b", "good c"),
        ])
        rows = self.kernel.load_graded_corpus()
        spec = self.kernel.GRADED_STUDENTS["fyr-prima"]
        dataset = self.kernel.build_graded_dataset(rows, spec["panel"], spec["seed"])
        self.assertEqual({row["teacher"] for row in dataset},
                         {"granite-4.2-3b", "phi-4-mini-instruct"})
        self.assertEqual({row["teacher_license"] for row in dataset}, {"apache-2.0", "mit"})
        for row in dataset:
            self.assertEqual([m["role"] for m in row["messages"]], ["system", "user", "assistant"])
            self.assertEqual(row["task_id"], row["task_id"].strip())

    def test_graded_student_panels_reference_known_licences(self):
        for name, spec in self.kernel.GRADED_STUDENTS.items():
            for teacher in spec["panel"]:
                self.assertIn(teacher, self.kernel.GRADED_TEACHER_LICENSES, f"{name} panel names {teacher}")


if __name__ == "__main__":
        unittest.main()
