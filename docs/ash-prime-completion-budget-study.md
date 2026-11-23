# ASH PRIME controlled completion-budget study

Status: implemented as a manual workflow; not dispatched. No new inference has been started by this change.

## Why a separate study is needed

The preserved run 40 baseline used greedy CPU BF16 generation with a 256-new-token cap. Observed cap hits were:

| Candidate | Cap hits at 256 | Rate |
|---|---:|---:|
| Granite 3.1 3B-A800M | 93/180 | 51.7% |
| Granite 4.2 3B | 104/180 | 57.8% |
| MiniCPM5 2B | 52/180 | 28.9% |
| LFM2.5-2.6B | 162/180 | 90.0% |
| Phi-4-mini-instruct | 69/180 | 38.3% |

These flags identify generations that reached the configured token limit without an EOS token. They are not correctness grades. The original 256-token response artifacts remain immutable and must not be replaced.

## Controlled comparison

The manual workflow offers 512, 768, or 1024 new tokens. It runs one candidate per matrix job on the same GitHub-hosted CPU runner class, using the same four Prime suites, greedy decoding, BF16, chat template, and disabled thinking. The only planned inference-setting change from run 40 is the output budget. Model-specific Transformers and Hugging Face Hub versions remain pinned to the previously verified loader combinations. Each job records its own CPU capability, available memory, RSS and runtime versions; hosted hardware can vary between jobs, so latency and resource comparisons across candidates must not be treated as controlled rankings.

The candidates are Granite 3.1, Granite 4.2, MiniCPM5, SmolLM3, LFM2.5, and Phi-4. SmolLM3 has no LICENSE file in its published snapshot, so it is admitted on tag-only evidence: the model-card licence tag is recorded as the evidence basis together with an explicit caveat, and its legal review stays pending. No other candidate may use that basis.

The workflow records each candidate's snapshot revision, workflow run and attempt, per-case internal run ID, completion classification, token counts, per-case latency, load/download/generation times, CPU capability, visible CPU count, peak RSS, runtime versions, and compute probe. Every candidate's JSON, JSONL, log, and compute record is uploaded as a separate artifact within the study artifact.

The runner now distinguishes:
- \`eos_completed\`: an EOS token was observed.
- \`token_cap_truncated\`: the configured token budget was exhausted without EOS.
- \`stopped_without_eos\`: generation stopped before the cap without EOS; do not assume completion.
- \`empty_output\`: no visible response was generated.
- \`error\`: generation failed.

The aggregate completion counts are machine-generated execution metadata, not human quality grades. Compare the new outputs with run 40 by exact case ID, candidate, immutable revision, prompt hash, and original rubric. Keep both generations. Do not overwrite, select, or discard any response.

## Dispatch control

The workflow is manual-only and the job runs only when the explicit \`confirm_study=true\` input is selected. Choose one budget (512, 768, or 1024). This is a CPU experiment and does not claim GPU performance or free-capacity availability. The study is not automatically started by PR or push events.

## Interpretation and gates

A lower cap-hit rate only demonstrates fewer budget-limited generations. It does not demonstrate correctness, completeness, safety, quality, or teacher qualification. All responses still require blinded independent human review. LFM2.5 and Phi-4 remain discovery-only. The three existing teachers remain additive. No candidate is ranked or selected.

No training is started. Legal review, separate written training-output permission, four-qualified-teacher, safety, private holdout, and corpus-integrity gates remain mandatory. FYR PRIMA remains paused.
