# Core Prime Run 42 teacher artifact integrity audit — 2026-11-17

## Scope and provenance

This audit covers the five teacher inference artifacts published by GitHub Actions workflow run `43820188813` (Run 42). The workflow run's recorded source was branch `add-qwen25-7b-to-expanded-intake`, commit `6f9157b8a4e2150dac6a8d777ed0a8057c795251`. These artifacts are candidate inference evidence; they were not produced by PR #73's `fix/core-prime-preflight-cli` branch. Preserve that provenance distinction when consuming them.

All five artifacts were downloaded from GitHub Actions and inspected locally. For each ZIP, the downloaded byte length and SHA-256 were recomputed and matched the GitHub artifact metadata. The embedded evaluation JSON was checked for expected case count, unique case IDs, rubric presence, response presence, generation errors, candidate ID and immutable revision.

## Verified artifact inventory

| Candidate | Immutable revision | Artifact ID | Responses | Errors | ZIP bytes | SHA-256 |
|---|---|---:|---:|---:|---:|---|
| Granite 3.1 3B-A800M | `a02780686e08a03fe0d2679a293b5c74a90efa89` | `14207923899` | 180/180 | 0 | 152,759 | `8d799a9c015ab6728079fe1f54bf8a6557d0c011d84fd4b826dbbd23e69a81fd` |
| Granite 4.2 3B | `4e9c275e232f10211ec88644d106a1f6a1b60e06` | `14222803141` | 180/180 | 0 | 170,882 | `088e3dbee15c26627cc97d6cb09d46bca0a37340cc5a5ae08af86e4ccebcb45e` |
| MiniCPM5 2B | `42433e90dad95123ab87729fd7011e7110629556` | `14230880744` | 180/180 | 0 | 130,130 | `8375eb2eb02192c07c5fdebdf661bda4c9eeb54d852f40679a3863f1210e94d4` |
| LFM2.5 2.6B | `7141b56cd4650af95c7c7b86983443aed050c96a` | `14262556692` | 180/180 | 0 | 200,298 | `f6502425a369cd3b86347c311445c729793f45f438e4f4aa4a6f155406216e64` |
| Phi-4-mini-instruct | `cfbefacb99257ffa30c83adab238a50856ac3083` | `14280614317` | 180/180 | 0 | 147,678 | `9b34e52ef661236741bae16b7de0ce9b04b065fdb223e2aec3bfb4d812cbac4c` |

**Verified aggregate:** 5 artifacts, 900 unique response records, 900 rubric-bearing records, 900 non-empty response texts, and zero generation errors. Each artifact contained 180 distinct case IDs and matched the exact immutable revision recorded in its embedded evaluation and snapshot metadata.

## Qualification and training status

The artifact contents explicitly retain these states for all five candidates:

- License review: `pending_human_legal_review`.
- Training-output permission: `not_verified`.
- Teacher qualification: `not_qualified`.
- Training started: `false`.

The evaluation records contain per-case rubric criteria, but they do not contain completed grade decisions. The artifact-level grading field is not a passed Grading report. Therefore this audit does **not** claim any response has passed Grading and does not create or imply a completed Grading report.

The five artifacts establish inference completion and byte-level artifact integrity only. They do not establish legal permission, teacher qualification, safety approval, corpus acceptance, protected-holdout success, foundation selection or training authorization.

## Retention

GitHub reported these artifacts as unexpired when inspected on 2026-11-17, with expiration on 2027-02-14. Retain the original ZIPs and their metadata in the restricted evidence vault before expiry. Keep raw outputs, private grading material, holdout data, scoring keys, credentials and access records out of this repository and public CI.

## Reproduction notes

The integrity check used the downloaded ZIP bytes for SHA-256, then inspected the embedded `evaluations/*.json` and `snapshots/*.json` entries. Response coverage was checked against the declared case count, actual result length, unique case IDs, non-empty rubric arrays and non-empty response text. This was an artifact-integrity audit, not a semantic quality grade.
