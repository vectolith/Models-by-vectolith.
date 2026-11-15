from __future__ import annotations

import unittest

from evaluation.summarize_human_grades import GRADE_SCHEMA, build_report


class HumanGradeSummaryTests(unittest.TestCase):
    def setUp(self):
        self.evidence = [
            {
                "benchmark_case_id": f"case-{number}",
                "candidate_id": "candidate-a",
                "model_revision": "abcdef123456",
                "role": "core_prime",
                "category": "reasoning",
                "rubric": ["correct reasoning", "clear explanation"],
                "response_text": "sample response",
                "error": None,
            }
            for number in range(1, 4)
        ]
        self.grades = []
        for case in self.evidence:
            for evaluator in ("reviewer-1", "reviewer-2"):
                self.grades.append({
                    "schema_version": GRADE_SCHEMA,
                    "benchmark_case_id": case["benchmark_case_id"],
                    "candidate_id": "candidate-a",
                    "model_revision": "abcdef123456",
                    "role": "core_prime",
                    "category": "reasoning",
                    "run_id": f"run-{case['benchmark_case_id']}",
                    "evaluator_id": evaluator,
                    "evaluator_version": "rubric-v1",
                    "rubric_scores": [
                        {"criterion": "correct reasoning", "score": 4, "notes": "Correct."},
                        {"criterion": "clear explanation", "score": 3, "notes": "Clear."},
                    ],
                })

    def test_reports_per_criterion_and_never_makes_qualification_decision(self):
        report = build_report(self.evidence, self.grades)
        self.assertEqual(report["qualification_decision"], "not_made")
        self.assertEqual(len(report["criterion_results"]), 2)
        correct = next(row for row in report["criterion_results"] if row["criterion"] == "correct reasoning")
        self.assertEqual(correct["case_count"], 3)
        self.assertEqual(correct["evaluator_count"], 2)
        self.assertEqual(correct["mean_score_0_to_4"], 4.0)
        self.assertEqual(correct["status"], "rubric_threshold_met")

    def test_insufficient_independent_evaluators_is_not_pass(self):
        report = build_report(self.evidence, self.grades[:3], min_evaluators=2)
        self.assertTrue(all(row["status"] == "insufficient_independent_evaluators" for row in report["criterion_results"]))

    def test_requires_every_rubric_criterion(self):
        broken = [dict(self.grades[0])]
        broken[0]["rubric_scores"] = broken[0]["rubric_scores"][:1]
        with self.assertRaisesRegex(ValueError, "every rubric criterion"):
            build_report(self.evidence, broken)

    def test_rejects_duplicate_grade_from_same_evaluator(self):
        duplicate = self.grades + [dict(self.grades[0])]
        with self.assertRaisesRegex(ValueError, "duplicate grade"):
            build_report(self.evidence, duplicate)

    def test_rejects_unknown_criterion_and_invalid_score(self):
        unknown = [dict(self.grades[0])]
        unknown[0]["rubric_scores"] = [{"criterion": "not in evidence", "score": 4}]
        with self.assertRaisesRegex(ValueError, "unknown rubric criterion"):
            build_report(self.evidence, unknown)
        invalid = [dict(self.grades[0])]
        invalid[0]["rubric_scores"] = [
            {"criterion": "correct reasoning", "score": 5},
            {"criterion": "clear explanation", "score": 3},
        ]
        with self.assertRaisesRegex(ValueError, "numeric 0..4"):
            build_report(self.evidence, invalid)


if __name__ == "__main__":
    unittest.main()
