# Core Prime teacher response evidence — workflow run 43796213917

Captured from GitHub Actions workflow run [#40](https://github.com/vectolith/Models-by-vectolith./actions/runs/43796213917), on branch `evaluation/expanded-balanced-qualification-v3-mainline`, head `2feabd8ece3dc6ce7034d2903a8e3d6b6edc441f`, on 2026-11-16. The workflow's overall conclusion is **failure** because the separate SmolLM3 snapshot job failed; the five jobs listed below completed successfully and produced real response artifacts.

## Evaluation coverage and integrity

Each successful run used the same 180-case Core Prime public suite set:

- `prime_benchmark_v1.jsonl`: 12 cases
- `prime_qualification_v2.jsonl`: 20 cases
- `prime_qualification_v3.jsonl`: 92 cases
- `prime_qualification_v4.jsonl`: 56 cases

For all five successful artifacts, the embedded JSON `results` array exactly matched the corresponding JSONL rows. All five JSONL files contain 180 non-empty response records. Each record is revision-pinned and prompt-hashed. The evaluation record schema is `vectolith-real-candidate-evaluation/1.1`; it does not include a `completion_status` field. Therefore, the outcome counts below use the actual `generation_status` and `generation_cap_reached` fields rather than inventing completion labels.

## Real response jobs

| Candidate | Immutable model revision | GitHub job | Model run UUID | Records | Token cap reached / EOS-or-early-stop | Errors / empty |
|---|---|---:|---|---:|---:|---:|
| Granite 3.1 3B-A800M | `a02780686e08a03fe0d2679a293b5c74a90efa89` | `133093491281` | `85b6298d17894cb598174a2dfd6133c2` | 180 | 93 / 87 | 0 / 0 |
| Granite 4.2 3B | `4e9c275e232f10211ec88644d106a1f6a1b60e06` | `133109238158` | `53544c4e38864faaa58b87ae7893f093` | 180 | 104 / 76 | 0 / 0 |
| MiniCPM5 2B | `42433e90dad95123ab87729fd7011e7110629556` | `133213797403` | `fe3eae7457cb4fa7b949d99852399724` | 180 | 52 / 128 | 0 / 0 |
| LFM2.5 2.6B | `7141b56cd4650af95c7c7b86983443aed050c96a` | `133281032019` | `5bba8ce341fb40bca1b68f06d9478b93` | 180 | 162 / 18 | 0 / 0 |
| Phi-4 Mini Instruct | `cfbefacb99257ffa30c83adab238a50856ac3083` | `133404486950` | `1f12c9ac5bb141a8a95a0c73b38392bd` | 180 | 69 / 111 | 0 / 0 |

All five jobs completed with 180 recorded results, zero error records, and zero empty responses. The cap-reached rows are explicitly incomplete/truncated and must remain so for grading and downstream use. The non-cap count is the recorded `eos_or_early_stop` count, not a human quality grade.

## Hardware and resource observations

All five jobs ran on CPU, BF16, with four visible CPUs and no CUDA devices. The runner environments were not identical; CPU capability and memory figures are recorded per artifact.

| Candidate | CPU capability | System RAM total / available (bytes) | Peak RSS (KiB) | Snapshot size (bytes) | Download / load / generation (seconds) |
|---|---|---:|---:|---:|---:|
| Granite 3.1 3B-A800M | AVX512 | 16,759,439,360 / 15,693,225,984 | 7,219,872 | 6,602,374,163 | 41.786 / 0.130 / 2,875.666 |
| Granite 4.2 3B | AVX2 | 16,759,435,264 / 15,748,771,840 | 7,805,724 | 7,329,310,731 | 23.094 / 0.775 / 15,497.379 |
| MiniCPM5 2B | AVX2 | 16,759,439,360 / 15,676,284,928 | 5,480,284 | 5,043,807,977 | 15.619 / 0.504 / 7,818.398 |
| LFM2.5 2.6B | AVX512 | 16,759,443,456 / 15,582,961,664 | 5,939,644 | 5,412,392,523 | 0.057 / 1.627 / 12,895.690 |
| Phi-4 Mini Instruct | AVX512 | 16,463,409,152 / 15,168,724,992 | 8,091,196 | 7,694,054,130 | 0.138 / 0.429 / 11,994.485 |

PyTorch was `2.8.0+cpu` in every job. Transformers was `4.57.1` for Granite 3.1, MiniCPM5 and Phi-4, and `5.0.0` for Granite 4.2 and LFM2.5. No GPU acceleration was observed. Generic GitHub runner logs do not establish account billing eligibility or remaining provider quota.

## Artifact names and SHA-256 digests

The archive digest from GitHub's artifact API was independently reproduced by hashing each downloaded ZIP. JSON and JSONL digests below are SHA-256 of the exact files inside those ZIPs.

| Artifact | Artifact ID | ZIP SHA-256 | JSON SHA-256 | JSONL SHA-256 | Exact archive URL |
|---|---:|---|---|---|---|
| `prime-teacher-granite-3.1-3b-a800m` | `14199574383` | `3f7fc738edef49a7347c50c906a4c3fd2e8a71bde7815de47f65dc03464ebc68` | `26fd01c55b75feb0124bc9920848d816cf03794827e456ebe30c9a4190515910` | `2d85b40e41baf8d8a3954e9e891fdb08cd3a22898b777dc5e0edf34696cdc044` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14199574383/zip) |
| `prime-teacher-granite-4.2-3b` | `14213985732` | `f5b4a223cdd77c89c32b5c8ccf759f7a7c8d41b8e488395d2b51ebcb1f335834` | `219e935601b7ac1a2321fc713a1c0e8808afbfc6395fb3e360ac94c4abbc74a8` | `ae886d8aef2cb01269f2f62e936930bdf74f3006a851513f85e141947ec94563` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14213985732/zip) |
| `prime-teacher-minicpm5-2b` | `14223103259` | `3e16583a0f6746b8b4f324b7468f8364283d02dd2c5064531de2f5fd1af990ff` | `0e499654f8aed9de2b30fbdfb870304e2835e8c5688518de5b7f8fef41d49948` | `b7c6f7a3fb190bae7bb530f41e7757b245df7936c112a0f0e8537a99d2ee0836` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14223103259/zip) |
| `prime-teacher-lfm2.5-2.6b` | `14238638626` | `a52addbe9aabdde9cbee0543d203cd100e3bf25a84fe4ccda2acd2cc5b9a9d11` | `943105f753bb3aa16233a4bf56094af69abf898ea57e75bce5395412761acd2a` | `cd554a0cf6a5ed02c4460eaab21abc93e939f9830e8c898b8b96cf15906665db` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14238638626/zip) |
| `prime-teacher-phi-4-mini-instruct` | `14260316025` | `ffb3ce18c6c966b4a2914dc3b9393cedc95585f89b41f2ce7067c677131b34d8` | `03eda0c3ecb4c923f4aae35c6081634bce55997be3f3b85b85eaf028a1a39b1d` | `aae7cb4c6862cf0eaa795b8cd538020214be5f2f97b37416e77035b687b633c8` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14260316025/zip) |

## Failed candidate job in the same workflow

- SmolLM3-3B job `133280490855` failed in **Resolve immutable revision and hash the full snapshot**.
- The exact logged exception was: `RuntimeError: Snapshot contains no license file; refusing to treat model-card tag as complete license evidence`.
- The subsequent real-response step was skipped. No SmolLM3 response artifact was uploaded. No output is inferred for that job.
- The other five teacher/candidate jobs above completed successfully despite the workflow's overall failure.

## Subsequent preserved multi-teacher runs 42 and 43

The later [run #42](https://github.com/vectolith/Models-by-vectolith./actions/runs/43820188813) (branch `add-qwen25-7b-to-expanded-intake`) and [latest run #43](https://github.com/vectolith/Models-by-vectolith./actions/runs/43821046671) (branch `audit-candidate-weight-memory-2026-11-16`) repeated the same immutable v1-v4 curriculum. Both workflow runs concluded **failure** because their separate SmolLM3 snapshot job hit the same missing-license-file gate. In both runs, all three existing Core Prime teacher jobs, LFM2.5, and Phi-4 completed successfully and uploaded real response artifacts.

### Run/job and response counts

| Candidate | Revision | Run 42 job | Run 42 model run UUID | Run 42 cap / non-cap | Run 43 job | Run 43 model run UUID | Run 43 cap / non-cap |
|---|---|---:|---|---:|---:|---|---:|
| Granite 3.1 3B-A800M | `a02780686e08a03fe0d2679a293b5c74a90efa89` | `133141260775` | `d54d33a5211e4857ac291e5df11e60a1` | 90 / 90 | `133143953242` | `4a6ba3e24eab46db9d4294f519cf0a4c` | 93 / 87 |
| Granite 4.2 3B | `4e9c275e232f10211ec88644d106a1f6a1b60e06` | `133174330091` | `417bbff034e24f93b7e948393974c507` | 103 / 77 | `133178581513` | `f757219863a04978bdca51ff9bc03d52` | 103 / 77 |
| MiniCPM5 2B | `42433e90dad95123ab87729fd7011e7110629556` | `133275261975` | `d3c4dfc9886f46b88a825b8d27fbc74e` | 52 / 128 | `133277594971` | `f8708c508c4a4ccc837cb2c729fae993` | 52 / 128 |
| LFM2.5 2.6B | `7141b56cd4650af95c7c7b86983443aed050c96a` | `133332287803` | `71d6b0497fa7480fbfe27c121a03fe4c` | 163 / 17 | `133347523890` | `956f5fb8f86048579a7cf7b2445da88d` | 162 / 18 |
| Phi-4 Mini Instruct | `cfbefacb99257ffa30c83adab238a50856ac3083` | `133549417510` | `e766bdfc2fce4aad809aa5bbf5d74a22` | 63 / 117 | `133444059471` | `80eb15dbf9f7483a9c4ce82e65c82a10` | 69 / 111 |

Each row represents 180 records: v1 12, v2 20, v3 92, v4 56. All ten artifacts contain 180 non-empty rows, zero error records, and JSONL rows that exactly match the embedded JSON `results` array. The cap / non-cap counts are actual `generation_cap_reached` and `generation_status` counts; cap-reached responses remain incomplete.

### Run 42 and 43 artifact digests

All ZIP hashes below were recomputed from the downloaded artifacts and match GitHub's artifact API digest. JSON and JSONL hashes are for the exact files inside each ZIP.

| Run | Artifact | Artifact ID | ZIP SHA-256 | JSON SHA-256 | JSONL SHA-256 | Exact archive URL |
|---|---|---:|---|---|---|---|
| 42 | `prime-teacher-granite-3.1-3b-a800m` | `14207923899` | `8d799a9c015ab6728079fe1f54bf8a6557d0c011d84fd4b826dbbd23e69a81fd` | `65b5e355da0f52f274a2104a28345420ac68e538de484ff8c2241329e9e0b137` | `d021c07ce5f5762056f1595f5da6e6ebf34b2db60a3addb594bc49937d7b55f5` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14207923899/zip) |
| 42 | `prime-teacher-granite-4.2-3b` | `14222803141` | `088e3dbee15c26627cc97d6cb09d46bca0a37340cc5a5ae08af86e4ccebcb45e` | `4930db1ce9da0ae25697572e5895b1809bb5a18f60afb67eccc6464e54f9e929` | `38e6a97ce518196d9c509c6b8ec2ee28889d08833d342b0f9338f487770c7a39` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14222803141/zip) |
| 42 | `prime-teacher-minicpm5-2b` | `14230880744` | `8375eb2eb02192c07c5fdebdf661bda4c9eeb54d852f40679a3863f1210e94d4` | `4314d4b5a64d61ad6270ed6eeed003d1ef917030c36ef9c6e3745ee83b09fbc6` | `d8be112a1336d4681a60d3758390d60fa88c582a8f9b400b2907b44786704748` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14230880744/zip) |
| 42 | `prime-teacher-lfm2.5-2.6b` | `14262556692` | `f6502425a369cd3b86347c311445c729793f45f438e4f4aa4a6f155406216e64` | `eb784cf48513ef9d52df7c5d73025062a8bf3be1311edd3484d7a2a157e96833` | `b6cf6e140f354e36d56b1588ea1c653f71ef590e6881c7b1a1ac13793df66808` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14262556692/zip) |
| 42 | `prime-teacher-phi-4-mini-instruct` | `14280614317` | `9b34e52ef661236741bae16b7de0ce9b04b065fdb223e2aec3bfb4d812cbac4c` | `c44f3b9a172f8bd7b79a5713696e847a957208d3a6aaaae8a5a33d915f8c3a8c` | `fedd465d04b4521f8bbdb191d53aeaf7afe3119fb98dd0d5fff28b37d63cb38b` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14280614317/zip) |
| 43 | `prime-teacher-granite-3.1-3b-a800m` | `14208733041` | `3e3e6d563c1deeb696f7004195de09172e4e2f2f49a2229a9c4d8d82d5218c05` | `fb87fdbf14e2967c44eaeb02e70fdd985dad6eeb9dba3f396d8911b9654a8122` | `db11e1c6b980a33cb7427771571b79d9713f28f95b6a910afdc44c9bb68ea5de` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14208733041/zip) |
| 43 | `prime-teacher-granite-4.2-3b` | `14223262221` | `a3781ef0dd5240eca4f223a44f69c39f641bb20d9adf6d2bb7f4efb3b44c2739` | `90026164949b4eb58cd2c082e20a205806eab3a1cc087fd994de55448120d5cd` | `06652a1b6afc7955bc5b14ded5283c5b9f20a93e602c16cca23ac49ccfece6fe` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14223262221/zip) |
| 43 | `prime-teacher-minicpm5-2b` | `14231498894` | `109c2f235ab8edde59b2beeeedf778f6ae3babf309e70952c62febf09cf93acb` | `d14d818dcbb1938e0caa3d8507fee64e3b70d587921027e97102c149543470a9` | `a2053c0ecdbcfbb339c1c8aefbc4e7323421b2eeb34756750eee124978fbc0f6` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14231498894/zip) |
| 43 | `prime-teacher-lfm2.5-2.6b` | `14245324681` | `7130d8c7f4754e689f4652951a12f09e70df43f7c7e67ecc27dfb1a1fea192ca` | `3b9b6dd658baee431f72beb9090992449684d83e39b58a3187d046b043628355` | `ea8e5aa4292b0c953f03f087303723993027e5b449921b4c64a174a8d2fde0bf` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14245324681/zip) |
| 43 | `prime-teacher-phi-4-mini-instruct` | `14261964529` | `584ac7979398db27234870b72e3c94c65ff79749828e78ba388db198c68df50f` | `0910b02c67b0bb11993a34f50ba075e6c1b44d0ce157211458d060cb366b80ff` | `b229dfae12981680547b5f3f28cb2f37a05299d81014a7553a3fcd6574dbdb69` | [ZIP](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14261964529/zip) |

Non-fatal generation warnings in runs 42 and 43: Transformers reported that `top_p` was ignored for Granite 4.2 and MiniCPM5, and `temperature` was ignored for LFM2.5. The runner used `do_sample=false` greedy decoding; these warnings did not fail the jobs, but they are retained as configuration/loader evidence.

### Run 42 and 43 resource observations

All jobs used four visible CPUs, CPU-only BF16, PyTorch `2.8.0+cpu`, and no CUDA devices. System RAM and peak RSS are exact values recorded in the corresponding runner and evaluation manifests.

| Run | Candidate | CPU capability | RAM total / available (bytes) | Peak RSS (KiB) | Snapshot bytes | Download / load / generation (seconds) | Transformers |
|---|---|---|---:|---:|---:|---:|---|
| 42 | Granite 3.1 | AVX512 | 16,758,394,880 / 15,674,757,120 | 7,208,568 | 6,602,374,163 | 41.300 / 0.215 / 5,003.469 | 4.57.1 |
| 42 | Granite 4.2 | AVX512 | 16,463,409,152 / 15,425,851,392 | 7,824,760 | 7,329,310,731 | 38.762 / 0.574 / 12,120.771 | 5.0.0 |
| 42 | MiniCPM5 | AVX512 | 16,759,439,360 / 15,674,445,824 | 5,515,692 | 5,043,807,977 | 32.258 / 0.383 / 6,412.381 | 4.57.1 |
| 42 | LFM2.5 | AVX512 | 16,758,394,880 / 15,685,791,744 | 5,944,736 | 5,412,392,523 | 0.116 / 2.016 / 20,787.314 | 5.0.0 |
| 42 | Phi-4 Mini | AVX2 | 16,759,439,360 / 15,111,196,672 | 8,030,660 | 7,694,054,130 | 0.091 / 0.558 / 13,610.500 | 4.57.1 |
| 43 | Granite 3.1 | AVX2 | 16,759,439,360 / 15,719,399,424 | 7,101,844 | 6,602,374,163 | 21.724 / 0.230 / 5,171.374 | 4.57.1 |
| 43 | Granite 4.2 | AVX512 | 16,463,409,152 / 15,377,174,528 | 7,799,152 | 7,329,310,731 | 38.004 / 0.563 / 11,824.206 | 5.0.0 |
| 43 | MiniCPM5 | AVX2 | 16,759,439,360 / 15,740,731,392 | 5,480,056 | 5,043,807,977 | 15.208 / 0.524 / 7,737.533 | 4.57.1 |
| 43 | LFM2.5 | AVX512 | 16,759,439,360 / 15,550,697,472 | 5,939,748 | 5,412,392,523 | 0.110 / 1.269 / 9,045.859 | 5.0.0 |
| 43 | Phi-4 Mini | AVX512 | 16,758,403,072 / 15,678,050,304 | 8,089,804 | 7,694,054,130 | 0.106 / 0.509 / 11,200.919 | 4.57.1 |

### Repeated SmolLM3 failure

The SmolLM3-3B job failed in the same snapshot-resolution step in runs 40, 42, and 43 with `RuntimeError: Snapshot contains no license file; refusing to treat model-card tag as complete license evidence`. The job IDs are `133280490855` (run 40), `133331553209` (run 42), and `133346694967` (run 43). In all three runs, the real-response step was skipped and no SmolLM3 response artifact exists. This is a repeatable license-evidence block, not a queued or running inference job.

## New-candidate rights-capture evidence

The separate [Core Prime runtime and evaluation workflow run](https://github.com/vectolith/Models-by-vectolith./actions/runs/44310409690) completed its `teacher-rights-capture` job `134822758989` successfully and uploaded [`core-prime-teacher-rights-capture` artifact #14429024357](https://api.github.com/repos/vectolith/Models-by-vectolith./actions/artifacts/14429024357/zip). Its ZIP SHA-256 is `ccfc6dc589a3519e4a6a6497059a8382f5a1b85c0a9e361285e6c7436bbf2c1c`. The manifest records nine captures, zero capture failures, no weight downloads and no inference performed by the rights-capture job.

- Qwen3.5-2B teacher: exact revision `5bf1871105527bed0f47e8fa941d2fc5170f7b1d`; repository LICENSE SHA-256 `bbedc3fda3305820b977265f01b8619d87570a6739de3a5582c3464840f1e57a`.
- Gemma 4 E2B IT: exact revision `4adf15748de9e1a0097b6274cee9c15836c41c37`; official Google license reference SHA-256 `870b0d58d4697272e59d97fddf9447d163b922ad2582cf76226bc953840dfec6`; repository has no LICENSE file, so the official publisher reference and separately captured SPDX Apache-2.0 text are retained.
- Nemotron 3 Nano 4B BF16: exact revision `ef26eca1cb6b37ea5e5d5b7e01c087e63345aeec`; repository LICENSE is zero bytes; official NVIDIA license PDF SHA-256 `2ffd837856bb99d4cee13d17f0b597ecfeb95c38e30abc08d3dffef7d589881d`. The model-card license label and OpenMDW timing remain a legal-scope discrepancy requiring authorized human review.
- LFM2.5-2.6B: exact revision `7141b56cd4650af95c7c7b86983443aed050c96a`; repository LICENSE SHA-256 `4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c`. Its real inference artifact above is technical evidence only.

For these candidates, legal review remains pending, training-output permission remains `not_verified`, and teacher qualification remains `not_qualified`. Qwen and Gemma have no teacher inference output in this run. Nemotron has no inference output. LFM2.5 has the real run-40 output above but remains discovery-only. The independent candidate inference workflow is `workflow_dispatch`-only, defaults `run_candidates=false`, and its candidate matrix is still gated by explicit per-candidate local-inference authorization. No independent candidate inference job was running or queued in the inspected branch runs.
The independent local-grader smoke on PR #73 also passed: it loaded Qwen3.5-2B at grader-only revision `15852e8c16360a2fea060d615a32b45270f8a8fc` on CPU/BF16 and validated one synthetic blinded smoke row. This is grader infrastructure validation only; it is not a Qwen teacher response or a human grade.


## Qualification and training status

These artifacts preserve additive teacher responses; they do not rank, select or discard a teacher. The three existing teachers remain additive. All recorded evaluation artifacts state `grading=human_review_required`, `license_review=pending_human_legal_review`, `training_output_permission=not_verified`, `teacher_qualification=not_qualified`, and `training_started=false`. Core Prima remains paused. No training, distillation or model release is evidenced by these runs.

## Follow-up test fixes and verification on open PRs

- PR #76: corrected the stale registry test that expected the LFM2.5 revision to be null; it now asserts the exact pinned SHA `7141b56cd4650af95c7c7b86983443aed050c96a`. The latest [Core Prime runtime and evaluation tests #520](https://github.com/vectolith/Models-by-vectolith./actions/runs/44311872306) passed 110 tests (3 skipped), including both v4 tests; [Vectolith Runtime #349](https://github.com/vectolith/Models-by-vectolith./actions/runs/44311872304) passed 84 tests.
- PR #73: corrected the model-card frontmatter test fixture, which used literal backslash-n characters instead of newline characters. [Core Prime runtime and evaluation tests #517](https://github.com/vectolith/Models-by-vectolith./actions/runs/44310409690) passed 114 tests (3 skipped); its teacher-rights-capture job captured 9 candidates with zero capture failures, and its local-grader-smoke job passed. [Vectolith Runtime #346](https://github.com/vectolith/Models-by-vectolith./actions/runs/44310409498) passed 81 tests.
- The local-grader smoke used a synthetic blinded test row and Qwen3.5-2B at grader-only revision `15852e8c16360a2fea060d615a32b45270f8a8fc` on CPU/BF16. It is not a Qwen teacher response, not a human grade, and not candidate qualification evidence.
- PR #33 is already closed and merged (2026-11-16T03:11:17Z, merge commit `fdf6b6a3066558901c7e69255dcfb906266789c0`). No attempt was made to merge or reopen it. The active evidence and validation updates are on open PR #76; the rights-capture test correction is on open PR #73.
