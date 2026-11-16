# Expanded foundation candidate intake — 2026-11-16

## Purpose

Expand the candidate pool around the current provisional Granite 3.1 3B-A800M lead. The four newly discovered candidates below have not yet been run in the Vectolith Prime/Prima public suites. Qwen2.5-7B-Instruct is also recorded as a **historical comparator** because it already has preserved Prime and Prima inference evidence; it is not a newly discovered candidate or an active-shortlist reinstatement. No candidate is qualified by this intake record.

The comparison remains role-specific: Core Prime prioritizes general reasoning, factual reliability, instruction following, synthesis and multilingual competence; Core Prima prioritizes coding, debugging, mathematics, structured tool use and reliable task completion.

## Candidates to snapshot and compatibility-test

| Candidate ID | Exact Hub repository | Size / architecture | Why it belongs in the comparison | Initial role hypotheses |
|---|---|---|---|---|
| granite-4.2-3b | `ibm-granite/granite-4.2-3b` | 3B dense, GraniteForCausalLM | Closest like-for-like successor: native reasoning modes, coding and native tool calling. Official Hub metadata currently reports immutable revision `4e9c275e232f10211ec88644d106a1f6a1b60e06`, Apache-2.0 tag, ungated. | Prime + Prima |
| minicpm5-2b | `openbmb/MiniCPM5-2B` | 2.52B dense, standard LlamaForCausalLM | Compact local model explicitly designed for coding agents, math, tool-calling and long-context workflows. Official model card declares Apache-2.0. | Prime + Prima |
| ministral-3b-instruct | `ministral/Ministral-3b-instruct` | 3B dense causal LM | Similar parameter scale; general instruction model with standard Transformers AutoModelForCausalLM loading and Apache-2.0 model-card license tag. Primarily English, so multilingual capability must be measured rather than assumed. | Prime + Prima |
| qwen3.5-4b | `Qwen/Qwen3.5-4B` | 4B-class multimodal model | Newer Qwen generation with a current Apache-2.0 Hub license tag; useful to test whether a modern generalist can beat the existing 3B lead. | Prime + Prima, subject to loader support |

## Historical comparator retained in the expanded list

| Candidate ID | Exact Hub repository | Immutable revision | Prior Vectolith evidence | Current disposition |
|---|---|---|---|---|
| qwen2.5-7b-instruct | `Qwen/Qwen2.5-7B-Instruct` | `a09a35458c702b33eeacc393d103063234e8bc28` | Preserved real inference runs: 124 Core Prime cases and 113 Core Prima cases. Mean latency was 107.86 s/case (Prime) and 155.45 s/case (Prima); peak RSS was 13.94 GiB and 13.96 GiB respectively. | Retain as a historical comparison/reference only. The 2026-11-16 disposition removed it from both active shortlists because the measured resource cost was high and the inspected evidence did not establish a sufficient quality advantage. Re-entry requires an explicit new evaluation decision; do not erase or replace prior results. |

## Evidence sources

- Granite 4.2 official model card and metadata: https://huggingface.co/ibm-granite/granite-4.2-3b
- IBM Granite 4.2 technical overview: https://huggingface.co/blog/ibm-granite/granite-4-2
- MiniCPM5-2B official model card: https://huggingface.co/openbmb/MiniCPM5-2B
- MiniCPM5-2B official deployment/technical guide: https://openbmb.cn/docs/en/guides/minicpm-text/minicpm5-2b
- Ministral 3B official model card: https://huggingface.co/ministral/Ministral-3b-instruct
- Qwen3.5-4B official Hub model page: https://huggingface.co/Qwen/Qwen3.5-4B

Publisher benchmark claims are discovery context only; they are not Vectolith results and will not be used as qualification scores.

## Mandatory intake gates before full-suite inference

1. Run the repository's Hugging Face snapshot tool for each exact repo. Preserve current immutable 40-character revision, exact model-card and license-file text, SHA-256 hashes, gating state, architecture/config, tokenizer files and weight inventory.
2. Inspect pinned license text and terms. A permissive weights license does not establish permission to train student models on generated outputs; keep `training_output_permission=not_verified` until separate written evidence and legal review.
3. Perform a real load-and-generate smoke test with the pinned revision. Record the exact Transformers/PyTorch versions, tokenizer/template, CPU capability, dtype, memory, download/load time and a fixed small prompt set.
4. Do not silently use `trust_remote_code`. Any custom model code requires a security review and pinned source revision before execution.
5. Check whether the existing evaluation runner correctly handles the candidate's architecture and chat template. Granite 4.2 needs a Transformers version that supports `GraniteForCausalLM`; its model card also documents a Granite-specific reasoning parser for vLLM. Qwen3.5-4B is exposed as a multimodal architecture and must not be forced through the current text-only `AutoModelForCausalLM` path without a verified compatible loader.
6. Only candidates that pass intake are added to the full 124-case Prime and 113-case Prima inference matrix. Keep the original fixture revision, decoding settings and all original candidates' evidence intact. Use role-separated results and repeated runs where compute permits.
7. Preserve failed downloads, unsupported architectures, out-of-memory conditions and other failures as explicit outcomes. Do not silently drop or replace a candidate.

## Current status

- Granite 4.2-3B: public metadata and official model card inspected; immutable revision identified; local/CI load test not yet performed.
- MiniCPM5-2B: official model card and deployment guide inspected; exact immutable revision snapshot and load test pending.
- Ministral-3B-Instruct: official model card inspected; exact immutable revision snapshot and load test pending.
- Qwen3.5-4B: official Hub page and Apache-2.0 tag inspected; exact immutable revision snapshot and loader compatibility test pending.
- Full Vectolith Prime/Prima inference: not yet run for any of the four newly discovered candidates.
- Qwen2.5-7B-Instruct: prior Prime and Prima inference is already preserved in the historical evidence set; this intake does not rerun it or reverse its active-shortlist disposition.
- Human grading, legal review and teacher qualification: not performed by this intake.

This file is a candidate intake register, not a result report or qualification decision.
