"""Fail-closed grade schema and response-population coverage checks."""
from __future__ import annotations
import hashlib, json, re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVISION_SHA = re.compile(r"^[0-9a-f]{40}$")
def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()
def verify_coverage(expected: Iterable[dict[str, str]], grades: Iterable[dict[str, Any]]) -> dict[str, Any]:
    expected_rows, grade_rows = list(expected), list(grades)
    expected_keys = [(x["candidate_id"], x["case_id"]) for x in expected_rows]
    grade_keys = [(x.get("candidate_id"), x.get("case_id")) for x in grade_rows]
    if len(expected_keys) != len(set(expected_keys)): raise ValueError("expected population contains duplicate candidate/case keys")
    duplicates = [key for key, count in Counter(grade_keys).items() if count > 1]
    if duplicates: raise ValueError(f"duplicate grade records: {duplicates[:5]}")
    expected_set, actual_set = set(expected_keys), set(grade_keys)
    missing, unexpected = sorted(expected_set - actual_set), sorted(actual_set - expected_set)
    if unexpected: raise ValueError(f"unexpected grade records: {unexpected[:5]}")
    return {"expected_response_count": len(expected_keys), "graded_response_count": len(actual_set), "ungraded_response_count": len(missing), "coverage_complete": not missing, "missing": [{"candidate_id": c, "case_id": k} for c, k in missing]}
def validate_grade_record(record: dict[str, Any]) -> None:
    required = {"schema_version", "inference_run_id", "candidate_id", "candidate_revision", "source_artifact_sha256", "case_id", "response_sha256", "rubric_sha256", "rubric_version", "grader", "criteria", "score", "graded_at"}
    if not isinstance(record, dict) or set(record) != required: raise ValueError("grade record fields do not match strict schema")
    if record["schema_version"] != "vectolith-core-prime-grade/1.0": raise ValueError("unsupported grade schema")
    for key in ("candidate_id", "case_id", "inference_run_id", "rubric_version", "graded_at"):
        if not isinstance(record[key], str) or not record[key].strip(): raise ValueError(f"{key} is required")
    if not isinstance(record["candidate_revision"], str) or not REVISION_SHA.fullmatch(record["candidate_revision"]):
        raise ValueError("candidate_revision must be a full 40-character lowercase Git commit SHA")
    for key in ("source_artifact_sha256", "response_sha256", "rubric_sha256"):
        if not isinstance(record[key], str) or not SHA256.fullmatch(record[key]):
            raise ValueError(f"{key} must be a lowercase 64-character SHA-256 digest")
    if not isinstance(record["grader"], dict) or set(record["grader"]) != {"method", "grader_id", "grader_version", "prompt_version"}: raise ValueError("grader metadata is invalid")
    if record["grader"]["method"] not in {"deterministic", "model_assisted", "human", "hybrid"} or any(not isinstance(record["grader"][k], str) or not record["grader"][k] for k in ("grader_id", "grader_version", "prompt_version")): raise ValueError("grader metadata is incomplete")
    if not isinstance(record["criteria"], list) or not record["criteria"]: raise ValueError("criteria must be non-empty")
    counts, seen = Counter(), set()
    for row in record["criteria"]:
        if not isinstance(row, dict) or set(row) != {"criterion_id", "status", "evidence_excerpt", "rationale", "method", "confidence"}: raise ValueError("criterion record shape invalid")
        cid = row["criterion_id"]
        if not isinstance(cid, str) or not cid or cid in seen: raise ValueError("criterion IDs must be unique")
        seen.add(cid)
        if row["status"] not in {"passed", "failed", "unscored"} or row["method"] not in {"deterministic", "semantic", "human"}: raise ValueError("criterion status or method invalid")
        if not isinstance(row["evidence_excerpt"], str) or not isinstance(row["rationale"], str) or not row["rationale"]: raise ValueError("criterion evidence and rationale required")
        confidence = row["confidence"]
        if confidence is not None and (isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1): raise ValueError("confidence must be null or between zero and one")
        counts[row["status"]] += 1
    expected_score = {"passed": counts["passed"], "failed": counts["failed"], "unscored": counts["unscored"], "total": len(record["criteria"])}
    if record["score"] != expected_score: raise ValueError("score totals do not match criterion decisions")
def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> str:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    data = b"".join(canonical_json(row) + bytes([10]) for row in rows)
    target.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def verify_grade_bindings(expected: Iterable[dict[str, Any]], grades: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Verify each grade is bound to the exact candidate revision, artifact, response and rubric."""
    expected_rows = {(row["candidate_id"], row["case_id"]): row for row in expected}
    checked = 0
    unresolved_criteria = 0
    for grade in grades:
        key = (grade["candidate_id"], grade["case_id"])
        source = expected_rows.get(key)
        if source is None:
            raise ValueError(f"grade has no matching source response: {key}")
        bindings = {
            "candidate_revision": source["candidate_revision"],
            "source_artifact_sha256": source["source_artifact_sha256"],
            "response_sha256": source["response_sha256"],
            "rubric_sha256": hashlib.sha256(canonical_json(source["rubric"])).hexdigest(),
            "inference_run_id": source["inference_run_id"],
        }
        for field, value in bindings.items():
            if grade[field] != value:
                raise ValueError(f"{key}: grade {field} does not match source evidence")
        rubric_ids = []
        for index, item in enumerate(source["rubric"]):
            rubric_ids.append(str(item.get("criterion_id") or item.get("id") or f"criterion-{index + 1:02d}") if isinstance(item, dict) else f"criterion-{index + 1:02d}")
        grade_ids = [row["criterion_id"] for row in grade["criteria"]]
        if len(grade_ids) != len(set(grade_ids)) or set(grade_ids) != set(rubric_ids) or len(grade_ids) != len(rubric_ids):
            raise ValueError(f"{key}: grade does not cover the exact original rubric criteria")
        unresolved_criteria += sum(1 for row in grade["criteria"] if row["status"] == "unscored")
        checked += 1
    return {"evidence_bindings_verified": checked, "unscored_criteria": unresolved_criteria,
            "criterion_decisions_complete": unresolved_criteria == 0}
