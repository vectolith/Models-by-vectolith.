#!/usr/bin/env python3
"""Capture public Hugging Face model-card/license evidence at an exact commit SHA."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://huggingface.co/api/models"
RAW = "https://huggingface.co"
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.md"}
USER_AGENT = "vectolith-teacher-qualification-intake/1.0"


def request(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def sha256_text(value: str | None) -> str | None:
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None


def get_text(url: str | None) -> str | None:
    if url is None:
        return None
    try:
        return request(url).decode("utf-8", errors="replace")
    except Exception as exc:
        if getattr(exc, "code", None) in (404, 410):
            return None
        raise


def snapshot(repo_id: str, revision: str) -> dict[str, Any]:
    if not SHA_RE.fullmatch(revision):
        raise ValueError("revision must be a full immutable 40-character commit SHA")
    revision = revision.lower()
    encoded_repo = urllib.parse.quote(repo_id, safe="/")
    endpoint = f"{API}/{encoded_repo}/revision/{revision}?blobs=true"
    info = json.loads(request(endpoint).decode("utf-8"))
    actual_sha = str(info.get("sha") or "").lower()
    if actual_sha != revision:
        raise ValueError(f"Hub revision mismatch: requested {revision}, received {actual_sha!r}")
    if info.get("private") or info.get("gated") or info.get("disabled"):
        raise ValueError(
            f"model is not publicly accessible: gated={info.get('gated')}, "
            f"private={info.get('private')}, disabled={info.get('disabled')}"
        )

    names = sorted({
        item["rfilename"] for item in (info.get("siblings") or [])
        if isinstance(item, dict) and isinstance(item.get("rfilename"), str)
    })
    license_path = next((
        name for name in names if Path(name).name.lower() in LICENSE_NAMES
    ), None)
    base = f"{RAW}/{encoded_repo}/resolve/{revision}"
    license_url = (
        f"{base}/{urllib.parse.quote(license_path, safe='/')}"
        if license_path else None
    )
    card_path = next((name for name in names if Path(name).name.lower() == "readme.md"), None)
    card_url = f"{base}/{urllib.parse.quote(card_path, safe='/')}" if card_path else None
    license_text = get_text(license_url)
    card_text = get_text(card_url)
    card_data = info.get("cardData") or {}
    safetensors = info.get("safetensors")
    return {
        "schema_version": "vectolith-candidate-snapshot/1.2",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "huggingface_hub_public_api_at_immutable_revision",
        "repo_id": repo_id,
        "immutable_revision": revision,
        "metadata_url": endpoint,
        "private": info.get("private"),
        "gated": info.get("gated"),
        "disabled": info.get("disabled"),
        "license_tag": card_data.get("license"),
        "license_file_path": license_path,
        "license_file_url": license_url,
        "license_file_text": license_text,
        "license_file_sha256": sha256_text(license_text),
        "license_file_present": license_text is not None,
        "license_review": "not_evaluated",
        "training_output_permission": "not_evaluated",
        "model_card_path": card_path,
        "model_card_url": card_url,
        "model_card_text": card_text,
        "model_card_sha256": sha256_text(card_text),
        "architectures": card_data.get("architectures"),
        "parameter_count": safetensors.get("total") if isinstance(safetensors, dict) else None,
        "weight_files": [name for name in names if name.lower().endswith((".safetensors", ".bin", ".gguf"))],
        "tokenizer_files": [name for name in names if "tokenizer" in Path(name).name.lower()],
        "config_files": [name for name in names if Path(name).name in {
            "config.json", "generation_config.json", "tokenizer_config.json", "special_tokens_map.json"
        }],
        "teacher_qualification": "not_evaluated",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    record = snapshot(args.repo, args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Captured pinned metadata for {args.repo}@{record['immutable_revision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
