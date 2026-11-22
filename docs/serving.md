# Serving ASH PRIME and FYR PRIMA

Both students are LoRA adapters over Apache-2.0 foundations, so they can be served by
any OpenAI-compatible runtime. Nothing here requires a paid service.

## Adapter layout

A training run writes:

    out/ash-prime-adapter/     LoRA weights + tokenizer
    out/fyr-prima-adapter/     LoRA weights + tokenizer
    out/ash-prime-training-manifest.json
    out/fyr-prima-training-manifest.json
    out/ash-prime-evaluation.json
    out/fyr-prima-evaluation.json
    out/run-summary.json

## Local GPU, vLLM

    vllm serve Qwen/Qwen3-4B-Instruct-2507 \
      --enable-lora \
      --lora-modules ash-prime=./out/ash-prime-adapter \
      --max-lora-rank 16 \
      --served-model-name ash-prime \
      --port 8000

FYR PRIMA runs the same way with `Qwen/Qwen3-1.7B` and `fyr-prima`.

## CPU or laptop, llama.cpp

    python llama.cpp/convert_lora_to_gguf.py ./out/ash-prime-adapter --outfile ash-prime-lora.gguf
    llama-server -m granite-or-qwen-base.gguf --lora ash-prime-lora.gguf --port 8000

## Contract the caller sees

The endpoint is plain OpenAI chat completions:

    POST /v1/chat/completions
    { "model": "ash-prime", "messages": [...] }

Any client that speaks that protocol can use the model without knowing it is an adapter.

## Wiring it into BLUD

BLUD selects a model per workspace through gateway settings, so serving ASH PRIME to
BLUD means registering the endpoint behind the gateway BLUD already calls and pointing a
workspace at the model id. BLUD needs no code change to switch models; it needs a
provider entry that resolves `ash-prime` to the endpoint above.

## Status

Adapters only exist after a training run completes. Until a run has produced
`run-summary.json` and the two manifests, nothing here is a claim that a model is
deployed.
