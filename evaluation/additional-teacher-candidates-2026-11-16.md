# Additional efficient teacher candidates — discovery register (2026-11-16)

This register expands discovery only. No new model is admitted as a teacher until its exact revision, license terms, loader, resource profile, real Prime responses, independent grading and training-output permissions are verified. Existing three contributors remain intact; these are additive candidates, not replacements.

| Candidate | Why test it | Main risks / gates | Initial disposition |
|---|---|---|---|
| HuggingFaceTB/SmolLM3-3B | Strong first-priority compact text-only candidate: 3B decoder-only GQA model, hybrid reasoning, tool calling, Transformers AutoModelForCausalLM path, Apache-2.0 model-card tag. | Pin immutable revision; verify exact license file and full model snapshot; ensure chat-template thinking controls are handled consistently; measure CPU memory/throughput. | **Priority 1: compatibility + smoke test** |
| LiquidAI/LFM2.5-2.6B | Strong first-priority efficiency/agentic candidate: text-only 2.69B hybrid model, tool-use post-training, 128K context; official card provides Transformers and CPU inference claims. | Nonstandard hybrid architecture; verify exact revision, actual Transformers version/model class and license terms (LFM Open License); reproduce CPU metrics. | **Priority 1: compatibility + smoke test** |
| microsoft/Phi-4-mini-instruct | 3.8B dense decoder-only model with 128K context; vendor positions it for constrained-memory/latency scenarios and reasoning, math, coding and function calling. | Verify Hugging Face model card and license files; larger size than 3B candidates; run same memory/latency tests and inspect factual reliability. | Priority 2: license + compatibility review |
| Qwen/Qwen3.5-2B | Compact 2B multimodal-family model; official card reports Apache-2.0, long context and broad language coverage. A useful independent architecture and efficiency test. | Multimodal/hybrid architecture; current text-only runner must not be assumed compatible. Pin revision, inspect exact license, verify tokenizer/template and Transformers loader. | Snapshot + compatibility smoke test only |
| google/gemma-4-E2B-it | Efficient edge-oriented model family with instruction tuning, reasoning, native tool/function calling and multimodal support. | Confirm repository access/gating, model-specific terms and full license; multimodal loader required; embeddings make total memory larger than effective parameter count. | Snapshot + compatibility smoke test only |
| LiquidAI/LFM2.5-2.6B | Hybrid on-device model; publisher reports agentic post-training, tool-use and CPU/edge efficiency. Official card lists LFM Open License rather than Apache-2.0. | Custom hybrid architecture may need a different runtime; benchmark claims are publisher-reported; legal review of LFM Open License required; training-output permission remains unverified. | Snapshot + compatibility smoke test only |
| nvidia/NVIDIA-Nemotron-3-Nano-4B | Hybrid Mamba/Transformer model with tool-use and edge-inference focus; useful efficiency candidate. | Architecture/runtime compatibility and OpenMDW-1.1 license review required; publisher's GPU measurements are not CPU guarantees. | Defer until license and loader review |

## Evidence links

- SmolLM3-3B official model card: https://huggingface.co/HuggingFaceTB/SmolLM3-3B
- SmolLM3 Transformers documentation: https://huggingface.co/docs/transformers/model_doc/smollm3
- Phi-4-mini-instruct Microsoft model catalog: https://ai.azure.com/catalog/models/Phi-4-mini-instruct

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

All candidates above are discovery-only and untested by Vectolith for this curriculum. SmolLM3-3B and LFM2.5-2.6B are first-priority compatibility candidates because their published model cards expose direct text-generation/Transformers paths and compact parameter counts. Phi-4-mini-instruct is second priority pending license and snapshot review. Qwen3.5-2B and Gemma 4 E2B IT remain lower-priority because multimodal architecture and/or model-specific license/access review add loader and governance complexity. Nemotron remains deferred. No new teacher has been admitted, run, qualified or authorized for training.


## Additional Core Prime teacher pipeline — implementation status

The three selected discovery candidates now have a sequential GitHub Actions pipeline at `.github/workflows/core-prime-additional-teachers.yml`:

1. SmolLM3-3B
2. LFM2.5-2.6B
3. Phi-4-mini-instruct

Each job resolves the current Hub main revision once, records the resulting full 40-character commit SHA, downloads the snapshot at that immutable SHA, validates the expected model type and architecture, inventories every file and computes SHA-256 hashes, and records license-file evidence in a JSON manifest. The exact immutable revision is then passed to the real Prime v1–v4 inference runner. Each teacher job depends on the preceding job, so the three additions run in order. All snapshots, raw JSON/JSONL outputs, logs and runner resource observations are uploaded as separate 90-day artifacts.

The workflow does not commit model weights to Git. The snapshot is held in the runner cache during the job; the artifact preserves a complete file inventory, sizes, hashes, immutable revision, config and license-file hashes. The weights can be re-fetched byte-for-byte by revision and verified against the manifest.

Compatibility is established by the pinned Transformers installation, snapshot config/architecture checks, tokenizer/model loading and actual generation in the inference runner. Phi-4 is deliberately loaded with the runner's default `trust_remote_code=False`; no repository-supplied Python modeling code is executed. If the built-in Transformers implementation cannot load it, that job records the failure rather than silently enabling remote code.

Important limitations:
- Hub `main` is resolved at the start of each run, then pinned to an immutable SHA for that run. The exact SHA is not guessed or hard-coded before the Hub returns it; the artifact is the source of truth.
- LFM2.5 publisher guidance does not recommend it for agentic coding or knowledge-heavy tasks. Its contribution is especially relevant to tool use, structured extraction and agentic interaction; its responses must still be retained and independently assessed across all Prime cases.
- LFM2.5 uses the LFM Open License (`lfm1.0`), so legal review and training-output permission remain separate unresolved gates.
- Phi-4's public model card documents `trust_remote_code=True` in its example. This pipeline intentionally does not enable that setting without a separate source-code security review.
- No new teacher is qualified, and no training starts from these artifacts.

The workflow and snapshot guardrail unit tests have been added to PR #33. Their GitHub Actions results, plus all three real teacher artifacts, must be inspected before declaring the new pipeline operational.
