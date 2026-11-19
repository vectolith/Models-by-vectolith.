#!/usr/bin/env python3
"""Reproducible baseline evaluator for Core Prime Experiment 001.

Loads a local or explicitly supplied Hugging Face model revision, executes JSONL
tasks, and writes JSONL raw records plus a run summary. No fallback model is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            for field in ("task_id", "prompt", "category"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise ValueError(f"{path}:{line_no}: missing/invalid {field}")
            if row.get("split") not in ("train", "development", "holdout"):
                raise ValueError(f"{path}:{line_no}: invalid split")
            rows.append(row)
    ids = [row["task_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("task_id values must be unique in the input file")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Exact HF repository ID or local model path")
    parser.add_argument("--revision", required=True, help="Immutable revision SHA for HF models")
    parser.add_argument("--tasks", required=True, type=Path, help="JSONL task records")
    parser.add_argument("--output", required=True, type=Path, help="Output directory")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=0, help="0 means all tasks")
    parser.add_argument("--trust-remote-code", action="store_true", help="Explicit opt-in to model code")
    parser.add_argument("--allow-holdout", action="store_true", help="Explicitly permit holdout inference")
    args = parser.parse_args()

    if args.max_new_tokens <= 0:
        parser.error("--max-new-tokens must be positive")
    if args.temperature < 0:
        parser.error("--temperature cannot be negative")
    tasks = load_jsonl(args.tasks)
    if any(t["split"] == "holdout" for t in tasks) and not args.allow_holdout:
        parser.error("holdout tasks blocked; use --allow-holdout only after config freeze")
    if args.limit > 0:
        tasks = tasks[:args.limit]
    if not tasks:
        parser.error("no tasks to evaluate")

    args.output.mkdir(parents=True, exist_ok=True)
    task_hash = sha256_file(args.tasks)
    run_id = datetime.now(timezone.utc).strftime("cp001-%Y%m%dT%H%M%SZ")
    raw_path = args.output / f"{run_id}-raw.jsonl"
    summary_path = args.output / f"{run_id}-summary.json"

    # Capture library errors explicitly; never substitute another model.
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except Exception as exc:
        summary = {"run_id": run_id, "status": "blocked", "error": repr(exc),
                   "task_file_sha256": task_hash, "model": args.model, "revision": args.revision}
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 2

    started = time.time()
    status = "completed"
    error: str | None = None
    records: list[dict[str, Any]] = []
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        hardware = torch.cuda.get_device_name(0)
    else:
        hardware = platform.processor() or platform.machine()

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            args.model, revision=args.revision, trust_remote_code=args.trust_remote_code
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.model, revision=args.revision, trust_remote_code=args.trust_remote_code,
            torch_dtype="auto", device_map="auto" if device == "cuda" else None
        )
        if device == "cpu":
            model.to(device)
        model.eval()
        for task in tasks:
            prompt = task["prompt"]
            if getattr(tokenizer, "chat_template", None):
                messages = [{"role": "user", "content": prompt}]
                encoded_text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                inputs = tokenizer(encoded_text, return_tensors="pt")
            else:
                inputs = tokenizer(prompt, return_tensors="pt")
            model_device = next(model.parameters()).device
            inputs = {key: val.to(model_device) for key, val in inputs.items()}
            input_tokens = int(inputs["input_ids"].shape[-1])
            if device == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            generation_kwargs = {"max_new_tokens": args.max_new_tokens}
            if args.temperature > 0:
                generation_kwargs.update({"do_sample": True, "temperature": args.temperature})
            else:
                generation_kwargs["do_sample"] = False
            with torch.inference_mode():
                generated = model.generate(**inputs, **generation_kwargs)
            if device == "cuda":
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - t0
            new_tokens = generated[0][input_tokens:]
            response = tokenizer.decode(new_tokens, skip_special_tokens=True)
            records.append({
                "run_id": run_id, "task_id": task["task_id"], "category": task["category"],
                "split": task["split"], "prompt_sha256": sha256_text(prompt),
                "prompt": prompt, "response": response, "response_sha256": sha256_text(response),
                "input_tokens": input_tokens, "output_tokens": int(new_tokens.shape[-1]),
                "generation_seconds": elapsed,
                "tokens_per_second": (int(new_tokens.shape[-1]) / elapsed) if elapsed else None,
                "status": "completed"
            })
    except Exception as exc:
        status = "failed"
        error = repr(exc)
        records.append({"run_id": run_id, "status": "failed", "error": error})

    with raw_path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "run_id": run_id, "status": status, "error": error,
        "model": args.model, "revision": args.revision, "task_file": str(args.tasks),
        "task_file_sha256": task_hash, "task_count": len(tasks),
        "completed_count": sum(r.get("status") == "completed" for r in records),
        "device": device, "hardware": hardware, "python": sys.version,
        "platform": platform.platform(), "torch_version": torch.__version__,
        "started_at_epoch": started, "duration_seconds": time.time() - started,
        "max_new_tokens": args.max_new_tokens, "temperature": args.temperature,
        "trust_remote_code": args.trust_remote_code, "raw_file": str(raw_path),
        "raw_file_sha256": sha256_file(raw_path)
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
