#!/usr/bin/env python3
"""Resolve and snapshot an additive ASH PRIME teacher at an immutable Hub revision."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


EXPECTED = {
    "smollm3-3b": {
        "repo": "HuggingFaceTB/SmolLM3-3B",
        "license": "apache-2.0",
        "model_type": "smollm3",
        "architectures": ["SmolLM3ForCausalLM"],
    },
    "lfm2.5-2.6b": {
        "repo": "LiquidAI/LFM2.5-2.6B",
        "license": "lfm1.0",
        "model_type": "lfm2",
        "architectures": ["Lfm2ForCausalLM"],
    },
    "phi-4-mini-instruct": {
        "repo": "microsoft/Phi-4-mini-instruct",
        "license": "mit",
        "model_type": "phi3",
        "architectures": ["Phi3ForCausalLM"],
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    *,
    candidate_id: str,
    expected: dict,
    requested_revision: str,
    revision: str,
    info,
    snapshot: Path,
    config: dict,
    files: list[dict],
) -> dict:
    card = info.card_data.to_dict() if info.card_data else {}
    license_files = [
        item for item in files
        if Path(item["path"]).name.upper().startswith("LICENSE")
    ]
    license_card_evidence = {
        key: card[key]
        for key in ("license", "license_name", "license_link", "license_url")
        if card.get(key) not in (None, "")
    }
    license_file_status = "present" if license_files else "missing"
    validation_status = (
        "complete" if license_files else "blocked_missing_license_file"
    )

    return {
        "schema_version": "vectolith-teacher-snapshot/1.1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "candidate_id": candidate_id,
        "repo_id": expected["repo"],
        "requested_revision": requested_revision,
        "immutable_revision": revision,
        "last_modified": info.last_modified.isoformat() if info.last_modified else None,
        "model_type": config["model_type"],
        "architectures": config["architectures"],
        "license_tag": str(card.get("license_name") or card.get("license") or "").lower(),
        "model_card_license_evidence": license_card_evidence,
        "license_file_status": license_file_status,
        "license_files": license_files,
        "snapshot_validation_status": validation_status,
        "license_review": "pending_human_legal_review",
        "training_output_permission": "not_verified",
        "teacher_qualification": "not_qualified",
        "snapshot_path_revision": snapshot.name,
        "snapshot_size_bytes": sum(item["size_bytes"] for item in files),
        "file_count": len(files),
        "files": files,
        "config": config,
        "snapshot_is_immutable": True,
        "training_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", choices=EXPECTED, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--revision", default="main")
    args = parser.parse_args()

    from huggingface_hub import HfApi, snapshot_download

    expected = EXPECTED[args.candidate_id]
    api = HfApi()
    info = api.model_info(expected["repo"], revision=args.revision, files_metadata=True)
    revision = (info.sha or "").lower()
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise RuntimeError(f"Hub did not return a full immutable commit SHA for {expected['repo']}")
    if info.gated or info.private or info.disabled:
        raise RuntimeError(f"Candidate is not publicly snapshot-accessible: gated={info.gated}, private={info.private}, disabled={info.disabled}")

    card = info.card_data.to_dict() if info.card_data else {}
    observed_license = str(card.get("license_name") or card.get("license") or "").lower()
    if observed_license != expected["license"]:
        raise RuntimeError(f"License tag mismatch: expected {expected['license']}, observed {observed_license!r}")

    snapshot = Path(snapshot_download(
        repo_id=expected["repo"],
        revision=revision,
        cache_dir=str(args.cache_dir),
    ))
    if snapshot.name != revision:
        raise RuntimeError(f"Downloaded snapshot {snapshot.name!r} does not match pinned SHA {revision}")

    config_path = snapshot / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("model_type") != expected["model_type"]:
        raise RuntimeError(f"Unexpected model_type: {config.get('model_type')!r}")
    if config.get("architectures") != expected["architectures"]:
        raise RuntimeError(f"Unexpected architectures: {config.get('architectures')!r}")

    files = []
    for path in sorted(p for p in snapshot.rglob("*") if p.is_file()):
        files.append({
            "path": path.relative_to(snapshot).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    manifest = build_manifest(
        candidate_id=args.candidate_id,
        expected=expected,
        requested_revision=args.revision,
        revision=revision,
        info=info,
        snapshot=snapshot,
        config=config,
        files=files,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidate_id": args.candidate_id,
        "repo_id": expected["repo"],
        "immutable_revision": revision,
        "file_count": len(files),
        "snapshot_size_bytes": manifest["snapshot_size_bytes"],
        "license_file_status": manifest["license_file_status"],
        "snapshot_validation_status": manifest["snapshot_validation_status"],
        "manifest": str(args.output),
    }, sort_keys=True), flush=True)

    if not manifest["license_files"]:
        print(
            "Snapshot manifest preserved, but inference is blocked because the "
            "snapshot contains no license file; model-card license metadata is "
            "not treated as a substitute for the missing file.",
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
