from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path

from evaluation.run_eval import load_cases


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class BalancedQualificationV3Tests(unittest.TestCase):
    def _assert_balanced(self, role: str) -> None:
        paths = [
            FIXTURES / f"{role}_benchmark_v1.jsonl",
            FIXTURES / f"{role}_qualification_v2.jsonl",
            FIXTURES / f"{role}_qualification_v3.jsonl",
        ]
        suites = [load_cases(path) for path in paths]
        cases = [case for suite in suites for case in suite]
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)), "case IDs must be unique across all public suites")
        counts = Counter(case.get("category", "uncategorized") for case in cases)
        self.assertTrue(counts, "suite must contain competency categories")
        self.assertTrue(
            all(count >= 5 for count in counts.values()),
            f"every competency needs at least five independent cases; got {dict(counts)}",
        )
        self.assertTrue(all(case.get("rubric") for case in cases))
        self.assertTrue(all(len(case["messages"]) >= 2 for case in cases))

    def test_prime_has_five_cases_per_competency(self):
        self._assert_balanced("prime")

    def test_prima_has_five_cases_per_competency(self):
        self._assert_balanced("prima")


if __name__ == "__main__":
    unittest.main()
