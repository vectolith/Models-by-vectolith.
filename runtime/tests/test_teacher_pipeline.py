import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from vectolith_runtime.teacher_pipeline import (
    QualifiedTeacher, TeacherEndpoint, TeacherQualification, TeachingTask, qualify_teacher, finalize_teacher_panel, select_teacher_panel,
)
from vectolith_runtime.distillation import IndependenceEvidence, TeacherContribution
from vectolith_runtime.independent_evaluation import (
    EvaluationCase, evaluate_release, leave_one_teacher_out, run_capability_suite,
)


REV = "a" * 40


def candidate(index, competencies=("reasoning",)):
    qualification = TeacherQualification(
        teacher_id=f"teacher-{index}", provider="local",
        immutable_revision=REV, license_id="Apache-2.0",
        training_output_permission_verified=True,
        output_training_permission_evidence="approved-for-training",
        assigned_competencies=competencies, quality_score=0.9,
        p50_latency_ms=100, cost_per_million_tokens_usd=0,
        qualification_suite="suite-v1", qualification_passed=True,
    )
    endpoint = TeacherEndpoint(f"teacher-{index}", f"model-{index}", "http://localhost:8000/v1", "TEST_KEY", REV)
    return QualifiedTeacher(qualification, endpoint)

class TeacherPipelineTests(unittest.TestCase):
    def test_selects_four_or_more_distinct_qualified_teachers(self):
        candidates = [candidate(i, ("reasoning", "planning") if i == 0 else ("reasoning",)) for i in range(5)]
        panel = select_teacher_panel("core_prime", REV, "run-a", candidates, required_competencies={"reasoning", "planning"})
        self.assertGreaterEqual(len(panel.teachers), 4)
        self.assertEqual(len({t.endpoint.teacher_id for t in panel.teachers}), len(panel.teachers))

    def test_refuses_fewer_than_four_qualified_teachers(self):
        with self.assertRaisesRegex(ValueError, "only 3"):
            select_teacher_panel("core_prima", REV, "run-b", [candidate(i) for i in range(3)], required_competencies={"reasoning"})

    def test_rejects_panel_with_missing_competency_coverage(self):
        with self.assertRaisesRegex(ValueError, "does not cover"):
            select_teacher_panel("core_prime", REV, "run-c", [candidate(i) for i in range(4)], required_competencies={"reasoning", "multilingual"})

    def test_keyword_overlap_never_scores_capability(self):
        result = run_capability_suite(lambda prompt: "reasoning planning but incorrect", [
            EvaluationCase("1", "reasoning", "solve", ("reasoning",)),
            EvaluationCase("2", "planning", "plan", ("planning",)),
        ])
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["verified_case_count"], 0)
        self.assertEqual(result["unscored_case_count"], 2)
        self.assertNotIn("pass_rate", result)
        self.assertEqual(result["evaluation_disposition"], "incomplete_requires_human_review")

    def test_criterion_verifier_requires_auditable_evidence(self):
        from vectolith_runtime.independent_evaluation import VerificationResult
        def verifier(case, output):
            return VerificationResult("verified_pass", "unit-test-verifier/1", (
                {"type": "test_report", "reference": "artifact://tests/123", "sha256": "a" * 64},
            ), confidence=1.0)
        result = run_capability_suite(lambda prompt: "output", [
            EvaluationCase("1", "coding", "implement")
        ], verifier=verifier)
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["pass_rate"], 1.0)
        self.assertEqual(result["quality_decision"], "not_made")

    def test_verifier_without_evidence_is_rejected(self):
        from vectolith_runtime.independent_evaluation import VerificationResult
        with self.assertRaisesRegex(ValueError, "evidence is required"):
            run_capability_suite(lambda prompt: "output", [
                EvaluationCase("1", "reasoning", "solve")
            ], verifier=lambda case, output: VerificationResult(
                "verified_pass", "unsubstantiated", ()
            ))



    def test_finalize_panel_requires_actual_contributions_and_ablation(self):
        assignment = select_teacher_panel(
            "core_prime", REV, "run-final",
            [candidate(i) for i in range(4)],
            required_competencies={"reasoning"},
        )
        report = {
            "release_eligible": True,
            "leave_one_teacher_out_deltas": {f"teacher-{i}": 0.02 for i in range(4)},
        }
        panel = finalize_teacher_panel(
            assignment,
            accepted_examples_by_teacher={f"teacher-{i}": 25 for i in range(4)},
            accepted_tokens_by_teacher={f"teacher-{i}": 5000 for i in range(4)},
            dataset_shard_id="core-prime-run-final",
            ablation_report=report,
        )
        self.assertEqual(len(panel.teachers), 4)
        self.assertEqual(sum(item.accepted_examples for item in panel.teachers), 100)
        with self.assertRaisesRegex(ValueError, "positive leave-one-teacher-out"):
            finalize_teacher_panel(
                assignment,
                accepted_examples_by_teacher={f"teacher-{i}": 25 for i in range(4)},
                accepted_tokens_by_teacher={f"teacher-{i}": 5000 for i in range(4)},
                dataset_shard_id="core-prime-run-final",
                ablation_report={"release_eligible": False, "leave_one_teacher_out_deltas": {}},
            )

    def test_release_gate_blocks_missing_teacher_independence(self):
        contributions = tuple(TeacherContribution(
            teacher_id=f"teacher-{i}", provider="local", immutable_revision=REV,
            license_id="Apache-2.0", training_output_permission_verified=True,
            assigned_competencies=("reasoning",), dataset_shard_id=f"shard-{i}",
            accepted_examples=10, accepted_tokens=1000, ablation_quality_delta=0.1,
            quality_score=0.9, p50_latency_ms=100, cost_per_million_tokens_usd=0,
        ) for i in range(4))
        evidence = IndependenceEvidence(
            student_checkpoint_sha256="b" * 64, teacher_endpoints_disabled=False,
            teacher_credentials_absent=True, teacher_calls_observed=0,
            required_capability_checks_passed=True,
        )
        decision = evaluate_release(
            capability_report={"pass_rate": 0.95}, minimum_capability_pass_rate=0.9,
            ablation_report={"release_eligible": True, "leave_one_teacher_out_deltas": {
                f"teacher-{i}": 0.01 for i in range(4)
            }},
            independence_evidence=evidence, teacher_contributions=contributions,
        )
        self.assertFalse(decision["release_approved"])
        self.assertTrue(any("endpoints must be disabled" in reason for reason in decision["blocking_reasons"]))

    def test_ablation_requires_four_and_detects_noncontributor(self):
        result = leave_one_teacher_out(lambda omitted: 0.8 if omitted else 0.9, ("a", "b", "c", "d"))
        self.assertTrue(result["release_eligible"])
        failed = leave_one_teacher_out(lambda omitted: 0.9 if omitted == "d" else (0.8 if omitted else 0.9), ("a", "b", "c", "d"))
        self.assertFalse(failed["release_eligible"])


    def test_keyword_rich_inference_is_not_teacher_qualification(self):
        endpoint = TeacherEndpoint("candidate-x", "model-x", "http://localhost:8000/v1", "TEST_KEY", REV)
        task = TeachingTask("case-1", "factuality", "What is the capital of France?", "Paris;correct country")
        with patch("vectolith_runtime.teacher_pipeline.OpenAICompatibleTeacher.generate",
                   return_value="Paris is the capital of France, but the Moon is made of cheese."):
            candidate = qualify_teacher(
                endpoint, provider="local", license_id="Apache-2.0",
                training_output_permission_verified=True,
                output_training_permission_evidence="permission-record",
                competencies=("factuality",), benchmark_tasks=[task],
            )
        self.assertFalse(candidate.qualification.qualification_passed)
        self.assertIsNone(candidate.qualification.quality_score)
        self.assertEqual(len(candidate.response_evidence), 1)
        self.assertEqual(candidate.response_evidence[0]["response"], "Paris is the capital of France, but the Moon is made of cheese.")
        self.assertEqual(len(candidate.response_evidence[0]["response_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
