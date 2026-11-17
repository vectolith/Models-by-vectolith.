"""Evaluation-facing compatibility exports for protected holdout evidence."""
from vectolith_runtime.protected_holdout import (
    DEPLOYMENT_SCHEMA as SCHEMA,
    canonical_digest as manifest_digest,
    validate_deployment_file as validate_file,
    validate_deployment_manifest as validate_manifest,
    validate_evaluation_report,
    validate_candidate_result,
)

__all__ = [
    "SCHEMA", "manifest_digest", "validate_file", "validate_manifest",
    "validate_evaluation_report", "validate_candidate_result",
]
