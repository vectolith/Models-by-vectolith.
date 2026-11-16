#!/usr/bin/env python3
"""Summarize independent human rubric grades without inventing an automatic quality score."""
from __future__ import annotations

import argparse
import json
import statistics
from itertools import combinations
from collections import defaultdict
from pathlib import Path
from typing import Any

GRADE_SCHEMA = "vectolith-human-grading/1.0"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{number}: invalid JSON: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number}: each line must be a JSON object")
            rows.append(value)
    return rows


def evidence_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        required = ("benchmark_case_id", "candidate_id", "model_revision", "role", "category")
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in required):
            raise ValueError("evidence row is missing case, candidate, revision, role, or category")
        key = tuple(row[name] for name in required) + (row.get("started_at", ""),)
        if key in indexed:
            raise ValueError(f"duplicate evidence identity: {key}")
        if (not isinstance(row.get("rubric"), list) or not row["rubric"]
                or any(not isinstance(item, str) or not item.strip() for item in row["rubric"])
                or len(set(row["rubric"])) != len(row["rubric"])):
            raise ValueError(f"evidence row {key} has invalid or duplicate rubric criteria")
        indexed[key] = row
    return indexed


def validate_grades(
    evidence: dict[tuple[str, str, str, str, str, str], dict[str, Any]],
    grades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str, str, str]] = set()
    validated: list[dict[str, Any]] = []
    for number, grade in enumerate(grades, start=1):
        if grade.get("schema_version") != GRADE_SCHEMA:
            raise ValueError(f"grade {number}: schema_version must be {GRADE_SCHEMA}")
        identity_fields = ("benchmark_case_id", "candidate_id", "model_revision", "role")
        if any(not isinstance(grade.get(key), str) or not grade[key].strip() for key in identity_fields):
            raise ValueError(f"grade {number}: missing candidate/case/revision/role identity")
        if not isinstance(grade.get("evaluator_id"), str) or not grade["evaluator_id"].strip():
            raise ValueError(f"grade {number}: evaluator_id is required")
        if not isinstance(grade.get("evaluator_version"), str) or not grade["evaluator_version"].strip():
            raise ValueError(f"grade {number}: evaluator_version is required")
        if not isinstance(grade.get("run_id"), str) or not grade["run_id"].strip():
            raise ValueError(f"grade {number}: run_id is required")
        if not isinstance(grade.get("evidence_started_at", ""), str):
            raise ValueError(f"grade {number}: evidence_started_at must be text")
        key = tuple(grade[name] for name in identity_fields) + (grade.get("category", ""), grade.get("evidence_started_at", ""))
        if key not in evidence:
            raise ValueError(f"grade {number}: no matching raw evidence row for {key}")
        unique = key + (grade["evaluator_id"],)
        if unique in seen:
            raise ValueError(f"grade {number}: duplicate grade from evaluator for {key}")
        seen.add(unique)
        if evidence[key].get("error") or (evidence[key].get("response_text") is None and not evidence[key].get("tool_calls")):
            raise ValueError(f"grade {number}: matching raw evidence has no successful model response")
        criteria = evidence[key]["rubric"]
        scores = grade.get("rubric_scores")
        if not isinstance(scores, list):
            raise ValueError(f"grade {number}: rubric_scores must be a list")
        by_criterion: dict[str, dict[str, Any]] = {}
        for item in scores:
            if not isinstance(item, dict):
                raise ValueError(f"grade {number}: each rubric score must be an object")
            criterion = item.get("criterion")
            score = item.get("score")
            if not isinstance(criterion, str) or not criterion.strip():
                raise ValueError(f"grade {number}: criterion must be non-empty text")
            if criterion not in criteria:
                raise ValueError(f"grade {number}: unknown rubric criterion {criterion!r}")
            if criterion in by_criterion:
                raise ValueError(f"grade {number}: duplicate criterion {criterion!r}")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 4:
                raise ValueError(f"grade {number}: score for {criterion!r} must be numeric 0..4")
            notes = item.get("notes", "")
            if not isinstance(notes, str):
                raise ValueError(f"grade {number}: notes must be text")
            by_criterion[criterion] = {"score": float(score), "notes": notes}
        if set(by_criterion) != set(criteria):
            missing = sorted(set(criteria) - set(by_criterion))
            raise ValueError(f"grade {number}: every rubric criterion must be scored; missing {missing}")
        validated.append({
            "key": key,
            "evaluator_id": grade["evaluator_id"],
            "evaluator_version": grade["evaluator_version"],
            "run_id": grade["run_id"],
            "scores": by_criterion,
        })
    return validated



def inter_rater_agreement(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute pairwise quadratic-weighted Cohen kappa and exact agreement by case."""
    ratings: dict[str, dict[str, float]] = defaultdict(dict)
    for item in observations:
        ratings[item["case_id"]][item["evaluator_id"]] = float(item["score"])
    evaluator_ids = sorted({evaluator for values in ratings.values() for evaluator in values})
    kappas = []
    exact_matches = 0
    paired_count = 0
    eligible_pairs = 0
    for left_id, right_id in combinations(evaluator_ids, 2):
        paired = [
            (values[left_id], values[right_id])
            for values in ratings.values()
            if left_id in values and right_id in values
        ]
        if len(paired) < 2:
            continue
        eligible_pairs += 1
        paired_count += len(paired)
        exact_matches += sum(1 for left, right in paired if left == right)
        observed_disagreement = sum(((left - right) ** 2) / 16 for left, right in paired) / len(paired)
        left_counts = {score: sum(1 for left, _ in paired if left == score) / len(paired) for score in range(5)}
        right_counts = {score: sum(1 for _, right in paired if right == score) / len(paired) for score in range(5)}
        expected_disagreement = sum(
            left_counts[left] * right_counts[right] * ((left - right) ** 2) / 16
            for left in range(5) for right in range(5)
        )
        if expected_disagreement == 0:
            kappa = 1.0 if observed_disagreement == 0 else None
        else:
            kappa = 1.0 - observed_disagreement / expected_disagreement
        if kappa is not None:
            kappas.append(kappa)
    return {
        "method": "mean_pairwise_quadratic_weighted_cohen_kappa",
        "eligible_evaluator_pairs": eligible_pairs,
        "paired_case_ratings": paired_count,
        "mean_weighted_kappa": round(statistics.fmean(kappas), 4) if kappas else None,
        "exact_agreement_rate": round(exact_matches / paired_count, 4) if paired_count else None,
        "status": "computed" if kappas else "insufficient_paired_ratings",
    }

def build_report(
    evidence_rows: list[dict[str, Any]],
    grades: list[dict[str, Any]],
    min_evaluators: int = 2,
    min_cases: int = 3,
    minimum_mean: float = 3.0,
) -> dict[str, Any]:
    if min_evaluators < 1 or min_cases < 1 or not 0 <= minimum_mean <= 4:
        raise ValueError("thresholds must be positive; minimum_mean must be 0..4")
    indexed = evidence_index(evidence_rows)
    validated = validate_grades(indexed, grades)
    buckets: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for grade in validated:
        role, candidate, revision, category = grade["key"][3], grade["key"][1], grade["key"][2], grade["key"][4]
        for criterion, item in grade["scores"].items():
            buckets[(role, candidate, revision, category, criterion)].append({
                "score": item["score"], "evaluator_id": grade["evaluator_id"],
                "evaluator_version": grade["evaluator_version"], "case_id": grade["key"][0],
                "run_id": grade["run_id"],
            })

    rows = []
    for key in sorted(buckets):
        role, candidate, revision, category, criterion = key
        observations = buckets[key]
        case_ids = sorted({item["case_id"] for item in observations})
        evaluators = sorted({item["evaluator_id"] for item in observations})
        scores = [item["score"] for item in observations]
        mean = statistics.fmean(scores)
        agreement = inter_rater_agreement(observations)
        if len(evaluators) < min_evaluators:
            status = "insufficient_independent_evaluators"
        elif len(case_ids) < min_cases:
            status = "insufficient_cases"
        elif mean < minimum_mean:
            status = "below_threshold"
        else:
            status = "rubric_threshold_met"
        rows.append({
            "role": role, "candidate_id": candidate, "model_revision": revision,
            "category": category, "criterion": criterion, "case_count": len(case_ids),
            "grade_count": len(scores), "evaluator_count": len(evaluators),
            "mean_score_0_to_4": round(mean, 4),
            "population_stddev": round(statistics.pstdev(scores), 4) if len(scores) > 1 else 0.0,
            "inter_rater_agreement": agreement,
            "status": status,
        })
    return {
        "schema_version": "vectolith-rubric-summary/1.0",
        "grading_scale": {"minimum": 0, "maximum": 4, "meaning": "Human rubric score; scoring anchors must be defined in the evaluation protocol."},
        "thresholds": {"minimum_independent_evaluators": min_evaluators, "minimum_cases_per_criterion": min_cases, "minimum_mean_score": minimum_mean},
        "evidence_rows": len(evidence_rows),
        "grade_rows": len(validated),
        "criterion_results": rows,
        "qualification_decision": "not_made",
        "qualification_note": "This report is descriptive evidence only. It does not appoint teachers, select a foundation, or replace legal, compute, ablation, holdout, or release gates.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path, help="Raw evaluation JSONL from run_eval.py")
    parser.add_argument("--grades", required=True, type=Path, help="Independent human rubric grades JSONL")
    parser.add_argument("--output", required=True, type=Path, help="Summary JSON output")
    parser.add_argument("--min-evaluators", type=int, default=2)
    parser.add_argument("--min-cases", type=int, default=3)
    parser.add_argument("--minimum-mean", type=float, default=3.0)
    args = parser.parse_args(argv)
    try:
        report = build_report(read_jsonl(args.evidence), read_jsonl(args.grades),
                              args.min_evaluators, args.min_cases, args.minimum_mean)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Summarized {report['grade_rows']} human grades across {len(report['criterion_results'])} criteria")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
