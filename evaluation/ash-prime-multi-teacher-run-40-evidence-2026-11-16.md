# ASH PRIME multi-teacher run 40 evidence — 2026-11-16

## Scope and outcome

Workflow run 43796213917 executed the four public ASH PRIME suites sequentially for the three existing contributors and three additional candidates. The three existing contributors all completed successfully. LFM2.5 and Phi-4 also completed real inference. SmolLM3 failed its snapshot gate because the downloaded snapshot contained no LICENSE file. The workflow-level conclusion is failure because of that SmolLM3 job; later jobs still ran because the chain allows continuation after a non-cancelled failure.

- Workflow: https://github.com/vectolith/Models-by-vectolith./actions/runs/43796213917
- PR head SHA: 2feabd8ece3dc6ce7034d2903a8e3d6b6edc441f
- Workflow result: completed / failure
- Generation settings: CPU, BF16, greedy decoding, chat template enabled, thinking disabled, 256 new-token cap
- Suite composition per successful model: benchmark v1 = 12; qualification v2 = 20; qualification v3 = 92; qualification v4 = 56; total = 180

All five successful response artifacts were downloaded and inspected. For each, the JSON results array and JSONL records are identical, all 180 case IDs are unique, and each case has candidate ID, model revision, run ID and prompt SHA-256 provenance. All five have 180 successful records, zero inference errors and no empty non-error responses. Every output remains raw evidence, not a quality score or human grade.

## Job results

| Candidate | Job ID | Result | Evidence |
|---|---:|---|---|
| Granite 3.1 3B-A800M | 133093491281 | Success | 180/180 responses |
| Granite 4.2 3B | 133109238158 | Success | 180/180 responses |
| MiniCPM5 2B | 133213797403 | Success | 180/180 responses |
| SmolLM3-3B | 133280490855 | Failure | Snapshot stopped: no LICENSE file; inference step skipped; no response artifact |
| LFM2.5-2.6B | 133281032019 | Success | Immutable snapshot plus 180/180 responses |
| Phi-4-mini-instruct | 133404486950 | Success | Immutable snapshot plus 180/180 responses |

SmolLM3 failure detail: evaluation/snapshot_additional_teacher.py raised the error "Snapshot contains no license file; refusing to treat model-card tag as complete license evidence". The model-card tag was Apache-2.0, but the downloaded snapshot did not contain a license file. The pipeline correctly did not infer that the tag was a substitute for the missing license text. No immutable revision manifest or response artifact was uploaded for this failed attempt.

## Immutable revisions, loader and resource observations

Runner probes show four visible CPUs, CPU-only PyTorch 2.8.0, no CUDA device, and approximately 15.3–15.6 GiB system RAM. CPU capabilities differed between hosted runners (AVX2 or AVX512), so these are per-run observations, not a controlled cross-model throughput ranking. GitHub account-level execution eligibility and available capacity were not verified.

| Candidate | Immutable revision | Model class / Transformers | Snapshot bytes | CPU capability | Peak RSS | Mean case latency | 256-token cap hits |
|---|---|---|---:|---|---:|---:|---:|
| Granite 3.1 | a02780686e08a03fe0d2679a293b5c74a90efa89 | GraniteMoeForCausalLM / 4.57.1 | 6,602,374,163 | AVX512 | 6.89 GiB | 15.98 s | 93/180 (51.7%) |
| Granite 4.2 | 4e9c275e232f10211ec88644d106a1f6a1b60e06 | GraniteForCausalLM / 5.0.0 | 7,329,310,731 | AVX2 | 7.44 GiB | 86.10 s | 104/180 (57.8%) |
| MiniCPM5 | 42433e90dad95123ab87729fd7011e7110629556 | LlamaForCausalLM / 4.57.1 | 5,043,807,977 | AVX2 | 5.23 GiB | 43.44 s | 52/180 (28.9%) |
| LFM2.5 | 7141b56cd4650af95c7c7b86983443aed050c96a | Lfm2ForCausalLM / 5.0.0 | 5,412,392,523 | AVX512 | 5.66 GiB | 71.64 s | 162/180 (90.0%) |
| Phi-4-mini | cfbefacb99257ffa30c83adab238a50856ac3083 | Phi3ForCausalLM / 4.57.1 | 7,694,054,130 | AVX512 | 7.72 GiB | 66.64 s | 69/180 (38.3%) |

The cap-hit flag means generation reached the configured 256-token limit without an observed EOS token. These records are retained as incomplete/truncated evidence. Cap hits are not correctness grades.

### Snapshot and license evidence

- LFM2.5: 11 files, 5,412,392,523 bytes, model type lfm2, architecture Lfm2ForCausalLM; license tag lfm1.0; LICENSE file SHA-256 4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c.
- Phi-4-mini: 21 files, 7,694,054,130 bytes, model type phi3, architecture Phi3ForCausalLM; license tag mit; LICENSE file SHA-256 fa8235e5b48faca34e3ca98cf4f694ef08bd216d28b58071a1f85b1d50cb814d.
- Granite 3.1, Granite 4.2 and MiniCPM5 use the exact immutable revisions in the table and the workflow-pinned loader stacks; their full model snapshots were downloaded and loaded by the inference runner.

For all five candidates, the JSON metadata explicitly records license_review=pending_human_legal_review, training_output_permission=not_verified, teacher_qualification=not_qualified and training_started=false. A model-weight license does not grant permission to use generated outputs for student training.

## Artifact identities and SHA-256

The ZIP hashes below were independently recomputed after downloading the artifacts and match the SHA-256 values emitted by GitHub Actions.

| Candidate | Artifact name | Artifact ID | ZIP SHA-256 |
|---|---|---:|---|
| Granite 3.1 | prime-teacher-granite-3.1-3b-a800m | 14199574383 | 3f7fc738edef49a7347c50c906a4c3fd2e8a71bde7815de47f65dc03464ebc68 |
| Granite 4.2 | prime-teacher-granite-4.2-3b | 14213985732 | f5b4a223cdd77c89c32b5c8ccf759f7a7c8d41b8e488395d2b51ebcb1f335834 |
| MiniCPM5 | prime-teacher-minicpm5-2b | 14223103259 | 3e16583a0f6746b8b4f324b7468f8364283d02dd2c5064531de2f5fd1af990ff |
| LFM2.5 | prime-teacher-lfm2.5-2.6b | 14238638626 | a52addbe9aabdde9cbee0543d203cd100e3bf25a84fe4ccda2acd2cc5b9a9d11 |
| Phi-4-mini | prime-teacher-phi-4-mini-instruct | 14260316025 | ffb3ce18c6c966b4a2914dc3b9393cedc95585f89b41f2ce7067c677131b34d8 |

| Candidate | JSON SHA-256 | JSONL SHA-256 |
|---|---|---|
| Granite 3.1 | 26fd01c55b75feb0124bc9920848d816cf03794827e456ebe30c9a4190515910 | 2d85b40e41baf8d8a3954e9e891fdb08cd3a22898b777dc5e0edf34696cdc044 |
| Granite 4.2 | 219e935601b7ac1a2321fc713a1c0e8808afbfc6395fb3e360ac94c4abbc74a8 | ae886d8aef2cb01269f2f62e936930bdf74f3006a851513f85e141947ec94563 |
| MiniCPM5 | 0e499654f8aed9de2b30fbdfb870304e2835e8c5688518de5b7f8fef41d49948 | b7c6f7a3fb190bae7bb530f41e7757b245df7936c112a0f0e8537a99d2ee0836 |
| LFM2.5 | 943105f753bb3aa16233a4bf56094af69abf898ea57e75bce5395412761acd2a | cd554a0cf6a5ed02c4460eaab21abc93e939f9830e8c898b8b96cf15906665db |
| Phi-4-mini | 03eda0c3ecb4c923f4aae35c6081634bce55997be3f3b85b85eaf028a1a39b1d | aae7cb4c6862cf0eaa795b8cd538020214be5f2f97b37416e77035b687b633c8 |

Additional manifest SHA-256 values: LFM2.5 snapshot manifest ffd64babd278da723b04eeb5d591d6fe65d7611ac518f0b0785e611e72e2eefb; Phi-4 snapshot manifest adb12189c4634dd190b134f289cd7a14dbf5b8dff8b7959687f46f8c800568d2.

## Evaluation and runtime checks

- ASH PRIME runtime and evaluation tests: run 43796213918, success. Runtime suite: 40 passed. Evaluation suite: 43 passed, 3 skipped. The skipped tests are live Hugging Face integration tests requiring VECTOLITH_RUN_LIVE_TESTS=1.
  - https://github.com/vectolith/Models-by-vectolith./actions/runs/43796213918
- Vectolith Runtime: run 43796213853, success; 40 tests passed.
  - https://github.com/vectolith/Models-by-vectolith./actions/runs/43796213853

The v4 fixture validator passed in the evaluation test suite. It validates 56 cases across 14 categories, four cases per category, non-empty rubrics, unique IDs and no collisions with the prior Prime suites. This validates fixture structure and coverage, not capability quality.

## Follow-up correction validation

Draft PR #39 received GitHub Actions run 43935195199 (workflow run number 118), completed successfully. Job 133537843283 passed all steps.

- Runtime suite: 40 tests passed.
- Evaluation suite: 45 tests passed; 3 live Hugging Face integration tests were skipped because VECTOLITH_RUN_LIVE_TESTS=1 was not enabled.
- All four snapshot tests passed, including the new tests that verify a missing LICENSE file preserves the immutable manifest but still blocks inference, and that a present LICENSE file passes the snapshot gate.
- Local snapshot test run: 4/4 passed.
- Run link: https://github.com/vectolith/Models-by-vectolith./actions/runs/43935195199

These checks validate the snapshot intake behavior and repository test suites. They do not constitute human grading, legal approval, training-output permission or teacher qualification.

## Candidate disposition and gates

- Granite 3.1, Granite 4.2 and MiniCPM5 remain the three existing additive Prime contributors. Their raw responses are preserved; no winner selection was performed.
- LFM2.5 is still discovery-only despite its successful snapshot, loader and full inference run. It has 162/180 cap hits and still requires independent human review, legal review and separate written training-output permission.
- Qwen3.5-2B and Gemma 4 E2B IT remain discovery-only; this run produced no new snapshot or inference evidence for either.
- Nemotron 3 Nano 4B remains deferred pending license and loader review.
- SmolLM3 remains blocked at the missing-license-file gate; this run did not produce a response artifact.
- Phi-4 has real inference evidence but remains unqualified and unauthorized for training pending independent review and separate output permission.

No human grading records were attached to run 40. No teacher was qualified. No student training started. FYR PRIMA remains paused. The four-qualified-teacher, legal, training-output permission, independent grading, safety, holdout and corpus-integrity gates remain mandatory.

## Repository and PR state

PR #33 is now recorded by GitHub as closed and merged at 2026-11-16 03:11:17 UTC, merge commit fdf6b6a3066558901c7e69255dcfb906266789c0. This automation did not perform the merge. The original head branch is now 63 commits ahead and 4 commits behind the current main branch, so PR #33 cannot be updated in place. Follow-up evidence and the snapshot-manifest correction are in draft PR #39; no follow-up PR is merged.
