#!/usr/bin/env python3
"""Run real CPU inference on one immutable foundation candidate checkpoint."""
from __future__ import annotations

import argparse
import gc
import json
import os
import resource
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import torch
import transformers
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

from generation import render_prompt
from run_eval import load_cases
from run_real_checkpoint_suite import prompt_hash


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--candidate-id")
    parser.add_argument("--role", choices=("core_prime", "core_prima"), default="core_prime")
    parser.add_argument("--suite", action="append", required=True, type=Path)
    parser.add_argument("--dtype", choices=("bfloat16", "float32"), default="bfloat16")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--cache-dir", type=Path, default=Path(".hf-cache"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    revision = args.revision.lower()
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        parser.error("--revision must be a full immutable 40-character commit SHA")
    if not 1 <= args.max_new_tokens <= 256:
        parser.error("--max-new-tokens must be between 1 and 256")

    requested_threads = max(1, int(os.environ.get("VELNOR_INFERENCE_THREADS", "2")))
    torch.set_num_threads(min(torch.get_num_threads(), requested_threads))
    if args.dtype == "bfloat16":
        try:
            probe = torch.ones((16, 16), dtype=torch.bfloat16)
            _ = probe @ probe
            del probe
        except Exception as exc:
            raise RuntimeError(f"CPU bfloat16 matrix multiplication is unavailable: {exc}") from exc

    cases = [(suite, case) for suite in args.suite for case in load_cases(suite)]
    if not cases:
        raise ValueError("no benchmark cases loaded")
    case_ids = [case["id"] for _, case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("benchmark case IDs must be unique across suites")

    candidate_id = args.candidate_id or args.repo
    run_id = uuid.uuid4().hex
    run_started_at = datetime.now(timezone.utc).isoformat()
    total_started = time.perf_counter()
    download_started = time.perf_counter()
    snapshot = Path(snapshot_download(
        repo_id=args.repo,
        revision=revision,
        cache_dir=str(args.cache_dir),
    ))
    download_seconds = round(time.perf_counter() - download_started, 3)
    if snapshot.name != revision:
        raise RuntimeError(f"Hub snapshot revision {snapshot.name!r} does not match {revision!r}")
    snapshot_bytes = sum(path.stat().st_size for path in snapshot.rglob("*") if path.is_file())

    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    dtype = torch.bfloat16 if args.dtype == "bfloat16" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        snapshot,
        local_files_only=True,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model.eval()
    load_seconds = round(time.perf_counter() - load_started, 3)

    generation_started = time.perf_counter()
    results = []
    raw_output = args.output.with_suffix(".jsonl")
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with raw_output.open("w", encoding="utf-8") as raw_handle:
        for suite, case in cases:
            case_started_at = datetime.now(timezone.utc).isoformat()
            result = {
                "suite": str(suite),
                "role": args.role,
                "case_id": case["id"],
                "benchmark_case_id": case["id"],
                "candidate_id": candidate_id,
                "model_revision": revision,
                "run_id": run_id,
                "started_at": case_started_at,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "category": case.get("category", "uncategorized"),
                "prompt_sha256": prompt_hash(case["messages"]),
                "rubric": case.get("rubric"),
                "max_new_tokens": args.max_new_tokens,
                "generation_cap_reached": False,
                "generation_status": "error",
                "latency_seconds": None,
                "input_tokens": None,
                "generated_tokens": 0,
                "response_text": None,
                "error": None,
            }
            started = time.perf_counter()
            try:
                encoded = render_prompt(tokenizer, case["messages"])
                with torch.inference_mode():
                    output = model.generate(
                        **encoded,
                        max_new_tokens=args.max_new_tokens,
                        do_sample=False,
                        use_cache=True,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                latency = round(time.perf_counter() - started, 3)
                input_tokens = int(encoded["input_ids"].shape[1])
                generated = output[0, input_tokens:]
                response = tokenizer.decode(generated, skip_special_tokens=True)
                if generated.numel() < 1 or not response.strip():
                    raise RuntimeError("no visible generated output")
                hit_cap = int(generated.numel()) >= args.max_new_tokens and (
                    tokenizer.eos_token_id is None
                    or tokenizer.eos_token_id not in generated.tolist()
                )
                result.update({
                    "input_tokens": input_tokens,
                    "generated_tokens": int(generated.numel()),
                    "generation_cap_reached": hit_cap,
                    "generation_status": "token_limit_reached" if hit_cap else "eos_or_early_stop",
                    "latency_seconds": latency,
                    "response_text": response,
                    "error": None,
                })
                print(f"{case['id']}: {generated.numel()} tokens in {latency}s", flush=True)
            except Exception as exc:
                failures += 1
                result.update({
                    "latency_seconds": round(time.perf_counter() - started, 3),
                    "error": f"{type(exc).__name__}: {exc}",
                })
                print(f"{case['id']}: ERROR {result['error']}", flush=True)
            results.append(result)
            raw_handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
            raw_handle.flush()

    generation_seconds = round(time.perf_counter() - generation_started, 3)
    model_vocab = int(model.get_input_embeddings().weight.shape[0])
    if len(tokenizer) > model_vocab:
        raise RuntimeError("tokenizer vocabulary exceeds model embedding vocabulary")
    record = {
        "schema_version": "vectolith-real-candidate-evaluation/1.2",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "family": args.family,
        "candidate_id": candidate_id,
        "role": args.role,
        "run_id": run_id,
        "started_at": run_started_at,
        "repo_id": args.repo,
        "immutable_revision": revision,
        "loaded_snapshot_path_revision": snapshot.name,
        "architectures": getattr(model.config, "architectures", None),
        "model_class": model.__class__.__name__,
        "tokenizer_class": tokenizer.__class__.__name__,
        "tokenizer_vocab_size": len(tokenizer),
        "model_vocab_size": model_vocab,
        "embedding_vocab_padding": model_vocab - len(tokenizer),
        "device": "cpu",
        "dtype": args.dtype,
        "cpu_capability": torch.backends.cpu.get_cpu_capability(),
        "cpu_count_visible": os.cpu_count(),
        "snapshot_size_bytes": snapshot_bytes,
        "download_seconds": download_seconds,
        "model_load_seconds": load_seconds,
        "generation_seconds": generation_seconds,
        "total_seconds": round(time.perf_counter() - total_started, 3),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "decoding": {
            "do_sample": False,
            "max_new_tokens": args.max_new_tokens,
            "chat_template": True,
            "enable_thinking": False,
        },
        "case_count": len(results),
        "error_count": failures,
        "successful_case_count": len(results) - failures,
        "raw_results_file": str(raw_output),
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "license_review": "pending_human_legal_review",
        "training_output_permission": "not_verified",
        "teacher_qualification": "not_qualified",
        "training_started": False,
        "grading": "human_review_required",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Captured {len(results)} {args.role} outputs for {args.repo}@{revision}", flush=True)
    del model, tokenizer
    gc.collect()
    shutil.rmtree(args.cache_dir / f"models--{args.repo.replace('/', '--')}", ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
