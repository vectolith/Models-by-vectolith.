#!/usr/bin/env python3
"""Fail-closed local inference authorization gate for one registered Prime candidate."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

REGISTRY = Path(__file__).with_name("prime_teacher_candidate_registry.json")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_owner_waivers() -> dict[str, dict[str, Any]]:
    """Owner waivers are owner decisions, never completed reviews."""
    try:
        from evaluation.teacher_qualification_gates import load_waivers
    except ModuleNotFoundError:
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from evaluation.teacher_qualification_gates import load_waivers
    return load_waivers()


def _aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _https_evidence(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://") and len(value) > 8


def candidate_is_authorized(
    candidate: dict[str, Any], waivers: dict[str, dict[str, Any]] | None = None
) -> bool:
    """Require revision-bound legal review and a separate inference approval.

    Revision binding is never waived. The two human gates (license_review and
    training_output_permission) may be waived by the repository owner, in which
    case the caller must report review_basis=owner_waiver.
    """
    waived = set(waivers or ())
    revision = candidate.get("revision")
    legal = candidate.get("license_review_evidence")
    authorization = candidate.get("local_inference_authorization")
    conflict = candidate.get("license_evidence_conflict")

    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        return False
    if "license_review" not in waived:
        if candidate.get("license_review") != "approved_for_local_inference":
            return False
        if candidate.get("local_inference_authorized") is not True:
            return False
    if conflict and (
        not isinstance(conflict, dict)
        or conflict.get("status") != "resolved"
        or not isinstance(conflict.get("resolution"), str)
        or not conflict["resolution"].strip()
    ):
        return False

    if "license_review" in waived:
        return True
    if not isinstance(legal, dict):
        return False
    if (
        legal.get("status") != "approved"
        or legal.get("model_revision") != revision
        or not SHA256.fullmatch(str(legal.get("license_text_sha256", "")))
        or not SHA256.fullmatch(str(legal.get("review_document_sha256", "")))
        or not legal.get("reviewer_id")
        or not _aware_timestamp(legal.get("reviewed_at"))
        or not _https_evidence(legal.get("evidence_uri"))
    ):
        return False

    if not isinstance(authorization, dict):
        return False
    if (
        authorization.get("status") != "approved"
        or authorization.get("model_revision") != revision
        or not SHA256.fullmatch(str(authorization.get("document_sha256", "")))
        or not authorization.get("authorized_by")
        or not _aware_timestamp(authorization.get("authorized_at"))
        or not _https_evidence(authorization.get("evidence_uri"))
    ):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = {item["candidate_id"]: item for item in data["contributors"]}
    if args.candidate_id not in rows:
        raise SystemExit("unknown candidate")
    candidate = rows[args.candidate_id]
    waivers = load_owner_waivers()
    approved = candidate_is_authorized(candidate, waivers)

    if args.github_output:
        args.github_output.parent.mkdir(parents=True, exist_ok=True)
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.write("approved=" + ("true" if approved else "false") + "\n")
    print(json.dumps({
        "candidate_id": args.candidate_id,
        "approved": approved,
        "license_review": candidate.get("license_review"),
        "training_output_permission": candidate.get("training_output_permission"),
        "teacher_qualification": candidate.get("teacher_qualification"),
        "review_basis": "owner_waiver" if waivers else "independent_review",
        "waived_gates": sorted(waivers),
        "training_started": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
