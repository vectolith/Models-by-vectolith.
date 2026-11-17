from __future__ import annotations

import unittest

from evaluation.run_completion_study import CANDIDATES


class CompletionStudyConfigurationTests(unittest.TestCase):
    def test_only_the_five_preserved_real_response_candidates_are_repeated(self):
        ids = [candidate["candidate_id"] for candidate in CANDIDATES]
        self.assertEqual(len(ids), 5)
        self.assertEqual(len(set(ids)), 5)
        self.assertEqual(
            set(ids),
            {
                "granite-3.1-3b-a800m",
                "granite-4.2-3b",
                "minicpm5-2b",
                "lfm2.5-2.6b",
                "phi-4-mini-instruct",
            },
        )
        self.assertNotIn("smollm3-3b", ids)

    def test_every_completion_candidate_uses_an_immutable_revision_and_pinned_loader(self):
        for candidate in CANDIDATES:
            revision = candidate["revision"]
            self.assertEqual(len(revision), 40)
            self.assertTrue(all(char in "0123456789abcdef" for char in revision))
            self.assertIn(candidate["transformers"], {"4.57.1", "5.0.0"})
            self.assertIn(candidate["hub"], {"0.36.0", "1.3.0"})


if __name__ == "__main__":
    unittest.main()
