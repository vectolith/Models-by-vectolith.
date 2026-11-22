# Independent ASH PRIME candidate inference

This workflow adds four independent teacher jobs for Qwen3.5-2B, Gemma 4 E2B IT, NVIDIA Nemotron 3 Nano 4B and Liquid AI LFM2.5-2.6B. It supplements the historical sequential multi-teacher workflow; each new candidate has its own job, failure boundary, snapshot manifest, loader smoke, full Prime v1-v4 response files and artifact.

## Execution controls

The workflow is manual-only and requires `run_candidates=true`. A preflight API check verifies repository visibility and runner eligibility before execution. The workflow is resource-limited; actual model fit, session availability and runtime must be measured before qualification.

## Candidate policy gate

The registry `prime_teacher_candidate_registry.json` records model repository, expected model type and architecture, loader class, license identifier, immutable revision where already verified, legal-review state, local-inference authorization, training-output permission and qualification state.

All four executable candidates start blocked:
- `license_review=pending_human_legal_review`
- `local_inference_authorized=false`
- `training_output_permission=not_verified`
- `teacher_qualification=not_qualified`

A human legal reviewer must inspect and record the exact governing model terms before changing only the local-inference fields to `approved_for_local_inference` and `true`. This does not authorize generated-output training. Do not modify the training permission or qualification fields as a side effect. The workflow skips weight download and inference while the policy gate is closed.

## Snapshot and loader verification

`snapshot_prime_teacher.py` resolves/validates a full immutable Hub commit, checks repository access, model-card license identifier, model config/model architecture and nonempty license text or an explicit model-card license URL, downloads that exact snapshot only after the local-inference gate is approved, and records a complete sorted file inventory with sizes and SHA-256 digests. It records the exact resolved revision for Gemma where the registry revision is intentionally unresolved.

`verify_prime_teacher_loader.py` loads the exact snapshot using the candidate's declared architecture-specific Transformers loader with `trust_remote_code=false`, generates one real smoke response, and records model/processor classes, versions, latency and peak RSS. A loader failure blocks the full curriculum for that candidate only.

The full inference runner supports:
- LFM2.5-2.6B: `AutoModelForCausalLM` (`lfm2` / `Lfm2ForCausalLM`; its custom LFM Open License v1.0 requires separate human legal review)
- Qwen3.5-2B: `AutoModelForMultimodalLM`
- Gemma 4 E2B IT: `AutoModelForMultimodalLM`
- Nemotron 3 Nano 4B: `AutoModelForCausalLM`

These are declared loader paths, not claims that compatibility has already been proven. The smoke step must produce a real response before full v1-v4 execution.

## Full curriculum and preservation

Each approved candidate runs the same public ASH PRIME v1, v2, v3 and v4 fixtures with deterministic decoding and a 256-token cap, matching the existing evidence protocol. The cap is explicitly recorded; capped responses are retained and not treated as complete. Every job uploads its snapshot manifest, resource probe, loader-smoke response, JSON record, JSONL per-case responses and logs even after failure.

The aggregator verifies that all five named historical teacher artifacts exist in each of preserved runs 40, 42 and 43 before downloading; missing historical evidence fails the aggregation job instead of being silently skipped. Historical downloads remain isolated by run directory, and the original JSON/JSONL files are not rewritten. The shared runner schema is compatible with the comparator, including legacy `*-ash_prime.json` filenames. The aggregator downloads artifacts without overwriting names and runs `compare_prime_teacher_responses.py`. The manual workflow has two independent inputs: `historical_only=true` with `run_candidates=false` rebuilds and uploads a historical-only report from runs 40, 42 and 43 without entering the candidate matrix; `run_candidates=true` runs only candidates whose individual legal gates approve, then produces a combined report containing the historical executions plus any available new candidate response artifacts. If both inputs are true, candidate execution is explicitly requested and all candidate policy gates still apply. The aggregator excludes loader-smoke files from the comparison set and uploads the resulting JSON report as `prime-teacher-comparison-report`. In historical-only mode it requires historical response artifacts. In candidate mode it refuses to label a report combined unless all four independently completed candidate response JSON files are present; partial candidate failures remain preserved as individual artifacts but do not produce a misleading combined report. It verifies JSON/JSONL case-count parity, unique case IDs, candidate/revision/run provenance, full immutable revision format, 64-character prompt SHA-256 values, response field types, and (when embedded) field-by-field parity between the JSON summary results and raw JSONL rows. It rejects duplicate candidate/run artifacts and computes SHA-256 digests of both source files. It reports per-teacher completion/error/empty-output/truncation counts, prompt-hash coverage, common and missing case coverage, exact response-match ratios and descriptive character-level disagreement. The report schema is `vectolith-prime-teacher-disagreement/1.1`; integrity must pass before a report is emitted. It does not grade quality, rank models, select a winner, discard outputs or authorize training.

## Historical-only integrity evidence

A historical-only verification was completed without dispatching any new model inference. The actual preserved workflow artifacts from runs 40, 42 and 43 were downloaded, ZIP-checked, extracted into isolated run/model directories and passed through the response comparator. All five historical teachers were present in each run.

The retained evidence is:
- `evaluation/evidence/historical-teacher-integrity-report-2026-11-18.md`
- `evaluation/evidence/historical-teacher-integrity-evidence-2026-11-18.json`

The report validates 15 executions and 2,700 response records (180 per execution), with 105 pairwise comparisons and 18,900 comparable case pairs. All pairwise prompt hashes matched; there were no JSON/JSONL integrity failures or execution errors. The legacy status fields are normalized for reporting without modifying source artifacts. Of the historical responses, 1,270 completed without reaching the generation cap and 1,430 were token-cap-truncated; truncated outputs remain preserved and are not counted as complete.

The JSON evidence records source workflow/artifact IDs, archive and response-file SHA-256 hashes, model revisions, completion counts and all pairwise disagreement measures. Exact-match and character-similarity measures are descriptive only, not quality scores. This historical-only report is not the final combined comparison: the three new candidate models have not been run.

## Operating boundary

- All outputs are ASH PRIME evaluation evidence only.
- Existing Granite 3.1, Granite 4.2 and MiniCPM5 contributions remain additive and untouched.
- LFM2.5 and Phi-4 remain active additional contributors with their prior real artifacts.
- New candidates contribute only after their individual local-inference gates pass.
- Inference participation is separate from teacher qualification and separate from training-output permission.
- Legal review, independent human grading/adjudication, safety, protected holdout, corpus integrity and the four-qualified-teacher requirement remain mandatory.
- FYR PRIMA remains paused. No training or distillation is implemented or invoked here.

## Dispatch

After the candidate-specific legal-review records are complete, dispatch **ASH PRIME independent additive teacher inference** with `run_candidates=true`. The workflow verifies repository and runner eligibility before proceeding. Do not dispatch while candidate rights gates are unresolved. Runner availability and hardware capacity are not guaranteed; each candidate's resource probe and loader smoke remain mandatory.


### Candidate-specific license issue

Nemotron 3 Nano 4B has an unresolved license-scope question: the selected BF16 Hugging Face model card states the NVIDIA Nemotron Open Model License and lists a 2026-03-16 release, while NVIDIA's May 28, 2026 OpenMDW announcement says adoption applies to future Nemotron-family releases. The later family-wide adoption is not assumed to retroactively change this earlier checkpoint's terms. Both official license texts and the source dates are recorded; local inference remains blocked until a human legal reviewer confirms the exact governing terms for this revision. See the [BF16 checkpoint card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16), [Linux Foundation's OpenMDW adoption announcement](https://www.linuxfoundation.org/press/linux-foundation-releases-openmdw-1.1-nvidia-adopts-openmdw-for-cosmos-isaac-gr00t-ising-and-nemotron-ai-model-families), [NVIDIA open-source catalogue](https://opensource.nvidia.com/en-eu/) and [NVIDIA Nemotron Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-nemotron-open-model-license/).


## Rebuilding reports without running models

To verify the reporting pipeline using preserved evidence only, manually dispatch **ASH PRIME independent additive teacher inference** with:
- `historical_only=true`
- `run_candidates=false`

The candidate matrix is skipped. The workflow downloads only the preserved historical artifacts and uploads `historical-prime-teacher-integrity.json` in the `prime-teacher-comparison-report` artifact. This path does not download model weights or invoke inference.

For the future combined comparison, dispatch with `run_candidates=true` only after each candidate's legal inference authorization is approved. The same aggregation job then includes the historical artifact sets and the new candidate response JSON/JSONL artifacts. It retains every candidate's outputs, rejects provenance/integrity failures, and does not rank or select teachers. Training-output permission and all training gates remain separate.


### LFM2.5 candidate-specific notes

LFM2.5-2.6B is now an independent new-run candidate in the registry and four-way matrix. Its official model card identifies `lfm2` / `Lfm2ForCausalLM` and documents `AutoModelForCausalLM`. Its license tag is `lfm1.0`, not Apache 2.0; the LFM Open License v1.0 includes a commercial-use revenue threshold. Legal review and local-inference authorization therefore remain blocked, independently of the earlier historical LFM2.5 artifacts. The historical artifacts remain unchanged and are not substituted for the new run. The model card also cautions that this checkpoint is not recommended for agentic coding and knowledge-heavy tasks; preserve that scope limitation in later interpretation. See the [model card](https://huggingface.co/LiquidAI/LFM2.5-2.6B), [license](https://www.liquid.ai/lfm-license), and [official model configuration](https://huggingface.co/LiquidAI/LFM2.5-2.6B/blob/main/config.json).


## Nemotron 3.5 candidate panel

The independently tracked Nemotron 3.5 candidates are recorded in `evaluation/nemotron_3_5_candidate_panel.json` for both ASH PRIME and FYR PRIMA panels. FYR PRIMA execution remains paused. Each variant has its own repository, license evidence, hardware/runtime requirement, legal-inference gate, training-output permission and qualification status:

- **Nemotron 3.5 Lightning 30B-A3B:** 30B total / 3B active; published BF16 deployment requires H100 80GB or newer compatible NVIDIA GPU. It is registered but blocked from the standard CPU runner.
- **Nemotron 3.5 Super VL 120B-A12B:** 120B total / 12B active; published BF16 deployment requires 4x H100 or 2x GB200. It is registered but blocked from the standard free CPU runner.
- **Nemotron 3.5 Bolt E4B:** 8B total / 4B effective; the Q4_K_M GGUF candidate is registered for a separate llama.cpp CPU feasibility adapter; the actual official GGUF file is 6.18 GB despite the repository's '4GB' name. It is not yet enabled in the Transformers matrix; runtime adapter, resource probe and real smoke response must pass first.

All three remain legally blocked, with training-output permission unverified and teacher qualification not granted. Their registration does not imply inference authorization. The exact model-specific governing terms and inherited Gemma 4 terms must be reviewed by a human. Do not silently substitute an API or a different checkpoint. The published hardware guidance is recorded in the panel; actual execution remains conditional on a verified compatible execution environment.
