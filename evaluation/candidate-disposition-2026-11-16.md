# Candidate disposition — 2026-11-16

## Decision scope

This is a **provisional active-shortlist decision**, not a qualification result and not a human quality grade. The decision uses the eight preserved public-suite inference artifacts from workflow run `43741294441`. All original outputs and artifacts remain retained for blinded review and audit. No historical evidence is deleted.

Execution conditions were the same for all candidates: CPU-only GitHub Actions runner class, BF16, greedy decoding, chat template enabled, thinking disabled, and a 256-new-token response cap. These are single-run measurements; they do not establish repeated-run variance or production performance. Runner account-level execution eligibility and available capacity were not verified.

## Active shortlist decision

| Candidate | ASH PRIME | FYR PRIMA | Disposition |
|---|---|---|---|
| IBM Granite 3.1 3B-A800M | Retain | Retain | Lead candidate for further blinded review; not qualified |
| Qwen3 0.6B | Remove | Retain provisionally | Exclude from Prime shortlist due to two observed reasoning failures; retain for Prima review because it is substantially more efficient, pending human assessment of coding/engineering quality |
| Qwen3 4B | Remove | Remove | Retire from active shortlist: materially slower and higher-memory than Granite in both roles, with similarly high or higher truncation; no demonstrated quality advantage in the inspected Prime cases |
| Qwen2.5 7B Instruct | Remove | Remove | Retire from active shortlist: highest latency and memory footprint, very high Prima truncation, and no demonstrated quality advantage sufficient to justify the compute cost |

“Remove” means no longer an active candidate for the next selection stage. It does **not** mean deleting the model's historical outputs, removing its identity from blinded comparison packets, or claiming a final quality failure. All four candidates remain in the historical evidence set and should be represented in the blinded review packets so reviewers can assess them without identity cues.

## Measured execution evidence

Mean per-case latency, token-cap hits, and maximum resident set size (RSS) were read from each candidate's actual JSON metadata and JSONL records.

### ASH PRIME

| Candidate | Cases | Mean latency (s/case) | Cap hits | Cap-hit rate | Peak RSS |
|---|---:|---:|---:|---:|---:|
| Qwen3 0.6B | 124 | 8.28 | 5 | 4.0% | 1.85 GiB |
| Qwen3 4B | 124 | 51.77 | 52 | 41.9% | 8.33 GiB |
| Granite 3.1 3B-A800M | 124 | 26.71 | 47 | 37.9% | 6.77 GiB |
| Qwen2.5 7B Instruct | 124 | 107.86 | 44 | 35.5% | 13.94 GiB |

### FYR PRIMA

| Candidate | Cases | Mean latency (s/case) | Cap hits | Cap-hit rate | Peak RSS |
|---|---:|---:|---:|---:|---:|
| Qwen3 0.6B | 113 | 9.46 | 35 | 31.0% | 1.80 GiB |
| Qwen3 4B | 113 | 74.39 | 96 | 85.0% | 8.32 GiB |
| Granite 3.1 3B-A800M | 113 | 22.19 | 99 | 87.6% | 6.87 GiB |
| Qwen2.5 7B Instruct | 113 | 155.45 | 98 | 86.7% | 13.96 GiB |

Token-cap hits indicate responses were cut off at the configured generation limit. They are a response-completeness concern, not automatically a correctness grade. In Prima, all three larger candidates hit the cap on roughly 85–88% of cases; Qwen3 0.6B had a lower cap-hit rate but still hit it on 31% of cases.

## Directly inspected ASH PRIME examples

- `prime-reasoning-001`: the rubric requires 126. Qwen3 0.6B returned 24. Granite returned 126. Qwen3 4B and Qwen2.5 7B reached the 256-token cap before stating the final answer.
- `prime-reasoning-002`: the rubric requires “no” because the commenters are not necessarily panel members. Granite answered no. Qwen3 0.6B, Qwen3 4B and Qwen2.5 7B answered yes.

These are directly observed response differences on two cases, not a substitute for reviewing all 124 Prime cases or for independent human grading. They are the reason Qwen3 0.6B is removed from the Prime shortlist and why Granite is the current Prime lead for review.

## Artifact provenance

Workflow run: `43741294441`. GitHub reports all eight jobs completed successfully. The artifact ZIP digests below are the GitHub-reported SHA-256 digests; each archive was downloaded again for this analysis.

| Candidate / role | Artifact ID | SHA-256 |
|---|---:|---|
| Qwen3 0.6B / Prime | 14172976685 | `b90c50bb96c5682083da23fd818b70a80a4b41e013fd6c60d7a6c68cc252702c` |
| Qwen3 0.6B / Prima | 14173715383 | `ae75428d2f386008d11969b7e6e6426a629e39e58d53426b6668ea3cd80d1ffe` |
| Qwen3 4B / Prime | 14176707306 | `86534856c62c625522f580c6da9c73b2ddf9d1e48a6ad84443e5f427580df65d` |
| Qwen3 4B / Prima | 14178320047 | `a8c0af215961cadcc68ef61e22e3f3e4f423d56f3e4b533149e66b9c9d56b288` |
| Granite 3.1 / Prime | 14179180518 | `b6b67df8382d14e3e3182e008add396f76e672c96cb31c0b7331227ccc0cd9ff` |
| Granite 3.1 / Prima | 14179691832 | `09904f4d9f1b4a4648876019b69585c24471b895a089b1511eb744bc52fe2424` |
| Qwen2.5 7B / Prime | 14181582462 | `77715b0a3f5afafa1852dd19eb4686e479a1de26e344326782991d643cbad9ce` |
| Qwen2.5 7B / Prima | 14184212627 | `f7672a6e0f68b0f032a8d29c8a2fa761489e4d5de03cabb544fad804fa6c0eff` |

## Qualification remains blocked

No candidate is qualified by this disposition. Independent blinded human grades, genuine restricted holdout evidence, legal review, explicit training-output permission, teacher contribution and the required four qualified teachers per student, ablations, safety/release evidence, and repeated-run reliability remain outstanding. The Prima role in particular still has a severe response-truncation issue that must be addressed and re-evaluated before selection.
