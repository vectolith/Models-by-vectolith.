#!/usr/bin/env python3
"""Run the public Prime and Prima smoke suites against one pinned real checkpoint.

This captures actual model outputs for human review. It does not grade or select
the model, and the public smoke fixtures are not held-out qualification data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

from run_eval import load_cases

DEFAULT_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
DEFAULT_REPO = "Qwen/Qwen3-0.6B"


def prompt_hash(messages: list[dict]) -> str:
    encoded = json.dumps(messages, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def render_prompt(tokenizer, messages: list[dict]):
    return tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
        return_tensors="pt",
        return_dict=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    parser.add_argument("--suite", action="append", required=True, type=Path)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluations/qwen3-0.6b-smoke-suites.json"))
    args = parser.parse_args()

    if len(args.revision) != 40 or any(ch not in "0123456789abcdefABCDEF" for ch in args.revision):
        parser.error("--revision must be a full immutable 40-character commit SHA")
    if not 1 <= args.max_new_tokens <= 256:
        parser.error("--max-new-tokens must be between 1 and 256")

    cases = []
    for suite in args.suite:
        for case in load_cases(suite):
            cases.append((suite, case))
    ids = [case["id"] for _, case in cases]
    if len(ids) != len(set(ids)):
        parser.error("benchmark case IDs must be unique across supplied suites")

    torch.set_num_threads(min(torch.get_num_threads(), 4))
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.repo, revision=args.revision)
    model = AutoModelForCausalLM.from_pretrained(
        args.repo,
        revision=args.revision,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.eval()

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
        print(f"{case['id']}: {len(new_tokens)} tokens in {elapsed}s")

    record = {
        "schema_version": "vectolith-real-checkpoint-suite/1.0",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "repo_id": args.repo,
        "immutable_revision": args.revision,
        "architectures": getattr(model.config, "architectures", None),
        "model_class": model.__class__.__name__,
        "tokenizer_class": tokenizer.__class__.__name__,
        "tokenizer_vocab_size": len(tokenizer),
        "model_vocab_size": int(model.get_input_embeddings().weight.shape[0]),
        "device": "cpu",
        "dtype": str(next(model.parameters()).dtype),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "decoding": {"do_sample": False, "max_new_tokens": args.max_new_tokens, "chat_template": True, "enable_thinking": False},
        "suite_count": len(args.suite),
        "case_count": len(results),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "training_started": False,
        "grading": "human_review_required",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Captured {len(results)} real model outputs: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
