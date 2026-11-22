"""Local interactive inference CLI for a ASH PRIME checkpoint."""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = "You are ASH PRIME, a model from Models by vectolith. Be accurate, state uncertainty, preserve constraints, and never claim actions you have not performed."


def render_messages(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return "\\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages) + "\\nASSISTANT:"


def trim_messages(tokenizer: Any, messages: list[dict[str, str]], budget: int) -> list[dict[str, str]]:
    """Drop oldest conversation turns while preserving the system message and newest input."""
    kept = list(messages)
    while len(kept) > 2 and len(tokenizer(render_messages(tokenizer, kept), add_special_tokens=False)["input_ids"]) > budget:
        # Keep system instructions and the latest user request; discard the oldest conversational item.
        del kept[1]
    return kept


def load_local_generator(checkpoint: Path, max_new_tokens: int = 512, max_context_tokens: int = 4096):
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
        budget = max(1, max_context_tokens - max_new_tokens)
        trimmed = trim_messages(tokenizer, messages, budget)
        rendered = render_messages(tokenizer, trimmed)
        inputs = tokenizer(rendered, return_tensors="pt")
        # For dispatched/sharded models, send inputs to the embedding layer's device.
        try:
            device = model.get_input_embeddings().weight.device
        except (AttributeError, RuntimeError):
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
    print("ASH PRIME local CLI. Type /exit to quit, /reset to clear conversation.")
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
        print(f"ASH PRIME> {answer}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ash-prime", description="Run a local ASH PRIME checkpoint.")
    parser.add_argument("--checkpoint", required=True, help="Local checkpoint directory (offline; no download).")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-context-tokens", type=int, default=4096, help="Input context budget including chat formatting.")
    parser.add_argument("--prompt", help="Run a single prompt and exit.")
    args = parser.parse_args(argv)
    if args.max_new_tokens < 1 or args.max_new_tokens > 8192:
        parser.error("--max-new-tokens must be between 1 and 8192")
    if args.max_context_tokens < 256 or args.max_context_tokens > 131072:
        parser.error("--max-context-tokens must be between 256 and 131072")
    try:
        generator = load_local_generator(Path(args.checkpoint), args.max_new_tokens, args.max_context_tokens)
    except Exception as exc:
        parser.exit(2, f"ash-prime: {type(exc).__name__}: {exc}\\n")
    return chat_loop(generator, one_shot=args.prompt)


if __name__ == "__main__":
    raise SystemExit(main())
