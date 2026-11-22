#!/usr/bin/env python3
"""Validate a GGUF file's magic and produce a provenance sidecar manifest.

This checks file integrity metadata only. It does not validate model quality,
llama.cpp compatibility, PocketPal compatibility, or whether the weights are
actually Core Prime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone


GGUF_MAGIC = b"GGUF"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, model_id: str | None, revision: str | None,
           quantization: str | None) -> dict:
    if not path.is_file():
        raise ValueError(f"Not a regular file: {path}")
    size = path.stat().st_size
    if size < 4:
        raise ValueError("File is too small to contain a GGUF header")
    with path.open("rb") as stream:
        magic = stream.read(4)
    if magic != GGUF_MAGIC:
        raise ValueError(f"Invalid GGUF signature: expected GGUF, got {magic!r}")
    return {
        "schema_version": "1.0",
        "artifact": path.name,
        "size_bytes": size,
        "sha256": sha256_file(path),
        "format": "GGUF",
        "model_id": model_id,
        "revision": revision,
        "quantization": quantization,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "scope": "file_signature_and_hash_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--model-id")
    parser.add_argument("--revision")
    parser.add_argument("--quantization")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.file, args.model_id, args.revision, args.quantization)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    output = args.manifest or args.file.with_suffix(args.file.suffix + ".manifest.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Manifest written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
