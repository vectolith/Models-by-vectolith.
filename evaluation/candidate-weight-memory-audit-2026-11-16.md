# Candidate checkpoint and inference-memory audit — 2026-11-16

## Status and interpretation

This is a source-backed storage and memory-planning audit of the complete current teacher-candidate register: 16 unique models in the Prime/Prima role panels plus three additional unique models in expanded intake (19 unique models total). Shared candidates are listed once below and retain their role assignments in `evaluation/fixtures/teacher_panel_candidates_v1.json`.

**No model was loaded or benchmarked during this audit.** Checkpoint sizes below are published Hugging Face repository/file inventory sizes or publisher-stated checkpoint sizes, not locally downloaded byte counts. Runtime memory is either an official publisher estimate or a planning estimate. It is not a measured VELNOR result. No free GPU session, accelerator type, VRAM, RAM, or disk quota has been verified for this project.

A Hugging Face repository's displayed total can include tokenizer/configuration files and multiple alternative weight layouts. It must not automatically be interpreted as one runtime checkpoint. Pinning exact immutable revisions and collecting each selected weight file's byte size and SHA-256 remains mandatory before inference.

## Candidate inventory

All sizes are decimal GB unless explicitly marked GiB. BF16 planning ranges for models without publisher memory guidance assume approximately 2 bytes per parameter plus a modest runtime reserve; they exclude variable KV-cache growth, allocator fragmentation, vision/audio encoders where not separately quantified, and framework overhead. For these models the planning range is deliberately conservative, not a hardware guarantee.

| Candidate | Role(s) | Published checkpoint / weight inventory | Inference-memory planning |
|---|---|---:|---|
| Qwen3.5-9B | Prime | 19.3 GB Hub snapshot | ~20–24 GB BF16 planning range |
| Qwen3.6-35B-A3B | Prime, Prima | 71.9 GB Hub snapshot; 35B total / ~3B active | ~76–86 GB BF16; all experts/weights must be resident |
| Granite 4.2-8B | Prime, Prima | IBM lists 16.38 GB BF16 weights | ~19 GB BF16 VRAM, IBM estimate |
| gpt-oss-20b | Prime, Prima | 12.8 GiB native MXFP4 checkpoint | 16 GB minimum-class memory with MXFP4; ~48 GB in BF16 |
| Qwen2.5-7B-Instruct | Prime (historical comparator) | 15.2 GB Hub snapshot; pinned revision in manifest | ~17–19 GB BF16 planning range |
| Devstral-Small-2-24B-Instruct-2512 | Prime, Prima | Hub displays 51.6 GB repository total with two parallel weight layouts; do not sum/choose blindly | ~48 GB BF16 theoretical weights before runtime; exact selected layout/dtype still requires pinned-index inspection |
| Qwen3.8-27B | Prime, Prima | 55.6 GB Hub snapshot | ~60–67 GB BF16 planning range |
| Gemma 4 E2B-it | Prime, Prima | 10.2 GB model file | 11.4 GB BF16 / 5.7 GB 8-bit / 2.9 GB Q4_0 official estimates |
| Gemma 4 E4B-it | Prime, Prima | 16.0 GB model file | 17.9 GB BF16 / 8.9 GB 8-bit / 4.5 GB Q4_0 official estimates |
| Gemma 4 12B-it | Prime, Prima | 23.9 GB model file | 26.7 GB BF16 / 13.4 GB 8-bit / 6.7 GB Q4_0 official estimates |
| Gemma 4 26B-A4B-it | Prime, Prima | 51.6 GB model files | 57.7 GB BF16 / 28.8 GB 8-bit / 14.4 GB Q4_0 official estimates; 26B total, ~4B active |
| Gemma 4 31B-it | Prime, Prima | 62.6 GB Hub snapshot | 69.9 GB BF16 / 34.9 GB 8-bit / 17.5 GB Q4_0 official estimates |
| Qwen3.6-27B | Prime, Prima | 55.6 GB Hub snapshot | ~60–67 GB BF16 planning range |
| Qwen3.5-4B | Prime, Prima | 9.34 GB Hub snapshot | ~10–12 GB BF16 planning range |
| Qwen3-Coder-Next | Prima | 159 GB Hub snapshot; 80B total / ~3B active | ~160 GB BF16 theoretical weights before runtime; active count does not reduce resident checkpoint storage |
| Qwen2.5-Coder-7B-Instruct | Prima | 15.2 GB Hub snapshot | ~17–19 GB BF16 planning range |
| Granite 4.2-3B | Expanded intake, Prime + Prima hypothesis | IBM lists 6.82 GB BF16 weights | ~8 GB BF16 VRAM, IBM estimate |
| MiniCPM5-2B | Expanded intake, Prime + Prima hypothesis | 5.03 GB model weight file (5.04 GB repo) | ~6–7 GB BF16 planning range |
| Ministral-3B-Instruct | Expanded intake, Prime + Prima hypothesis | 6.63 GB Hub snapshot | ~7–8 GB BF16 planning range |

## Important corrections to prior rough estimates

1. **gpt-oss-20b is not a 42 GB native checkpoint.** OpenAI publishes it natively in MXFP4: 12.8 GiB checkpoint and approximately 16 GB memory requirement. The approximately 48 GB figure applies to a BF16-expanded execution path, not the native artifact.
2. **MoE active parameters are not the storage requirement.** Qwen3.6-35B-A3B, Qwen3-Coder-Next and Gemma 4 26B-A4B still need the full expert weights available. Active parameters primarily affect per-token compute, not total resident checkpoint size.
3. **Gemma E2B/E4B total storage is larger than effective parameter count suggests.** Per-layer embeddings contribute to weight storage. Use the publisher's measured memory table, not effective parameters × 2.
4. **Devstral's 51.6 GB Hub repository total is not a safe single-checkpoint estimate.** The repository exposes two parallel weight layouts. The exact revision, index, dtype and intended serving layout must be pinned and inspected before download or runtime planning.
5. **Qwen2.5-7B-Instruct remains a historical comparator.** Its inclusion does not reinstate it on either active shortlist or qualify it as a teacher.

## Sources

- Qwen3.5-9B Hub file inventory: https://huggingface.co/Qwen/Qwen3.5-9B/tree/main
- Qwen3.6-35B-A3B Hub file inventory: https://huggingface.co/Qwen/Qwen3.6-35B-A3B/tree/main
- Qwen3.8-27B Hub file inventory: https://huggingface.co/Qwen/Qwen3.8-27B/tree/main
- Qwen3.6-27B Hub file inventory: https://huggingface.co/Qwen/Qwen3.6-27B/tree/main
- Qwen3.5-4B Hub file inventory: https://huggingface.co/Qwen/Qwen3.5-4B/tree/main
- Qwen3-Coder-Next Hub file inventory: https://huggingface.co/Qwen/Qwen3-Coder-Next/tree/main
- Qwen2.5-7B-Instruct Hub file inventory: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/tree/a09a35458c702b33eeacc393d103063234e8bc28
- Qwen2.5-Coder-7B-Instruct Hub file inventory: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct/tree/main
- IBM Granite 4.2 model selector (BF16 weight sizes and estimated VRAM): https://www.ibm.com/granite/playground/model-selector/models
- IBM Granite 4.2-8B model card: https://huggingface.co/ibm-granite/granite-4.2-8b
- IBM Granite 4.2-3B pinned snapshot inventory: https://huggingface.co/ibm-granite/granite-4.2-3b/tree/be9e7d995f2a6be22def5dd815f9f2bae98c8b6e
- OpenAI gpt-oss model card and checkpoint size: https://deploymentsafety.openai.com/gpt-oss/architecture
- OpenAI gpt-oss inference requirements: https://developers.openai.com/cookbook/articles/gpt-oss/run-transformers
- Mistral Devstral-Small-2 Hub inventory: https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512/tree/main
- Gemma 4 official memory requirements: https://ai.google.dev/gemma/docs/core
- Gemma 4 E2B-it: https://huggingface.co/google/gemma-4-E2B-it/tree/main
- Gemma 4 E4B-it: https://huggingface.co/google/gemma-4-E4B-it/tree/main
- Gemma 4 12B-it: https://huggingface.co/google/gemma-4-12B-it/tree/main
- Gemma 4 26B-A4B-it: https://huggingface.co/google/gemma-4-26B-A4B-it/tree/main
- Gemma 4 31B-it: https://huggingface.co/google/gemma-4-31B-it/tree/main
- MiniCPM5-2B: https://huggingface.co/openbmb/MiniCPM5-2B/tree/main
- Ministral-3B-Instruct: https://huggingface.co/ministral/Ministral-3b-instruct/tree/main

## Next mandatory execution gates

1. Snapshot every candidate at a full immutable 40-character revision; preserve model card, license, config, tokenizer, chat template, weight index and exact file inventory.
2. Sum only the chosen checkpoint's weight files, recording exact bytes, SHA-256, dtype and quantization. Record duplicate/alternative formats separately.
3. Validate architecture and tokenizer/template compatibility in the VELNOR runner. Do not bypass unsupported multimodal or custom architectures with unsafe remote code.
4. Probe each candidate on a verified free session and record GPU model, VRAM, system RAM, disk, load time, peak allocated/reserved memory, KV-cache growth at fixed context lengths, time-to-first-token and tokens/second.
5. Run the same fixed prompt and concurrency profile at explicit context lengths (at minimum 4K and 16K; larger contexts only where capacity allows). Preserve OOM and load failures as evidence.
6. Keep all candidates unqualified until legal/output-training permission, role-specific quality evaluation, independent grading, contribution-shard validation and leave-one-teacher-out ablation are complete.

**Current qualification state remains unchanged: zero qualified teachers for ASH PRIME and zero for FYR PRIMA.** This audit is storage/memory planning evidence only; it does not authorize student training or appoint any teacher.
