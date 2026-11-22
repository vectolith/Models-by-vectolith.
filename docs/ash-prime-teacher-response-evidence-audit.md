# ASH PRIME teacher response evidence audit

**Status: raw-output integrity checks passed; independent grading and all authorization gates remain blocked.**

This audit records existing artifacts from workflow run **43796213917** (workflow run #40) at commit \`2feabd8ece3dc6ce7034d2903a8e3d6b6edc441f\`, completed on 16 November 2026. It does not rerun any model or evaluate response quality.

## Verified raw-output set

Five completed teacher jobs produced **180 responses each (900 total)**. Each candidate's JSON and JSONL representations contain the same 180 records in the same order; IDs are unique within each candidate, and the five candidate ID sets and prompt SHA-256 values match.

The common suite distribution is:

| Suite | Cases per candidate |
|---|---:|
| Benchmark v1 | 12 |
| Qualification v2 | 20 |
| Qualification v3 | 92 |
| Qualification v4 | 56 |
| **Total** | **180** |

All five completed jobs report zero generation errors and 180 successful cases. These checks establish raw artifact consistency, not correctness, teacher qualification, rights, or model quality.

## Artifact inventory and hashes

The hashes below are SHA-256 values captured from the downloaded existing GitHub Actions artifacts. The artifact ZIP digest is the digest reported by GitHub; the JSON/JSONL hashes were independently computed from the files inside the downloaded ZIPs.

| Candidate | Immutable revision | Artifact ID | Artifact ZIP digest |
|---|---|---:|---|
| Granite 3.1 3B-A800M | \`a02780686e08a03fe0d2679a293b5c74a90efa89\` | 14199574383 | \`3f7fc738edef49a7347c50c906a4c3fd2e8a71bde7815de47f65dc03464ebc68\` |
| Granite 4.2 3B | \`4e9c275e232f10211ec88644d106a1f6a1b60e06\` | 14213985732 | \`f5b4a223cdd77c89c32b5c8ccf759f7a7c8d41b8e488395d2b51ebcb1f335834\` |
| MiniCPM5 2B | \`42433e90dad95123ab87729fd7011e7110629556\` | 14223103259 | \`3e16583a0f6746b8b4f324b7468f8364283d02dd2c5064531de2f5fd1af990ff\` |
| LFM2.5 2.6B | \`7141b56cd4650af95c7c7b86983443aed050c96a\` | 14238638626 | \`a52addbe9aabdde9cbee0543d203cd100e3bf25a84fe4ccda2acd2cc5b9a9d11\` |
| Phi-4 mini instruct | \`cfbefacb99257ffa30c83adab238a50856ac3083\` | 14260316025 | \`ffb3ce18c6c966b4a2914dc3b9393cedc95585f89b41f2ce7067c677131b34d8\` |

| Candidate | JSON SHA-256 | JSONL SHA-256 |
|---|---|---|
| Granite 3.1 3B-A800M | \`26fd01c55b75feb0124bc9920848d816cf03794827e456ebe30c9a4190515910\` | \`2d85b40e41baf8d8a3954e9e891fdb08cd3a22898b777dc5e0edf34696cdc044\` |
| Granite 4.2 3B | \`219e935601b7ac1a2321fc713a1c0e8808afbfc6395fb3e360ac94c4abbc74a8\` | \`ae886d8aef2cb01269f2f62d936930bdf74f3006a851513f85e141947ec94563\` |
| MiniCPM5 2B | \`0e499654f8aed9de2b30fbdfb870304e2835e8c5688518de5b7f8fef41d49948\` | \`b7c6f7a3fb190bae7bb530f41e7757b245df7936c112a0f0e8537a99d2ee0836\` |
| LFM2.5 2.6B | \`943105f753bb3aa16233a4bf56094af69abf898ea57e75bce5395412761acd2a\` | \`cd554a0cf6a5ed02c4460eaab21abc93e939f9830e8c898b8b96cf15906665db\` |
| Phi-4 mini instruct | \`03eda0c3ecb4c923f4aae35c6081634bce55997be3f3b85b85eaf028a1a39b1d\` | \`aae7cb4c6862cf0eaa795b8cd538020214be5f2f97b37416e77035b687b633c8\` |

Artifacts were retained by GitHub until **14 February 2027** at the time of this audit. The report contains hashes and metadata only; no raw response text is copied into this document.

## Generation-cap audit

**480 of 900 responses (53.33%) reached the 256-token generation limit.** Preserve these as incomplete/truncated raw responses and do not silently discard them.

| Candidate | Token-limit records | Uncapped records |
|---|---:|---:|
| Granite 3.1 3B-A800M | 93 | 87 |
| Granite 4.2 3B | 104 | 76 |
| MiniCPM5 2B | 52 | 128 |
| LFM2.5 2.6B | 162 | 18 |
| Phi-4 mini instruct | 69 | 111 |
| **Total** | **480** | **420** |

Across all five candidates, token-limit counts by suite were: benchmark v1 **18/60**, qualification v2 **46/100**, qualification v3 **207/460**, and qualification v4 **209/280**. The generation-cap marker is retained in the raw evidence.

## Snapshot and license evidence limitations

- LFM2.5 and Phi-4 artifacts include immutable snapshot manifests with file inventories and SHA-256 hashes. Their manifest status still records legal review pending and output-training permission unverified.
- Granite 3.1, Granite 4.2, and MiniCPM5 record immutable model revisions in their response metadata, but this artifact set does not contain a complete snapshot-file hash inventory for those three.
- Every output manifest records \`license_review=pending_human_legal_review\`, \`training_output_permission=not_verified\`, \`teacher_qualification=not_qualified\`, and \`grading=human_review_required\`. None of these statuses is changed by this audit.

## Failed sixth candidate — SmolLM3-3B

The SmolLM3 snapshot step failed before inference because the downloaded snapshot contained no license file:

\`RuntimeError: Snapshot contains no license file; refusing to treat model-card tag as complete license evidence\`

The response-generation step was skipped and no usable SmolLM3 response artifact was produced. This is a license-evidence blocker. The pipeline must not be relaxed to bypass it or to start inference without the required review and permission.

## Remaining gates

- [ ] Independent human grading of all 900 raw responses, with reviewer independence and rubric provenance.
- [ ] Written output-training permissions and independent legal review for every admitted teacher.
- [ ] Complete provenance, license evidence, immutable snapshot verification and source permissions.
- [ ] Teacher qualification decisions based on independent grading and defined gates.
- [ ] A newly authored, restricted-custody protected holdout; the public draft holdout is compromised.
- [ ] Verified genuinely free compute and zero-budget preflight.
- [ ] Final explicit training authorization.

**Decision:** the raw 900-response evidence set is integrity-checked and ready to be packaged for independent human grading, but it is not graded, qualified, authorized, or ready for training. No inference or training was performed by this audit.
