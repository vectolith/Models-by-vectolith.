#!/usr/bin/env python3
"""Generate paired local Core Prime evaluation outputs. No hosted inference or training."""
import argparse
import json
from pathlib import Path


def build_messages(row, system_prompt=None):
    context = row.get("context", "").strip()
    prompt = row["prompt"].strip()
    user_text = "\n\n".join(part for part in (context, prompt) if part)
    messages = []
    if system_prompt and system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    messages.append({"role": "user", "content": user_text})
    return messages


def serialize_messages(messages):
    """Explicit role-marked fallback for tokenizers without a chat template."""
    return "\n\n".join(f"{message['role'].upper()}:\n{message['content']}" for message in messages)


def validate_cases(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Evaluation cases must be a nonempty JSONL list")
    ids = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each evaluation case must be a JSON object")
        case_id, prompt = row.get("id"), row.get("prompt")
        context = row.get("context", "")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Evaluation case IDs must be nonempty strings")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{case_id}: prompt must be a nonempty string")
        if not isinstance(context, str):
            raise ValueError(f"{case_id}: context must be a string")
        ids.append(case_id)
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation case IDs must be unique")
    return rows


def _input_device(model):
    try:
        return model.get_input_embeddings().weight.device
    except (AttributeError, RuntimeError, TypeError):
        return model.device


def _eos_token_ids(model, tokenizer):
    token_ids = getattr(tokenizer, "eos_token_id", None)
    if token_ids is None:
        token_ids = getattr(getattr(model, "generation_config", None), "eos_token_id", None)
    if token_ids is None:
        raise RuntimeError("Cannot verify completion: no EOS token ID is configured")
    if isinstance(token_ids, (list, tuple, set)):
        normalized = {int(token_id) for token_id in token_ids}
    else:
        normalized = {int(token_ids)}
    if not normalized:
        raise RuntimeError("Cannot verify completion: EOS token ID set is empty")
    return normalized


def generate(model, tokenizer, torch, messages, max_new_tokens):
    if max_new_tokens < 1:
        raise ValueError("max_new_tokens must be positive")
    if getattr(tokenizer, "chat_template", None) and callable(getattr(tokenizer, "apply_chat_template", None)):
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        )
    else:
        encoded = tokenizer(serialize_messages(messages), return_tensors="pt")
    if isinstance(encoded, dict):
        input_ids = encoded["input_ids"]
        attention_mask = encoded.get("attention_mask")
    else:
        input_ids = encoded
        attention_mask = None
    input_ids = input_ids.to(_input_device(model))
    generation_kwargs = {"max_new_tokens": max_new_tokens, "do_sample": False}
    if attention_mask is not None:
        generation_kwargs["attention_mask"] = attention_mask.to(_input_device(model))
    with torch.no_grad():
        generated = model.generate(input_ids, **generation_kwargs)
    sequences = getattr(generated, "sequences", generated)
    new_tokens = sequences[0][input_ids.shape[-1]:]
    token_ids = new_tokens.tolist() if hasattr(new_tokens, "tolist") else list(new_tokens)
    eos_ids = _eos_token_ids(model, tokenizer)
    eos_index = next((i for i, token_id in enumerate(token_ids) if int(token_id) in eos_ids), None)
    if eos_index is None:
        raise RuntimeError("Generation did not reach EOS within max_new_tokens; response rejected")
    token_ids = token_ids[: eos_index + 1]
    response = tokenizer.decode(token_ids, skip_special_tokens=True).strip()
    if not response:
        raise RuntimeError("Generation returned an empty response; response rejected")
    return response


def write_outputs(path, outputs):
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(outputs, ensure_ascii=False, indent=2) + "\n"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(serialized)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="Model ID or local directory")
    p.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--offline", action="store_true", help="Load only from local model cache/directory")
    p.add_argument("--character-prompt", type=Path, required=True, help="System prompt file for paired condition")
    p.add_argument("--max-new-tokens", type=int, required=True, help="Explicit per-run generation budget; no fixed default is imposed")
    args = p.parse_args()
    if args.max_new_tokens < 1:
        p.error("--max-new-tokens must be positive")
    try:
        rows = validate_cases([json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()])
        character = args.character_prompt.read_text(encoding="utf-8").strip()
        if not character:
            p.error("Character prompt file must not be empty")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    if args.output.exists():
        p.error("Output file already exists; use a fresh path to preserve prior results")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
    except ImportError as exc:
        raise SystemExit("Install optional transformers and torch in a free local environment; no inference was run.") from exc
    tok = AutoTokenizer.from_pretrained(args.model, local_files_only=args.offline)
    model = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=args.offline, torch_dtype="auto", device_map="auto")
    outputs = {}
    for row in rows:
        outputs[row["id"]] = {}
        for condition, system_prompt in (("base", None), ("character_prompt", character)):
            outputs[row["id"]][condition] = generate(
                model, tok, torch, build_messages(row, system_prompt), args.max_new_tokens
            )
    try:
        write_outputs(args.output, outputs)
    except FileExistsError:
        p.error("Output file already exists; use a fresh path to preserve prior results")
    print(f"Generated paired outputs for {len(outputs)} cases using {args.model}")


if __name__ == "__main__":
    main()
