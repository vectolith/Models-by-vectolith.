import unittest

from vectolith_runtime.distillation import (
    IndependenceEvidence,
    TeacherContribution,
    TeacherPanel,
    validate_panels,
)


REVISION = "a" * 40


def teacher(index: int, *, delta: float = 0.02) -> TeacherContribution:
    return TeacherContribution(
        teacher_id=f"teacher-{index}",
        provider="test-provider",
        immutable_revision=REVISION,
        license_id="Apache-2.0",
        training_output_permission_verified=True,
        assigned_competencies=("reasoning",),
        dataset_shard_id=f"shard-{index}",
        accepted_examples=100,
        accepted_tokens=10000,
        ablation_quality_delta=delta,
        quality_score=0.9,
        p50_latency_ms=450,
        cost_per_million_tokens_usd=0.25,
    )


def panel(*teachers: TeacherContribution) -> TeacherPanel:
    return TeacherPanel("core_prime", REVISION, tuple(teachers), "run-001")


class DistillationValidationTests(unittest.TestCase):
    def test_four_contributing_teachers_are_accepted(self):
        panel(*[teacher(i) for i in range(4)]).require_valid()

    def test_three_teachers_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least four"):
            panel(*[teacher(i) for i in range(3)]).require_valid()

    def test_duplicate_teacher_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            panel(teacher(1), teacher(1), teacher(2), teacher(3)).require_valid()

    def test_teacher_without_permission_or_contribution_is_rejected(self):
        invalid = TeacherContribution(
            teacher_id="teacher-x",
            provider="provider",
            immutable_revision=REVISION,
            license_id="unknown",
            training_output_permission_verified=False,
            assigned_competencies=("coding",),
            dataset_shard_id="shard-x",
            accepted_examples=0,
            accepted_tokens=0,
            ablation_quality_delta=0,
            quality_score=0.9,
            p50_latency_ms=450,
            cost_per_million_tokens_usd=0.25,
        )
        errors = invalid.validate()
        self.assertTrue(any("permission" in error for error in errors))
        self.assertTrue(any("positive" in error for error in errors))
        self.assertTrue(any("ablation" in error for error in errors))

    def test_student_independence_requires_teacher_free_execution(self):
        evidence = IndependenceEvidence(
            student_checkpoint_sha256="b" * 64,
            teacher_endpoints_disabled=True,
            teacher_credentials_absent=True,
            teacher_calls_observed=0,
            required_capability_checks_passed=True,
        )
        evidence.require_valid()

    def test_teacher_dependency_fails_independence_gate(self):
        evidence = IndependenceEvidence(
            student_checkpoint_sha256="b" * 64,
            teacher_endpoints_disabled=False,
            teacher_credentials_absent=False,
            teacher_calls_observed=1,
            required_capability_checks_passed=True,
            inference_dependencies=("teacher-api",),
        )
        with self.assertRaisesRegex(ValueError, "independence gate failed"):
            evidence.require_valid()

    def test_duplicate_run_ids_are_rejected(self):
        valid = panel(*[teacher(i) for i in range(4)])
        with self.assertRaisesRegex(ValueError, "duplicate training run"):
            validate_panels((valid, valid))


if __name__ == "__main__":
    unittest.main()
