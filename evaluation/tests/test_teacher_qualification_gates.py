from __future__ import annotations

import copy
import unittest

from evaluation.teacher_qualification_gates import evaluate_candidate, evaluate_cohort


def valid_manifest(candidate_id="candidate-a"):
    sha = "a" * 64
    revision = "b" * 40
    return {
        "schema_version": "vectolith-teacher-qualification-candidate/1.0",
        "candidate_id": candidate_id,
        "immutable_revision": revision,
        "gates": {
            "snapshot": {
                "status": "verified",
                "immutable_revision": revision,
                "manifest_sha256": sha,
            },
            "license_review": {
                "status": "approved",
                "license_text_sha256": sha,
                "legal_reviewer_id": "legal-reviewer",
                "reviewed_at": "2026-11-16T10:00:00+00:00",
                "evidence_uri": "https://example.invalid/license-review-evidence",
            },
            "loader_compatibility": {
                "status": "passed",
                "tested_revision": revision,
                "model_class": "AutoModelForCausalLM",
                "runtime_versions": {"torch": "2.8.0", "transformers": "5.0.0"},
                "remote_code": {"status": "disabled"},
            },
            "real_inference": {
                "status": "completed",
                "tested_revision": revision,
                "workflow_run_id": "run-123",
                "internal_run_id": "internal-run-123",
                "expected_response_count": 180,
                "response_count": 180,
                "error_count": 0,
                "artifact_sha256": sha,
            },
            "resource_measurement": {
                "status": "recorded",
                "runner_type": "ubuntu-latest",
                "device": "cpu",
                "peak_rss_bytes": 1024,
                "mean_latency_seconds": 1.5,
                "compute_record_sha256": sha,
            },
            "grading": {
                "status": "passed",
                "expected_response_count": 180,
                "graded_response_count": 180,
                "grade_report_sha256": sha,
                "rubric_version": "prime-rubric-v1",
                "review_method": "independent_human",
                "independent_reviewer_ids": ["human-reviewer-1", "human-reviewer-2"],
                "independence_attestation_sha256": sha,
                "agreement_report_sha256": sha,
                "adjudication_report_sha256": sha,
            },
            "safety_review": {
                "status": "passed",
                "reviewer_id": "safety-reviewer",
                "report_sha256": sha,
            },
            "holdout": {
                "status": "passed",
                "case_count": 56,
                "leakage_audit_passed": True,
                "audit_sha256": sha,
            },
            "corpus_integrity": {
                "status": "passed",
                "corpus_sha256": sha,
                "duplicate_count": 0,
                "provenance_verified": True,
            },
            "training_output_permission": {
                "status": "granted",
                "document_sha256": sha,
                "authorized_by": "rights-holder",
                "authorized_at": "2026-11-16T11:00:00+00:00",
            },
        },
    }


class TeacherQualificationGateTests(unittest.TestCase):
    def test_all_independent_gates_are_required_for_candidate_qualification(self):
        result = evaluate_candidate(valid_manifest())
        self.assertEqual(result["qualification_status"], "qualified")
        self.assertEqual(result["failed_gates"], [])
        self.assertEqual(result["gate_count"], 10)
        self.assertFalse(result["training_started"])
        self.assertEqual(result["teacher_ranking"], "not_performed")
        self.assertEqual(result["teacher_selection"], "not_performed")

    def test_inference_success_alone_cannot_qualify_candidate(self):
        manifest = valid_manifest()
        for name in manifest["gates"]:
            if name not in ("real_inference", "snapshot"):
                manifest["gates"][name] = {}
        result = evaluate_candidate(manifest)
        self.assertEqual(result["qualification_status"], "not_qualified")
        self.assertTrue(any(x.startswith("license_review:") for x in result["failed_gates"]))
        self.assertTrue(any(x.startswith("grading:") for x in result["failed_gates"]))
        self.assertTrue(any(x.startswith("training_output_permission:") for x in result["failed_gates"]))

    def test_license_and_training_output_permission_are_separate_gates(self):
        manifest = valid_manifest()
        manifest["gates"]["license_review"]["status"] = "pending"
        manifest["gates"]["training_output_permission"]["status"] = "not_verified"
        result = evaluate_candidate(manifest)
        self.assertTrue(any(x.startswith("license_review:") for x in result["failed_gates"]))
        self.assertTrue(any(x.startswith("training_output_permission:") for x in result["failed_gates"]))

    def test_grading_requires_independent_human_review_agreement_and_adjudication(self):
        manifest = valid_manifest()
        self.assertEqual(evaluate_candidate(manifest)["qualification_status"], "qualified")
        cases = [
            ("review_method", "ai", "grading:review_method_not_independent_human"),
            ("independent_reviewer_ids", ["human-1"], "grading:independent_reviewers_insufficient_or_invalid"),
            ("independence_attestation_sha256", "bad", "grading:independence_attestation_missing"),
            ("agreement_report_sha256", "bad", "grading:agreement_report_missing"),
            ("adjudication_report_sha256", "bad", "grading:adjudication_report_missing"),
        ]
        for field, value, expected in cases:
            mutated = valid_manifest()
            mutated["gates"]["grading"][field] = value
            result = evaluate_candidate(mutated)
            self.assertEqual(result["qualification_status"], "not_qualified")
            self.assertIn(expected, result["failed_gates"])
        mutated = valid_manifest()
        mutated["gates"]["grading"]["independent_reviewer_ids"] = ["candidate-a", "human-2"]
        self.assertIn("grading:independent_reviewers_insufficient_or_invalid", evaluate_candidate(mutated)["failed_gates"])

    def test_cohort_reviewers_must_be_independent_of_teacher_cohort(self):
        manifests = [valid_manifest(f"candidate-{n}") for n in range(4)]
        manifests[0]["gates"]["grading"]["independent_reviewer_ids"] = ["candidate-1", "human-2"]
        result = evaluate_cohort(manifests, required_teachers=4)
        self.assertEqual(result["cohort_gate"], "blocked")
        self.assertIn("grading:reviewers_not_independent_of_teacher_cohort", result["candidate_results"][0]["failed_gates"])

    def test_revision_mismatch_and_incomplete_grading_block_qualification(self):
        manifest = valid_manifest()
        manifest["gates"]["loader_compatibility"]["tested_revision"] = "c" * 40
        manifest["gates"]["grading"]["graded_response_count"] = 179
        result = evaluate_candidate(manifest)
        self.assertEqual(result["qualification_status"], "not_qualified")
        self.assertTrue(any("revision_mismatch" in x for x in result["failed_gates"]))
        self.assertTrue(any("grading:coverage_incomplete" in x for x in result["failed_gates"]))

    def test_four_teacher_cohort_gate_counts_without_ranking_or_selecting(self):
        three = [valid_manifest(f"candidate-{n}") for n in range(3)]
        blocked = evaluate_cohort(three, required_teachers=4)
        self.assertEqual(blocked["cohort_gate"], "blocked")
        self.assertEqual(blocked["qualified_teacher_count"], 3)
        four = [valid_manifest(f"candidate-{n}") for n in range(4)]
        passed = evaluate_cohort(four, required_teachers=4)
        self.assertEqual(passed["cohort_gate"], "passed")
        self.assertEqual(passed["qualified_teacher_count"], 4)
        self.assertEqual(passed["teacher_ranking"], "not_performed")
        self.assertEqual(passed["teacher_selection"], "not_performed")
        self.assertFalse(passed["training_started"])

    def test_cohort_cannot_lower_the_four_teacher_requirement(self):
        with self.assertRaisesRegex(ValueError, "at least four"):
            evaluate_cohort([valid_manifest()], required_teachers=3)

    def test_duplicate_candidate_entries_block_the_cohort(self):
        manifest = valid_manifest()
        result = evaluate_cohort([manifest, copy.deepcopy(manifest)], required_teachers=4)
        self.assertEqual(result["cohort_gate"], "blocked")
        self.assertTrue(result["duplicate_candidate_ids"])


if __name__ == "__main__":
    unittest.main()
