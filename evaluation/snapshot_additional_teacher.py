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


# Candidates whose Hub snapshot legitimately ships no LICENSE file. Tag-only evidence
# is accepted only for these, only with the explicit CLI flag, and the manifest always
# records the caveat that a model-card tag is metadata, not licence text.
TAG_ONLY_LICENSE_EVIDENCE_CANDIDATES = frozenset({"smollm3-3b"})

TAG_ONLY_LICENSE_EVIDENCE_CAVEAT = (
    "Snapshot contains no LICENSE or NOTICE file. Licence status rests on the model-card "
    "tag alone, which is Hub metadata and not licence text; it is not a substitute for a "
    "bundled licence file and must be re-reviewed if the upstream card changes."
)


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
    accept_tag_only_license_evidence: bool = False,
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
    named_license_tag = str(card.get("license_name") or card.get("license") or "").lower()
    tag_only_accepted = bool(
        accept_tag_only_license_evidence and not license_files and named_license_tag
    )
    license_file_status = "present" if license_files else "missing"
    if license_files:
        validation_status = "complete"
        license_evidence_basis = "license_file"
    elif tag_only_accepted:
        validation_status = "complete_with_tag_only_license_evidence"
        license_evidence_basis = "model_card_tag_only"
    else:
        validation_status = "blocked_missing_license_file"
        license_evidence_basis = "none"

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
        "license_evidence_basis": license_evidence_basis,
        "license_evidence_caveat": (
            TAG_ONLY_LICENSE_EVIDENCE_CAVEAT if tag_only_accepted else None
        ),
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
    parser.add_argument(
        "--accept-model-card-tag-evidence",
        action="store_true",
        help=(
            "Accept the model-card licence tag as the licence evidence basis when the "
            "snapshot ships no LICENSE file. Only valid for candidates in "
            "TAG_ONLY_LICENSE_EVIDENCE_CANDIDATES; the manifest records the caveat."
        ),
    )
    args = parser.parse_args()
    if (
        args.accept_model_card_tag_evidence
        and args.candidate_id not in TAG_ONLY_LICENSE_EVIDENCE_CANDIDATES
    ):
        parser.error(
            f"--accept-model-card-tag-evidence is not enabled for {args.candidate_id}; "
            f"allowed: {sorted(TAG_ONLY_LICENSE_EVIDENCE_CANDIDATES)}"
        )

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
        accept_tag_only_license_evidence=args.accept_model_card_tag_evidence,
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
        if manifest["license_evidence_basis"] == "model_card_tag_only":
            print(
                "Snapshot manifest preserved; inference proceeds on TAG-ONLY licence "
                "evidence. CAVEAT: "
                + TAG_ONLY_LICENSE_EVIDENCE_CAVEAT,
                flush=True,
            )
            return 0
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
