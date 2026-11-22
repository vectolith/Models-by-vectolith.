# ASH PRIME active teacher contribution program

**Status: active implementation track.** Models listed here are contributors to the evaluation program, not a replacement shortlist and not a ranking. A candidate may contribute raw inference and evaluation evidence before it is qualified for any training use.

## Contributor roster

| Contributor | Current evidence / next contribution |
|---|---|
| IBM Granite 3.1 3B-A800M | Existing additive contributor; preserve all prior artifacts and continue matched-suite runs. |
| IBM Granite 4.2 3B | Existing additive contributor; preserve all prior artifacts and continue matched-suite runs. |
| OpenBMB MiniCPM5 2B | Existing additive contributor; preserve all prior artifacts and continue matched-suite runs. |
| LiquidAI LFM2.5-2.6B | Active additional contributor. Two full Prime v1-v4 runs exist; repeat with completion-aware budgets and retain every capped response. |
| Microsoft Phi-4-mini-instruct | Active additional contributor. Full Prime v1-v4 inference exists; continue matched runs and independent review. |
| Qwen3.5-2B | Active intake contributor. Resolve and pin revision, capture license and snapshot hashes, validate loader/template, then run smoke and full Prime v1-v4 inference. |
| Google Gemma 4 E2B IT | Active intake contributor. Resolve access and exact license terms, pin revision, validate multimodal/text loader and template, then run smoke and full Prime v1-v4 inference. |
| NVIDIA Nemotron 3 Nano 4B | Active intake contributor. Resolve OpenMDW-1.1 terms, immutable snapshot, hybrid Mamba/Transformer loader compatibility and resource envelope, then run smoke and full Prime v1-v4 inference. |

"Active intake contributor" means the candidate has an owned execution path and is not parked as catalog-only discovery. It does not claim that inference has already run. Until a real artifact exists, report inference as pending and do not infer responses from queued work.

## Execution contract

1. Run candidates independently. One candidate's license, access, loader, OOM or inference failure must not prevent other candidates from completing.
2. Resolve a full immutable 40-character model revision before downloading weights. Preserve model card, config, tokenizer, license/NOTICE text, complete file inventory, byte sizes and SHA-256 digests.
3. Do not infer license permission from a Hub tag. Missing or ambiguous terms block weight execution until human legal review resolves the applicable terms. Model-weight licensing and permission to use generated outputs for training are separate decisions.
4. Validate the candidate's actual architecture and tokenizer/chat template. Never force multimodal or hybrid checkpoints through a text-only loader. Do not enable `trust_remote_code` without a separately pinned and reviewed source.
5. Run a deterministic smoke suite first. If loading and generation succeed, run the same public ASH PRIME benchmark v1 and qualification v2/v3/v4 suites with identical prompt revisions and decoding settings. Keep model-specific dependency pins where required.
6. Capture raw JSON and JSONL responses, logs, job/run IDs, exact revisions, suite and case IDs, prompt hashes, completion/truncation/error counts, latency, throughput, download/load time, CPU/GPU details, peak RSS/VRAM, dtype, quantization and runtime versions.
7. Preserve every real response, including partial, capped, refused, empty and failed cases. Never overwrite or silently drop an earlier run. Keep candidate/run/revision identities unique.
8. Analyse response coverage, completion and cross-teacher disagreement. Do not produce a winner ranking or discard any teacher response. Independent human graders remain responsible for quality judgements.
9. Participation in inference/evaluation does not imply teacher qualification. Qualification still requires legal review, independent human grading/adjudication, safety, protected holdout and corpus-integrity gates, and the four-qualified-teacher requirement.
10. Training-output permission is a separate explicit gate. No response may enter a training corpus or optimization run until written permission is recorded for that candidate and intended use.

## Execution availability and resource controls

Before dispatch, verify that the selected execution environment is accessible, the intended workload is permitted, and its actual CPU/GPU, memory, storage, session and concurrency limits can accommodate the candidate. Record measured capacity and runtime observations. Do not infer availability from public claims or model-download access. If a candidate cannot run within the verified environment, preserve the measured blocker and keep its intake work active; never bypass platform limits or silently substitute an unverified execution path.

## ASH PRIME scope and safeguards

- All contributors target ASH PRIME only. FYR PRIMA remains paused.
- This program is evaluation/inference only. It does not start training, authorize distillation, or add outputs to a corpus.
- Existing Granite 3.1, Granite 4.2 and MiniCPM5 contributions remain additive and immutable.
- New candidates join alongside them; none is a replacement.
- Public v1-v4 suites are not secret holdouts. Protected holdout access remains separately controlled.
- No human grade, legal approval, qualification or training permission may be fabricated or inferred from successful inference.

## Current evidence boundary

LFM2.5 and Phi-4 have real inference artifacts already recorded in the run 40–43 evidence. Qwen3.5-2B has only a prior one-case semantic-grader smoke, not teacher inference. No verified full Prime response artifact is currently recorded here for Qwen3.5-2B, Gemma 4 E2B IT or Nemotron 3 Nano 4B. Their next contribution is immutable intake and compatibility evidence followed by real inference when the rights, loader and execution-environment gates pass.
