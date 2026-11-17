"""Dependency-free completion/truncation classification for model response evidence."""
from __future__ import annotations

from collections import Counter
from typing import Any


def classify_completion(
    token_ids: list[int],
    max_new_tokens: int,
    eos_token_id: int | None,
    response_text: str | None,
    error: str | None = None,
) -> str:
    """Classify one generation without treating an unmarked stop as completion."""
    if error:
        return "error"
    if not token_ids or not isinstance(response_text, str) or not response_text.strip():
        return "empty_output"
    if eos_token_id is not None and eos_token_id in token_ids:
        return "eos_completed"
    if len(token_ids) >= max_new_tokens:
        return "token_cap_truncated"
    return "stopped_without_eos"


def summarize_completion(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        row.get("completion_status", "unclassified")
        for row in rows
    )
    return dict(sorted(counts.items()))
