"""Deterministic checks; unsupported rubric criteria remain unscored."""
from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation
from typing import Any

SUPPORTED = {"exact_match", "decimal", "max_words", "min_words", "bullet_count", "required_literal"}

def _result(status: str, method: str, evidence: str, rationale: str) -> dict[str, Any]:
    return {"status": status, "method": method, "evidence_excerpt": evidence[:500], "rationale": rationale}

def check_criterion(response: str, criterion: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, str) or not isinstance(criterion, dict):
        raise ValueError("response and criterion object are required")
    kind = criterion.get("check")
    if kind not in SUPPORTED:
        return _result("unscored", "deterministic", "", "No supported deterministic check is declared.")
    text = response.strip()
    if kind == "exact_match":
        expected = criterion.get("expected")
        if not isinstance(expected, str): raise ValueError("exact_match requires expected string")
        passed = text == expected.strip()
    elif kind == "decimal":
        try:
            observed, expected = Decimal(text), Decimal(str(criterion["expected"]))
            tolerance = Decimal(str(criterion.get("absolute_tolerance", "0")))
        except (KeyError, InvalidOperation, ValueError) as exc:
            return _result("unscored", kind, text, f"Strict decimal parse failed: {exc}")
        if not all(x.is_finite() for x in (observed, expected, tolerance)) or tolerance < 0:
            return _result("unscored", kind, text, "Decimal values or tolerance are invalid.")
        passed = abs(observed - expected) <= tolerance
    elif kind in {"max_words", "min_words"}:
        limit = criterion.get("limit")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError(f"{kind} requires a non-negative integer limit")
        count = len(re.findall(r"\S+", text))
        passed = count <= limit if kind == "max_words" else count >= limit
    elif kind == "bullet_count":
        expected = criterion.get("count")
        if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
            raise ValueError("bullet_count requires a non-negative integer count")
        count = sum(1 for line in response.splitlines() if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line))
        passed = count == expected
    else:
        literal = criterion.get("literal")
        if not isinstance(literal, str) or not literal: raise ValueError("required_literal requires literal")
        passed = literal in response
    return _result("passed" if passed else "failed", kind, text, f"Deterministic check {kind}: {'passed' if passed else 'failed'}.")

def evaluate_rubric(response: str, rubric: list[Any]) -> list[dict[str, Any]]:
    if not isinstance(rubric, list) or not rubric: raise ValueError("rubric must be a non-empty list")
    results = []
    for index, item in enumerate(rubric):
        cid = item.get("criterion_id") or item.get("id") or f"criterion-{index + 1:02d}" if isinstance(item, dict) else f"criterion-{index + 1:02d}"
        result = check_criterion(response, item) if isinstance(item, dict) else _result("unscored", "deterministic", "", "Natural-language criteria require semantic grading.")
        results.append({"criterion_id": str(cid), **result})
    return results
