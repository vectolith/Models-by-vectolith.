from __future__ import annotations

import unittest

from vectolith_runtime.distillation_training import split_dataset_by_prompt_group


class TrainingDatasetSplitTests(unittest.TestCase):
    def _rows(self):
        return [
            {"teacher_id": f"teacher-{teacher}", "prompt": f"prompt-{task}",
             "response": f"response-{teacher}-{task}"}
            for teacher in range(4) for task in range(12)
        ]

    def test_split_is_deterministic_and_prompt_disjoint(self):
        rows = self._rows()
        train_a, validation_a, metadata_a = split_dataset_by_prompt_group(rows, seed=42)
        train_b, validation_b, metadata_b = split_dataset_by_prompt_group(rows, seed=42)
        self.assertEqual(metadata_a, metadata_b)
        self.assertEqual(train_a, train_b)
        self.assertEqual(validation_a, validation_b)
        train_prompts = {row["prompt"] for row in train_a}
        validation_prompts = {row["prompt"] for row in validation_a}
        self.assertFalse(train_prompts & validation_prompts)
        self.assertEqual({row["teacher_id"] for row in rows}, {row["teacher_id"] for row in train_a})
        self.assertGreaterEqual(metadata_a["validation_prompt_groups"], 2)

    def test_all_teacher_responses_for_a_prompt_stay_in_one_partition(self):
        train, validation, _ = split_dataset_by_prompt_group(self._rows(), seed=9)
        for prompt in {row["prompt"] for row in train + validation}:
            partitions = {
                "train" if row in train else "validation"
                for row in train + validation if row["prompt"] == prompt
            }
            self.assertEqual(len(partitions), 1)

    def test_too_few_unique_prompts_is_rejected(self):
        rows = [
            {"teacher_id": f"teacher-{teacher}", "prompt": "same prompt", "response": "answer"}
            for teacher in range(4)
        ]
        with self.assertRaisesRegex(ValueError, "distinct prompts"):
            split_dataset_by_prompt_group(rows)

    def test_cannot_remove_the_only_training_examples_for_any_teacher(self):
        rows = [
            {"teacher_id": f"teacher-{task}", "prompt": f"prompt-{task}", "response": "answer"}
            for task in range(4)
        ]
        with self.assertRaisesRegex(ValueError, "retaining every teacher"):
            split_dataset_by_prompt_group(rows, validation_fraction=0.5, minimum_validation_groups=2)


if __name__ == "__main__":
    unittest.main()
