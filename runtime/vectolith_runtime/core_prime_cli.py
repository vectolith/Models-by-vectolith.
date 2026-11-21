"""Local interactive inference CLI for a Core Prime checkpoint."""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = "You are Core Prime, a model from Models by vectolith. Be accurate, state uncertainty, preserve constraints, and never claim actions you have not performed."


def render_messages(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages) + "\nASSISTANT:"


def load_local_generator(checkpoint: Path, max_new_tokens: int = 512):
    if not checkpoint.is_dir():
        raise FileNotFoundError(f"Checkpoint directory does not exist: {checkpoint}")
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Install inference dependencies: pip install 'vectolith-runtime[training]'") from exc
    tokenizer = AutoTokenizer.from_pretrained(str(checkpoint), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(checkpoint), device_map="auto", dtype="auto", local_files_only=True
    )
    model.eval()

    def generate(messages: list[dict[str, str]]) -> str:
        rendered = render_messages(tokenizer, messages)
        inputs = tokenizer(rendered, return_tensors="pt")
        device = getattr(model, "device", None)
        if device is not None:
            inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        suffix = output[0][inputs["input_ids"].shape[-1]:]
        return tokenizer.decode(suffix, skip_special_tokens=True).strip()
    return generate


def chat_loop(generate, *, one_shot: str | None = None) -> int:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if one_shot is not None:
        messages.append({"role": "user", "content": one_shot})
        print(generate(messages))
        return 0
    print("Core Prime local CLI. Type /exit to quit, /reset to clear conversation.")
    while True:
        try:
            user = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user:
            continue
        if user.lower() in {"/exit", "/quit"}:
            return 0
        if user.lower() == "/reset":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("Conversation reset.")
            continue
        messages.append({"role": "user", "content": user})
        try:
            answer = generate(messages)
        except Exception as exc:  # surface model errors without crashing the session
            messages.pop()
            print(f"Inference error: {type(exc).__name__}: {exc}")
            continue
        messages.append({"role": "assistant", "content": answer})
        print(f"Core Prime> {answer}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="core-prime", description="Run a local Core Prime checkpoint.")
    parser.add_argument("--checkpoint", required=True, help="Local checkpoint directory (offline; no download).")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--prompt", help="Run a single prompt and exit.")
    args = parser.parse_args(argv)
    if args.max_new_tokens < 1 or args.max_new_tokens > 8192:
        parser.error("--max-new-tokens must be between 1 and 8192")
    try:
        generator = load_local_generator(Path(args.checkpoint), args.max_new_tokens)
    except Exception as exc:
        parser.exit(2, f"core-prime: {type(exc).__name__}: {exc}\n")
    return chat_loop(generator, one_shot=args.prompt)


if __name__ == "__main__":
    raise SystemExit(main())
