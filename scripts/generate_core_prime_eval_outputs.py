#!/usr/bin/env python3
"""Generate evaluation outputs using a local HF Transformers model. No hosted inference."""
import argparse
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, help="Model ID or local directory")
    p.add_argument("--cases", type=Path, default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--character-prompt", type=Path, help="System prompt file; generates prompt-only character condition")
    p.add_argument("--max-new-tokens", type=int, default=256)
    args = p.parse_args()
    if args.max_new_tokens < 1:
        p.error("--max-new-tokens must be positive")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
    except ImportError as exc:
        raise SystemExit("Install optional transformers and torch in a free local environment; no inference was run.") from exc
    tok = AutoTokenizer.from_pretrained(args.model, local_files_only=args.offline)
    model = AutoModelForCausalLM.from_pretrained(args.model, local_files_only=args.offline, torch_dtype="auto", device_map="auto")
    rows = [json.loads(x) for x in args.cases.read_text(encoding="utf-8").splitlines() if x.strip()]
    character = args.character_prompt.read_text(encoding="utf-8").strip() if args.character_prompt else None
    outputs = {}
    for row in rows:
        prompt = (row.get("context", "") + "\n" + row["prompt"]).strip()
        conditions = {"base": None}
        if character:
            conditions["character_prompt"] = character
        outputs[row["id"]] = {}
        for condition, system_prompt in conditions.items():
            messages = ([{"role": "system", "content": system_prompt}] if system_prompt else []) + [{"role": "user", "content": prompt}]
            if hasattr(tok, "apply_chat_template") and tok.chat_template:
                encoded = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt")
            else:
                fallback = ((system_prompt + "\n") if system_prompt else "") + prompt
                encoded = tok(fallback, return_tensors="pt").input_ids
            encoded = encoded.to(model.device)
            with torch.no_grad():
                generated = model.generate(encoded, max_new_tokens=args.max_new_tokens, do_sample=False)
            response = tok.decode(generated[0][encoded.shape[-1]:], skip_special_tokens=True).strip()
            outputs[row["id"]][condition] = response
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(outputs)} cases; conditions: base" + (", character_prompt" if character else ""))

if __name__ == "__main__":
    main()
