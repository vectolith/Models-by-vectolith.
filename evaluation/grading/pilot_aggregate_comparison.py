"""Compare a newly graded 30-response pilot with the preserved aggregate reference."""
from __future__ import annotations
from collections import defaultdict
from typing import Any

def compare_pilot_aggregates(grades: list[dict[str, Any]], reference: dict[str, Any]) -> dict[str, Any]:
    order = reference.get("candidate_order")
    expected_candidates = reference.get("candidate_totals")
    expected_cases = reference.get("case_totals")
    if not isinstance(order, list) or not isinstance(expected_candidates, dict) or not isinstance(expected_cases, dict):
        raise ValueError("pilot reference is malformed")
    if len(grades) != 30:
        raise ValueError(f"pilot comparison requires exactly 30 grade records, received {len(grades)}")
    candidate_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"passed": 0, "total": 0})
    case_totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"criteria_by_candidate": {}, "passed_by_candidate": defaultdict(int)})
    seen = set()
    for grade in grades:
        candidate, case = grade.get("candidate_id"), grade.get("case_id")
        key = (candidate, case)
        if key in seen:
            raise ValueError(f"duplicate pilot grade record: {key}")
        seen.add(key)
        if candidate not in order or case not in expected_cases:
            raise ValueError(f"unexpected pilot candidate/case: {key}")
        score = grade.get("score")
        if not isinstance(score, dict) or any(
            isinstance(score.get(k), bool) or not isinstance(score.get(k), int)
            for k in ("passed", "total")
        ):
            raise ValueError(f"invalid pilot score for {key}")
        if score["passed"] < 0 or score["total"] < 1 or score["passed"] > score["total"]:
            raise ValueError(f"pilot score out of range for {key}")
        candidate_totals[candidate]["passed"] += score["passed"]
        candidate_totals[candidate]["total"] += score["total"]
        case_totals[case]["criteria_by_candidate"][candidate] = score["total"]
        case_totals[case]["passed_by_candidate"][candidate] += score["passed"]
    if len(seen) != 30 or set(candidate_totals) != set(order) or set(case_totals) != set(expected_cases):
        raise ValueError("pilot grade records do not cover all five candidates and six pilot cases")
    actual_candidates = {candidate: candidate_totals[candidate] for candidate in order}
    expected_candidate_projection = {candidate: expected_candidates[candidate] for candidate in order}
    candidate_matches = actual_candidates == expected_candidate_projection
    actual_cases = {}
    case_matches = True
    for case, expected in expected_cases.items():
        criteria_counts = [case_totals[case]["criteria_by_candidate"].get(candidate, 0) for candidate in order]
        if len(set(criteria_counts)) != 1:
            raise ValueError(f"pilot case has inconsistent rubric criterion counts: {case}")
        passed = [case_totals[case]["passed_by_candidate"].get(candidate, 0) for candidate in order]
        actual = {"criteria": criteria_counts[0], "passed": passed}
        actual_cases[case] = actual
        if actual != expected:
            case_matches = False
    return {"candidate_totals_match": candidate_matches, "case_totals_match": case_matches,
            "matches_historical_totals": candidate_matches and case_matches,
            "actual_candidate_totals": actual_candidates, "actual_case_totals": actual_cases,
            "historical_candidate_totals": expected_candidate_projection, "historical_case_totals": expected_cases,
            "note": "Aggregate comparison only; historical criterion-level decisions were not retained."}
