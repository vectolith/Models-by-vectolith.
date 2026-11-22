# ASH PRIME foundation candidate hardware screen — 2026-11-18

## Status and scope

This is a preliminary hardware/loader feasibility screen, not a benchmark, legal opinion, candidate ranking, or foundation selection. No model weights were downloaded and no inference was run for this screen. Exact-checkpoint legal review and explicit training-output permission remain mandatory.

The currently observed Kaggle environment has two independent NVIDIA Tesla T4 GPUs, each with 15 GiB VRAM. Their VRAM is not pooled. NVIDIA lists T4 at CUDA compute capability 7.5; the CUDA capability matrix lists FP16 Tensor Core support at 7.5 but BF16 Tensor Core support beginning at 8.0. Therefore the present T4 session must not be treated as a BF16 training environment. FP16 is the hardware-supported mixed-precision path, subject to software/model validation.

## Important trainer compatibility finding

The current ASH PRIME trainer imports `AutoModelForCausalLM`, calls `from_pretrained(..., device_map="auto")`, and does not set an explicit model dtype. It uses ordinary LoRA, not QLoRA, and does not currently configure gradient checkpointing. This is not yet a safe generic loader for every candidate below.

Before a training run, the trainer must:
- Bind the selected model architecture and loader class to the immutable foundation manifest.
- Require an explicit dtype in the run configuration and validate it against observed GPU compute capability.
- Refuse BF16 on the T4; use FP16 only where the exact model and kernels support it.
- Avoid assuming that two T4 devices provide one 30 GiB allocation. Measure whether a single-device load fits, or implement and test a supported distributed-training strategy.
- Measure peak allocated/reserved VRAM, host RAM, throughput, and stability with a bounded no-training load/forward probe before authorizing SFT.
- Add gradient checkpointing and memory-bounded sequence/batch settings where supported. Do not assume LoRA removes base-weight or activation memory.

## Preliminary candidate screen

| Exact model ID | Published size and architecture | Published license metadata | Preliminary T4 fit / loader notes |
|---|---|---|---|
| `ibm-granite/granite-4.2-3b` | 3B dense; `GraniteForCausalLM`; BF16 checkpoint; observed Hub snapshot listing totals about 7.33 GB | Apache 2.0 | Strongest immediate compatibility candidate for a controlled FP16 test: it is a causal-LM architecture compatible in principle with the current loader. Still needs explicit FP16 load, measured single-T4 memory, exact revision pin, tokenizer/chat-template check, and legal/output-permission review. Not selected. |
| `Qwen/Qwen3.5-2B-Base` | 2B language backbone with vision encoder; hybrid Gated DeltaNet/Gated Attention; image-text-to-text pipeline | Apache 2.0 | Attractive size, but the published pipeline is image-text-to-text and architecture is multimodal. Do not assume the current `AutoModelForCausalLM` trainer is compatible; an explicit architecture/processor adapter and text-only training path must be tested. |
| `google/gemma-4-E2B` | 2.3B effective parameters / 5.1B including embeddings; multimodal; model card uses `AutoModelForMultimodalLM`; Google estimates 11.4 GB BF16 load memory | Apache 2.0 | Potentially within raw capacity only with a validated low-memory path, but Google's published Gemma QLoRA example explicitly checks for BF16 GPU support. T4 is CC 7.5 and lacks BF16 Tensor Core support. The current trainer has no QLoRA path. Do not schedule on T4 without a separately tested FP16/quantized route. |
| `ibm-granite/granite-4.2-8b` | 8B dense; `GraniteForCausalLM`; BF16; IBM model selector estimates about 19 GB VRAM | Apache 2.0 | Does not fit one 15 GiB T4 in the published BF16 configuration. Two GPUs do not make a single 30 GiB pool. Not a first-run candidate on this hardware. |
| `Qwen/Qwen3.5-9B` | 9B language backbone with vision encoder; image-text-to-text pipeline; 262K native context | Apache 2.0 | Approximate BF16 weight payload alone is about 18 GB before runtime/activation overhead. Not viable on one T4; architecture adapter also required. |
| `mistralai/Mistral-Small-4-119B-2603` | 119B total / 6.5B active MoE; multimodal; 256K context | Apache 2.0 | Mistral's own launch material specifies minimum infrastructure of 4× HGX H100. Not viable on the current Kaggle T4 session. |

These are capability/fit observations only. A smaller model is not automatically better; quality must be measured on the same protected evaluation design and rubric. No model is declared the winner.

## Practical direction

The current T4 environment narrows the first-run feasibility investigation to small candidates with a tested FP16 route and a supported loader. Granite 4.2 3B is the most straightforward architecture fit to test first because it is a dense causal LM and has a 3B checkpoint. Qwen3.5-2B Base and Gemma 4 E2B remain separate comparators, but each needs a model-specific training adapter and additional memory/dtype validation.

This is a proposal for the order of engineering investigation, not approval to download or execute any model. Do not begin model downloads, inference, or training until the candidate-specific legal and permission gates and the user's run-specific execution approval are satisfied.

## Sources

- NVIDIA CUDA compute capability and Tensor Core input-type matrix: https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html
- NVIDIA T4 specifications: https://www.nvidia.com/en-us/data-center/tesla-t4/
- IBM Granite 4.2 3B model card: https://huggingface.co/ibm-granite/granite-4.2-3b
- IBM Granite 4.2 3B pinned snapshot inventory: https://huggingface.co/ibm-granite/granite-4.2-3b/tree/be9e7d995f2a6be22def5dd815f9f2bae98c8b6e
- IBM Granite 4.2 8B model selector and memory estimate: https://www.ibm.com/granite/playground/model-selector
- Qwen3.5-2B Base model card: https://huggingface.co/Qwen/Qwen3.5-2B-Base
- Qwen3.5-9B model card: https://huggingface.co/Qwen/Qwen3.5-9B
- Google Gemma 4 model card: https://ai.google.dev/gemma/docs/core/model_card_4.md
- Google Gemma 4 QLoRA guide and BF16 hardware check: https://ai.google.dev/gemma/docs/core/huggingface_vision_finetune_qlora
- Mistral Small 4 official release and minimum infrastructure: https://mistral.ai/news/mistral-small-4/
