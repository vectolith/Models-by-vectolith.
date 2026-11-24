# ASH PRIME sequential six-teacher run 45162517839 evidence - 2026-11-24

Recorded from the live workflow run https://github.com/vectolith/Models-by-vectolith./actions/runs/45162517839 (workflow `expanded-qualification-inference.yml`, dispatch input `run_qualification=true`, head `d3d70a0707324081a9284c212f3e8d9afeda1637`). Artifacts were downloaded by artifact ID with `gh api`, extracted and inspected locally; ZIP digests were recomputed and compared with GitHub artifact digest metadata. This record does not qualify, rank or select any candidate and does not satisfy any human gate.

## Job completion state

| Candidate | Job ID | State | Started (UTC) | Completed (UTC) |
|---|---|---|---|---|
| granite-3.1-3b-a800m | 137651308894 | success | 2026-11-23T11:09:18Z | 2026-11-23T12:21:51Z |
| granite-4.2-3b | 137689001667 | success | 2026-11-23T12:21:54Z | 2026-11-23T15:36:42Z |
| minicpm5-2b | 137805871258 | success | 2026-11-23T15:36:44Z | 2026-11-23T17:42:41Z |
| smollm3-3b | 137888715672 | success | 2026-11-23T17:42:43Z | 2026-11-23T19:48:56Z |
| lfm2.5-2.6b | 137966713991 | success | 2026-11-23T19:48:58Z | 2026-11-24T00:15:13Z |
| phi-4-mini-instruct | 138115183115 | success | 2026-11-24T00:15:15Z | 2026-11-24T04:09:28Z |

All six jobs completed successfully. Phi-4-mini-instruct job 138115183115 finished at 2026-11-24T04:09:28Z, after the first revision of this register, so its artifact was downloaded and verified separately and is recorded below with the same procedure as the other five. This document is additive: nothing above it was rewritten.

## Artifact integrity

| Candidate | Artifact name | Artifact ID | ZIP bytes | ZIP SHA-256 | Matches GitHub digest |
|---|---|---|---:|---|---|
| granite-3.1-3b-a800m | `prime-teacher-granite-3.1-3b-a800m` | 14817063602 | 155,204 | `51d2928ed8da7f95deb4d990ed44d06a7fdbda1aa70957a24850503ff49647dc` | yes |
| granite-4.2-3b | `prime-teacher-granite-4.2-3b` | 14834436941 | 171,313 | `078eaa26174305f0409a1054b141db5e82fedac136f8f0ee2b6c3f45d43de1e4` | yes |
| minicpm5-2b | `prime-teacher-minicpm5-2b` | 14847127062 | 130,489 | `3ead6c0936aa2cb8f213197f996a28c70c86434e3078b011c2c6b2a3f3069c8f` | yes |
| smollm3-3b | `prime-teacher-smollm3-3b` | 14856493494 | 156,638 | `13be31b44098c3762e62349e4883afd280f722c5299f436513b3ad087939e9cd` | yes |
| lfm2.5-2.6b | `prime-teacher-lfm2.5-2.6b` | 14877000376 | 200,951 | `e862d224c5b8e5cecde3a4a43fbd6cac2503bcceace18f8ccf4d185b43263c16` | yes |
| phi-4-mini-instruct | `prime-teacher-phi-4-mini-instruct` | 14888583630 | 149,720 | `9cec18142407dce0bf42777d940ed74cfbc19f7d7f2cb9e855969a46e8004730` | yes |

## Response coverage and completion-budget outcome

Per-artifact check on the embedded `evaluations/*-ash_prime.json`: 180 records, 180 unique case IDs, 180 rubric-bearing records, 180 non-empty responses, zero generation errors, every record bound to the expected immutable revision. Completion counts are execution metadata, not grades.

| Candidate | Immutable revision | Records | Errors | eos_completed | token_cap_truncated | stopped_without_eos | Generation s | Peak RSS GiB | Transformers |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| granite-3.1-3b-a800m | `a02780686e08a03fe0d2679a293b5c74a90efa89` | 180 | 0 | 86 | 94 | 0 | 4271.4 | 6.86 | 4.57.1 |
| granite-4.2-3b | `4e9c275e232f10211ec88644d106a1f6a1b60e06` | 180 | 0 | 75 | 105 | 0 | 11606.0 | 7.44 | 5.0.0 |
| minicpm5-2b | `42433e90dad95123ab87729fd7011e7110629556` | 180 | 0 | 0 | 54 | 126 | 7501.6 | 5.25 | 4.57.1 |
| smollm3-3b | `a07cc9a04f16550a088caea529712d1d335b0ac1` | 180 | 0 | 95 | 85 | 0 | 7496.2 | 6.26 | 4.57.1 |
| lfm2.5-2.6b | `7141b56cd4650af95c7c7b86983443aed050c96a` | 180 | 0 | 22 | 158 | 0 | 15892.7 | 5.64 | 5.0.0 |
| phi-4-mini-instruct | `cfbefacb99257ffa30c83adab238a50856ac3083` | 180 | 0 | 0 | 63 | 117 | 13981.0 | 7.66 | 4.57.1 |

These are new 256-token-budget generations on the four Prime suites with the same procedure as runs 40/42/43: additive response evidence for a new run, not a controlled completion-budget study, not a replacement for any earlier response set.

### Observations that must not be read as quality

- MiniCPM5 2B reports 126/180 `stopped_without_eos` and only 54 `token_cap_truncated`. Generation ended before the cap without an EOS token on most cases; the runner deliberately does not treat that as completion. Those responses need inspection before any grading interpretation.

- LFM2.5-2.6B is the most budget-limited candidate: 158/180 generations hit the 256-token cap (162/180 in run 43).

- Phi-4-mini-instruct likewise reports 117/180 `stopped_without_eos` against 63 `token_cap_truncated`: the runner stopped before the cap without emitting EOS and does not count that as completion. Same caveat as MiniCPM5: inspect before reading anything into those responses.

- All six artifacts used CPU-only PyTorch 2.8.0, BF16, greedy decoding. No GPU or hosted inference. Phi-4-mini-instruct's snapshot is 7,694,054,130 bytes with a LICENSE file present (`license_file_status: present`, tag `mit`), which is stronger licence evidence than SmolLM3's tag-only snapshot but still `pending_human_legal_review`.

## Licence evidence

- SmolLM3-3B ran on tag-only licence evidence: snapshot revision `a07cc9a04f16550a088caea529712d1d335b0ac1`, `license_file_status: missing`, snapshot size 6,167,865,576 bytes, `snapshot_validation_status: complete_with_tag_only_license_evidence`, `license_review: pending_human_legal_review`. The job log prints: "Snapshot contains no LICENSE or NOTICE file. Licence status rests on the model-card tag alone, which is Hub metadata and not licence text".

- Phi-4-mini-instruct carries `license_tag: mit` with `license_file_status: present` and `snapshot_validation_status: complete`; it is still `pending_human_legal_review`.

- Every artifact retains `license_review: pending_human_legal_review`, `training_output_permission: not_verified`, `teacher_qualification: not_qualified`, `training_started: false`.

## Gate disposition against docs/ash-prime-four-teacher-qualification.md

- Gate 1 (immutable snapshot): only the per-artifact revision binding is checked here; no completed gate manifest exists.
- Gate 4 (real inference): response coverage, zero errors and matching revision are verified per candidate for this run.
- Gate 5 (resource measurement): per-run CPU/RSS/runtime observations exist in each `compute/*-runner.json`; hosted hardware varies so they are not controlled measurements.
- Gates 2, 3, 6, 7, 8, 9, 10 remain unverified: no legal review, two independent human graders, safety review, protected holdout, corpus-integrity attestation or written training-output permission exists.

No candidate is qualified and no gate is marked verified in this document. Granite 3.1, Granite 4.2 and MiniCPM5 remain the three additive teachers; SmolLM3, LFM2.5 and Phi-4 remain discovery-only. FYR PRIMA stays paused and no training is authorized.

## Retention

Artifacts expire 2027-02-21. Copy the six ZIPs and this register to restricted evidence storage before then; the ZIPs are not committed to this repository.
