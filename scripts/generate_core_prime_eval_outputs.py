#!/usr/bin/env python3
"""Generate local paired Core Prime evaluation outputs. No hosted inference or training."""
import argparse
import json
from pathlib import Path

def build_messages(row, system_prompt=None):
    prompt = "\\n\\n".join(part for part in (row.get("context", "").strip(), row["prompt"].strip()) if part)
    messages = []
    if system_prompt and system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": prompt})
    return messages

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="Model ID or local directory")
    p.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--character-prompt", type=Path, required=True, help="System prompt file for paired condition")
    p.add_argument("--max-new-tokens", type=int, default=256)
    args = p.parse_args()
    if args.max_new_tokens < 1: p.error("--max-new-tokens must be positive")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
    except ImportError as exc:
        raise SystemExit("Install optional transformers and torch in a free local environment; no inference was run.") from exc
    tok = AutoTokenizer.from_pretrained(args.model, local_files_only=args.offline)
    model = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=args.offline, torch_dtype="auto", device_map="auto")
    rows = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row.get("id") for row in rows]
    if any(not isinstance(x, str) or not x.strip() for x in ids) or len(ids) != len(set(ids)):
        p.error("Evaluation cases must have unique, nonempty string IDs")
    character = args.character_prompt.read_text(encoding="utf-8").strip()
    if not character: p.error("Character prompt file must not be empty")
    outputs = {}
    for row in rows:
        outputs[row["id"]] = {}
        for condition, system_prompt in (("base", None), ("character_prompt", character)):
            messages = build_messages(row, system_prompt)
            if hasattr(tok, "apply_chat_template") and tok.chat_template:
                encoded = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
            else:
                text = "\\n\\n".join(m["content"] for m in messages)
                encoded = tok(text, return_tensors="pt").input_ids
            encoded = encoded.to(model.device)
            with torch.no_grad():
                generated = model.generate(encoded, max_new_tokens=args.max_new_tokens, do_sample=False)
            outputs[row["id"]][condition] = tok.decode(generated[0][encoded.shape[-1]:], skip_special_tokens=True).strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(f"Generated paired outputs for {len(outputs)} cases using {args.model}")

if __name__ == "__main__":
    main()
