#!/usr/bin/env python3
"""Generate paired base and prompt-character outputs for blind Core Prime evaluation.

Inference is local/offline when requested. This script does not train a model.
"""
import argparse
import json
from pathlib import Path

def build_messages(row, system_prompt=None):
    user_text = "\n\n".join(part for part in (row.get("context", "").strip(), row["prompt"].strip()) if part)
    messages = []
    if system_prompt and system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": user_text})
    return messages

def generate(model, tokenizer, torch, messages, max_new_tokens):
    if not hasattr(tokenizer, "apply_chat_template"):
        raise RuntimeError("Tokenizer must support apply_chat_template for consistent chat evaluation.")
    inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
    if not isinstance(inputs, torch.Tensor):
        inputs = inputs["input_ids"]
    inputs = inputs.to(model.device)
    with torch.no_grad():
        generated = model.generate(inputs, max_new_tokens=max_new_tokens, do_sample=False)
    return tokenizer.decode(generated[0][inputs.shape[-1]:], skip_special_tokens=True).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="HF model ID or local directory")
    parser.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true", help="Load only from local model cache/directory")
    parser.add_argument("--character-prompt", type=Path, required=True, help="Character system prompt text")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()
    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
    except ImportError as exc:
        raise SystemExit("Install optional transformers and torch in a genuinely free local environment; no inference was run.") from exc
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=args.offline)
    model = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=args.offline, torch_dtype="auto", device_map="auto")
    character = args.character_prompt.read_text(encoding="utf-8")
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    outputs = {}
    seen = set()
    for row in cases:
        case_id = row.get("id")
        if not case_id or case_id in seen:
            raise ValueError(f"Missing or duplicate case id: {case_id}")
        seen.add(case_id)
        outputs[case_id] = {
            "base": generate(model, tokenizer, torch, build_messages(row), args.max_new_tokens),
            "character_prompt": generate(model, tokenizer, torch, build_messages(row, character), args.max_new_tokens),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated paired base and character-prompt outputs for {len(outputs)} cases using {args.model}")

if __name__ == "__main__":
    main()
