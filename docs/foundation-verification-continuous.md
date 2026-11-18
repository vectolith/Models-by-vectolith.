# Foundation verification — continuous execution standard

**Applies to:** Core Prime and Core Prima foundation-model research.
**Decision state:** Open. No foundation is approved.
**Execution principle:** Verification is continuous and concurrent, not a sequence of approval gates.

## Candidate identity ledger

The active research records must use exact repository IDs:

| Candidate | Exact repository | Current immutable revision evidence |
|---|---|---|
| Qwen3.5-9B | `Qwen/Qwen3.5-9B` | Hub API observed SHA: `c202236235762e1c871ad0ccb60c8ee5ba337b9a` |
| Granite 4.2 8B | `ibm-granite/granite-4.2-8b` | Hub API observed SHA: `a7042144125ce5ae64f89610e8289647fc000b9a` |
| Gemma 4 E4B | `google/gemma-4-E4B` | Exact immutable SHA not yet captured |
| Mistral Small 4 | `mistralai/Mistral-Small-4` | Exact immutable SHA not yet captured |

The two observed SHAs above are discovery observations, not yet approved evaluation pins. Capture a fresh Hub snapshot through the repository discovery utility immediately before artifact retrieval, then verify that the loaded runtime reports the same immutable revision. Do not treat a moving `main` reference as a pin. For Gemma and Mistral, keep revision state pending until the exact official repository metadata has been retrieved.

## Evidence lifecycle

Maintain independent evidence fields per candidate. Workstreams may proceed concurrently:

1. Identity and artifact provenance: repository, publisher, immutable revision, architecture, tokenizer/processor, config, file inventory and hashes.
2. Rights and permissions: exact revision license text, additional terms, gated status, human legal review, and explicit determination of whether outputs may be used for student training.
3. Availability and deployment: real provider session evidence, hardware, memory, quotas, session duration, storage, egress, billing state, and zero-charge evidence.
4. Runtime and training compatibility: exact framework/driver versions, model load, tokenizer/template behavior, tool parser, adapter target discovery, save/reload, and bounded training smoke test.
5. Comparative capability: common controlled tasks, role-specific tasks, raw responses, blinded grading, reliability, multilingual and global-English performance.
6. Performance and economics: measured peak RAM/VRAM, time-to-first-token, output throughput, concurrency, cold start, actual resource consumption and cost.

Update each record as evidence arrives. An unresolved field does not stop unrelated work on that candidate or other candidates. A candidate with a failed or unavailable requirement remains visible with its actual status; it is not replaced automatically.

## Evidence labels

- `provider_claim`: statement published by the model publisher or service provider.
- `metadata_observed`: information retrieved from an official model repository or API at a recorded time.
- `verified`: independently checked fact with retained supporting evidence.
- `measured`: result observed in an identified, product-specific evaluation run, with configuration and raw evidence.
- `pending`: not yet established.
- `blocked`: an attempted action cannot proceed under current conditions; include the reason.
- `not_applicable`: field does not apply, with a short rationale.

Never promote a provider claim or estimate to a verified or measured result. Never mark a candidate qualified solely from a model card, family reputation, or public leaderboard.

## No-substitution contract

Each evaluation run must bind to one exact repository ID and immutable revision, plus exact tokenizer/processor and serving artifact identities. Quantization and conversion are distinct artifacts and must be recorded separately. A different revision, variant, parameter size, architecture, mirror, API endpoint, or quantization is a separate candidate/run.

If the exact candidate cannot be fetched, licensed, loaded, or evaluated, preserve the failure evidence and continue with other candidates. Do not swap in a substitute. Any proposed change to an authorized target requires explicit user approval. Results from one artifact must never be attributed to another.

## Reporting

Publish a per-candidate evidence ledger and separate Prime/Prima scorecards. Report missing evidence and uncertainty alongside results. Preserve raw outputs, per-case grades, run manifests, dataset/prompt hashes, software versions, hardware observations, and failures. Compare trade-offs by dimension rather than hiding them in one score.

The current repository research note is a discovery shortlist, not a benchmark report. At the time this standard was added, no comparative foundation benchmark in this repository, final selection, or foundation-specific training approval had been established.
