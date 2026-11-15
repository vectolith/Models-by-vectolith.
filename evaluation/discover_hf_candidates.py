#!/usr/bin/env python3
"""Snapshot public Hugging Face model metadata at immutable revisions.

This discovers metadata only. It does not download weights, certify license
compatibility, infer training-output permissions, or appoint teachers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://huggingface.co/api/models"
RAW = "https://huggingface.co"


def get_json(url: str, timeout: float = 30.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "vectolith-foundation-discovery/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_text(url: str, timeout: float = 30.0) -> str | None:
    request = urllib.request.Request(url, headers={"User-Agent": "vectolith-foundation-discovery/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            return None
        raise


def snapshot(repo_id: str) -> dict[str, Any]:
    info = get_json(f"{API}/{repo_id}?blobs=true")
    revision = info.get("sha")
    if not isinstance(revision, str) or len(revision) < 40:
        raise ValueError(f"{repo_id}: Hub did not return an immutable commit SHA")
    siblings = info.get("siblings") or []
    names = {item.get("rfilename") for item in siblings if isinstance(item, dict)}
    license_path = next((name for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING") if name in names), None)
    license_text = get_text(f"{RAW}/{repo_id}/resolve/{revision}/{license_path}") if license_path else None
    card = get_text(f"{RAW}/{repo_id}/resolve/{revision}/README.md") if "README.md" in names else None
    tags = info.get("tags") or []
    card_data = info.get("cardData") or {}
    return {
        "schema_version": "vectolith-candidate-snapshot/1.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "huggingface_hub_public_api",
        "repo_id": repo_id,
        "immutable_revision": revision,
        "private": info.get("private"),
        "gated": info.get("gated"),
        "pipeline_tag": info.get("pipeline_tag"),
        "library_name": info.get("library_name"),
        "architectures": card_data.get("architectures"),
        "parameter_count": info.get("safetensors", {}).get("total") if isinstance(info.get("safetensors"), dict) else None,
        "license_tag": card_data.get("license"),
        "license_file_path": license_path,
        "license_file_sha256": hashlib.sha256(license_text.encode("utf-8")).hexdigest() if license_text is not None else None,
        "license_file_present": license_text is not None,
        "license_review": "pending_human_legal_review",
        "training_output_permission": "not_verified",
        "tags": tags,
        "model_card_sha256": hashlib.sha256(card.encode("utf-8")).hexdigest() if card is not None else None,
        "weight_files": [name for name in sorted(names) if name.endswith((".safetensors", ".bin", ".gguf"))],
        "training_compatibility": "not_tested",
        "teacher_qualification": "not_qualified",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", required=True, help="Hugging Face repo ID; repeat for multiple candidates")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    records = []
    failures = 0
    for repo_id in args.repo:
        try:
            record = snapshot(repo_id)
            records.append(record)
            print(f"{repo_id}: revision={record['immutable_revision']} license={record['license_tag']} license_file={record['license_file_present']}", file=sys.stderr)
        except Exception as exc:
            failures += 1
            print(f"{repo_id}: ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in records), encoding="utf-8")
    print(f"Snapshots: {len(records)}; failures: {failures}; output: {args.output}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
