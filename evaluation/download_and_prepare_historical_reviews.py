#!/usr/bin/env python3
"""Download verified historical teacher artifacts and build local blinded review packages.

No model weights, inference endpoints, or training jobs are used. The private
identity key remains local and must never be uploaded or shared with reviewers.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import urllib.error
import urllib.request
from pathlib import Path
import sys

# When invoked as `python evaluation/script.py`, Python puts the evaluation/
# directory (not the repository root) at sys.path[0]. Add the root explicitly
# so the sibling evaluation namespace package resolves from any working dir.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from evaluation.prepare_blinded_human_review import (
    ARTIFACT_PROVENANCE,
    build_review_packages,
)

REPOSITORY = "vectolith/Models-by-vectolith."
SUITES = (
    "evaluation/fixtures/prime_benchmark_v1.jsonl",
    "evaluation/fixtures/prime_qualification_v2.jsonl",
    "evaluation/fixtures/prime_qualification_v3.jsonl",
    "evaluation/fixtures/prime_qualification_v4.jsonl",
)


def download_verified_artifact(
    artifact_id: int,
    filename: str,
    expected_sha256: str,
    destination: Path,
    token: str | None = None,
) -> dict[str, object]:
    """Download one Actions ZIP, verify its immutable digest, and preserve it."""
    if destination.exists():
        actual = hashlib.sha256(destination.read_bytes()).hexdigest()
        if actual != expected_sha256:
            raise ValueError(
                f"{destination} already exists with a different SHA-256; "
                "refusing to overwrite preserved evidence"
            )
        return {"filename": filename, "status": "already_verified", "sha256": actual}

    url = f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact_id}/zip"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "vectolith-ash-prime-historical-review-preparation",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            archive_bytes = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(
                "GitHub denied artifact download. For this public repository, retry "
                "without a token if the endpoint allows it; otherwise set GITHUB_TOKEN "
                "to a fine-grained token with Actions: read. Never paste the token into "
                "the notebook or print it."
            ) from exc
        raise RuntimeError(f"GitHub artifact download failed for {artifact_id}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Network error downloading artifact {artifact_id}: {exc}") from exc

    if not archive_bytes.startswith(bytes.fromhex("504b0304")):
        raise ValueError(f"{filename}: GitHub did not return a ZIP archive")
    actual = hashlib.sha256(archive_bytes).hexdigest()
    if actual != expected_sha256:
        raise ValueError(
            f"{filename}: SHA-256 mismatch; expected {expected_sha256}, received {actual}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    temporary.write_bytes(archive_bytes)
    temporary.replace(destination)
    return {"filename": filename, "status": "downloaded_and_verified", "sha256": actual}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/human-review/historical-runs-40-42-43"),
    )
    parser.add_argument("--reviewers", type=int, default=2)
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()

    if len(ARTIFACT_PROVENANCE) != 15:
        raise RuntimeError(
            f"historical provenance registry must contain 15 artifacts, found {len(ARTIFACT_PROVENANCE)}"
        )
    if args.reviewers < 2:
        raise ValueError("at least two separate reviewer packages are required")

    token = os.environ.get(args.github_token_env) or None
    source_dir = args.output_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(args.output_dir, 0o700)
        os.chmod(source_dir, 0o700)
    except OSError:
        pass

    evidence_paths = []
    download_results = []
    for filename, metadata in sorted(ARTIFACT_PROVENANCE.items()):
        destination = source_dir / filename
        result = download_verified_artifact(
            int(metadata["artifact_id"]),
            filename,
            str(metadata["sha256"]),
            destination,
            token,
        )
        evidence_paths.append(destination)
        download_results.append(result)

    suite_paths = [Path(item) for item in SUITES]
    missing = [str(path) for path in suite_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Run this script from the repository root; missing suite files: " + ", ".join(missing)
        )

    summary = build_review_packages(
        evidence_paths=evidence_paths,
        suite_paths=suite_paths,
        output_dir=args.output_dir,
        reviewer_count=args.reviewers,
        expected_artifacts=15,
        expected_cases=180,
        workflow_run_id="historical-runs-40-42-43",
    )

    private_dir = args.output_dir / "private"
    identity_key = private_dir / "identity-key.json"
    if identity_key.is_file():
        try:
            os.chmod(private_dir, 0o700)
            os.chmod(identity_key, 0o600)
        except OSError:
            pass

    print({
        "artifact_count": len(download_results),
        "downloaded_count": sum(x["status"] == "downloaded_and_verified" for x in download_results),
        "already_verified_count": sum(x["status"] == "already_verified" for x in download_results),
        "response_count": summary["response_count"],
        "gradeable_response_count": summary["gradeable_response_count"],
        "reviewer_package_count": summary["reviewer_package_count"],
        "reviewer_packages": [x["reviewer_package"] for x in summary["reviewer_packages"]],
        "private_identity_key": str(identity_key),
        "qualification_decision": "not_made",
        "training_started": False,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
