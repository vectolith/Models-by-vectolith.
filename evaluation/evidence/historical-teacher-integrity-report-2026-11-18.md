# Historical Core Prime Teacher Integrity Report

**Scope:** historical artifacts only. No new model inference, model-weight downloads, grading, training, or distillation were performed.

## Result

- Integrity validation: **passed**
- Preserved workflow runs: **40, 42, 43**
- Historical teachers: **5**
- Teacher executions: **15** (five in each preserved run)
- Response records validated: **2,700** (180 per execution)
- Pairwise comparisons: **105**
- Comparable case pairs: **18,900**
- Prompt-hash mismatches: **0**
- Execution errors: **0**
- Responses completed without reaching the generation cap: **1,270**
- Token-cap-truncated responses: **1,430**

All 15 source ZIP archives passed ZIP integrity checks. Every execution had paired JSON and JSONL files; the JSON `case_count` matched all 180 JSONL rows. The comparator validated candidate, immutable revision, run ID, case IDs, prompt SHA-256 values, response types, and embedded JSON-versus-JSONL parity. Source archive, JSON and JSONL SHA-256 hashes are recorded in the machine-readable evidence.

## Per-execution completion accounting

| Historical run | Teacher | Cases | Completed without token cap | Token-cap truncated | Errors |
|---:|---|---:|---:|---:|---:|
| 40 | Granite 3.1 3B A800M | 180 | 87 | 93 | 0 |
| 40 | Granite 4.2 3B | 180 | 76 | 104 | 0 |
| 40 | MiniCPM5 2B | 180 | 128 | 52 | 0 |
| 40 | LFM2.5 2.6B | 180 | 18 | 162 | 0 |
| 40 | Phi-4 Mini Instruct | 180 | 111 | 69 | 0 |
| 42 | Granite 3.1 3B A800M | 180 | 90 | 90 | 0 |
| 42 | Granite 4.2 3B | 180 | 77 | 103 | 0 |
| 42 | MiniCPM5 2B | 180 | 128 | 52 | 0 |
| 42 | LFM2.5 2.6B | 180 | 17 | 163 | 0 |
| 42 | Phi-4 Mini Instruct | 180 | 117 | 63 | 0 |
| 43 | Granite 3.1 3B A800M | 180 | 87 | 93 | 0 |
| 43 | Granite 4.2 3B | 180 | 77 | 103 | 0 |
| 43 | MiniCPM5 2B | 180 | 128 | 52 | 0 |
| 43 | LFM2.5 2.6B | 180 | 18 | 162 | 0 |
| 43 | Phi-4 Mini Instruct | 180 | 111 | 69 | 0 |

## Pairwise comparison integrity

All 105 pairwise comparisons had 180 common benchmark case IDs, 180 comparable prompt hashes, and zero prompt-hash mismatches. The comparison includes both cross-teacher pairs and repeated executions of the same teacher across historical runs.

Exact-response match ratios and character-level similarity are descriptive disagreement measures only. They are not quality scores and do not establish correctness, reasoning quality, safety, or model superiority. No teacher was ranked or selected; no response was modified or discarded. Human grading remains a separate process.

## Legacy status normalization

The historical outputs use `generation_status` and `generation_cap_reached` rather than the newer `completion_status` field. The comparator now maps `token_limit_reached` / cap-reached records to `token_cap_truncated`, and `eos_or_early_stop` records to `completed_without_token_cap`. This label deliberately does not claim that every response ended with an EOS token. Original source rows are not rewritten.

## Provenance and reproduction

- Repository: `vectolith/Models-by-vectolith.`
- PR: [#76](https://github.com/vectolith/Models-by-vectolith./pull/76)
- Comparator: `evaluation/compare_prime_teacher_responses.py`
- Comparator status-normalization change: `739b25cd03c4947179e5c4e2345da7ce4ffffc27`
- Regression test commit: `3d43af8fa5a46f85d30b95929f7acc55a005ce15`
- Validation: [GitHub Actions run #44259002496](https://github.com/vectolith/Models-by-vectolith./actions/runs/44259002496) — passed
- Historical source workflow run IDs: `43796213917`, `43820188813`, `43821046671`

The companion JSON contains all 15 artifact IDs, source archive SHA-256 values, member counts, JSON/JSONL SHA-256 values, execution provenance, contributor completion counts, and all 105 pairwise comparison results. Pairwise rows reference the contributor indices in the `contributors` array; the shared coverage and prompt-hash invariants are recorded once under `pairwise_global_invariants` in the evidence schema.

## Limitations and gates

- This is a historical-only integrity and disagreement report. It contains no results from Qwen3.5-2B, Gemma 4 E2B IT, or Nemotron 3 Nano 4B.
- Token-cap-truncated responses remain preserved and are explicitly counted; they must not be treated as complete answers.
- New candidate inference remains blocked pending human legal review and explicit authorization.
- Training-output permission remains separate and unverified. No training or distillation was started.

Machine-readable companion: [historical-teacher-integrity-evidence-2026-11-18.json](historical-teacher-integrity-evidence-2026-11-18.json).
