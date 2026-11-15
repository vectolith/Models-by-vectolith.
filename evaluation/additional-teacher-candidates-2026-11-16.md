# Additional efficient teacher candidates — discovery register (2026-11-16)

This register expands discovery only. No new model is admitted as a teacher until its exact revision, license terms, loader, resource profile, real Prime responses, independent grading and training-output permissions are verified. Existing three contributors remain intact; these are additive candidates, not replacements.

| Candidate | Why test it | Main risks / gates | Initial disposition |
|---|---|---|---|
| Qwen/Qwen3.5-2B | Compact 2B multimodal-family model; official card reports Apache-2.0, long context and broad language coverage. A useful independent architecture and efficiency test. | Multimodal/hybrid architecture; current text-only runner must not be assumed compatible. Pin revision, inspect exact license, verify tokenizer/template and Transformers loader. | Snapshot + compatibility smoke test only |
| google/gemma-4-E2B-it | Efficient edge-oriented model family with instruction tuning, reasoning, native tool/function calling and multimodal support. | Confirm repository access/gating, model-specific terms and full license; multimodal loader required; embeddings make total memory larger than effective parameter count. | Snapshot + compatibility smoke test only |
| LiquidAI/LFM2.5-2.6B | Hybrid on-device model; publisher reports agentic post-training, tool-use and CPU/edge efficiency. Official card lists LFM Open License rather than Apache-2.0. | Custom hybrid architecture may need a different runtime; benchmark claims are publisher-reported; legal review of LFM Open License required; training-output permission remains unverified. | Snapshot + compatibility smoke test only |
| nvidia/NVIDIA-Nemotron-3-Nano-4B | Hybrid Mamba/Transformer model with tool-use and edge-inference focus; useful efficiency candidate. | Architecture/runtime compatibility and OpenMDW-1.1 license review required; publisher's GPU measurements are not CPU guarantees. | Defer until license and loader review |

## Evidence links

- Qwen3.5-2B official model card: https://huggingface.co/Qwen/Qwen3.5-2B
- Gemma 4 official model card: https://huggingface.co/google/gemma-4-E2B-it
- Gemma 4 technical overview: https://huggingface.co/blog/gemma4
- LiquidAI LFM2.5-2.6B official model card: https://huggingface.co/LiquidAI/LFM2.5-2.6B
- NVIDIA Nemotron 3 Nano 4B technical overview: https://huggingface.co/blog/nvidia/nemotron-3-nano-4b

Publisher benchmark, latency and memory figures are discovery leads only. Vectolith must reproduce measurements on the same runner and identical prompts. Parameter count is not equivalent to memory footprint, particularly for multimodal, hybrid and shared-embedding architectures.

## Admission protocol

1. Snapshot immutable Hub revision, full model card, config, tokenizer, all license files, weight inventory and SHA-256.
2. Record architecture, parameter count (total and active where applicable), dtype/quantization, context, dependencies, trust_remote_code requirements and loader class.
3. Run a deterministic 5–10 prompt smoke test, then the same full Prime v1–v4 suite only after successful loading.
4. Measure download size/time, load time, peak RSS/VRAM, tokens/sec, time-to-first-token, prompt throughput, output length and failure rate.
5. Grade actual outputs independently using the same blinded rubric and preserve every response.
6. Verify explicit written permission for using generated outputs in student training separately from the model-weight license. Keep training_output_permission=not_verified until verified.
7. Add admitted candidates as additive contributors. Never remove an existing teacher's preserved responses or select one teacher as the winner.

## Current status

All candidates above are untested by Vectolith for this curriculum. No new teacher has been admitted, run, qualified or authorized for training.
