"""Criterion-specific verifiers. Lexical overlap is never a quality score."""
from __future__ import annotations
import hashlib, hmac, json, re
from decimal import Decimal, InvalidOperation
from typing import Any

def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def _result(status: str, method: str, payload: dict[str, Any], reference: str,
            limitations: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"status": status, "method": method,
            "evidence": [{"type": "criterion_verification", "reference": reference,
                          "sha256": hashlib.sha256(_canonical(payload)).hexdigest()}],
            "confidence": 1.0 if status in {"verified_pass", "verified_fail"} else None,
            "limitations": list(limitations)}

def verify_exact_answer(*, actual: str, expected: str, case_id: str,
                        reference_id: str) -> dict[str, Any]:
    if not all(isinstance(x, str) and x.strip() for x in (actual, expected, case_id, reference_id)):
        raise ValueError("actual, expected, case_id and reference_id are required")
    payload = {"schema_version": "vectolith-exact-answer-evidence/1.0", "case_id": case_id,
               "expected_sha256": hashlib.sha256(expected.encode()).hexdigest(),
               "actual_sha256": hashlib.sha256(actual.encode()).hexdigest(),
               "match": actual.strip() == expected.strip()}
    return _result("verified_pass" if payload["match"] else "verified_fail",
                   "vectolith-exact-answer/1.0", payload, reference_id,
                   ("Only for rubric-defined single-answer tasks.",))

def verify_decimal_answer(*, actual: str, expected: str, case_id: str,
                          reference_id: str, absolute_tolerance: str = "0",
                          relative_tolerance: str = "0") -> dict[str, Any]:
    try:
        observed, target = Decimal(actual.strip()), Decimal(expected.strip())
        abs_tol, rel_tol = Decimal(absolute_tolerance), Decimal(relative_tolerance)
    except (AttributeError, InvalidOperation) as exc:
        raise ValueError("numeric verifier accepts plain decimal strings only") from exc
    if not all(x.is_finite() for x in (observed, target, abs_tol, rel_tol)):
        raise ValueError("numeric values and tolerances must be finite")
    if abs_tol < 0 or rel_tol < 0 or not case_id.strip() or not reference_id.strip():
        raise ValueError("non-negative tolerances and evidence identifiers are required")
    error, allowed = abs(observed-target), max(abs_tol, abs(target)*rel_tol)
    payload = {"schema_version": "vectolith-decimal-verification/1.0", "case_id": case_id,
               "observed": str(observed), "expected": str(target),
               "absolute_error": str(error), "allowed_error": str(allowed), "passed": error <= allowed}
    return _result("verified_pass" if error <= allowed else "verified_fail",
                   "vectolith-decimal-answer/1.0", payload, reference_id)

def verify_sandbox_attestation(*, attestation: dict[str, Any], signing_key: bytes,
                               expected_case_id: str, expected_output_sha256: str,
                               expected_runner_id: str) -> dict[str, Any]:
    """Verify a signed report from a separately operated untrusted-code sandbox."""
    if not isinstance(signing_key, bytes) or len(signing_key) < 32:
        raise ValueError("sandbox attestation key must contain at least 32 bytes")
    if not isinstance(attestation, dict):
        raise ValueError("attestation must be an object")
    signature = attestation.get("signature")
    body = {k: v for k, v in attestation.items() if k != "signature"}
    expected = hmac.new(signing_key, _canonical(body), hashlib.sha256).hexdigest()
    if not isinstance(signature, str) or not hmac.compare_digest(signature, expected):
        raise ValueError("sandbox attestation signature is invalid")
    required = {"schema_version": "vectolith-code-sandbox-attestation/1.0",
                "case_id": expected_case_id, "runner_id": expected_runner_id,
                "output_sha256": expected_output_sha256}
    for key, value in required.items():
        if body.get(key) != value:
            raise ValueError(f"sandbox attestation {key} mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", str(body.get("report_sha256", ""))):
        raise ValueError("sandbox report SHA-256 is missing or invalid")
    if body.get("isolation_profile") != "untrusted-code-v1":
        raise ValueError("sandbox isolation profile is not approved")
    for flag in ("network_egress_disabled", "filesystem_isolated", "timeout_enforced",
                 "memory_limit_enforced", "process_limit_enforced"):
        if body.get(flag) is not True:
            raise ValueError(f"sandbox control is not attested: {flag}")
    values = (body.get("exit_code"), body.get("tests_passed"), body.get("tests_failed"))
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in values):
        raise ValueError("sandbox exit and test counts must be non-negative integers")
    if values[1] + values[2] < 1:
        raise ValueError("at least one sandbox test must have executed")
    passed = values[0] == 0 and values[2] == 0
    payload = {**body, "signature": signature, "verified_signature": True,
               "test_outcome": "passed" if passed else "failed"}
    return _result("verified_pass" if passed else "verified_fail",
                   "vectolith-signed-sandbox-attestation/1.0", payload,
                   f"sandbox://{expected_runner_id}/{expected_case_id}",
                   ("Trust depends on the sandbox signing key and independent runner operations.",))

def verify_fact_claim_review(*, case_id: str, output_sha256: str,
                             claims: list[dict[str, Any]], review_record: dict[str, Any],
                             review_record_sha256: str) -> dict[str, Any]:
    """Require claim-level source evidence and an independent adjudication record."""
    if not re.fullmatch(r"[0-9a-f]{64}", output_sha256 or ""):
        raise ValueError("output SHA-256 is required")
    if not re.fullmatch(r"[0-9a-f]{64}", review_record_sha256 or ""):
        raise ValueError("review record SHA-256 is required")
    if not isinstance(claims, list) or not claims or not isinstance(review_record, dict):
        raise ValueError("claims and review record are required")
    if review_record.get("case_id") != case_id or review_record.get("output_sha256") != output_sha256:
        raise ValueError("review record is not bound to this exact output")
    reviewer, adjudicator = review_record.get("reviewer_id"), review_record.get("adjudicator_id")
    if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(adjudicator, str) or not adjudicator.strip():
        raise ValueError("independent reviewer and adjudicator identities are required")
    if reviewer == adjudicator:
        raise ValueError("factuality adjudicator must be independent of the reviewer")
    if review_record.get("status") != "adjudicated":
        raise ValueError("factuality review must be independently adjudicated")
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict) or not isinstance(claim.get("claim"), str) or not claim["claim"].strip():
            raise ValueError(f"claim[{index}] text missing")
        if not isinstance(claim.get("source_uri"), str) or not claim["source_uri"].startswith(("https://", "doi:")):
            raise ValueError(f"claim[{index}] source URI missing")
        if not re.fullmatch(r"[0-9a-f]{64}", str(claim.get("source_sha256", ""))):
            raise ValueError(f"claim[{index}] source digest missing")
        if claim.get("review_status") not in {"supported", "contradicted", "not_verifiable"}:
            raise ValueError(f"claim[{index}] has no adjudicated status")
    unsupported = [c for c in claims if c["review_status"] != "supported"]
    payload = {"schema_version": "vectolith-factual-claim-review/1.0", "case_id": case_id,
               "output_sha256": output_sha256, "claim_count": len(claims),
               "supported_claim_count": len(claims)-len(unsupported),
               "reviewer_id": reviewer, "adjudicator_id": adjudicator,
               "review_record_sha256": review_record_sha256, "claims": claims}
    return _result("verified_pass" if not unsupported else "verified_fail",
                   "vectolith-source-backed-factuality-review/1.0", payload,
                   f"review://{case_id}/{review_record_sha256}",
                   ("This validates supplied human/source-review evidence; it does not independently browse publishers.",))
