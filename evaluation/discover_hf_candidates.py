#!/usr/bin/env python3
"""Discover Hugging Face candidates and preserve auditable metadata evidence.

This tool reads public Hub metadata and text files only. It does not download
weights, certify legal suitability, infer output-training permission, or
appoint teachers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://huggingface.co/api/models"
RAW = "https://huggingface.co"
USER_AGENT = "vectolith-foundation-discovery/1.1"
IMMUTABLE_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
LICENSE_NAMES = {"license", "license.md", "license.txt", "copying", "copying.md"}


def request(url: str, timeout: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def get_json_page(url: str, timeout: float = 30.0) -> tuple[Any, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        link_header = response.headers.get("Link", "")
    next_url = None
    for link in link_header.split(","):
        if 'rel="next"' in link:
            match = re.search(r"<([^>]+)>", link)
            if match:
                next_url = match.group(1)
                break
    return payload, next_url


def get_json(url: str, timeout: float = 30.0) -> Any:
    return get_json_page(url, timeout)[0]


def get_text(url: str, timeout: float = 30.0) -> str | None:
    try:
        return request(url, timeout).decode("utf-8", errors="replace")
    except Exception as exc:
        # Missing files are normal; transport/auth/rate-limit errors are not.
        if getattr(exc, "code", None) in (404, 410):
            return None
        raise


def sha256_text(value: str | None) -> str | None:
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None


def discover(search: str, limit: int = 50, sort: str = "downloads") -> list[dict[str, Any]]:
    """Search the public Hub catalog, following pagination up to limit."""
    if not search.strip():
        raise ValueError("search query must not be empty")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    results: list[dict[str, Any]] = []
    page_size = min(100, limit)
    params = urllib.parse.urlencode({
        "search": search,
        "limit": page_size,
        "sort": sort,
        "direction": "-1",
    })
    next_url: str | None = f"{API}?{params}"
    while next_url and len(results) < limit:
        page, next_url = get_json_page(next_url)
        if not isinstance(page, list) or not page:
            break
        results.extend(item for item in page if isinstance(item, dict))
    return results[:limit]


def snapshot(repo_id: str) -> dict[str, Any]:
    info = get_json(f"{API}/{urllib.parse.quote(repo_id, safe='/')}?blobs=true")
    revision = info.get("sha")
    if not isinstance(revision, str) or not IMMUTABLE_SHA.fullmatch(revision):
        raise ValueError(f"{repo_id}: Hub did not return a 40-character immutable commit SHA")
    siblings = info.get("siblings") or []
    names = sorted({
        item.get("rfilename") for item in siblings
        if isinstance(item, dict) and isinstance(item.get("rfilename"), str)
    })
    license_path = next(
        (name for name in names if Path(name).name.lower() in LICENSE_NAMES),
        None,
    )
    base = f"{RAW}/{urllib.parse.quote(repo_id, safe='/')}/resolve/{revision}"
    license_url = f"{base}/{urllib.parse.quote(license_path, safe='/')}" if license_path else None
    card_url = f"{base}/README.md" if "README.md" in names else None
    license_text = get_text(license_url) if license_url else None
    card_text = get_text(card_url) if card_url else None
    card_data = info.get("cardData") or {}
    safetensors = info.get("safetensors")
    weight_files = [name for name in names if name.lower().endswith((".safetensors", ".bin", ".gguf"))]
    return {
        "schema_version": "vectolith-candidate-snapshot/1.1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "huggingface_hub_public_api",
        "repo_id": repo_id,
        "metadata_url": f"{API}/{urllib.parse.quote(repo_id, safe='/')}",
        "immutable_revision": revision.lower(),
        "private": info.get("private"),
        "gated": info.get("gated"),
        "pipeline_tag": info.get("pipeline_tag"),
        "library_name": info.get("library_name"),
        "architectures": card_data.get("architectures"),
        "parameter_count": safetensors.get("total") if isinstance(safetensors, dict) else None,
        "license_tag": card_data.get("license"),
        "license_file_path": license_path,
        "license_file_url": license_url,
        "license_file_sha256": sha256_text(license_text),
        "license_file_text": license_text,
        "license_file_present": license_text is not None,
        "license_review": "pending_human_legal_review",
        "training_output_permission": "not_verified",
        "model_card_url": card_url,
        "model_card_sha256": sha256_text(card_text),
        "model_card_text": card_text,
        "tags": info.get("tags") or [],
        "weight_files": weight_files,
        "tokenizer_files": [name for name in names if "tokenizer" in Path(name).name.lower() or Path(name).name in {"vocab.json", "merges.txt", "spiece.model"}],
        "config_files": [name for name in names if Path(name).name in {"config.json", "generation_config.json", "tokenizer_config.json", "special_tokens_map.json"}],
        "training_compatibility": "not_tested",
        "teacher_qualification": "not_qualified",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo", action="append", help="Exact Hub repo ID; repeat for multiple candidates")
    source.add_argument("--search", action="append", help="Search public Hub catalog; repeat for multiple queries")
    parser.add_argument("--limit", type=int, default=50, help="Maximum results per search query (1-1000)")
    parser.add_argument("--sort", choices=("downloads", "likes", "lastModified", "createdAt"), default="downloads")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    repo_ids: list[str] = list(args.repo or [])
    failures = 0
    if args.search:
        for query in args.search:
            try:
                matches = discover(query, args.limit, args.sort)
                repo_ids.extend(
                    item["id"] for item in matches
                    if isinstance(item.get("id"), str)
                )
                print(f"search={query!r}: discovered={len(matches)}", file=sys.stderr)
            except Exception as exc:
                failures += 1
                print(f"search={query!r}: ERROR {type(exc).__name__}: {exc}", file=sys.stderr)

    records = []
    for repo_id in dict.fromkeys(repo_ids):
        try:
            record = snapshot(repo_id)
            records.append(record)
            print(f"{repo_id}: revision={record['immutable_revision']} license={record['license_tag']} license_text={'retained' if record['license_file_text'] is not None else 'missing'}", file=sys.stderr)
        except Exception as exc:
            failures += 1
            print(f"{repo_id}: ERROR {type(exc).__name__}: {exc}", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in records), encoding="utf-8")
    print(f"Snapshots: {len(records)}; failures: {failures}; output: {args.output}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
