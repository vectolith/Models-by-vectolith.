from __future__ import annotations

import unittest
from pathlib import Path

from evaluation.completion import classify_completion, summarize_completion


class CompletionClassificationTests(unittest.TestCase):
    def test_eos_is_completed_even_when_token_count_reaches_budget(self):
        self.assertEqual(
            classify_completion([10, 11, 2], 3, 2, "finished"),
            "eos_completed",
        )

    def test_multiple_eos_ids_are_supported_for_multimodal_tokenizers(self):
        self.assertEqual(
            classify_completion([10, 106], 8, [1, 106], "finished"),
            "eos_completed",
        )

    def test_full_budget_without_eos_is_truncated(self):
        self.assertEqual(
            classify_completion([10, 11, 12], 3, 2, "partial answer"),
            "token_cap_truncated",
        )

    def test_short_stop_without_eos_is_not_claimed_complete(self):
        self.assertEqual(
            classify_completion([10, 11], 3, 2, "answer"),
            "stopped_without_eos",
        )

    def test_errors_and_empty_outputs_are_separate(self):
        self.assertEqual(classify_completion([], 10, 2, None, "RuntimeError"), "error")
        self.assertEqual(classify_completion([], 10, 2, ""), "empty_output")

    def test_real_inference_runner_source_compiles_with_expanded_budget(self):
        runner = Path(__file__).resolve().parents[1] / "run_real_candidate_eval.py"
        source = runner.read_text(encoding="utf-8")
        compile(source, str(runner), "exec")
        self.assertIn("1<=a.max_new_tokens<=1024", source)
        self.assertIn("completion_status_counts", source)

    def test_completion_summary_counts_all_statuses(self):
        rows = [
            {"completion_status": "eos_completed"},
            {"completion_status": "eos_completed"},
            {"completion_status": "token_cap_truncated"},
            {"completion_status": "error"},
        ]
        self.assertEqual(
            summarize_completion(rows),
            {"eos_completed": 2, "error": 1, "token_cap_truncated": 1},
        )


if __name__ == "__main__":
    unittest.main()
