#!/usr/bin/env python3
"""Generate paired base and prompt-character outputs for blind Core Prime evaluation."""
import argparse
import json
from pathlib import Path


def read_cases(path):
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row.get("id") for row in cases]
    if not ids or any(not case_id for case_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Cases must have nonempty, unique IDs.")
    if any(not isinstance(row.get("prompt"), str) or not row["prompt"].strip() for row in cases):
        raise ValueError("Every case must have a nonempty prompt.")
    return cases


def build_messages(row, system_prompt=None):
    user_text = "\n\n".join(part for part in (row.get("context", "").strip(), row["prompt"].strip()) if part)
    messages = []
    if system_prompt and system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": user_text})
    return messages


def generate(model, tokenizer, torch, messages, max_new_tokens):
    if not getattr(tokenizer, "chat_template", None):
        raise RuntimeError("Tokenizer must provide a chat template for consistent paired evaluation.")
    inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
    if not isinstance(inputs, torch.Tensor):
        inputs = inputs["input_ids"]
    inputs = inputs.to(model.get_input_embeddings().weight.device)
    with torch.no_grad():
        generated = model.generate(inputs, max_new_tokens=max_new_tokens, do_sample=False, use_cache=True)
    text = tokenizer.decode(generated[0][inputs.shape[-1]:], skip_special_tokens=True).strip()
    if not text:
        raise RuntimeError("Model returned an empty response; refusing incomplete experiment data.")
    return text


def validate_outputs(cases, outputs):
    expected = {row["id"] for row in cases}
    if set(outputs) != expected:
        raise ValueError(f"Output IDs mismatch: missing={sorted(expected-set(outputs))}, extra={sorted(set(outputs)-expected)}")
    for case_id, conditions in outputs.items():
        if set(conditions) != {"base", "character_prompt"}:
            raise ValueError(f"{case_id}: expected exactly base and character_prompt")
        if any(not isinstance(value, str) or not value.strip() for value in conditions.values()):
            raise ValueError(f"{case_id}: both responses must be nonempty strings")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Model ID or local directory; use an immutable revision where possible")
    parser.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true", help="Load only from local model cache/directory")
    parser.add_argument("--character-prompt", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()
    if args.max_new_tokens < 1:
        parser.error("--max-new-tokens must be positive")
    if not args.cases.is_file() or not args.character_prompt.is_file():
        parser.error("Cases and character prompt files must exist.")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
    except ImportError as exc:
        raise SystemExit("Install torch and transformers in a genuinely free environment; no inference was run.") from exc
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=args.offline)
    model = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=args.offline, torch_dtype="auto", device_map="auto")
    model.eval()
    character = args.character_prompt.read_text(encoding="utf-8")
    cases = read_cases(args.cases)
    outputs = {}
    for row in cases:
        case_id = row["id"]
        outputs[case_id] = {
            "base": generate(model, tokenizer, torch, build_messages(row), args.max_new_tokens),
            "character_prompt": generate(model, tokenizer, torch, build_messages(row, character), args.max_new_tokens),
        }
    validate_outputs(cases, outputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validated paired outputs: {len(outputs)} cases, 2 conditions each, model={args.model}")


if __name__ == "__main__":
    main()
