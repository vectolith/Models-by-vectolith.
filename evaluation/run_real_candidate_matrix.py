#!/usr/bin/env python3
"""Run every pinned candidate sequentially on one identical CPU runner.

This prevents CPU model/capability differences between separate hosted runners
from contaminating latency comparisons. Raw outputs remain separate per model.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("evaluation/fixtures/real_cpu_candidates_v1.json"))
    parser.add_argument("--suite", action="append", required=True, type=Path)
    parser.add_argument("--dtype", choices=("bfloat16", "float32"), default="bfloat16")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--cache-dir", type=Path, default=Path(".hf-cache"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/evaluations/sequential"))
    parser.add_argument("--summary-output", type=Path, default=Path("artifacts/evaluations/sequential/summary.json"))
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        parser.error("candidate manifest must contain a non-empty candidates array")
    if any(item.get("gated") for item in candidates):
        parser.error("gated candidates must not be included in unauthenticated CI comparisons")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    runner = Path(__file__).with_name("run_real_candidate_eval.py")
    runs = []
    successful_records = []
    failures = []

    for candidate in candidates:
        candidate_id = candidate["id"]
        output = args.output_dir / f"{candidate_id}.json"
        command = [
            sys.executable, str(runner),
            "--repo", candidate["repo_id"],
            "--revision", candidate["revision"],
            "--family", candidate["family"],
            "--dtype", args.dtype,
            "--max-new-tokens", str(args.max_new_tokens),
            "--cache-dir", str(args.cache_dir),
            "--output", str(output),
        ]
        for suite in args.suite:
            command.extend(["--suite", str(suite)])

        print(f"Starting {candidate_id}: {candidate['repo_id']}@{candidate['revision']}", flush=True)
        completed = subprocess.run(command, check=False)
        run_record = {
            "candidate_id": candidate_id,
            "repo_id": candidate["repo_id"],
            "revision": candidate["revision"],
            "output_file": str(output),
            "return_code": completed.returncode,
            "status": "passed" if completed.returncode == 0 and output.exists() else "failed",
        }
        runs.append(run_record)
        if run_record["status"] == "passed":
            record = json.loads(output.read_text(encoding="utf-8"))
            if record["repo_id"] != candidate["repo_id"] or record["immutable_revision"] != candidate["revision"]:
                failures.append(f"{candidate_id}: output provenance mismatch")
                run_record["status"] = "failed"
                continue
            successful_records.append((candidate, record))
        else:
            failures.append(f"{candidate_id}: inference process returned {completed.returncode}")

    hardware_keys = ("cpu_model", "cpu_capability", "cpu_count", "system_memory_bytes", "torch_version", "transformers_version", "dtype")
    hardware = None
    hardware_consistent = True
    if successful_records:
        hardware = {key: successful_records[0][1].get(key) for key in hardware_keys}
        for candidate, record in successful_records[1:]:
            other = {key: record.get(key) for key in hardware_keys}
            if other != hardware:
                hardware_consistent = False
                failures.append(f"{candidate['id']}: CPU/runtime hardware differs from first candidate")
    if len(successful_records) != len(candidates):
        hardware_consistent = False

    baseline_cases = None
    for candidate, record in successful_records:
        case_map = {
            item["case_id"]: item["prompt_sha256"]
            for item in record["results"]
        }
        if baseline_cases is None:
            baseline_cases = case_map
        elif case_map != baseline_cases:
            failures.append(f"{candidate['id']}: benchmark case/prompt set differs from other candidates")
            hardware_consistent = False

    metrics = []
    for candidate, record in successful_records:
        latencies = [item["latency_seconds"] for item in record["results"]]
        token_count = sum(item["generated_tokens"] for item in record["results"])
        generation_seconds = sum(latencies)
        metrics.append({
            "candidate_id": candidate["id"],
            "family": candidate["family"],
            "repo_id": candidate["repo_id"],
            "revision": candidate["revision"],
            "parameter_count": candidate.get("parameter_count"),
            "case_count": len(record["results"]),
            "generated_tokens": token_count,
            "generation_seconds": round(generation_seconds, 3),
            "aggregate_generation_tokens_per_second": round(token_count / generation_seconds, 3) if generation_seconds else None,
            "peak_rss_kib": record["max_rss_kib"],
            "output_file": next(run["output_file"] for run in runs if run["candidate_id"] == candidate["id"]),
        })

    summary = {
        "schema_version": "vectolith-sequential-candidate-comparison/1.0",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(args.manifest),
        "same_runner_hardware": hardware_consistent,
        "hardware": hardware,
        "dtype": args.dtype,
        "max_new_tokens": args.max_new_tokens,
        "suites": [str(path) for path in args.suite],
        "candidate_runs": runs,
        "metrics": metrics,
        "failures": failures,
        "interpretation": "execution and resource comparison only; no capability grading or foundation selection",
        "training_started": False,
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 1 if failures or not hardware_consistent else 0


if __name__ == "__main__":
    raise SystemExit(main())
