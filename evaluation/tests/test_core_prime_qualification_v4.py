from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path

from evaluation.run_eval import load_cases

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED_CATEGORIES = {
    "coding_generation",
    "debugging",
    "code_review",
    "software_architecture",
    "testing_verification",
    "algorithms_data_structures",
    "data_analysis",
    "technical_mathematics",
    "tool_calling",
    "agentic_task_planning",
    "state_recovery",
    "research_evidence",
    "long_context_retrieval",
    "multilingual_translation",
    "security_privacy",
    "safety_policy",
    "robustness_adversarial",
    "reliability_calibration",
    "documentation_communication",
}

class CorePrimeQualificationV4Tests(unittest.TestCase):
    def test_v4_has_four_cases_per_new_competency(self):
        path = FIXTURES / "prime_qualification_v4.jsonl"
        cases = load_cases(path)
        counts = Counter(case.get("category", "uncategorized") for case in cases)
        self.assertEqual(set(counts), EXPECTED_CATEGORIES)
        self.assertEqual(len(cases), 4 * len(EXPECTED_CATEGORIES))
        self.assertTrue(all(count == 4 for count in counts.values()))
        self.assertTrue(all(case.get("rubric") and len(case["rubric"]) >= 3 for case in cases))
        self.assertTrue(all(len(case["messages"]) >= 2 for case in cases))
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in cases:
            self.assertTrue(case["id"].startswith("prime-v4-"))
            self.assertEqual(case["messages"][0]["role"], "system")
            self.assertEqual(case["messages"][-1]["role"], "user")

    def test_v4_ids_do_not_collide_with_existing_prime_suites(self):
        paths = [
            FIXTURES / "prime_benchmark_v1.jsonl",
            FIXTURES / "prime_qualification_v2.jsonl",
            FIXTURES / "prime_qualification_v3.jsonl",
            FIXTURES / "prime_qualification_v4.jsonl",
        ]
        all_ids = [case["id"] for path in paths for case in load_cases(path)]
        self.assertEqual(len(all_ids), len(set(all_ids)))

if __name__ == "__main__":
    unittest.main()
