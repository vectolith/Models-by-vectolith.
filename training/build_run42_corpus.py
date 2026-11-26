#!/usr/bin/env python3
"""Build an ASH PRIME training corpus from graded Run 42 responses.

Inputs are the three artifacts the grading pipeline already produces:

  * the Run 42 response index (one row per candidate/case, with the response
    text and its SHA-256),
  * the evidence-bound grade ledger (strict vectolith-ash-prime-grade/1.0
    records, one criterion decision per rubric item),
  * the benchmark case suite, which supplies the system and user prompts that
    the response index deliberately omits.

A response becomes training data only when every one of its rubric criteria
passed and none is unscored. Anything failed, unscored, missing a grade record,
or whose response digest no longer matches the index is written out with
accepted=false so the rejection is auditable instead of silently dropped.

Offline only: no model calls, no network, no training execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "vectolith-ash-prime-graded-training-corpus/1.0"

REQUIRED_ROW_FIELDS = (
    "schema_version",
    "case_id",
    "teacher",
    "teacher_revision",
    "source_artifact_sha256",
    "system",
    "prompt",
    "response",
    "response_sha256",
    "grade",
    "accepted",
    "rejection_reason",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise ValueError(f"{path}:{number}: {exc}") from exc
    return rows


def load_cases(path: Path) -> dict[str, dict[str, str]]:
    """Map case_id to the system and user prompts the student will see."""
    cases: dict[str, dict[str, str]] = {}
    for case in read_jsonl(path):
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path}: case without an id")
        messages = case.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError(f"{path}: case {case_id} without messages")
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        if not user.strip():
            raise ValueError(f"{path}: case {case_id} has no user prompt")
        cases[case_id] = {"system": system, "prompt": user}
    if not cases:
        raise ValueError(f"{path}: no cases loaded")
    return cases


def index_grades(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    grades: dict[tuple[str, str], dict[str, Any]] = {}
    for grade in read_jsonl(path):
        key = (grade.get("candidate_id"), grade.get("case_id"))
        if not all(isinstance(part, str) and part for part in key):
            raise ValueError(f"{path}: grade record without candidate_id/case_id")
        if key in grades:
            raise ValueError(f"{path}: duplicate grade record for {key}")
        grades[key] = grade
    if not grades:
        raise ValueError(f"{path}: no grade records loaded")
    return grades


def acceptance(grade: dict[str, Any] | None, response_sha256: str) -> tuple[bool, str | None]:
    """A response trains only on a complete, all-passed, digest-matched grade."""
    if grade is None:
        return False, "ungraded"
    if grade.get("response_sha256") != response_sha256:
        return False, "response_digest_mismatch"
    score = grade.get("score") or {}
    if score.get("unscored"):
        return False, "unscored_criteria"
    if score.get("failed"):
        return False, "failed_criteria"
    if not score.get("total"):
        return False, "no_criteria"
    return True, None


def build_rows(
    response_index: list[dict[str, Any]],
    grades: dict[tuple[str, str], dict[str, Any]],
    cases: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    rows = []
    for entry in response_index:
        case_id = entry.get("case_id")
        if case_id not in cases:
            raise ValueError(f"response index references unknown case {case_id!r}")
        response = entry.get("response_text")
        if not isinstance(response, str) or not response.strip():
            raise ValueError(f"{case_id}: empty response in the index")
        response_sha = sha256_text(response)
        if entry.get("response_sha256") and entry["response_sha256"] != response_sha:
            raise ValueError(f"{case_id}: response digest in the index does not match its text")
        key = (entry.get("candidate_id"), case_id)
        grade = grades.get(key)
        accepted, reason = acceptance(grade, response_sha)
        score = (grade or {}).get("score") or {}
        rows.append(
            {
                "schema_version": SCHEMA,
                "case_id": case_id,
                "teacher": entry.get("candidate_id"),
                "teacher_revision": entry.get("candidate_revision"),
                "source_artifact_sha256": entry.get("source_artifact_sha256"),
                "system": cases[case_id]["system"],
                "prompt": cases[case_id]["prompt"],
                "response": response,
                "response_sha256": response_sha,
                "grade": {
                    "passed": score.get("passed", 0),
                    "failed": score.get("failed", 0),
                    "unscored": score.get("unscored", 0),
                    "total": score.get("total", 0),
                    "grader_id": (grade or {}).get("grader", {}).get("grader_id"),
                    "grader_version": (grade or {}).get("grader", {}).get("grader_version"),
                    "prompt_version": (grade or {}).get("grader", {}).get("prompt_version"),
                    "graded_at": (grade or {}).get("graded_at"),
                },
                "accepted": accepted,
                "rejection_reason": reason,
            }
        )
    rows.sort(key=lambda row: (row["teacher"] or "", row["case_id"]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response-index", type=Path, required=True)
    parser.add_argument("--grade-records", type=Path, required=True)
    parser.add_argument("--cases", type=Path, action="append",
                        help="Benchmark case suite; repeat to merge several suites (Run 42 spans "
                             "prime_benchmark_v1 plus qualification v2-v4)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--accepted-only", action="store_true", help="Write only accepted rows")
    parser.add_argument("--require-coverage", action="store_true", help="Fail unless every indexed response is graded")
    args = parser.parse_args()

    index = read_jsonl(args.response_index)
    if not index:
        parser.error(f"{args.response_index}: empty response index")
    grades = index_grades(args.grade_records)
    case_paths = args.cases or [Path("evaluation/fixtures/prime_benchmark_v1.jsonl")]
    cases: dict[str, dict[str, str]] = {}
    for case_path in case_paths:
        merged = load_cases(case_path)
        clash = set(merged) & set(cases)
        if clash:
            raise ValueError(f"{case_path}: duplicate case ids already loaded: {sorted(clash)[:5]}")
        cases.update(merged)
    rows = build_rows(index, grades, cases)

    for row in rows:
        missing = [field for field in REQUIRED_ROW_FIELDS if field not in row]
        if missing:  # pragma: no cover - build_rows always fills these
            raise ValueError(f"{row.get('case_id')}: corpus row missing {missing}")

    graded = sum(1 for row in rows if row["rejection_reason"] != "ungraded")
    if args.require_coverage and graded != len(rows):
        parser.error(f"only {graded}/{len(rows)} indexed responses carry a grade record")

    accepted = [row for row in rows if row["accepted"]]
    payload = accepted if args.accepted_only else rows
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(b"".join(canonical(row) + b"\n" for row in payload))

    reasons = Counter(row["rejection_reason"] for row in rows if not row["accepted"])
    by_teacher = Counter(row["teacher"] for row in accepted)
    manifest = {
        "schema_version": SCHEMA,
        "response_index_sha256": hashlib.sha256(args.response_index.read_bytes()).hexdigest(),
        "grade_records_sha256": hashlib.sha256(args.grade_records.read_bytes()).hexdigest(),
        "cases_sha256": hashlib.sha256(
            "".join(f"{path.name}:{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
                    for path in case_paths).encode("utf-8")).hexdigest(),
        "case_suites": [
            {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
             "cases": sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())}
            for path in case_paths
        ],
        "indexed_responses": len(rows),
        "graded_responses": graded,
        "accepted_responses": len(accepted),
        "rejected_reasons": dict(sorted(reasons.items())),
        "accepted_by_teacher": dict(sorted(by_teacher.items())),
        "corpus_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
    }
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
