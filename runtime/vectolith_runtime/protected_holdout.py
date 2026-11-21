"""Protected holdout deployment and candidate-result evidence validation."""
from __future__ import annotations
import hashlib, json, math, re
from pathlib import Path
from typing import Any

DEPLOYMENT_SCHEMA = "vectolith-protected-holdout-deployment/1.0"
RESULT_SCHEMA = "vectolith-protected-holdout-evaluation/1.0"
SHA = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MINIMUM_HOLDOUT_PASS_RATE = 0.80
REVISION_SHA = re.compile(r"^[0-9a-f]{40}$")

def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def validate_deployment_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != DEPLOYMENT_SCHEMA:
        return ["unsupported_or_missing_schema"]
    if not isinstance(manifest.get("dataset_version"), str) or not manifest["dataset_version"].strip():
        errors.append("dataset_version_missing")
    if not SHA.fullmatch(str(manifest.get("dataset_sha256", ""))):
        errors.append("dataset_digest_invalid")
    count = manifest.get("case_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        errors.append("case_count_invalid")
    threshold = manifest.get("minimum_required_pass_rate")
    if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold) or not MINIMUM_HOLDOUT_PASS_RATE <= threshold <= 1):
        errors.append("minimum_required_pass_rate_invalid")
    custody = manifest.get("custody")
    if not isinstance(custody, dict):
        custody = {}
        errors.append("custody_missing")
    uri = custody.get("storage_uri")
    if not isinstance(uri, str) or not uri.startswith(("s3://", "gs://", "azure://", "vault://")):
        errors.append("restricted_storage_uri_required")
    if custody.get("access_boundary") not in {"separate_account", "separate_project", "dedicated_vault"}:
        errors.append("separate_custody_boundary_required")
    if custody.get("encryption_at_rest") is not True or custody.get("key_custody_separate") is not True:
        errors.append("independent_encryption_and_key_custody_required")
    custodian, evaluator = custody.get("custodian_id"), custody.get("evaluator_operator_id")
    if not isinstance(custodian, str) or not custodian.strip():
        errors.append("custodian_identity_missing")
    if (not isinstance(evaluator, str) or not evaluator.strip()
            or not isinstance(custodian, str) or evaluator.strip() == custodian.strip()):
        errors.append("independent_evaluator_operator_required")
    execution = manifest.get("execution")
    if not isinstance(execution, dict):
        execution = {}
        errors.append("execution_boundary_missing")
    service_id = execution.get("evaluator_service_id")
    if not isinstance(service_id, str) or not service_id.strip():
        errors.append("dedicated_evaluator_service_required")
    if not SHA.fullmatch(str(execution.get("deployment_image_sha256", ""))):
        errors.append("evaluator_deployment_digest_invalid")
    for field in ("pull_request_code_denied", "candidate_network_egress_denied",
                  "dataset_mount_read_only", "result_channel_separated"):
        if execution.get(field) is not True:
            errors.append(f"execution_control_missing:{field}")
    audit = manifest.get("audit")
    if not isinstance(audit, dict):
        audit = {}
        errors.append("audit_evidence_missing")
    for field in ("access_log_sha256", "leakage_audit_sha256", "provenance_report_sha256"):
        if not SHA.fullmatch(str(audit.get(field, ""))):
            errors.append(f"audit_digest_invalid:{field}")
    if audit.get("public_fixture_overlap_checked") is not True:
        errors.append("public_fixture_overlap_audit_required")
    unauthorized_count = audit.get("unauthorized_access_count")
    if isinstance(unauthorized_count, bool) or not isinstance(unauthorized_count, int) or unauthorized_count != 0:
        errors.append("unauthorized_access_detected_or_unreported")
    reviewer = audit.get("reviewed_by")
    if (not isinstance(reviewer, str) or not reviewer.strip()
            or reviewer.strip() in {str(custodian).strip(), str(evaluator).strip()}):
        errors.append("independent_audit_reviewer_required")
    return errors

def validate_evaluation_report(report: dict[str, Any], deployment: dict[str, Any],
                               candidate_id: str, candidate_revision: str) -> list[str]:
    errors: list[str] = []
    deployment_errors = validate_deployment_manifest(deployment)
    if deployment_errors:
        errors.extend(f"deployment_manifest_invalid:{item}" for item in deployment_errors)
    if not isinstance(report, dict) or report.get("schema_version") != RESULT_SCHEMA:
        return errors + ["unsupported_or_missing_evaluation_schema"]
    deployment_sha = canonical_digest(deployment)
    if report.get("deployment_manifest_sha256") != deployment_sha:
        errors.append("evaluation_not_bound_to_protected_deployment")
    if report.get("candidate_id") != candidate_id or report.get("candidate_revision") != candidate_revision:
        errors.append("evaluation_candidate_identity_or_revision_mismatch")
    report_revision = report.get("candidate_revision")
    if not isinstance(report_revision, str) or not REVISION_SHA.fullmatch(report_revision):
        errors.append("evaluation_report_candidate_revision_invalid")
    if not isinstance(candidate_revision, str) or not REVISION_SHA.fullmatch(candidate_revision):
        errors.append("evaluation_candidate_revision_invalid")
    custody = deployment.get("custody", {}) if isinstance(deployment, dict) else {}
    execution = deployment.get("execution", {}) if isinstance(deployment, dict) else {}
    if report.get("evaluator_id") != custody.get("evaluator_operator_id"):
        errors.append("evaluation_evaluator_identity_mismatch")
    if report.get("evaluator_image_sha256") != execution.get("deployment_image_sha256"):
        errors.append("evaluation_evaluator_image_mismatch")
    report_case_count = report.get("case_count")
    if (isinstance(report_case_count, bool) or not isinstance(report_case_count, int)
            or report_case_count < 1):
        errors.append("evaluation_case_count_invalid")
    elif report_case_count != deployment.get("case_count"):
        errors.append("evaluation_case_count_mismatch")
    counts = [report.get(k) for k in ("verified_pass_count", "verified_fail_count", "unscored_count")]
    counts_valid = all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in counts)
    if not counts_valid:
        errors.append("evaluation_case_counts_invalid")
    else:
        if (isinstance(report_case_count, int) and not isinstance(report_case_count, bool)
                and sum(counts) != report_case_count):
            errors.append("evaluation_case_counts_do_not_sum")
        if counts[2] != 0:
            errors.append("evaluation_contains_unscored_cases")
    score = report.get("pass_rate")
    report_threshold = report.get("minimum_required_pass_rate")
    deployment_threshold = deployment.get("minimum_required_pass_rate") if isinstance(deployment, dict) else None
    score_valid = (not isinstance(score, bool) and isinstance(score, (int, float))
                   and math.isfinite(score) and 0 <= score <= 1)
    threshold_valid = (not isinstance(report_threshold, bool)
                       and isinstance(report_threshold, (int, float))
                       and math.isfinite(report_threshold)
                       and MINIMUM_HOLDOUT_PASS_RATE <= report_threshold <= 1)
    if not score_valid or not threshold_valid or report_threshold != deployment_threshold:
        errors.append("evaluation_did_not_meet_or_bind_declared_threshold")
    elif score < report_threshold:
        errors.append("evaluation_did_not_meet_or_bind_declared_threshold")
    elif counts_valid and isinstance(report_case_count, int) and not isinstance(report_case_count, bool) and report_case_count > 0:
        expected_rate = counts[0] / report_case_count
        if not math.isclose(score, expected_rate, rel_tol=0, abs_tol=1e-12):
            errors.append("evaluation_pass_rate_does_not_match_case_counts")
    if report.get("status") != "passed":
        errors.append("holdout_evaluation_not_passed")
    for field in ("evaluation_suite_version", "evaluated_at", "evaluator_run_id"):
        if not isinstance(report.get(field), str) or not report[field].strip():
            errors.append(f"evaluation_provenance_missing:{field}")
    return errors

def validate_deployment_file(path: str | Path) -> tuple[dict[str, Any], str]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_deployment_manifest(manifest)
    if errors:
        raise ValueError("protected holdout deployment validation failed: " + "; ".join(errors))
    return manifest, canonical_digest(manifest)

def validate_candidate_result(path: str | Path, deployment: dict[str, Any],
                              deployment_sha256: str, candidate_id: str,
                              candidate_revision: str) -> tuple[dict[str, Any], str]:
    if not IDENTIFIER.fullmatch(candidate_id) or ".." in candidate_id:
        raise ValueError("unsafe candidate ID for holdout result lookup")
    if not isinstance(candidate_revision, str) or not REVISION_SHA.fullmatch(candidate_revision):
        raise ValueError("candidate revision must be a 40-character immutable SHA")
    actual_deployment_sha256 = canonical_digest(deployment)
    if deployment_sha256 != actual_deployment_sha256:
        raise ValueError("holdout deployment digest argument mismatch")
    deployment_errors = validate_deployment_manifest(deployment)
    if deployment_errors:
        raise ValueError("protected holdout deployment validation failed: " + "; ".join(deployment_errors))
    result_path = Path(path)
    if not result_path.is_file():
        raise FileNotFoundError(result_path)
    report = json.loads(result_path.read_text(encoding="utf-8"))
    errors = validate_evaluation_report(report, deployment, candidate_id, candidate_revision)
    if report.get("deployment_manifest_sha256") != deployment_sha256:
        errors.append("holdout_result_deployment_digest_mismatch")
    if errors:
        raise ValueError(f"{candidate_id}: protected holdout result validation failed: " + "; ".join(errors))
    return report, hashlib.sha256(result_path.read_bytes()).hexdigest()
