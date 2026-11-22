from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from evaluation.audit_historical_teacher_outputs import load_rows, screen, summarize


class HistoricalOutputAuditTests(unittest.TestCase):
    def test_screens_truncation_meta_text_and_action_claims_without_scoring(self):
        row = {
            "candidate_id": "candidate-a",
            "model_revision": "a" * 40,
            "run_id": "run-1",
            "case_id": "case-1",
            "category": "tool_calling",
            "generation_status": "token_limit_reached",
            "generation_cap_reached": True,
            "generated_tokens": 256,
            "max_new_tokens": 256,
            "latency_seconds": 1.25,
            "response_text": "The user wants me to act. I have successfully deleted the account.",
            "error": None,
        }
        findings = screen([row])
        self.assertIn("truncated_at_generation_cap", findings[0]["flags"])
        self.assertIn("possible_internal_reasoning_or_meta_text", findings[0]["flags"])
        self.assertIn("possible_unverified_action_claim", findings[0]["flags"])
        self.assertEqual(len(findings[0]["response_sha256"]), 64)
        summary = summarize([row], findings)
        self.assertEqual(summary["response_count"], 1)
        self.assertEqual(summary["candidate_summaries"]["candidate-a"]["token_cap_hits"], 1)
        self.assertEqual(summary["duplicate_candidate_run_case_keys"], 0)
        self.assertTrue(summary["all_errors_null"])
        self.assertEqual(summary["review_type"], "automated_evidence_screening_not_human_grading")

    def test_load_rows_reads_jsonl_from_archives_and_preserves_source_name(self):
        row = {
            "candidate_id": "candidate-a", "model_revision": "a" * 40,
            "run_id": "run-1", "case_id": "case-1", "category": "reasoning",
            "generation_status": "eos_or_early_stop", "generation_cap_reached": False,
            "generated_tokens": 8, "max_new_tokens": 256, "latency_seconds": 0.5,
            "response_text": "A complete answer.", "error": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "ash-prime-test.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("evaluations/sample.jsonl", json.dumps(row) + "\n")
            loaded = load_rows([str(archive_path)])
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["_artifact"], "ash-prime-test.zip")
        self.assertEqual(loaded[0]["response_text"], "A complete answer.")


if __name__ == "__main__":
    unittest.main()
