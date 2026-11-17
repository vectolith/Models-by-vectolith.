# Core Prime intake and local-grader evidence — 2026-11-17

## Source workflow and pull-request state

This record preserves completed evidence from the Core Prime runtime/evaluation workflow associated with draft PR #73. No workflow was dispatched by this inspection.

- PR: https://github.com/vectolith/Models-by-vectolith./pull/73
- PR state at inspection: open, draft
- Head branch: `fix/core-prime-preflight-cli`
- Head SHA: `884873aec877ee3e48998fb54030c6ff1cced535`
- Core Prime runtime/evaluation workflow: run 44110893414, run number 363, completed successfully
- Vectolith Runtime workflow: run 44110893442, run number 247, completed successfully

PR #33 is closed and merged; PR #39 is also closed and merged. This evidence is therefore recorded in a new follow-up branch rather than attempting to modify either merged pull request.

## Core Prime tests

Run 44110893414 jobs:

| Job | Job ID | Result | Evidence |
|---|---:|---|---|
| local-grader-smoke | 134139265813 | success | One synthetic local grading case completed and output schema checks passed |
| teacher-rights-capture | 134139266408 | success | Five pinned rights captures, zero capture failures |
| python-tests | 134139266532 | success | 109 tests total; 3 live Hugging Face integration tests skipped |

The Python test log explicitly reports both Core Prime v4 validator tests passing:

- Four cases per each of the 14 v4 categories, three rubric criteria per case, unique IDs and valid message structure.
- No v4 case-ID collisions with benchmark v1 or qualification v2/v3.

The test job completed with 109 tests and 3 skips (106 passed, 3 skipped). The three skipped tests require VECTOLITH_RUN_LIVE_TESTS=1; they are not reported as passing live Hub integration checks.

Run 44110893442 completed with its runtime-tests job 134135852158 successful: 81 tests passed.

Links:
- https://github.com/vectolith/Models-by-vectolith./actions/runs/44110893414
- https://github.com/vectolith/Models-by-vectolith./actions/runs/44110893442

## Qwen3.5-2B local grader smoke — not teacher inference

Job 134139265813 completed a single synthetic grading request using a local CPU checkpoint:

- Model: Qwen/Qwen3.5-2B
- Immutable revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- Prompt version: `core-prime-semantic-grader-v2-local`
- Device/dtype: CPU / BF16
- Runtime: PyTorch 2.8.0+cpu; Transformers 5.23.0
- Response count: 1
- Decision-file SHA-256: `4c3a77db321104abe62f01ce65129d2797d104e84f06321571e2933ef5000e43`
- Remote inference API: false
- Grader-reported billing requirement: false

The smoke validates that this pinned checkpoint can execute one local semantic-grading request and emit a schema-valid decision record. It does **not** establish Qwen3.5-2B as a Prime teacher: no Prime teacher response suite was run, no teacher artifact was produced, no resource/latency/RSS profile was recorded, and no human grade or qualification decision was made.

The log reports fallback to reference PyTorch implementations because `causal_conv1d` and `flash-linear-attention` were not installed. The smoke completed successfully, but those missing optimized kernels may reduce performance. The log does not establish GitHub Actions account billing or free-capacity eligibility.

## Teacher rights-capture artifact

Job 134139266408 completed with five captures and zero failures. The job downloaded model-card and legal files only:

- Weights downloaded: false
- Inference performed: false
- Legal review: pending authorized review
- Training-output permission: not verified

Artifact:
- Name: `core-prime-teacher-rights-capture`
- Artifact ID: 14341626257
- Size: 67,495 bytes
- ZIP SHA-256: `49a45745d272a5f451f0ad5042ffd2ded0f2a8a0f187c2db6c3a1e09c3688a62`
- Capture summary SHA-256: `9278afe92d58a2faf89a4e2e45fa668c30f56773488bfe7fde2a11c0a0425cb1`
- Download: https://github.com/vectolith/Models-by-vectolith./actions/runs/44110893414/artifacts/14341626257

### Captured candidate revisions and legal-file evidence

| Candidate | Immutable revision | Rights capture result | License evidence |
|---|---|---|---|
| Granite 3.1 3B-A800M | `a02780686e08a03fe0d2679a293b5c74a90efa89` | Captured SPDX reference | Model-card tag Apache-2.0; no repository LICENSE/COPYING file; canonical SPDX Apache-2.0 text captured separately |
| Granite 4.2 3B | `4e9c275e232f10211ec88644d106a1f6a1b60e06` | Captured SPDX reference | Model-card tag Apache-2.0; no repository LICENSE/COPYING file; canonical SPDX Apache-2.0 text captured separately |
| MiniCPM5 2B | `42433e90dad95123ab87729fd7011e7110629556` | Captured SPDX reference | Model-card tag Apache-2.0; no repository LICENSE/COPYING file; canonical SPDX Apache-2.0 text captured separately |
| LFM2.5-2.6B | `7141b56cd4650af95c7c7b86983443aed050c96a` | Captured | Repository LICENSE present; model-card license identifier `lfm1.0` |
| Phi-4-mini-instruct | `cfbefacb99257ffa30c83adab238a50856ac3083` | Captured | Repository LICENSE and NOTICE present; model-card license tag MIT |

For Granite 3.1, Granite 4.2 and MiniCPM5, the canonical SPDX text is not represented as a license file supplied by the model repository. The captured SPDX source revision is `31ba1a50e5397e00a304dbadc76531740e89ee48`; the Apache-2.0 text SHA-256 is `074e6e32c86a4c0ef8b3ed25b721ca23aca83df277cd88106ef7177c354615ff`.

Selected per-file digests:

| Candidate/file | SHA-256 |
|---|---|
| Granite 3.1 README.md | `5a875520c70d9faae1255eb9aad66fdacf023db595d5e57a9c70026d0ffc0f77` |
| Granite 4.2 README.md | `8f22ddce440f0c15ecb58fc9f8501b882baf5f2b7ab0d13872fe77d88c1ad792` |
| MiniCPM5 README.md | `59e93770502358d56b30b8e2ef7e744cf7fc91bfb923c7c787876defac35cdbe` |
| LFM2.5 README.md | `206383f9e7d86fb44fb260474c5a0793830c5691b5ca6f7d5f955058de320886` |
| LFM2.5 LICENSE | `4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c` |
| Phi-4 README.md | `c4f34916182a3ee87d95d00c92847cfa687ab21dc338a577275f0c34cf0e1dfd` |
| Phi-4 LICENSE | `fa8235e5b48faca34e3ca98cf4f694ef08bd216d28b58071a1f85b1d50cb814d` |
| Phi-4 NOTICE.md | `a3386cc7125ec75ed34d4f0a340c47782982095e251d322e01d8ecab22d87ba4` |

Individual rights-capture manifest SHA-256 values:

| Candidate | Manifest SHA-256 |
|---|---|
| Granite 3.1 | `5b24d157e2b6560a8ad14d33153a60b65dfbcc30330d59da7690ad03d9dca9b3` |
| Granite 4.2 | `c625c6513bd9782b41ce3fa8fddf15e106c211dc9cc3946b694ab2cbeb163362` |
| MiniCPM5 | `db0b4a5158bf33eaf829a47a5770bbe416e864e41cd180aa846078017d7593e5` |
| LFM2.5 | `05154d75e146ef47b15c3a921bfadf630a18329392fe4a2ac6addd60ba55edeb` |
| Phi-4 | `663d25b4505ac0b2b5843021556692496ce961546e4bf0728b271f504f47b149` |

The rights capture is an evidence-preservation step, not legal approval. Each manifest continues to record `legal_review=pending_authorized_review`, `training_output_permission=not_verified`, and `teacher_qualification=not_qualified`. Inference and weights were not part of this job.

## Candidate disposition and safety boundaries

- Granite 3.1, Granite 4.2 and MiniCPM5 remain the three existing additive Core Prime contributors. The capture does not replace, rank or discard any teacher or response.
- LFM2.5 and Phi-4 remain discovery-only and unqualified despite existing inference evidence.
- Qwen3.5-2B was exercised only in the local grader role in this run; this is not a teacher inference result or teacher qualification gate.
- Gemma 4 E2B IT was not captured or inferred in this run and remains discovery-only.
- Nemotron 3 Nano 4B remains deferred; no rights capture or inference was performed for it.
- No independent human grades or adjudications were created by these jobs.
- Core Prima remains paused. No student training was started.

The four-qualified-teacher requirement, legal review, separate written training-output permission, independent human grading/adjudication, safety, protected holdout and corpus-integrity gates remain mandatory.