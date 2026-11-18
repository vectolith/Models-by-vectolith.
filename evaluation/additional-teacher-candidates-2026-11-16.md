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

As of Core Prime workflow run 43796213917 on 2026-11-16, the candidates in this register remain discovery-only and no new teacher has been admitted or qualified.

- SmolLM3-3B: the snapshot attempt stopped because the downloaded repository snapshot had no LICENSE file. The model-card tag alone was not accepted as complete license evidence. No response artifact was produced.
- LFM2.5-2.6B: immutable revision 7141b56cd4650af95c7c7b86983443aed050c96a was snapshotted and loaded with Lfm2ForCausalLM / Transformers 5.0.0. It produced 180/180 Prime v1-v4 records with zero inference errors, but 162/180 reached the 256-token cap. License review, independent human grading and separate training-output permission remain outstanding. It is still discovery-only.
- Phi-4-mini-instruct: immutable revision cfbefacb99257ffa30c83adab238a50856ac3083 was snapshotted and loaded with Phi3ForCausalLM / Transformers 4.57.1 while keeping trust_remote_code disabled. It produced 180/180 Prime v1-v4 records with zero inference errors; 69/180 reached the 256-token cap. Human grading, legal review and separate training-output permission remain outstanding.
- Qwen3.5-2B and Gemma 4 E2B IT remain discovery-only; this run produced no snapshot or inference artifacts for them.
- Nemotron 3 Nano 4B remains deferred pending license and loader review.

No human grades were created. No candidate has passed teacher qualification or received training-output authorization. The three existing Granite 3.1, Granite 4.2 and MiniCPM5 contributors remain intact and additive. Full artifact identities and measured resources are recorded in evaluation/core-prime-multi-teacher-run-40-evidence-2026-11-16.md.

## Additional Core Prime teacher pipeline — implementation status

The sequential GitHub Actions workflow is now manually dispatched and requires the explicit run_qualification=true input. It retains the three existing Prime contributors first, followed by the additional discovery candidates:

1. Granite 3.1 3B-A800M
2. Granite 4.2 3B
3. MiniCPM5 2B
4. SmolLM3-3B
5. LFM2.5-2.6B
6. Phi-4-mini-instruct

Run 43796213917 completed on 2026-11-16. The first three existing contributors each produced 180 real responses across Prime v1-v4. LFM2.5 and Phi-4 also produced 180 responses each. SmolLM3 stopped at the snapshot/license-file gate and did not run inference. The overall workflow conclusion is failure because of SmolLM3, despite the successful later jobs.

The evidence record includes immutable revisions, per-case provenance checks, suite counts, token-cap counts, resource measurements, artifact IDs, archive SHA-256 values and raw JSON/JSONL hashes. See evaluation/core-prime-multi-teacher-run-40-evidence-2026-11-16.md.

The snapshot tool continues to require an exact model-card license tag and a license file before it allows inference. A follow-up correction preserves the immutable revision, full file inventory and hashes in a manifest even when the license file is missing, while still returning failure and blocking inference. It does not weaken the legal gate or treat model-card metadata as a substitute for license text.

The workflow does not commit model weights to Git. Snapshot weights remain in the ephemeral runner cache; the uploaded manifest contains the immutable revision and complete file inventory with sizes and SHA-256 hashes. Phi-4 remains loaded with trust_remote_code disabled; no repository-supplied Python code is executed.

The follow-up snapshot-manifest correction and evidence record passed GitHub Actions run 43935195199 (40 runtime tests; 45 evaluation tests; 3 live-Hugging-Face tests skipped). All candidates remain unqualified. LFM2.5 is still discovery-only despite having real inference evidence: its 90% token-cap rate requires careful review, and its LFM Open License requires legal review. The model-weight license remains separate from permission to use generated outputs for student training. No candidate is authorized for training, no human grades are inferred, and no training is performed.

PR #33 has been merged on GitHub and cannot be updated in place. Follow-up evidence and the snapshot-manifest correction are in draft PR #39; no follow-up PR is merged.


## Status correction — active contribution program (2026-11-18)

This section supersedes the earlier "discovery-only" and "deferred" dispositions above. The candidates are now active contributors to the Core Prime evaluation program, with concrete intake and inference work assigned; they are not being considered only as catalog discoveries. This status is not a claim that every candidate has already produced a real teacher response.

- **LFM2.5-2.6B and Phi-4-mini-instruct:** active additional contributors with existing real Prime v1-v4 inference artifacts. Continue repeated matched runs and preserve the high truncation/cap-hit evidence for human review.
- **Qwen3.5-2B:** active intake contributor. The previously recorded single-case semantic-grader smoke is not teacher inference. Next: immutable teacher snapshot, license-file evidence, actual loader/template smoke, resource measurement and full Prime v1-v4 inference when gates pass.
- **Gemma 4 E2B IT:** active intake contributor. Next: resolve repository access and exact terms, immutable snapshot, supported text/multimodal loader validation, resource measurement and full Prime v1-v4 inference when gates pass.
- **NVIDIA Nemotron 3 Nano 4B:** active intake contributor, no longer deferred as a research topic. Next: verify OpenMDW-1.1 terms and snapshot evidence, test the actual hybrid Mamba/Transformer architecture with a compatible pinned loader, measure resource requirements and run full Prime v1-v4 inference when gates pass.

Every candidate runs independently so one candidate's failure cannot block another. Verify execution access, workload permissions and resource limits before dispatch. Preserve measured blockers and all real outputs, including truncations and failures; never bypass platform limits. No candidate is ranked or selected, and no teacher response is discarded.

Inference participation remains separate from qualification and training authorization. Legal review, independent human grading/adjudication, safety, protected holdout, corpus integrity and the four-qualified-teacher gate remain mandatory. Written permission for generated-output training use must be separately recorded. Core Prima remains paused; no training is authorized or started.

See [the active teacher contribution program](active-teacher-contribution-program.md) for the current operating contract. Earlier paragraphs in this historical register describe the previous intake state and must not be used as the current disposition after this correction.
