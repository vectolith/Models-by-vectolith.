#!/usr/bin/env python3
"""Fail-closed candidate and four-teacher cohort qualification gates."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "vectolith-teacher-qualification-candidate/1.0"
WAIVER_SCHEMA = "vectolith-owner-waiver/1.0"
SHA_LENGTH = 64
DEFAULT_WAIVER_PATH = Path(__file__).with_name("owner_waivers.json")
HUMAN_GATE_NAMES = (
    "license_review",
    "grading",
    "safety_review",
    "holdout",
    "corpus_integrity",
    "training_output_permission",
)


def valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) == SHA_LENGTH
        and all(char in "0123456789abcdef" for char in value.lower())
    )


def valid_time(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except ValueError:
        return False


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def zero_int(value: Any) -> bool:
    return type(value) is int and value == 0


def positive_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value) and value > 0
    except (OverflowError, ValueError):
        return False


def load_waivers(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load owner waivers.

    A waiver is an owner decision to proceed without a review. It is recorded
    separately from gate status and is never reported as a passed review.
    """
    target = Path(path) if path is not None else DEFAULT_WAIVER_PATH
    if not target.exists():
        return {}
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != WAIVER_SCHEMA:
        raise ValueError(f"{target}: unsupported owner waiver schema")
    if not nonempty_string(data.get("owner_id")) or not valid_time(data.get("decided_at")):
        raise ValueError(f"{target}: owner waiver requires owner_id and decided_at")
    entries = data.get("waived_gates")
    if not isinstance(entries, list):
        raise ValueError(f"{target}: waived_gates must be a list")
    waivers: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{target}: each waived gate must be an object")
        name = entry.get("gate")
        if name not in HUMAN_GATE_NAMES:
            raise ValueError(f"{target}: gate {name!r} is not waivable")
        if entry.get("status") != "waived_by_owner":
            raise ValueError(f"{target}: gate {name!r} must declare status waived_by_owner")
        if not nonempty_string(entry.get("reason")):
            raise ValueError(f"{target}: gate {name!r} requires a reason")
        if name in waivers:
            raise ValueError(f"{target}: gate {name!r} is waived twice")
        waivers[name] = dict(entry, owner_id=data["owner_id"], decided_at=data["decided_at"])
    return waivers


def evaluate_candidate(
    manifest: dict[str, Any], waivers: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    waived = dict(waivers or {})
    applied_waivers: list[str] = []
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

    def mark_waived(name: str) -> None:
        if name not in applied_waivers:
            applied_waivers.append(name)

    def require(name: str, condition: bool, reason: str) -> None:
        if condition:
            return
        if name in waived:
            mark_waived(name)
            return
        failures.append(f"{name}:{reason}")

    def gate(name: str) -> dict[str, Any]:
        value = gates.get(name)
        if not isinstance(value, dict):
            if name in waived:
                mark_waived(name)
                return {}
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
    require("license_review", nonempty_string(legal.get("legal_reviewer_id")), "legal_reviewer_missing")
    require("license_review", legal.get("legal_reviewer_id") != candidate_id, "legal_reviewer_not_independent")
    require("license_review", valid_time(legal.get("reviewed_at")), "review_timestamp_invalid")
    require("license_review", nonempty_string(legal.get("evidence_uri")), "legal_evidence_missing")

    loader = gate("loader_compatibility")
    require("loader_compatibility", loader.get("status") == "passed", "not_passed")
    require("loader_compatibility", loader.get("tested_revision") == revision, "revision_mismatch")
    require("loader_compatibility", nonempty_string(loader.get("model_class")), "model_class_missing")
    runtime_versions = loader.get("runtime_versions")
    require("loader_compatibility", isinstance(runtime_versions, dict) and bool(runtime_versions) and all(nonempty_string(key) and nonempty_string(value) for key, value in runtime_versions.items()), "runtime_versions_missing_or_invalid")
    remote_code = loader.get("remote_code")
    if not isinstance(remote_code, dict):
        failures.append("loader_compatibility:remote_code_gate_missing")
        remote_code = {}
    require("loader_compatibility", remote_code.get("status") in ("disabled", "audited"), "remote_code_not_cleared")
    if remote_code.get("status") == "audited":
        require("loader_compatibility", valid_sha(remote_code.get("audit_sha256")), "remote_code_audit_missing")

    inference = gate("real_inference")
    require("real_inference", inference.get("status") == "completed", "not_completed")
    require("real_inference", inference.get("tested_revision") == revision, "revision_mismatch")
    require("real_inference", nonempty_string(inference.get("workflow_run_id")), "workflow_run_id_missing")
    require("real_inference", nonempty_string(inference.get("internal_run_id")), "internal_run_id_missing")
    require("real_inference", positive_int(inference.get("expected_response_count")), "expected_count_invalid")
    require("real_inference", type(inference.get("response_count")) is int and inference.get("response_count") == inference.get("expected_response_count"), "response_count_incomplete")
    require("real_inference", zero_int(inference.get("error_count")), "inference_errors_present")
    require("real_inference", valid_sha(inference.get("artifact_sha256")), "artifact_digest_missing")

    resources = gate("resource_measurement")
    require("resource_measurement", resources.get("status") == "recorded", "not_recorded")
    require("resource_measurement", nonempty_string(resources.get("runner_type")), "runner_type_missing")
    require("resource_measurement", nonempty_string(resources.get("device")), "device_missing")
    require("resource_measurement", positive_int(resources.get("peak_rss_bytes")), "peak_rss_missing")
    require("resource_measurement", positive_number(resources.get("mean_latency_seconds")), "latency_missing")
    require("resource_measurement", resources.get("free_compute_verified") is True, "free_compute_not_verified")
    require("resource_measurement", valid_sha(resources.get("free_compute_evidence_sha256")), "free_compute_evidence_missing")
    require("resource_measurement", valid_sha(resources.get("compute_record_sha256")), "compute_digest_missing")

    grading = gate("grading")
    expected_grades = grading.get("expected_response_count")
    require("grading", grading.get("status") == "passed", "not_passed")
    require("grading", positive_int(expected_grades), "expected_count_invalid")
    require("grading", positive_int(grading.get("graded_response_count")) and grading.get("graded_response_count") == expected_grades, "coverage_incomplete")
    require("grading", valid_sha(grading.get("grade_report_sha256")), "grade_report_digest_missing")
    require("grading", nonempty_string(grading.get("rubric_version")), "rubric_version_missing")
    reviewers=grading.get("independent_reviewer_ids")
    distinct_reviewers={value for value in reviewers if isinstance(value,str) and value.strip()} if isinstance(reviewers,list) else set()
    require("grading", grading.get("review_method")=="independent_human", "review_method_not_independent_human")
    require("grading", isinstance(reviewers,list) and len(distinct_reviewers)>=2 and len(distinct_reviewers)==len(reviewers) and (not isinstance(candidate_id, str) or candidate_id not in distinct_reviewers), "independent_reviewers_insufficient_or_invalid")
    require("grading", valid_sha(grading.get("independence_attestation_sha256")), "independence_attestation_missing")
    require("grading", valid_sha(grading.get("agreement_report_sha256")), "agreement_report_missing")
    require("grading", valid_sha(grading.get("adjudication_report_sha256")), "adjudication_report_missing")

    safety = gate("safety_review")
    require("safety_review", safety.get("status") == "passed", "not_passed")
    require("safety_review", nonempty_string(safety.get("reviewer_id")), "reviewer_missing")
    require("safety_review", safety.get("reviewer_id") != candidate_id, "reviewer_not_independent")
    require("safety_review", valid_sha(safety.get("report_sha256")), "report_digest_missing")

    holdout = gate("holdout")
    require("holdout", holdout.get("status") == "passed", "not_passed")
    require("holdout", positive_int(holdout.get("case_count")), "holdout_cases_missing")
    require("holdout", holdout.get("leakage_audit_passed") is True, "leakage_audit_not_passed")
    require("holdout", valid_sha(holdout.get("audit_sha256")), "audit_digest_missing")

    corpus = gate("corpus_integrity")
    require("corpus_integrity", corpus.get("status") == "passed", "not_passed")
    require("corpus_integrity", valid_sha(corpus.get("corpus_sha256")), "corpus_digest_missing")
    require("corpus_integrity", zero_int(corpus.get("duplicate_count")), "duplicates_present_or_unverified")
    require("corpus_integrity", corpus.get("provenance_verified") is True, "provenance_not_verified")

    permission = gate("training_output_permission")
    require("training_output_permission", permission.get("status") == "granted", "not_granted")
    require("training_output_permission", valid_sha(permission.get("document_sha256")), "permission_document_missing")
    require("training_output_permission", nonempty_string(permission.get("authorized_by")), "authorizer_missing")
    require("training_output_permission", permission.get("authorized_by") != candidate_id, "authorizer_not_independent")
    require("training_output_permission", valid_time(permission.get("authorized_at")), "authorization_timestamp_invalid")

    return {
        "candidate_id": candidate_id,
        "immutable_revision": revision,
        "qualification_status": "qualified" if not failures else "not_qualified",
        "failed_gates": failures,
        "waived_gates": applied_waivers,
        "review_basis": "owner_waiver" if applied_waivers else "independent_review",
        "gate_count": 10,
        "qualification_decision": "gate_validation_only",
        "teacher_ranking": "not_performed",
        "teacher_selection": "not_performed",
        "training_started": False,
    }


def evaluate_cohort(
    manifests: list[dict[str, Any]],
    required_teachers: int = 4,
    waivers: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if type(required_teachers) is not int or required_teachers < 4:
        raise ValueError("Core Prime cohort qualification requires at least four teachers (integer count)")
    results = [evaluate_candidate(manifest, waivers) for manifest in manifests]
    candidate_ids = [row.get("candidate_id") for row in results]
    valid_candidate_ids = [candidate_id for candidate_id in candidate_ids if isinstance(candidate_id, str) and candidate_id.strip()]
    duplicates = len(valid_candidate_ids) != len(set(valid_candidate_ids))
    cohort_teacher_ids = set(valid_candidate_ids)
    for row,manifest in zip(results,manifests):
        gates = manifest.get("gates", {})
        grading = gates.get("grading", {}) if isinstance(gates, dict) else {}
        reviewers = grading.get("independent_reviewer_ids", []) if isinstance(grading, dict) else []
        legal = gates.get("license_review", {}) if isinstance(gates, dict) else {}
        safety = gates.get("safety_review", {}) if isinstance(gates, dict) else {}
        permission = gates.get("training_output_permission", {}) if isinstance(gates, dict) else {}
        distinct = {value for value in reviewers if isinstance(value, str) and value.strip()} if isinstance(reviewers, list) else set()
        role_ids = set(distinct)
        for section, field in ((legal, "legal_reviewer_id"), (safety, "reviewer_id"), (permission, "authorized_by")):
            if isinstance(section, dict) and nonempty_string(section.get(field)):
                role_ids.add(section[field])
        if distinct.intersection(cohort_teacher_ids):
            row["failed_gates"].append("grading:reviewers_not_independent_of_teacher_cohort")
            row["qualification_status"]="not_qualified"
        other_role_ids = role_ids - distinct
        if other_role_ids.intersection(cohort_teacher_ids):
            row["failed_gates"].append("reviewer_roles_not_independent_of_teacher_cohort")
            row["qualification_status"]="not_qualified"
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
    parser.add_argument("--waivers", type=Path, default=DEFAULT_WAIVER_PATH)
    parser.add_argument("--strict", action="store_true", help="ignore owner waivers")
    args = parser.parse_args()
    waivers = {} if args.strict else load_waivers(args.waivers)
    if args.command == "validate":
        result = evaluate_candidate(read_manifest(args.manifest), waivers)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0 if result["qualification_status"] == "qualified" else 1
    paths = sorted(args.manifest_dir.glob("*.json"))
    manifests = [read_manifest(path) for path in paths]
    result = evaluate_cohort(manifests, args.required_teachers, waivers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["cohort_gate"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
