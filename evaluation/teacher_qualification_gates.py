#!/usr/bin/env python3
"""Fail-closed candidate and four-teacher cohort qualification gates."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "vectolith-teacher-qualification-candidate/1.0"
SHA_LENGTH = 64


def valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) == SHA_LENGTH
        and all(char in "0123456789abcdef" for char in value.lower())
    )


def valid_time(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def evaluate_candidate(manifest: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if manifest.get("schema_version") != SCHEMA:
        failures.append("unsupported_schema")
    candidate_id = manifest.get("candidate_id")
    revision = manifest.get("immutable_revision")
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        failures.append("candidate_id_missing")
    if not isinstance(revision, str) or len(revision) != 40 or any(
        char not in "0123456789abcdef" for char in revision.lower()
    ):
        failures.append("immutable_revision_invalid")

    gates = manifest.get("gates")
    if not isinstance(gates, dict):
        gates = {}
        failures.append("gates_object_missing")

    def require(name: str, condition: bool, reason: str) -> None:
        if not condition:
            failures.append(f"{name}:{reason}")

    def gate(name: str) -> dict[str, Any]:
        value = gates.get(name)
        if not isinstance(value, dict):
            failures.append(f"{name}:gate_object_missing")
            return {}
        return value

    snapshot = gate("snapshot")
    require("snapshot", snapshot.get("status") == "verified", "not_verified")
    require("snapshot", snapshot.get("immutable_revision") == revision, "revision_mismatch")
    require("snapshot", valid_sha(snapshot.get("manifest_sha256")), "manifest_digest_missing")

    legal = gate("license_review")
    require("license_review", legal.get("status") == "approved", "not_approved")
    require("license_review", valid_sha(legal.get("license_text_sha256")), "license_text_digest_missing")
    require("license_review", bool(legal.get("legal_reviewer_id")), "legal_reviewer_missing")
    require("license_review", valid_time(legal.get("reviewed_at")), "review_timestamp_invalid")
    require("license_review", bool(legal.get("evidence_uri")), "legal_evidence_missing")

    loader = gate("loader_compatibility")
    require("loader_compatibility", loader.get("status") == "passed", "not_passed")
    require("loader_compatibility", loader.get("tested_revision") == revision, "revision_mismatch")
    require("loader_compatibility", bool(loader.get("model_class")), "model_class_missing")
    require("loader_compatibility", bool(loader.get("runtime_versions")), "runtime_versions_missing")
    remote_code = loader.get("remote_code", {})
    require("loader_compatibility", remote_code.get("status") in ("disabled", "audited"), "remote_code_not_cleared")
    if remote_code.get("status") == "audited":
        require("loader_compatibility", valid_sha(remote_code.get("audit_sha256")), "remote_code_audit_missing")

    inference = gate("real_inference")
    require("real_inference", inference.get("status") == "completed", "not_completed")
    require("real_inference", inference.get("tested_revision") == revision, "revision_mismatch")
    require("real_inference", bool(inference.get("workflow_run_id")), "workflow_run_id_missing")
    require("real_inference", bool(inference.get("internal_run_id")), "internal_run_id_missing")
    require("real_inference", isinstance(inference.get("expected_response_count"), int) and not isinstance(inference.get("expected_response_count"), bool) and inference.get("expected_response_count", 0) > 0, "expected_count_invalid")
    require("real_inference", inference.get("response_count") == inference.get("expected_response_count"), "response_count_incomplete")
    require("real_inference", inference.get("error_count") == 0, "inference_errors_present")
    require("real_inference", valid_sha(inference.get("artifact_sha256")), "artifact_digest_missing")

    resources = gate("resource_measurement")
    require("resource_measurement", resources.get("status") == "recorded", "not_recorded")
    require("resource_measurement", bool(resources.get("runner_type")), "runner_type_missing")
    require("resource_measurement", bool(resources.get("device")), "device_missing")
    require("resource_measurement", isinstance(resources.get("peak_rss_bytes"), int) and resources.get("peak_rss_bytes", 0) > 0, "peak_rss_missing")
    require("resource_measurement", isinstance(resources.get("mean_latency_seconds"), (int, float)) and not isinstance(resources.get("mean_latency_seconds"), bool) and resources.get("mean_latency_seconds", 0) > 0, "latency_missing")
    require("resource_measurement", valid_sha(resources.get("compute_record_sha256")), "compute_digest_missing")

    human = gate("human_review")
    reviewer_ids = human.get("independent_reviewer_ids", [])
    require("human_review", human.get("status") == "passed", "not_passed")
    require("human_review", isinstance(reviewer_ids, list) and all(isinstance(x, str) and x.strip() for x in reviewer_ids) and len(set(reviewer_ids)) >= 2, "two_independent_reviewers_required")
    require("human_review", human.get("independence_attested") is True, "reviewer_independence_not_attested")
    require("human_review", human.get("adjudication_complete") is True, "adjudication_incomplete")
    require("human_review", isinstance(human.get("expected_response_count"), int) and human.get("expected_response_count", 0) > 0, "expected_review_count_invalid")
    require("human_review", human.get("graded_response_count") == human.get("expected_response_count"), "review_coverage_incomplete")
    require("human_review", valid_sha(human.get("grade_report_sha256")), "grade_report_digest_missing")
    require("human_review", valid_sha(human.get("adjudication_sha256")), "adjudication_digest_missing")

    safety = gate("safety_review")
    require("safety_review", safety.get("status") == "passed", "not_passed")
    require("safety_review", bool(safety.get("reviewer_id")), "reviewer_missing")
    require("safety_review", valid_sha(safety.get("report_sha256")), "report_digest_missing")

    holdout = gate("holdout")
    require("holdout", holdout.get("status") == "passed", "not_passed")
    require("holdout", isinstance(holdout.get("case_count"), int) and holdout.get("case_count", 0) > 0, "holdout_cases_missing")
    require("holdout", holdout.get("leakage_audit_passed") is True, "leakage_audit_not_passed")
    require("holdout", valid_sha(holdout.get("audit_sha256")), "audit_digest_missing")

    corpus = gate("corpus_integrity")
    require("corpus_integrity", corpus.get("status") == "passed", "not_passed")
    require("corpus_integrity", valid_sha(corpus.get("corpus_sha256")), "corpus_digest_missing")
    require("corpus_integrity", isinstance(corpus.get("duplicate_count"), int) and not isinstance(corpus.get("duplicate_count"), bool) and corpus.get("duplicate_count") == 0, "duplicates_present_or_unverified")
    require("corpus_integrity", corpus.get("provenance_verified") is True, "provenance_not_verified")

    permission = gate("training_output_permission")
    require("training_output_permission", permission.get("status") == "granted", "not_granted")
    require("training_output_permission", valid_sha(permission.get("document_sha256")), "permission_document_missing")
    require("training_output_permission", bool(permission.get("authorized_by")), "authorizer_missing")
    require("training_output_permission", valid_time(permission.get("authorized_at")), "authorization_timestamp_invalid")

    return {
        "candidate_id": candidate_id,
        "immutable_revision": revision,
        "qualification_status": "qualified" if not failures else "not_qualified",
        "failed_gates": failures,
        "gate_count": 10,
        "qualification_decision": "gate_validation_only",
        "teacher_ranking": "not_performed",
        "teacher_selection": "not_performed",
        "training_started": False,
    }


def evaluate_cohort(manifests: list[dict[str, Any]], required_teachers: int = 4) -> dict[str, Any]:
    results = [evaluate_candidate(manifest) for manifest in manifests]
    candidate_ids = [row.get("candidate_id") for row in results]
    duplicates = len(candidate_ids) != len(set(candidate_ids))
    qualified_count = sum(row["qualification_status"] == "qualified" for row in results)
    return {
        "schema_version": "vectolith-teacher-qualification-cohort/1.0",
        "candidate_count": len(results),
        "qualified_teacher_count": qualified_count,
        "required_teacher_count": required_teachers,
        "cohort_gate": "passed" if not duplicates and qualified_count >= required_teachers else "blocked",
        "duplicate_candidate_ids": duplicates,
        "candidate_results": results,
        "teacher_ranking": "not_performed",
        "teacher_selection": "not_performed",
        "training_started": False,
    }


def read_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("validate")
    one.add_argument("--manifest", type=Path, required=True)
    one.add_argument("--output", type=Path, required=True)
    cohort = sub.add_parser("cohort")
    cohort.add_argument("--manifest-dir", type=Path, required=True)
    cohort.add_argument("--required-teachers", type=int, default=4)
    cohort.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "validate":
        result = evaluate_candidate(read_manifest(args.manifest))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0 if result["qualification_status"] == "qualified" else 1
    paths = sorted(args.manifest_dir.glob("*.json"))
    manifests = [read_manifest(path) for path in paths]
    result = evaluate_cohort(manifests, args.required_teachers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["cohort_gate"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
