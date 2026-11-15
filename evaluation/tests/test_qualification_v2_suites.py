from __future__ import annotations

import unittest
from pathlib import Path

from evaluation.run_eval import load_cases


class QualificationSuiteV2Tests(unittest.TestCase):
    def test_prime_suite_is_substantial_and_ids_are_unique(self):
        path = Path(__file__).resolve().parents[1] / "fixtures" / "prime_qualification_v2.jsonl"
        cases = load_cases(path)
        self.assertGreaterEqual(len(cases), 20)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertGreaterEqual(len({case["category"] for case in cases}), 10)
        self.assertTrue(all(case.get("rubric") for case in cases))

    def test_prima_suite_is_substantial_and_ids_are_unique(self):
        path = Path(__file__).resolve().parents[1] / "fixtures" / "prima_qualification_v2.jsonl"
        cases = load_cases(path)
        self.assertGreaterEqual(len(cases), 20)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        self.assertGreaterEqual(len({case["category"] for case in cases}), 10)
        self.assertTrue(all(case.get("rubric") for case in cases))


if __name__ == "__main__":
    unittest.main()
