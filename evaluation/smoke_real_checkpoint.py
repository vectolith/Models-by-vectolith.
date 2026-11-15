#!/usr/bin/env python3
"""Load one immutable public checkpoint and perform real CPU generation.

This is an execution-path smoke test, not a capability benchmark or training run.
"""
from __future__ import annotations

import argparse
import json
import re
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--revision", default="c1899de289a04d12100db370d81485cdf75e47ca")
    parser.add_argument("--prompt", default="Write one short greeting.")
    parser.add_argument("--max-new-tokens", type=int, default=12)
    parser.add_argument("--output", type=Path, default=Path("artifacts/checkpoints/qwen3-0.6b-smoke.json"))
    args = parser.parse_args()

    if not SHA.fullmatch(args.revision):
        parser.error("--revision must be a full immutable 40-character commit SHA")
    if args.max_new_tokens < 1 or args.max_new_tokens > 64:
        parser.error("--max-new-tokens must be between 1 and 64")

    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.repo, revision=args.revision)
    model = AutoModelForCausalLM.from_pretrained(
        args.repo,
        revision=args.revision,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,
    )
    model.eval()
    inputs = tokenizer(args.prompt, return_tensors="pt")
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    elapsed = round(time.perf_counter() - started, 3)
    new_tokens = generated[0, inputs["input_ids"].shape[1]:]
    decoded = tokenizer.decode(new_tokens, skip_special_tokens=True)
    if new_tokens.numel() < 1 or not decoded.strip():
        raise RuntimeError("checkpoint loaded but produced no visible generated text")

    record = {
        "schema_version": "vectolith-real-checkpoint-smoke/1.0",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "repo_id": args.repo,
        "immutable_revision": args.revision,
        "loaded_config_architectures": getattr(model.config, "architectures", None),
        "tokenizer_class": tokenizer.__class__.__name__,
        "model_class": model.__class__.__name__,
        "tokenizer_vocab_size": len(tokenizer),
        "model_vocab_size": model.get_input_embeddings().weight.shape[0],
        "device": "cpu",
        "dtype": str(next(model.parameters()).dtype),
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "prompt": args.prompt,
        "generated_token_count": int(new_tokens.numel()),
        "generated_text": decoded,
        "elapsed_seconds": elapsed,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "training_started": False,
        "result": "pass",
    }
    if record["tokenizer_vocab_size"] != record["model_vocab_size"]:
        raise RuntimeError("tokenizer/model vocabulary mismatch")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
