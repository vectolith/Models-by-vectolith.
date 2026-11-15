# Automated foundation discovery and qualification

## Current scope

The discovery script snapshots public Hugging Face metadata at an immutable commit SHA. It records the repository, revision, architecture, tags, license metadata, model-card hash, license-file hash, gating state, and weight-file inventory. It does not download weights or decide legal suitability. A human review must inspect the exact license text, linked terms, attribution obligations, use restrictions, and whether model outputs may be used to train another model. The latter is recorded as **not verified** by default, even when the weights carry a permissive license.

Run:

```bash
python evaluation/discover_hf_candidates.py \
  --repo Qwen/Qwen3.5-9B \
  --repo ibm-granite/granite-4.2-8b \
  --repo google/gemma-4-E4B \
  --repo mistralai/Mistral-Small-4 \
  --output artifacts/candidates/huggingface-snapshot.jsonl
```

A snapshot is time-stamped evidence. Re-run discovery to detect changed repository heads; do not overwrite an earlier snapshot when comparing results.

## Compute availability evidence

Run `python evaluation/probe_compute.py --output artifacts/compute/observation.json` inside the actual provider session. The probe captures the hardware visible to the process. It cannot authenticate the account, read private quota dashboards, prove regional eligibility, or guarantee another session. These fields remain explicitly unverified.

For each provider, maintain a separate account-level record containing:

- Provider, account owner/identifier (never commit secrets), country/region and verification state.
- Whether a payment card is required, whether billing activation is required, and whether any credit is promotional.
- Successful session start timestamp and observed accelerator model/count/VRAM.
- Quota remaining before and after the run, reset policy, maximum session duration, idle timeout, queue wait and observed interruption.
- Storage, persistent volume, egress, download and model-cache limits.
- Provider terms URL, capture timestamp and the exact no-cost entitlement used.
- Workload restrictions and whether model inference, benchmarking, fine-tuning and long-running jobs are permitted.

Only mark a resource **verified available** after a real session starts and a workload probe succeeds. Use **conditional** for queue/quota/account-dependent offers; **promotional** for credits or trials; **unverified** when only public marketing documentation exists. A zero-cost claim requires a zero charge and no billing-enabled fallback. If a provider requires billing activation, it is not eligible for the strict no-budget pool.

## Benchmark protocol

The checked-in `prime_benchmark_v1.jsonl` and `prima_benchmark_v1.jsonl` are public qualification sets with task diversity. They are not secret holdouts: public fixtures can leak into model training. Keep a separately controlled, access-restricted holdout set outside the public repository and record its cryptographic hash in each evaluation run. Never train on benchmark answers.

Before comparing actual checkpoints:

1. Snapshot every candidate at an immutable revision and preserve its model card/license evidence.
2. Confirm tokenizer, chat template, architecture, serving parser and exact server version.
3. Run the same prompt suite, decoding parameters, context settings and repeated trials for each candidate.
4. Grade with blinded evaluators using the case rubrics; retain raw outputs and per-case scores.
5. Report per-category results, confidence intervals, repeated-run variance, refusals, invalid tool calls and failures. Do not collapse everything into one score without publishing the dimensions.
6. Measure peak VRAM/RAM, time-to-first-token, output tokens/sec, throughput, concurrency, cold-start time and actual zero-cost quota consumed.
7. Run a bounded adapter compatibility test: model load, tokenizer consistency, target-module discovery, tiny LoRA/QLoRA step, adapter save/reload and deterministic inference check. This is a compatibility test, not student training.
8. Select Prime and Prima independently against their own minimum gates and weighted scorecards.

## Teacher appointment gate

A teacher is not qualified by family name, model-card claim or benchmark result alone. For each student, qualify at least four distinct exact checkpoints. Each teacher must pass identity/revision, license, training-output permission, role-relevant quality, latency/resource fit, and output provenance checks. Every teacher must contribute accepted examples with per-teacher counts and competency coverage. Keep teacher rosters replaceable through registry records; do not couple student architecture to a teacher family.

## Stop conditions

- No free GPU session: record not currently testable; do not call paid APIs.
- Missing immutable revision: reject snapshot.
- Missing or ambiguous license evidence: block appointment.
- Unverified training-output permission: block use as a distillation teacher.
- No held-out evaluation: no foundation selection.
- Fewer than four qualified teachers for a student: no distillation run.
- No explicit approval for paid resources: no paid fallback.
- Any student depends on teachers at inference: release blocked.
