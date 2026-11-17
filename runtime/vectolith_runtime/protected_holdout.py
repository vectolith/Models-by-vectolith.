"""Protected holdout deployment and candidate-result evidence validation."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any

DEPLOYMENT_SCHEMA = "vectolith-protected-holdout-deployment/1.0"
RESULT_SCHEMA = "vectolith-protected-holdout-evaluation/1.0"
SHA = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

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
    if not isinstance(evaluator, str) or not evaluator.strip() or evaluator == custodian:
        errors.append("independent_evaluator_operator_required")
    execution = manifest.get("execution")
    if not isinstance(execution, dict):
        execution = {}
        errors.append("execution_boundary_missing")
    if not execution.get("evaluator_service_id"):
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
    if audit.get("unauthorized_access_count") != 0:
        errors.append("unauthorized_access_detected_or_unreported")
    if audit.get("reviewed_by") in (None, "", custodian, evaluator):
        errors.append("independent_audit_reviewer_required")
    return errors

def validate_evaluation_report(report: dict[str, Any], deployment: dict[str, Any],
                               candidate_id: str, candidate_revision: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict) or report.get("schema_version") != RESULT_SCHEMA:
        return ["unsupported_or_missing_evaluation_schema"]
    deployment_sha = canonical_digest(deployment)
    if report.get("deployment_manifest_sha256") != deployment_sha:
        errors.append("evaluation_not_bound_to_protected_deployment")
    if report.get("candidate_id") != candidate_id or report.get("candidate_revision") != candidate_revision:
        errors.append("evaluation_candidate_identity_or_revision_mismatch")
    custody = deployment.get("custody", {})
    execution = deployment.get("execution", {})
    if report.get("evaluator_id") != custody.get("evaluator_operator_id"):
        errors.append("evaluation_evaluator_identity_mismatch")
    if report.get("evaluator_image_sha256") != execution.get("deployment_image_sha256"):
        errors.append("evaluation_evaluator_image_mismatch")
    if report.get("case_count") != deployment.get("case_count"):
        errors.append("evaluation_case_count_mismatch")
    counts = [report.get(k) for k in ("verified_pass_count", "verified_fail_count", "unscored_count")]
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in counts):
        errors.append("evaluation_case_counts_invalid")
    elif sum(counts) != report.get("case_count"):
        errors.append("evaluation_case_counts_do_not_sum")
    elif counts[2] != 0:
        errors.append("evaluation_contains_unscored_cases")
    score, threshold = report.get("pass_rate"), report.get("minimum_required_pass_rate")
    if (isinstance(score, bool) or not isinstance(score, (int, float)) or
        isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or
        not 0 <= threshold <= 1 or not 0 <= score <= 1 or score < threshold):
        errors.append("evaluation_did_not_meet_declared_threshold")
    elif counts[0] / max(1, report.get("case_count", 0)) != score:
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
