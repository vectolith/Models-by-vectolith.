# Core Prime foundation candidate screening — 2026-11-17

**Decision: OPEN. No foundation is selected or approved.** This is a source-backed screening comparison, not a measured benchmark or selection decision.

| Candidate | Publicly documented size / architecture | Context / modality | Public license declaration | Screening observation |
|---|---|---|---|---|
| `Qwen/Qwen3.5-9B` | 9B language model with hybrid Gated DeltaNet / attention and vision encoder | 262K native context; text + image | Apache 2.0 | Broad multilingual and multimodal candidate; must measure actual memory, latency, tool use and coding on VELNOR fixtures. |
| `ibm-granite/granite-4.2-8b` | 8B dense reasoning model | 128K; text, reasoning and tool-calling | Apache 2.0 | Strong candidate for coding, reasoning and tool-use; publisher lists approximately 19GB BF16 VRAM, so measure exact serving/training profile. |
| `google/gemma-4-E4B` | E4B effective parameters; dense model with per-layer embeddings | 128K; text, image and audio | Apache 2.0 | Smaller effective footprint and multimodal inputs; validate total parameter/embedding memory, tokenizer, loader and license conditions at exact revision. |
| `mistralai/Mistral-Small-4` | 119B total MoE, about 6.5B active per token | 256K; text + image, reasoning and tool calls | Apache 2.0 | High-capability reference, but not a lightweight deployment candidate: publisher recommends multi-H100/H200/B200-class infrastructure. Keep as a capability/architecture reference only if it can be measured on verified no-cost hardware; otherwise mark it blocked by compute availability. |
| `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` | 30B total / 3B active MoE; hybrid Mamba-2 + MoE + attention | Up to 1M; text-only | OpenMDW License Agreement 1.1 | Add to the controlled shortlist for efficient agent execution and distillation research. Despite 3B active parameters, 30B total weights still affect storage and memory; benchmark BF16 and NVFP4 separately. Exact revision and legal review pending. |

## Sources

- [Qwen3.5-9B model card](https://huggingface.co/Qwen/Qwen3.5-9B) — Apache 2.0 declaration, 9B, multimodal and 262K context.
- [Granite 4.2 official model documentation](https://www.ibm.com/granite/docs/models/granite/) and [Granite 4.2 8B model selector](https://www.ibm.com/granite/playground/model-selector) — Apache 2.0, 8B and published resource estimates.
- [Google Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4) — Apache 2.0, E4B effective size and multimodal support.
- [Mistral Small 4 announcement](https://mistral.ai/news/mistral-small-4/) and [Mistral model comparison](https://docs.mistral.ai/getting-started/models/compare?models=mistral-small-4-0-26-03) — Apache 2.0, 119B total / 6.5B active, 256K context and recommended infrastructure.

## What this comparison does not establish

- It does not compare measured Core Prime quality, coding correctness, tool-use reliability, multilingual performance, safety, latency, throughput, VRAM, or resource efficiency on a common controlled setup.
- It does not pin immutable revisions or hash exact-revision LICENSE, NOTICE, config, tokenizer, chat template or weight inventory.
- It does not approve the model's use as a foundation or verify training rights.
- It does not authorize compute or training.

## Next controlled comparison

Run the exact five candidates without substituting model IDs, revisions, quantizations or architectures. Capture immutable snapshots and exact license files; test loader compatibility; execute the same public controlled suite and deterministic verifiers; measure peak VRAM/RAM, throughput, TTFT and concurrency; preserve raw artifacts; then make a separate protected-holdout comparison for active Core Prime. Core Prima is paused and has no active foundation-selection scorecard. The authorized model-selection owner must approve one exact model ID and 40-character revision only after reviewing the evidence package. If a candidate cannot be tested in a currently available and approved execution environment, mark it blocked rather than relaxing the evaluation.


## Nemotron 3.5 research addition

NVIDIA's October 14, 2026 release describes Nemotron 3.5 Lightning as a 30B-total / 3B-active text model with a hybrid Mamba-Transformer MoE architecture, up to 1M context, and BF16/NVFP4 checkpoints. It is designed for efficient long-running agent execution, with NeMo training and inference recipes. This makes it a relevant candidate for controlled Core Prime evaluation, but not an automatic foundation choice: active parameter count is not the same as checkpoint memory, and its 30B total parameters must be included in storage, VRAM/RAM and deployment-cost measurements. Its governing terms are OpenMDW 1.1, not Apache 2.0.

Nemotron 3.5's specialized teacher family is also relevant to the teacher-orchestration research, but these models are not added to the five-candidate Run 42 grading population and do not count toward teacher qualification. See [Nemotron specialist teacher research](core-prime-nemotron-teacher-research.md).

Additional sources:
- [NVIDIA Nemotron 3.5 Super and Lightning release](https://research.nvidia.com/labs/nemotron/Nemotron-3.5-Super-and-Lightning/) — architecture, parameter counts, context, checkpoint variants and training recipe.
- [Nemotron 3.5 Lightning training recipe](https://docs.nvidia.com/nemotron/nightly/nemotron/lightning35/README.html) — base/instruct checkpoints and deployment recipes.
- [NVIDIA Nemotron 3.5 Lightning model card](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b/modelcard) — benchmark methodology, use cases and OpenMDW 1.1 declaration.
