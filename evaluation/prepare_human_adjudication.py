#!/usr/bin/env python3
"""Create and validate separate append-only adjudication records for human-grade disagreements."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "vectolith-human-adjudication/1.0"
KEY_FIELDS = (
    "candidate_id", "model_revision", "role", "run_id",
    "benchmark_case_id", "evidence_started_at", "category",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{number}: expected a JSON object")
        rows.append(item)
    return rows


def disagreement_records(grades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], dict[str, Any]] = defaultdict(dict)
    metadata: dict[tuple[str, ...], dict[str, Any]] = {}
    for grade in grades:
        for score in grade.get("rubric_scores", []):
            key = (
                grade["candidate_id"], grade["model_revision"], grade["role"],
                grade["run_id"], grade["benchmark_case_id"],
                grade["evidence_started_at"], grade["category"], score["criterion"],
            )
            if grade["evaluator_id"] in grouped[key]:
                raise ValueError(f"duplicate reviewer score for adjudication key: {key}")
            grouped[key][grade["evaluator_id"]] = {
                "evaluator_id": grade["evaluator_id"],
                "score": score["score"],
                "notes": score.get("notes", ""),
            }
            metadata[key] = {
                field: grade[field] for field in KEY_FIELDS
            }
    records = []
    for key, reviewers in sorted(grouped.items()):
        if len(reviewers) < 2 or len({item["score"] for item in reviewers.values()}) < 2:
            continue
        identity = json.dumps([*key], separators=(",", ":"), ensure_ascii=False)
        adjudication_id = "adjudicate-" + hashlib.sha256(identity.encode()).hexdigest()[:24]
        criterion = key[-1]
        records.append({
            "schema_version": SCHEMA,
            "adjudication_id": adjudication_id,
            **metadata[key],
            "criterion": criterion,
            "reviewer_scores": [reviewers[evaluator] for evaluator in sorted(reviewers)],
            "adjudicator_id": "",
            "decision_score": None,
            "rationale": "",
            "adjudicated_at": "",
            "status": "pending",
        })
    return records


def validate_adjudications(
    grades: list[dict[str, Any]],
    adjudications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    expected = {row["adjudication_id"]: row for row in disagreement_records(grades)}
    seen = set()
    validated = []
    for number, item in enumerate(adjudications, 1):
        if item.get("schema_version") != SCHEMA:
            raise ValueError(f"adjudication {number}: unsupported schema")
        adjudication_id = item.get("adjudication_id")
        if adjudication_id not in expected:
            raise ValueError(f"adjudication {number}: unknown or non-disagreement record")
        if adjudication_id in seen:
            raise ValueError(f"adjudication {number}: duplicate adjudication ID")
        seen.add(adjudication_id)
        source = expected[adjudication_id]
        for field in (*KEY_FIELDS, "criterion", "reviewer_scores"):
            if item.get(field) != source.get(field):
                raise ValueError(f"adjudication {number}: immutable source field changed: {field}")
        adjudicator = item.get("adjudicator_id")
        if not isinstance(adjudicator, str) or not adjudicator.strip():
            raise ValueError(f"adjudication {number}: adjudicator_id is required")
        if adjudicator in {x["evaluator_id"] for x in source["reviewer_scores"]}:
            raise ValueError(f"adjudication {number}: adjudicator must be independent of the reviewers")
        score = item.get("decision_score")
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 4:
            raise ValueError(f"adjudication {number}: decision_score must be an integer from 0 to 4")
        rationale = item.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"adjudication {number}: rationale is required")
        timestamp = item.get("adjudicated_at")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(f"adjudication {number}: adjudicated_at is required")
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"adjudication {number}: adjudicated_at must be ISO-8601") from exc
        if item.get("status") != "adjudicated":
            raise ValueError(f"adjudication {number}: status must be adjudicated")
        validated.append(dict(item))
    if seen != set(expected):
        raise ValueError(f"incomplete adjudication: missing {len(set(expected) - seen)} disagreements")
    return validated


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--grades", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--grades", type=Path, required=True)
    validate.add_argument("--adjudications", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    grades = read_jsonl(args.grades)
    if args.command == "prepare":
        records = disagreement_records(grades)
        write_jsonl(args.output, records)
        print(json.dumps({"disagreement_count": len(records), "qualification_decision": "not_made"}))
        return 0
    completed = validate_adjudications(grades, read_jsonl(args.adjudications))
    write_jsonl(args.output, completed)
    print(json.dumps({"adjudicated_count": len(completed), "qualification_decision": "not_made"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
