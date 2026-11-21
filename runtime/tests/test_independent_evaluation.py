"""Tests for the evidence-backed evaluation gate.

The rule this module encodes is "keyword overlap is never a quality score", so
the tests here push on the evidence contract instead: a report must only carry
a pass rate when a verifier actually scored every case, and independence must
only pass when the checkpoint genuinely stands alone.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vectolith_runtime import independent_evaluation as ie
from vectolith_runtime.independent_evaluation import (
    EvaluationCase,
    VerificationResult,
    evaluate_release,
    load_student_generator,
    run_capability_suite,
    run_teacher_disabled_check,
    write_release_report,
)
from vectolith_runtime.distillation import IndependenceEvidence, TeacherContribution

DIGEST = "a" * 64
GOOD_EVIDENCE = ({"type": "unit-test", "reference": "case-1", "sha256": DIGEST},)


def _verified(case, output, status="verified_pass"):
    return VerificationResult(status, "exact-match/1.0", GOOD_EVIDENCE, 1.0)


class VerificationResultValidationTests(unittest.TestCase):
    def test_accepts_well_formed_evidence(self):
        self.assertEqual(VerificationResult("verified_pass", "m/1", GOOD_EVIDENCE, 0.5).validate(), [])

    def test_rejects_unknown_status(self):
        errors = VerificationResult("passed", "m/1", GOOD_EVIDENCE).validate()
        self.assertIn("invalid verifier status", errors)

    def test_rejects_blank_method(self):
        self.assertIn("verifier method/version is required", VerificationResult("verified_pass", "   ", GOOD_EVIDENCE).validate())

    def test_requires_evidence(self):
        self.assertIn("verifier evidence is required", VerificationResult("verified_pass", "m/1", ()).validate())

    def test_evidence_needs_type_and_reference(self):
        bad = ({"type": "x", "sha256": DIGEST},)
        self.assertIn("evidence[0] requires type and reference", VerificationResult("verified_pass", "m/1", bad).validate())

    def test_evidence_needs_sha256(self):
        bad = ({"type": "x", "reference": "y", "sha256": "abc"},)
        self.assertIn("evidence[0] requires a SHA-256 digest", VerificationResult("verified_pass", "m/1", bad).validate())

    def test_sha256_with_uppercase_hex_is_accepted(self):
        upper = ({"type": "x", "reference": "y", "sha256": "A" * 64},)
        self.assertEqual(VerificationResult("verified_pass", "m/1", upper).validate(), [])

    def test_rejects_out_of_range_confidence(self):
        self.assertIn("confidence must be between 0 and 1", VerificationResult("verified_pass", "m/1", GOOD_EVIDENCE, 1.5).validate())

    def test_rejects_boolean_confidence(self):
        self.assertIn("confidence must be between 0 and 1", VerificationResult("verified_pass", "m/1", GOOD_EVIDENCE, True).validate())

    def test_confidence_is_optional(self):
        self.assertEqual(VerificationResult("inconclusive", "m/1", GOOD_EVIDENCE).validate(), [])


class VerificationNormalisationTests(unittest.TestCase):
    def test_mapping_is_converted_and_then_validated(self):
        result = ie._verification({"status": "verified_pass", "method": "m/1", "evidence": list(GOOD_EVIDENCE)})
        self.assertIsInstance(result, VerificationResult)
        self.assertEqual(result.status, "verified_pass")

    def test_mapping_without_evidence_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            ie._verification({"status": "verified_pass", "method": "m/1"})
        self.assertIn("invalid verifier evidence", str(ctx.exception))

    def test_other_types_are_rejected(self):
        with self.assertRaises(TypeError):
            ie._verification("verified_pass")


class CapabilitySuiteTests(unittest.TestCase):
    def test_empty_suite_is_rejected(self):
        with self.assertRaises(ValueError):
            run_capability_suite(lambda p: "x", [])

    def test_duplicate_case_ids_are_rejected(self):
        cases = [EvaluationCase("dup", "math", "a"), EvaluationCase("dup", "math", "b")]
        with self.assertRaises(ValueError):
            run_capability_suite(lambda p: "x", cases)

    def test_without_verifier_nothing_is_scored(self):
        report = run_capability_suite(lambda p: "answer", [EvaluationCase("c1", "math", "q")])
        self.assertNotIn("pass_rate", report)
        self.assertEqual(report["evaluation_disposition"], "incomplete_requires_human_review")
        self.assertEqual(report["unscored_case_count"], 1)
        self.assertEqual(report["quality_decision"], "not_made")
        self.assertEqual(report["cases"][0]["status"], "requires_human_review")
        self.assertEqual(report["cases"][0]["output_sha256"], hashlib.sha256(b"answer").hexdigest())

    def test_fully_verified_suite_reports_pass_rate(self):
        cases = [EvaluationCase("c1", "math", "q1"), EvaluationCase("c2", "math", "q2")]
        report = run_capability_suite(lambda p: "answer", cases, lambda c, o: _verified(c, o, "verified_fail" if c.case_id == "c2" else "verified_pass"))
        self.assertEqual(report["pass_rate"], 0.5)
        self.assertEqual(report["passed"], 1)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["evaluation_disposition"], "complete_with_verifier_evidence")

    def test_unscored_case_removes_pass_rate_entirely(self):
        cases = [EvaluationCase("c1", "math", "q1"), EvaluationCase("c2", "math", "q2")]

        def verifier(case, output):
            if case.case_id == "c2":
                return VerificationResult("inconclusive", "m/1", GOOD_EVIDENCE)
            return _verified(case, output)

        report = run_capability_suite(lambda p: "answer", cases, verifier)
        self.assertNotIn("pass_rate", report)
        self.assertEqual(report["verified_case_count"], 1)
        self.assertEqual(report["unscored_case_count"], 1)

    def test_mapping_verifier_output_is_accepted(self):
        report = run_capability_suite(
            lambda p: "answer",
            [EvaluationCase("c1", "math", "q")],
            lambda c, o: {"status": "verified_pass", "method": "m/1", "evidence": list(GOOD_EVIDENCE)},
        )
        self.assertEqual(report["pass_rate"], 1.0)
        self.assertEqual(report["cases"][0]["scoring_method"], "m/1")

    def test_non_text_generator_output_is_rejected(self):
        with self.assertRaises(TypeError) as ctx:
            run_capability_suite(lambda p: None, [EvaluationCase("c1", "math", "q")])
        self.assertIn("non-text output", str(ctx.exception))

    def test_invalid_verifier_evidence_surfaces(self):
        with self.assertRaises(ValueError):
            run_capability_suite(
                lambda p: "answer",
                [EvaluationCase("c1", "math", "q")],
                lambda c, o: VerificationResult("verified_pass", "m/1", ()),
            )


class TeacherDisabledCheckTests(unittest.TestCase):
    def _checkpoint(self, tmp: str, files: dict[str, bytes]) -> str:
        root = Path(tmp) / "checkpoint"
        root.mkdir()
        for name, payload in files.items():
            (root / name).write_bytes(payload)
        return str(root)

    def test_removes_teacher_credentials_and_digests_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._checkpoint(tmp, {"model.bin": b"weights", "config.json": b"{}"})
            env = {"TEACHER_API_KEY": "secret", "OPENAI_BASE_URL": "https://teacher"}
            with mock.patch.dict(os.environ, env, clear=False):
                evidence = run_teacher_disabled_check(
                    checkpoint_dir=root,
                    endpoint_env_names=("OPENAI_BASE_URL",),
                    credential_env_names=("TEACHER_API_KEY",),
                    inference_dependencies=(),
                    capability_passed=True,
                    teacher_calls_observed=0,
                )
                self.assertNotIn("TEACHER_API_KEY", os.environ)
                self.assertNotIn("OPENAI_BASE_URL", os.environ)
            digest = hashlib.sha256()
            for path in sorted(p for p in Path(root).rglob("*") if p.is_file()):
                digest.update(str(path.relative_to(root)).encode())
                digest.update(path.read_bytes())
            self.assertEqual(evidence.student_checkpoint_sha256, digest.hexdigest())
            self.assertEqual(evidence.validate(), [])

    def test_digest_covers_file_names_not_just_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._checkpoint(tmp, {"a.bin": b"same"})
            first = run_teacher_disabled_check(checkpoint_dir=root, endpoint_env_names=(), credential_env_names=(),
                                              inference_dependencies=(), capability_passed=True, teacher_calls_observed=0)
            (Path(root) / "a.bin").rename(Path(root) / "b.bin")
            second = run_teacher_disabled_check(checkpoint_dir=root, endpoint_env_names=(), credential_env_names=(),
                                               inference_dependencies=(), capability_passed=True, teacher_calls_observed=0)
        self.assertNotEqual(first.student_checkpoint_sha256, second.student_checkpoint_sha256)

    def test_teacher_calls_fail_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._checkpoint(tmp, {"model.bin": b"w"})
            with self.assertRaises(ValueError) as ctx:
                run_teacher_disabled_check(checkpoint_dir=root, endpoint_env_names=(), credential_env_names=(),
                                           inference_dependencies=(), capability_passed=True, teacher_calls_observed=2)
        self.assertIn("teacher calls", str(ctx.exception))

    def test_teacher_inference_dependencies_fail_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._checkpoint(tmp, {"model.bin": b"w"})
            with self.assertRaises(ValueError) as ctx:
                run_teacher_disabled_check(checkpoint_dir=root, endpoint_env_names=(), credential_env_names=(),
                                           inference_dependencies=("teacher-api",), capability_passed=True, teacher_calls_observed=0)
        self.assertIn("inference dependencies", str(ctx.exception))

    def test_missing_checkpoint_directory_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                run_teacher_disabled_check(checkpoint_dir=str(Path(tmp) / "nope"), endpoint_env_names=(),
                                           credential_env_names=(), inference_dependencies=(),
                                           capability_passed=True, teacher_calls_observed=0)

    def test_empty_checkpoint_directory_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            with self.assertRaises(ValueError):
                run_teacher_disabled_check(checkpoint_dir=str(empty), endpoint_env_names=(), credential_env_names=(),
                                           inference_dependencies=(), capability_passed=True, teacher_calls_observed=0)


class StudentLoaderTests(unittest.TestCase):
    def test_missing_training_extra_gives_actionable_error(self):
        blocked = {"torch": None, "transformers": None}
        with mock.patch.dict(sys.modules, blocked):
            with self.assertRaises(RuntimeError) as ctx:
                load_student_generator("/tmp/does-not-exist")
        self.assertIn("vectolith-runtime[training]", str(ctx.exception))


class ReleaseReportTests(unittest.TestCase):
    def test_write_release_report_round_trips_unicode(self):
        report = {"release_approved": False, "blocking_reasons": ["naïve claim — unverified"]}
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "release.json"
            write_release_report(target, report)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), report)
            self.assertIn("naïve", target.read_text(encoding="utf-8"))

    def test_write_release_report_leaves_no_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "release.json"
            write_release_report(target, {"release_approved": True})
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["release.json"])


class EvaluateReleaseTests(unittest.TestCase):
    TEACHERS = ("teacher-a", "teacher-b", "teacher-c", "teacher-d")

    def _contribution(self, teacher_id: str, delta: float = 0.05) -> TeacherContribution:
        return TeacherContribution(
            teacher_id=teacher_id,
            provider="fixture",
            immutable_revision="b" * 40,
            license_id="CC-BY-4.0",
            training_output_permission_verified=True,
            assigned_competencies=("reasoning",),
            dataset_shard_id=f"shard-{teacher_id}",
            accepted_examples=100,
            accepted_tokens=1000,
            ablation_quality_delta=delta,
            quality_score=0.8,
            p50_latency_ms=250.0,
            cost_per_million_tokens_usd=0.0,
        )

    def _evidence(self) -> IndependenceEvidence:
        return IndependenceEvidence(
            student_checkpoint_sha256=DIGEST,
            teacher_endpoints_disabled=True,
            teacher_credentials_absent=True,
            teacher_calls_observed=0,
            required_capability_checks_passed=True,
        )

    def _report(self, pass_rate=0.9, delta=0.05):
        return {
            "capability_report": {"pass_rate": pass_rate},
            "minimum_capability_pass_rate": 0.8,
            "ablation_report": {
                "leave_one_teacher_out_deltas": {t: delta for t in self.TEACHERS},
                "release_eligible": True,
            },
            "independence_evidence": self._evidence(),
            "teacher_contributions": tuple(self._contribution(t, delta) for t in self.TEACHERS),
        }

    def test_clean_release_is_approved(self):
        result = evaluate_release(**self._report())
        self.assertTrue(result["release_approved"], result["blocking_reasons"])
        self.assertEqual(result["blocking_reasons"], [])
        self.assertEqual(result["teacher_count"], 4)
        self.assertEqual(result["capability_pass_rate"], 0.9)

    def test_low_pass_rate_blocks_release(self):
        result = evaluate_release(**self._report(pass_rate=0.5))
        self.assertFalse(result["release_approved"])
        self.assertIn("capability pass rate is below the release threshold", result["blocking_reasons"])

    def test_unscored_capability_report_blocks_release(self):
        result = evaluate_release(**self._report(pass_rate=None))
        self.assertFalse(result["release_approved"])
        self.assertIn("capability evaluation is unscored or incomplete; criterion-specific evidence and human review are required", result["blocking_reasons"])

    def test_boolean_pass_rate_is_treated_as_unscored(self):
        result = evaluate_release(**self._report(pass_rate=True))
        self.assertFalse(result["release_approved"])
        self.assertIsNone(result["capability_pass_rate"])

    def test_too_few_teachers_blocks_release(self):
        report = self._report()
        report["ablation_report"]["leave_one_teacher_out_deltas"] = {"teacher-a": 0.05}
        report["teacher_contributions"] = (self._contribution("teacher-a"),)
        result = evaluate_release(**report)
        self.assertIn("fewer than four teacher contributions are recorded", result["blocking_reasons"])

    def test_duplicate_teacher_identities_block_release(self):
        report = self._report()
        report["teacher_contributions"] = tuple(self._contribution("teacher-a") for _ in range(4))
        report["ablation_report"]["leave_one_teacher_out_deltas"] = {"teacher-a": 0.05}
        result = evaluate_release(**report)
        self.assertIn("teacher contributions do not come from four distinct identities", result["blocking_reasons"])

    def test_ablation_evidence_must_match_contributing_teachers(self):
        report = self._report()
        report["ablation_report"]["leave_one_teacher_out_deltas"] = {t: 0.05 for t in self.TEACHERS[:3]}
        result = evaluate_release(**report)
        self.assertIn("ablation evidence does not cover exactly the contributing teachers", result["blocking_reasons"])

    def test_non_positive_delta_blocks_release(self):
        report = self._report()
        report["ablation_report"]["leave_one_teacher_out_deltas"]["teacher-b"] = 0.0
        report["teacher_contributions"] = tuple(
            self._contribution(t, 0.0 if t == "teacher-b" else 0.05) for t in self.TEACHERS
        )
        result = evaluate_release(**report)
        self.assertIn("each teacher must have a positive measured leave-one-out delta", result["blocking_reasons"])

    def test_recorded_delta_must_match_measured_delta(self):
        report = self._report()
        report["teacher_contributions"] = tuple(
            self._contribution(t, 0.05 if t != "teacher-c" else 0.09) for t in self.TEACHERS
        )
        result = evaluate_release(**report)
        self.assertIn("teacher-c: recorded ablation delta does not match evaluation evidence", result["blocking_reasons"])

    def test_invalid_independence_evidence_blocks_release(self):
        report = self._report()
        report["independence_evidence"] = IndependenceEvidence(
            student_checkpoint_sha256="not-a-digest",
            teacher_endpoints_disabled=True,
            teacher_credentials_absent=True,
            teacher_calls_observed=0,
            required_capability_checks_passed=True,
        )
        result = evaluate_release(**report)
        self.assertFalse(result["release_approved"])
        self.assertIn("student checkpoint must have a SHA-256 digest", result["blocking_reasons"])

    def test_invalid_teacher_contribution_blocks_release(self):
        report = self._report()
        broken = TeacherContribution(
            teacher_id="teacher-a", provider="fixture", immutable_revision="short", license_id="",
            training_output_permission_verified=False, assigned_competencies=(), dataset_shard_id="",
            accepted_examples=0, accepted_tokens=0, ablation_quality_delta=0.05, quality_score=0.8,
            p50_latency_ms=1.0, cost_per_million_tokens_usd=0.0,
        )
        report["teacher_contributions"] = (broken,) + tuple(self._contribution(t) for t in self.TEACHERS[1:])
        result = evaluate_release(**report)
        self.assertFalse(result["release_approved"])
        self.assertTrue(any("immutable_revision" in reason for reason in result["blocking_reasons"]))
