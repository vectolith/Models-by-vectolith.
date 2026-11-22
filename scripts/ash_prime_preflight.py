#!/usr/bin/env python3
"""Fail-closed ASH PRIME experiment evidence preflight. This does not launch training."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

REQUIRED = ("rights", "grading", "dataset", "holdout", "student", "compute", "experiment", "authorization")

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def validate(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    errors = []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"manifest unreadable/invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return ["manifest root must be an object"]
    if data.get("schema_version") != "ash-prime-training-readiness/1.0":
        errors.append("schema_version must be ash-prime-training-readiness/1.0")
    gates = data.get("gates")
    if not isinstance(gates, dict):
        return errors + ["gates must be an object"]
    base = manifest_path.parent.resolve()
    for gate in REQUIRED:
        record = gates.get(gate)
        if not isinstance(record, dict):
            errors.append(f"{gate}: missing gate record")
            continue
        if record.get("status") != "verified":
            errors.append(f"{gate}: status is not verified")
        reviewer, verified_at = record.get("reviewer"), record.get("verified_at")
        if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(verified_at, str) or not verified_at.strip():
            errors.append(f"{gate}: reviewer and verified_at required")
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{gate}: at least one artifact reference required")
            continue
        for i, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                errors.append(f"{gate}: artifact {i} malformed")
                continue
            rel, expected = artifact.get("path"), artifact.get("sha256")
            if (not isinstance(rel, str) or not rel.strip() or Path(rel).is_absolute()
                or not isinstance(expected, str) or len(expected) != 64
                or any(ch not in "0123456789abcdefABCDEF" for ch in expected)):
                errors.append(f"{gate}: artifact {i} needs a relative path and 64-char hexadecimal sha256")
                continue
            path = (base / rel).resolve()
            if not path.is_relative_to(base):
                errors.append(f"{gate}: artifact path escapes manifest directory")
                continue
            if not path.is_file():
                errors.append(f"{gate}: artifact missing: {rel}")
                continue
            if digest(path) != expected.lower():
                errors.append(f"{gate}: digest mismatch: {rel}")
    if data.get("training_authorized") is not True:
        errors.append("training_authorized must be explicitly true")
    auth_id = data.get("authorization_id")
    if not isinstance(auth_id, str) or not auth_id.strip():
        errors.append("authorization_id required")
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    errors = validate(args.manifest)
    if errors:
        print("BLOCKED")
        for error in errors:
            print("- " + error)
        return 1
    print("PREFLIGHT PASS: evidence manifest and referenced artifact digests validated.")
    print("This validator does not independently authenticate reviewers, legal conclusions, provider quotas, holdout security, or authorization.")
    print("It does not start training.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
