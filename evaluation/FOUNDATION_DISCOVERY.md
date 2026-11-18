# Automated foundation discovery and qualification

## Candidate discovery and evidence

Search the public Hugging Face catalog instead of relying only on a manually curated list:

```bash
python evaluation/discover_hf_candidates.py \
  --search "Qwen instruct" \
  --search "Granite instruct" \
  --search "Gemma instruct" \
  --search "Ministral instruct" \
  --search "Ministral instruct" \
  --author "Qwen" \
  --author "ibm-granite" \
  --author "google" \
  --author "mistralai" \
  --author "ministral" \
  --limit 100 \
  --sort downloads \
  --output artifacts/candidates/huggingface-discovery.jsonl
```

Or snapshot exact repository IDs with repeated `--repo` arguments. Search results are restricted to the text-generation pipeline and, when supplied, exact official publisher accounts. They are discovery leads, not recommendations or qualifications. Search results can change over time; preserve each timestamped output rather than overwriting earlier evidence.

Each candidate snapshot pins a 40-character immutable Hub commit SHA and records the metadata URL, model-card and license-file source URLs, exact retrieved text, SHA-256 hashes, architecture, parameter metadata when supplied, weight/tokenizer/config file inventories, gating state and tags. The exact text is retained in the JSONL record so legal reviewers can inspect the evidence later. A missing license file is recorded as missing; it is not inferred from a tag.

The script does not determine legal suitability. A human review must inspect the exact license text, linked terms, attribution obligations, use restrictions, and whether model outputs may be used to train another model. The latter remains **not verified** by default, even when the weights carry a permissive license. A model-card license tag is discovery metadata, not legal approval.

## Compute availability evidence

Run `python evaluation/probe_compute.py --output artifacts/compute/observation.json` inside the actual provider session. The probe captures the hardware visible to the process. It cannot authenticate the account, read private quota dashboards, prove regional eligibility, or guarantee another session. Generic hardware observations must never be represented as provider-account availability.

For each provider, maintain a separate account-level record containing:

- Provider, account owner/identifier (never commit secrets), country/region and verification state.
- Whether the account is eligible, the workload is permitted, and access depends on a trial, quota or time-limited offer.
- Successful session start timestamp and observed accelerator model/count/VRAM.
- Quota remaining before and after the run, reset policy, maximum session duration, idle timeout, queue wait and observed interruption.
- Storage, persistent volume, egress, download and model-cache limits.
- Provider terms URL, capture timestamp and the exact execution access condition verified.
- Workload restrictions and whether model inference, benchmarking, fine-tuning and long-running jobs are permitted.
- Evidence of account-level execution access and confirmation that no unverified fallback path was used.

Only mark a resource **verified available** after an eligible account actually starts a session and a workload probe succeeds. Use **conditional** for queue, quota or account-dependent offers; **unverified** when only public marketing documentation exists; **unavailable** when an attempted session cannot start. Do not assume a provider label guarantees access, duration, workload permission or usable capacity.

## Benchmark protocol

The checked-in `prime_benchmark_v1.jsonl` and `prima_benchmark_v1.jsonl` are public starter qualification sets. They are not secret holdouts: public fixtures can leak into model training. Keep a separately controlled, access-restricted holdout set outside the public repository and record its cryptographic hash in each evaluation run. Never train on benchmark answers.

Before comparing actual checkpoints:

1. Snapshot every candidate at an immutable revision and preserve its model card/license evidence.
2. Confirm tokenizer, chat template, architecture, serving parser and exact server version.
3. Verify the serving process loaded the same immutable checkpoint revision recorded in the experiment; operator-supplied labels alone are insufficient.
4. Run the same prompt suite, decoding parameters, context settings and repeated trials for each candidate.
5. Grade with blinded evaluators using the case rubrics; retain raw outputs, evaluator/version, per-case scores and disagreements.
6. Report per-category results, confidence intervals, repeated-run variance, refusals, invalid tool calls and failures. Do not collapse everything into one score without publishing the dimensions.
7. Measure peak VRAM/RAM, time-to-first-token, output tokens/sec, throughput, concurrency, cold-start time and actual zero-cost quota consumed.
8. Run a bounded adapter compatibility test: model load, tokenizer consistency, target-module discovery, tiny LoRA/QLoRA step, adapter save/reload and deterministic inference check. This is a compatibility test, not student training.
9. Select Prime and Prima independently against their own minimum gates.

## Teacher appointment gate

A teacher is not qualified by family name, model-card claim or benchmark result alone. For each student, qualify at least four distinct exact checkpoints. Each teacher must pass identity/revision, license, training-output permission, role-relevant quality, latency/resource fit, and output provenance checks. Every teacher must contribute accepted examples with per-teacher counts and competency coverage. Keep teacher rosters replaceable through registry records; do not couple student architecture to a teacher family.

## Stop conditions

- No verified zero-cost GPU session: record not currently testable; do not call paid APIs.
- Missing immutable revision: reject snapshot.
- Missing or ambiguous license evidence: block appointment.
- Unverified training-output permission: block use as a distillation teacher.
- No controlled held-out evaluation: no foundation selection.
- Fewer than four qualified teachers for a student: no distillation run.
- No explicit approval for paid resources: no paid fallback.
- Any student depends on teachers at inference: release blocked.

## Current implementation boundary

Catalog search and evidence-preserving metadata snapshots are automated. Provider-account quota/eligibility verification still requires a real provider session and account evidence; the generic compute probe does not provide it. This repository does not yet claim actual candidate inference comparisons, hidden-holdout results, or training compatibility. Do not select foundations or start student training until those gates are satisfied.
