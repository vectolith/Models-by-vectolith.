"""Fail-closed deployment evidence validator for genuinely protected holdout suites.

A manifest documents an external custody boundary; it cannot create that boundary.
Never store holdout prompts, answers, labels, keys, or source files in Git.
"""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any

SCHEMA = "vectolith-protected-holdout-deployment/1.0"
SHA = re.compile(r"^[0-9a-f]{64}$")

def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA:
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

def manifest_digest(manifest: dict[str, Any]) -> str:
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()

def validate_file(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_manifest(manifest)
    return {"schema_version": "vectolith-protected-holdout-validation/1.0",
            "status": "passed" if not errors else "blocked",
            "manifest_sha256": manifest_digest(manifest), "errors": errors,
            "deployment_claim": "externally_attested" if not errors else "not_established",
            "note": "A passing manifest validates supplied deployment evidence; it does not provision or independently inspect the external custody environment."}
