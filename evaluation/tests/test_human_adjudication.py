from __future__ import annotations

import unittest

from evaluation.prepare_human_adjudication import (
    disagreement_records,
    validate_adjudications,
)


class HumanAdjudicationTests(unittest.TestCase):
    def setUp(self):
        base = {
            "candidate_id": "blind-candidate-a",
            "model_revision": "a" * 40,
            "role": "core_prime",
            "run_id": "run-1",
            "benchmark_case_id": "prime-v4-case-1",
            "evidence_started_at": "2026-11-16T10:00:00+00:00",
            "category": "reasoning",
        }
        self.grades = [
            {
                **base,
                "evaluator_id": "reviewer-1",
                "rubric_scores": [
                    {"criterion": "Correctness", "score": 4, "notes": "Correct."},
                    {"criterion": "Completeness", "score": 3, "notes": "Complete."},
                ],
            },
            {
                **base,
                "evaluator_id": "reviewer-2",
                "rubric_scores": [
                    {"criterion": "Correctness", "score": 2, "notes": "Material gap."},
                    {"criterion": "Completeness", "score": 3, "notes": "Complete."},
                ],
            },
        ]

    def test_creates_adjudication_only_for_disagreements(self):
        records = disagreement_records(self.grades)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["criterion"], "Correctness")
        self.assertEqual(
            [(x["evaluator_id"], x["score"]) for x in record["reviewer_scores"]],
            [("reviewer-1", 4), ("reviewer-2", 2)],
        )
        self.assertEqual(record["status"], "pending")
        self.assertIsNone(record["decision_score"])

    def test_validates_independent_adjudicator_and_preserves_original_scores(self):
        record = disagreement_records(self.grades)[0]
        completed = {
            **record,
            "adjudicator_id": "independent-adjudicator",
            "decision_score": 3,
            "rationale": "Reviewed the original prompt, rubric and both rationales.",
            "adjudicated_at": "2026-11-16T12:00:00+00:00",
            "status": "adjudicated",
        }
        result = validate_adjudications(self.grades, [completed])
        self.assertEqual(result[0]["reviewer_scores"], record["reviewer_scores"])
        self.assertEqual(result[0]["decision_score"], 3)

    def test_rejects_reviewer_as_adjudicator(self):
        record = disagreement_records(self.grades)[0]
        completed = {
            **record,
            "adjudicator_id": "reviewer-1",
            "decision_score": 3,
            "rationale": "A reason.",
            "adjudicated_at": "2026-11-16T12:00:00+00:00",
            "status": "adjudicated",
        }
        with self.assertRaisesRegex(ValueError, "independent"):
            validate_adjudications(self.grades, [completed])

    def test_rejects_missing_adjudication_or_modified_reviewer_scores(self):
        record = disagreement_records(self.grades)[0]
        with self.assertRaisesRegex(ValueError, "incomplete adjudication"):
            validate_adjudications(self.grades, [])
        completed = {
            **record,
            "reviewer_scores": [],
            "adjudicator_id": "independent-adjudicator",
            "decision_score": 3,
            "rationale": "A reason.",
            "adjudicated_at": "2026-11-16T12:00:00+00:00",
            "status": "adjudicated",
        }
        with self.assertRaisesRegex(ValueError, "immutable source field"):
            validate_adjudications(self.grades, [completed])


if __name__ == "__main__":
    unittest.main()
