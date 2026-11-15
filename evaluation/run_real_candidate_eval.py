#!/usr/bin/env python3
"""Run real CPU inference on one immutable foundation candidate checkpoint."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import resource
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
import transformers
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer

from run_real_checkpoint_suite import prompt_hash, render_prompt
from run_eval import load_cases


def cpu_model_name() -> str | None:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return platform.processor() or None
    return platform.processor() or None


def total_memory_bytes() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--suite", action="append", required=True, type=Path)
    parser.add_argument("--dtype", choices=("bfloat16", "float32"), default="bfloat16")
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--cache-dir", type=Path, default=Path(".hf-cache"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    revision = args.revision.lower()
    if len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision):
        parser.error("--revision must be a full immutable 40-character commit SHA")
    if not 1 <= args.max_new_tokens <= 256:
        parser.error("--max-new-tokens must be between 1 and 256")

    torch.set_num_threads(min(torch.get_num_threads(), 4))
    if args.dtype == "bfloat16":
        try:
            probe = torch.ones((16, 16), dtype=torch.bfloat16)
            _ = probe @ probe
        except Exception as exc:
            raise RuntimeError(f"CPU bfloat16 matrix multiplication is unavailable: {exc}") from exc
        del probe

    cases = []
    for suite in args.suite:
        cases.extend((suite, case) for case in load_cases(suite))
    if not cases:
        raise ValueError("no benchmark cases loaded")
    case_ids = [case["id"] for _, case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("benchmark case IDs must be unique across suites")

    started = time.perf_counter()
    snapshot_path = Path(snapshot_download(
        repo_id=args.repo,
        revision=revision,
        cache_dir=str(args.cache_dir),
    ))
    if snapshot_path.name != revision:
        raise RuntimeError(
            f"Hub snapshot path revision {snapshot_path.name!r} does not match requested {revision!r}"
        )

    tokenizer = AutoTokenizer.from_pretrained(snapshot_path, local_files_only=True)
    dtype = torch.bfloat16 if args.dtype == "bfloat16" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        snapshot_path,
        local_files_only=True,
        torch_dtype=dtype,
        low_cpu_mem_usage=True,
    )
    model.eval()
    model_started = time.perf_counter()
    results = []
    for suite, case in cases:
        encoded = render_prompt(tokenizer, case["messages"])
        case_started = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                use_cache=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = round(time.perf_counter() - case_started, 3)
        input_count = int(encoded["input_ids"].shape[1])
        new_tokens = generated[0, input_count:]
        response = tokenizer.decode(new_tokens, skip_special_tokens=True)
        if new_tokens.numel() < 1 or not response.strip():
            raise RuntimeError(f"{case['id']}: checkpoint produced no visible output")
        results.append({
            "suite": str(suite),
            "role": "core_prima" if suite.name.startswith("prima") else "core_prime",
            "case_id": case["id"],
            "category": case.get("category", "uncategorized"),
            "prompt_sha256": prompt_hash(case["messages"]),
            "rubric": case.get("rubric"),
            "input_tokens": input_count,
            "generated_tokens": int(new_tokens.numel()),
            "latency_seconds": elapsed,
            "response_text": response,
            "error": None,
        })
        print(f"{case['id']}: {len(new_tokens)} tokens in {elapsed}s", flush=True)

    model_vocab = int(model.get_input_embeddings().weight.shape[0])
    if len(tokenizer) > model_vocab:
        raise RuntimeError("tokenizer vocabulary exceeds model embedding vocabulary")
    record = {
        "schema_version": "vectolith-real-candidate-evaluation/1.0",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "family": args.family,
        "repo_id": args.repo,
        "immutable_revision": revision,
        "loaded_snapshot_path_revision": snapshot_path.name,
        "architectures": getattr(model.config, "architectures", None),
        "model_class": model.__class__.__name__,
        "tokenizer_class": tokenizer.__class__.__name__,
        "tokenizer_vocab_size": len(tokenizer),
        "model_vocab_size": model_vocab,
        "embedding_vocab_padding": model_vocab - len(tokenizer),
        "device": "cpu",
        "dtype": args.dtype,
        "cpu_capability": torch.backends.cpu.get_cpu_capability(),
        "cpu_model": cpu_model_name(),
        "cpu_count": os.cpu_count(),
        "system_memory_bytes": total_memory_bytes(),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "decoding": {"do_sample": False, "max_new_tokens": args.max_new_tokens, "chat_template": True, "enable_thinking": False},
        "case_count": len(results),
        "model_load_and_suite_seconds": round(time.perf_counter() - started, 3),
        "suite_generation_seconds": round(time.perf_counter() - model_started, 3),
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
    print(f"Captured {len(results)} real outputs for {args.repo}@{revision}", flush=True)

    del model, tokenizer
    gc.collect()
    shutil.rmtree(args.cache_dir / f"models--{args.repo.replace('/', '--')}", ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
