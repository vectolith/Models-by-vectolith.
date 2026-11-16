from __future__ import annotations

import unittest

from evaluation.snapshot_additional_teacher import EXPECTED, license_evidence


class AdditionalTeacherSnapshotTests(unittest.TestCase):
    def test_three_new_candidates_are_explicitly_pinned_to_expected_architectures(self):
        self.assertEqual(set(EXPECTED), {"smollm3-3b", "lfm2.5-2.6b", "phi-4-mini-instruct"})
        self.assertEqual(EXPECTED["smollm3-3b"]["repo"], "HuggingFaceTB/SmolLM3-3B")
        self.assertEqual(EXPECTED["smollm3-3b"]["model_type"], "smollm3")
        self.assertEqual(EXPECTED["lfm2.5-2.6b"]["repo"], "LiquidAI/LFM2.5-2.6B")
        self.assertEqual(EXPECTED["lfm2.5-2.6b"]["license"], "lfm1.0")
        self.assertEqual(EXPECTED["phi-4-mini-instruct"]["repo"], "microsoft/Phi-4-mini-instruct")
        self.assertEqual(EXPECTED["phi-4-mini-instruct"]["license"], "mit")

    def test_every_candidate_requires_an_explicit_model_architecture(self):
        for candidate in EXPECTED.values():
            self.assertTrue(candidate["model_type"])
            self.assertTrue(candidate["architectures"])
            self.assertEqual(len(candidate["architectures"]), 1)

    def test_upstream_license_file_is_hash_inventory_evidence(self):
        files = [{"path": "LICENSE", "size_bytes": 12, "sha256": "abc"}]
        evidence = license_evidence(files, "owner/model", "a" * 40, "mit")
        self.assertEqual(evidence["status"], "license_file_present_pending_human_review")
        self.assertEqual(evidence["license_files"], files)

    def test_missing_license_file_is_recorded_as_pending_not_a_snapshot_failure(self):
        files = [{"path": "README.md", "size_bytes": 24, "sha256": "def"}]
        evidence = license_evidence(files, "owner/model", "b" * 40, "apache-2.0")
        self.assertEqual(evidence["status"], "model_card_tag_only_pending_human_review")
        self.assertEqual(evidence["license_files"], [])
        self.assertEqual(evidence["model_card_files"], files)
        self.assertIn("/blob/" + "b" * 40 + "/README.md", evidence["model_card_url"])


if __name__ == "__main__":
    unittest.main()
