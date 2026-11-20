#!/usr/bin/env python3
"""Capture exact-revision public model LICENSE/NOTICE/model-card bytes without downloading weights."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPDX_LICENSE_LIST_COMMIT = "31ba1a50e5397e00a304dbadc76531740e89ee48"
SPDX_LICENSE_IDS = {"apache-2.0": "Apache-2.0", "mit": "MIT"}
CANDIDATES: dict[str, dict[str, Any]] = {
    "granite-3.1-3b-a800m": {
        "repo_id": "ibm-granite/granite-3.1-3b-a800m-instruct",
        "revision": "a02780686e08a03fe0d2679a293b5c74a90efa89",
    },
    "granite-4.2-3b": {
        "repo_id": "ibm-granite/granite-4.2-3b",
        "revision": "4e9c275e232f10211ec88644d106a1f6a1b60e06",
    },
    "minicpm5-2b": {
        "repo_id": "openbmb/MiniCPM5-2B",
        "revision": "42433e90dad95123ab87729fd7011e7110629556",
    },
    "lfm2.5-2.6b": {
        "repo_id": "LiquidAI/LFM2.5-2.6B",
        "revision": "7141b56cd4650af95c7c7b86983443aed050c96a",
        "role": "historical_and_active_teacher",
    },
    "phi-4-mini-instruct": {
        "repo_id": "microsoft/Phi-4-mini-instruct",
        "revision": "cfbefacb99257ffa30c83adab238a50856ac3083",
    },
    "qwen3.5-2b-local-grader": {
        "repo_id": "Qwen/Qwen3.5-2B",
        "revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
        "role": "evaluation_grader",
    },
    "qwen3.5-2b-teacher": {
        "repo_id": "Qwen/Qwen3.5-2B",
        "revision": "5bf1871105527bed0f47e8fa941d2fc5170f7b1d",
        "role": "teacher",
    },
    "gemma-4-e2b-it": {
        "repo_id": "google/gemma-4-E2B-it",
        "revision": "4adf15748de9e1a0097b6274cee9c15836c41c37",
        "role": "teacher",
        "external_license_sources": [
            {
                "path": "OFFICIAL_LICENSE_REFERENCES/Gemma-4-License.html",
                "url": "https://ai.google.dev/gemma/docs/gemma_4_license",
                "file_role": "license_text",
                "source_kind": "official_publisher_reference",
            }
        ],
    },
    "nemotron-3-nano-4b": {
        "repo_id": "nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16",
        "revision": "ef26eca1cb6b37ea5e5d5b7e01c087e63345aeec",
        "role": "teacher",
        "external_license_sources": [
            {
                "path": "OFFICIAL_LICENSE_REFERENCES/NVIDIA-Nemotron-Open-Model-License-12-12-25.pdf",
                "url": "https://www.nvidia.com/content/dam/en-zz/Solutions/license-agreements/enterprise-software/NVIDIA-Nemotron-Open-Model-License-12-12-25.pdf",
                "file_role": "license_text",
                "source_kind": "official_publisher_reference",
            },
            {
                "path": "OFFICIAL_LICENSE_REFERENCES/Nemotron-3-Nano-4B-Model-Card.pdf",
                "url": "https://developer.download.nvidia.com/assets/ace/model_card/Nemotron_3_Nano_4B.pdf",
                "file_role": "context_reference",
                "source_kind": "official_publisher_reference",
            },
            {
                "path": "OFFICIAL_LICENSE_REFERENCES/OpenMDW-1.1-context.html",
                "url": "https://openmdw.ai/license/1-1/",
                "file_role": "context_reference",
                "source_kind": "official_publisher_reference",
            }
        ],
    },
}


def extract_model_card_metadata(model_card_bytes: bytes) -> dict[str, str]:
    text = model_card_bytes.decode("utf-8", errors="replace")
    match = re.match(r"^---\s*\n(.*?)\n---(?:\s|$)", text, flags=re.DOTALL)
    if not match:
        return {}
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        normalized_key = key.strip()
        if normalized_key in {"license", "license_name", "license_link", "license_url"}:
            metadata[normalized_key] = value.strip().strip("\"'")
    return metadata


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_legal_file(name: str) -> bool:
    base = Path(name).name.upper()
    return base.startswith(("LICENSE", "NOTICE", "COPYING"))


def build_capture_manifest(
    *,
    candidate_id: str,
    expected: dict[str, Any],
    observed_revision: str,
    card_data: dict[str, Any],
    captured_files: list[dict[str, Any]],
) -> dict[str, Any]:
    license_files = [
        item for item in captured_files
        if item.get("file_role") == "license_text" and item.get("size_bytes", 0) > 0
    ]
    repository_license_files = [
        item for item in license_files
        if item.get("source_kind", "repository_revision") == "repository_revision"
    ]
    empty_repository_license_files = [
        item for item in captured_files
        if item.get("file_role") == "empty_license_placeholder"
    ]
    notice_files = [
        item for item in captured_files
        if item.get("file_role") == "notice" and item.get("size_bytes", 0) > 0
    ]
    model_card = next((item for item in captured_files if Path(item["path"]).name == "README.md"), None)
    return {
        "schema_version": "vectolith-teacher-rights-capture/1.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "candidate_id": candidate_id,
        "role": expected.get("role", "historical_teacher"),
        "repo_id": expected["repo_id"],
        "requested_revision": expected["revision"],
        "immutable_revision": observed_revision,
        "exact_revision_confirmed": observed_revision == expected["revision"],
        "model_card_license_metadata": {
            key: card_data[key]
            for key in ("license", "license_name", "license_link", "license_url")
            if card_data.get(key) not in (None, "")
        },
        "model_card": model_card,
        "license_files": license_files,
        "repository_license_file_present": bool(repository_license_files),
        "empty_repository_license_files": empty_repository_license_files,
        "license_text_source_kinds": sorted({item.get("source_kind", "repository_revision") for item in license_files}),
        "notice_files": notice_files,
        "captured_files": captured_files,
        "capture_status": "captured" if repository_license_files else ("captured_external_reference" if any(item.get("source_kind") == "official_publisher_reference" for item in license_files) else ("captured_spdx_reference" if any(item.get("source_kind") == "spdx_license_list" for item in license_files) else "blocked_missing_license_file")),
        "legal_review": "pending_authorized_review",
        "training_output_permission": "not_verified",
        "teacher_qualification": "not_qualified",
        "weights_downloaded": False,
        "inference_performed": False,
        "credentials_required": False,
        "training_started": False,
    }


def capture_candidate(candidate_id: str, out_dir: Path, api, hf_hub_download) -> dict[str, Any]:
    expected = CANDIDATES[candidate_id]
    info = api.model_info(
        expected["repo_id"],
        revision=expected["revision"],
        files_metadata=True,
    )
    observed_revision = str(info.sha or "").lower()
    if observed_revision != expected["revision"]:
        raise RuntimeError(
            f"{candidate_id}: Hub revision mismatch; expected {expected['revision']}, got {observed_revision!r}"
        )
    if info.gated or info.private or info.disabled:
        raise RuntimeError(
            f"{candidate_id}: public anonymous access unavailable "
            f"(gated={info.gated}, private={info.private}, disabled={info.disabled})"
        )

    siblings = [getattr(item, "rfilename", "") for item in (info.siblings or [])]
    legal_names = sorted(name for name in siblings if is_legal_file(name))
    card_names = [name for name in siblings if Path(name).name == "README.md"]
    capture_names = sorted(set(legal_names + card_names))
    candidate_dir = out_dir / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    captured_files = []

    for name in capture_names:
        cached = Path(hf_hub_download(
            repo_id=expected["repo_id"],
            filename=name,
            revision=expected["revision"],
            repo_type="model",
            token=False,
        ))
        data = cached.read_bytes()
        destination = candidate_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cached, destination)
        captured_files.append({
            "path": name,
            "size_bytes": len(data),
            "sha256": sha256_bytes(data),
            "immutable_url": f"https://huggingface.co/{expected['repo_id']}/blob/{expected['revision']}/{name}",
            "captured_path": str(destination),
            "file_role": (
                "empty_license_placeholder"
                if is_legal_file(name) and not data.strip()
                else ("notice" if Path(name).name.upper().startswith("NOTICE") else ("license_text" if is_legal_file(name) else "model_card"))
            ),
            "source_kind": "repository_revision",
            **({"note": "The exact-revision repository file is zero bytes and is not treated as license or notice text."} if is_legal_file(name) and not data.strip() else {}),
        })

    card_data = info.card_data.to_dict() if info.card_data else {}
    model_card_record = next((item for item in captured_files if item.get("file_role") == "model_card"), None)
    if model_card_record:
        card_data.update(extract_model_card_metadata(
            Path(model_card_record["captured_path"]).read_bytes()
        ))
    if not any(item.get("file_role") == "license_text" and item.get("size_bytes", 0) > 0 for item in captured_files):
        declared = str(card_data.get("license") or "").strip().lower()
        spdx_id = SPDX_LICENSE_IDS.get(declared)
        if spdx_id:
            source_url = (
                f"https://raw.githubusercontent.com/spdx/license-list-data/"
                f"{SPDX_LICENSE_LIST_COMMIT}/text/{spdx_id}.txt"
            )
            request = urllib.request.Request(source_url, headers={"User-Agent": "vectolith-teacher-rights-capture/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                license_bytes = response.read()
            if not license_bytes:
                raise RuntimeError(f"{candidate_id}: SPDX license text was empty")
            relative_name = f"SPDX/{spdx_id}.txt"
            destination = candidate_dir / relative_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(license_bytes)
            captured_files.append({
                "path": relative_name,
                "size_bytes": len(license_bytes),
                "sha256": sha256_bytes(license_bytes),
                "immutable_url": source_url,
                "captured_path": str(destination),
                "file_role": "license_text",
                "source_kind": "spdx_license_list",
                "source_revision": SPDX_LICENSE_LIST_COMMIT,
                "note": "Canonical SPDX text captured because this model repository has no LICENSE/COPYING file; this is not represented as a repository-supplied license file.",
            })
    for source in expected.get("external_license_sources", []):
        request = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "vectolith-model-rights-capture/1.0"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            source_bytes = response.read()
        if not source_bytes:
            raise RuntimeError(
                f"{candidate_id}: external reference was empty: {source['url']}"
            )
        destination = candidate_dir / source["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source_bytes)
        captured_files.append({
            "path": source["path"],
            "size_bytes": len(source_bytes),
            "sha256": sha256_bytes(source_bytes),
            "immutable_url": source["url"],
            "captured_path": str(destination),
            "file_role": source["file_role"],
            "source_kind": source["source_kind"],
            "note": "Official publisher reference captured as evidence; legal applicability remains subject to authorized review.",
        })

    manifest = build_capture_manifest(
        candidate_id=candidate_id,
        expected=expected,
        observed_revision=observed_revision,
        card_data=card_data,
        captured_files=captured_files,
    )
    manifest_path = candidate_dir / "rights-capture.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True, help="Restricted evidence directory outside the repository")
    parser.add_argument("--candidate", action="append", choices=sorted(CANDIDATES), help="Model ID; repeat to select multiple (default: all pinned teacher and evaluation-grader models)")
    args = parser.parse_args()

    out_dir = args.out_dir.resolve()
    try:
        out_dir.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        parser.error("--out-dir must be outside the repository checkout")

    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError as exc:
        raise SystemExit("Install huggingface_hub before running rights capture.") from exc

    api = HfApi(token=False)
    selected = args.candidate or list(CANDIDATES)
    results = []
    failures = []
    for candidate_id in selected:
        try:
            result = capture_candidate(candidate_id, out_dir, api, hf_hub_download)
            results.append(result)
            print(json.dumps({
                "candidate_id": candidate_id,
                "revision": result["immutable_revision"],
                "capture_status": result["capture_status"],
                "license_files": len(result["license_files"]),
                "notice_files": len(result["notice_files"]),
                "manifest_path": result["manifest_path"],
            }, sort_keys=True), flush=True)
            if result["capture_status"] == "blocked_missing_license_file":
                failures.append(f"{candidate_id}: no repository license file or supported canonical SPDX text")
        except Exception as exc:
            failures.append(f"{candidate_id}: {type(exc).__name__}: {exc}")

    summary = {
        "schema_version": "vectolith-teacher-rights-capture-summary/1.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "selected_candidates": selected,
        "captured_count": len(results),
        "failed_count": len(failures),
        "failures": failures,
        "out_dir": str(out_dir),
        "weights_downloaded": False,
        "inference_performed": False,
        "legal_review": "pending_authorized_review",
        "training_output_permission": "not_verified",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "capture-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
