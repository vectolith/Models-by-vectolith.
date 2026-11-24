#!/usr/bin/env python3
"""Validate the ASH PRIME protected holdout v2 and enforce split isolation.

The holdout is usable only if (a) its bytes match the manifest digest and record
count, and (b) none of its content appears in any non-holdout path of the tree.
A leak is a hard failure with the offending file, line and record reported.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT_DIR = Path("data/personality/holdout")
MANIFEST = HOLDOUT_DIR / "ash-prime-protected-holdout-v2-manifest.json"
SHINGLE_WORDS = 8
TEXT_SUFFIXES = {".jsonl", ".json", ".md", ".py", ".txt", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".csv"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
FIELDS = ("prompt", "expected_observable_behavior", "criterion", "chosen", "rejected")


class HoldoutError(ValueError):
    pass


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def _shingles(text: str, size: int = SHINGLE_WORDS) -> set[str]:
    words = _norm(text).split()
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}


def load_manifest(root: Path = ROOT) -> dict:
    path = root / MANIFEST
    if not path.is_file():
        raise HoldoutError(f"holdout manifest missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_holdout(root: Path = ROOT) -> tuple[dict, list[dict]]:
    manifest = load_manifest(root)
    path = root / manifest["path"]
    if not path.is_file():
        raise HoldoutError(f"holdout file missing: {path}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest["sha256"]:
        raise HoldoutError(f"{path}: digest mismatch: manifest {manifest['sha256']} actual {digest}")
    if len(raw) != manifest["bytes"]:
        raise HoldoutError(f"{path}: byte length {len(raw)} != manifest {manifest['bytes']}")
    records = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise HoldoutError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    if len(records) != manifest["record_count"]:
        raise HoldoutError(f"{path}: {len(records)} records != manifest {manifest['record_count']}")
    ids = [r.get("id") for r in records]
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        raise HoldoutError(f"{path}: missing or duplicate record IDs")
    if sorted(ids) != sorted(manifest["record_ids"]):
        raise HoldoutError(f"{path}: record IDs do not match manifest")
    for r in records:
        if r.get("split") != "holdout":
            raise HoldoutError(f"{path}: {r.get('id')} is not split=holdout")
        if not all(isinstance(r.get(f), str) and r.get(f, "").strip() for f in ("prompt", "criterion")):
            raise HoldoutError(f"{path}: {r.get('id')} is missing prompt or criterion")
    return manifest, records


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        yield path, rel


def check_leaks(root: Path = ROOT, holdout_dir: Path = HOLDOUT_DIR) -> None:
    manifest, records = load_holdout(root)
    probes: dict[str, str] = {}
    for record in records:
        for field in FIELDS:
            value = record.get(field)
            if isinstance(value, str) and value.strip():
                for shingle in _shingles(value):
                    probes[shingle] = f"{record['id']}.{field}"
    if not probes:
        raise HoldoutError("holdout produced no leakage probes")
    holdout_ids = set(manifest["record_ids"])
    leaks: list[str] = []
    for path, rel in iter_text_files(root):
        if holdout_dir in rel.parents or rel == MANIFEST:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lowered = _norm(text)
        for shingle, origin in probes.items():
            if shingle and shingle in lowered:
                line_no = next((i for i, l in enumerate(text.splitlines(), 1) if shingle in _norm(l)), 0)
                leaks.append(f"{rel}:{line_no}: holdout {origin} content leaked into a non-holdout path")
        for record_id in holdout_ids:
            if re.search(rf"(?<![a-z0-9-]){re.escape(record_id)}(?![a-z0-9-])", text):
                line_no = next((i for i, l in enumerate(text.splitlines(), 1) if record_id in l), 0)
                leaks.append(f"{rel}:{line_no}: holdout record ID {record_id} referenced outside the holdout")
    if leaks:
        raise HoldoutError("split isolation violated:\n  " + "\n  ".join(leaks[:50]))


def main() -> int:
    try:
        manifest, records = load_holdout()
        check_leaks()
    except HoldoutError as exc:
        print(f"HOLDOUT VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "holdout_split_isolation_validated",
        "holdout_id": manifest["holdout_id"],
        "record_count": len(records),
        "sha256": manifest["sha256"],
        "custody_status": manifest["custody"]["status"],
        "private_holdout_gate": "unverified",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
