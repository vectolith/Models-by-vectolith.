#!/usr/bin/env python3
"""Run a same-runner, same-suite ASH PRIME output-budget comparison."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CANDIDATES = [
    {
        "candidate_id": "granite-3.1-3b-a800m",
        "repo": "ibm-granite/granite-3.1-3b-a800m",
        "revision": "a02780686e08a03fe0d2679a293b5c74a90efa89",
        "family": "IBM Granite",
        "transformers": "4.57.1",
        "hub": "0.36.0",
    },
    {
        "candidate_id": "granite-4.2-3b",
        "repo": "ibm-granite/granite-4.2-3b",
        "revision": "4e9c275e232f10211ec88644d106a1f6a1b60e06",
        "family": "IBM Granite",
        "transformers": "5.0.0",
        "hub": "1.3.0",
    },
    {
        "candidate_id": "minicpm5-2b",
        "repo": "openbmb/MiniCPM5-2B",
        "revision": "42433e90dad95123ab87729fd7011e7110629556",
        "family": "OpenBMB MiniCPM",
        "transformers": "4.57.1",
        "hub": "0.36.0",
    },
    {
        "candidate_id": "lfm2.5-2.6b",
        "repo": "LiquidAI/LFM2.5-2.6B",
        "revision": "7141b56cd4650af95c7c7b86983443aed050c96a",
        "family": "LiquidAI LFM2.5",
        "transformers": "5.0.0",
        "hub": "1.3.0",
    },
    {
        "candidate_id": "phi-4-mini-instruct",
        "repo": "microsoft/Phi-4-mini-instruct",
        "revision": "cfbefacb99257ffa30c83adab238a50856ac3083",
        "family": "Microsoft Phi-4",
        "transformers": "4.57.1",
        "hub": "0.36.0",
    },
]


def run(command: list[str], log_path: Path) -> int:
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            command, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-new-tokens", type=int, choices=(512, 768, 1024), required=True)
    parser.add_argument("--candidate", choices=tuple(x["candidate_id"] for x in CANDIDATES) + ("all",), default="all")
    parser.add_argument("--suite", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    args = parser.parse_args()
    if len(args.suite) != 4:
        parser.error("the controlled study requires the exact four Prime v1-v4 suites")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "compute").mkdir(exist_ok=True)
    (args.output_dir / "evaluations").mkdir(exist_ok=True)
    results: list[dict[str, Any]] = []
    selected_candidates = CANDIDATES if args.candidate == "all" else [
        candidate for candidate in CANDIDATES if candidate["candidate_id"] == args.candidate
    ]
    for candidate in selected_candidates:
        cid = candidate["candidate_id"]
        base = args.output_dir / "evaluations" / f"{cid}-completion-{args.max_new_tokens}"
        compute_path = args.output_dir / "compute" / f"{cid}-runner.json"
        dependency_log = args.output_dir / "evaluations" / f"{cid}-dependencies.log"
        inference_log = base.with_suffix(".log")
        output_path = base.with_suffix(".json")
        install = run(
            [
                sys.executable, "-m", "pip", "install",
                f"transformers=={candidate['transformers']}",
                f"huggingface_hub=={candidate['hub']}",
                "accelerate==1.10.1", "safetensors==0.6.2",
            ],
            dependency_log,
        )
        if install:
            results.append({
                "candidate_id": cid, "immutable_revision": candidate["revision"],
                "status": "dependency_install_failed", "exit_code": install,
                "dependency_log": str(dependency_log),
            })
            continue
        probe = run(
            [
                sys.executable, "evaluation/probe_compute.py",
                "--output", str(compute_path),
            ],
            args.output_dir / "compute" / f"{cid}-probe.log",
        )
        if probe:
            results.append({
                "candidate_id": cid, "immutable_revision": candidate["revision"],
                "status": "compute_probe_failed", "exit_code": probe,
                "compute_log": str(args.output_dir / "compute" / f"{cid}-probe.log"),
            })
            continue
        command = [
            sys.executable, "evaluation/run_real_candidate_eval.py",
            "--repo", candidate["repo"],
            "--revision", candidate["revision"],
            "--family", candidate["family"],
            "--candidate-id", cid,
            "--dtype", "bfloat16",
            "--max-new-tokens", str(args.max_new_tokens),
            "--cache-dir", str(args.cache_dir),
            "--output", str(output_path),
        ]
        for suite in args.suite:
            command.extend(["--suite", str(suite)])
        exit_code = run(command, inference_log)
        record = None
        if output_path.exists():
            try:
                record = json.loads(output_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                record = None
        results.append({
            "candidate_id": cid,
            "immutable_revision": candidate["revision"],
            "status": "success" if exit_code == 0 and record else "inference_failed",
            "exit_code": exit_code,
            "case_count": record.get("case_count") if record else None,
            "error_count": record.get("error_count") if record else None,
            "completion_status_counts": record.get("completion_status_counts") if record else None,
            "token_cap_truncated_count": record.get("token_cap_truncated_count") if record else None,
            "result_json": str(output_path) if output_path.exists() else None,
            "result_jsonl": str(output_path.with_suffix(".jsonl")) if output_path.with_suffix(".jsonl").exists() else None,
            "inference_log": str(inference_log),
            "compute_record": str(compute_path),
        })
    summary = {
        "schema_version": "vectolith-prime-completion-study/1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "workflow_run_id": __import__("os").environ.get("GITHUB_RUN_ID"),
        "role": "ash_prime",
        "suite_set": [str(path) for path in args.suite],
        "max_new_tokens": args.max_new_tokens,
        "candidate_selection": args.candidate,
        "decoding": {
            "do_sample": False, "dtype": "bfloat16",
            "chat_template": True, "enable_thinking": False,
        },
        "device": "cpu",
        "candidate_results": results,
        "qualification_decision": "not_made",
        "training_started": False,
    }
    summary_path = args.output_dir / "study-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if any(row["status"] != "success" for row in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
