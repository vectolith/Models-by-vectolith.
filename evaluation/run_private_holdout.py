#!/usr/bin/env python3
"""Run a restricted holdout without placing prompts or outputs in the public repository."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

from evaluation.run_eval import RunConfig, load_cases, run_case

MANIFEST_SCHEMA = "vectolith-private-holdout-manifest/1.0"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _outside_repo(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve(strict=True)
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise ValueError(f"{label} must be outside the public repository")
    return resolved


def _private_permissions(path: Path, *, directory: bool = False) -> None:
    if os.name == "posix":
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            kind = "directory" if directory else "file"
            raise ValueError(f"{kind} permissions must deny group and other access (use 0700/0600)")


def load_private_holdout(
    suite_path: Path,
    manifest_path: Path,
    expected_sha256: str,
    expected_version: str,
    role: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    suite = _outside_repo(suite_path, "private holdout suite")
    manifest_file = _outside_repo(manifest_path, "private holdout manifest")
    if not suite.is_file() or not manifest_file.is_file():
        raise ValueError("private holdout suite and manifest must be regular files")
    _private_permissions(suite)
    _private_permissions(manifest_file)
    _private_permissions(suite.parent, directory=True)
    _private_permissions(manifest_file.parent, directory=True)

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError(f"manifest schema_version must be {MANIFEST_SCHEMA}")
    if manifest.get("dataset_version") != expected_version or not expected_version:
        raise ValueError("private holdout dataset version does not match the protected expected version")
    digest = hashlib.sha256(suite.read_bytes()).hexdigest()
    if digest != expected_sha256 or manifest.get("sha256") != digest:
        raise ValueError("private holdout SHA-256 does not match the protected expected digest and manifest")
    if manifest.get("access_control") != "restricted":
        raise ValueError("manifest must explicitly declare access_control=restricted")
    allowed_roles = manifest.get("authorized_roles")
    if not isinstance(allowed_roles, list) or role not in allowed_roles:
        raise ValueError(f"role {role!r} is not authorized by the private holdout manifest")
    cases = load_cases(suite)
    if manifest.get("case_count") != len(cases):
        raise ValueError("manifest case_count does not match the private holdout suite")
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("private holdout case IDs must be unique")
    return cases, {
        "dataset_version": expected_version,
        "sha256": digest,
        "case_count": len(cases),
        "role": role,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=os.environ.get("VECTOLITH_PRIVATE_HOLDOUT_PATH"))
    parser.add_argument("--manifest", type=Path, default=os.environ.get("VECTOLITH_PRIVATE_HOLDOUT_MANIFEST"))
    parser.add_argument("--expected-sha256", default=os.environ.get("VECTOLITH_PRIVATE_HOLDOUT_SHA256"))
    parser.add_argument("--expected-version", default=os.environ.get("VECTOLITH_PRIVATE_HOLDOUT_VERSION"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--role", choices=("core_prime", "core_prima"), required=True)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--api-key-env", default="VECTOLITH_INFERENCE_API_KEY")
    args = parser.parse_args(argv)
    if not args.suite or not args.manifest or not args.expected_sha256 or not args.expected_version:
        parser.error("private suite, manifest, expected SHA-256 and expected version must be supplied via flags or protected environment variables")
    if len(args.expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in args.expected_sha256.lower()):
        parser.error("--expected-sha256 must be a 64-character hexadecimal digest")
    try:
        cases, holdout = load_private_holdout(
            args.suite, args.manifest, args.expected_sha256.lower(),
            args.expected_version, args.role,
        )
        output = args.output.expanduser().resolve()
        if output == REPO_ROOT or REPO_ROOT in output.parents:
            raise ValueError("private holdout output must be outside the public repository")
        output.parent.mkdir(parents=True, exist_ok=True)
        _private_permissions(output.parent, directory=True)
        if output.exists():
            _private_permissions(output)
        config = RunConfig(
            base_url=args.base_url, model=args.model, role=args.role,
            candidate_id=args.candidate_id, revision=args.revision,
            temperature=args.temperature, top_p=args.top_p,
            max_tokens=args.max_tokens, timeout_seconds=args.timeout,
            api_key=os.environ.get(args.api_key_env),
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        fd = os.open(output, flags, 0o600)
        failures = 0
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for case in cases:
                record = run_case(case, config)
                record["holdout_dataset_version"] = holdout["dataset_version"]
                record["holdout_sha256"] = holdout["sha256"]
                record["holdout_role"] = holdout["role"]
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                failures += int(bool(record.get("error")))
        print(json.dumps({
            "dataset_version": holdout["dataset_version"],
            "dataset_sha256": holdout["sha256"],
            "cases": len(cases),
            "request_failures": failures,
            "raw_output_path": str(output),
            "raw_outputs_are_private": True,
        }, sort_keys=True))
        return 1 if failures else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
