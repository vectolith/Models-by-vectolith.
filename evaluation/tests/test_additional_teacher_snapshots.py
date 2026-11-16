from __future__ import annotations

import unittest

from evaluation.snapshot_additional_teacher import EXPECTED


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


if __name__ == "__main__":
    unittest.main()
