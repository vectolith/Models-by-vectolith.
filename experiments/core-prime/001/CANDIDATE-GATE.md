# Candidate evidence and training authorization gate — Experiment 001

This is an evidence checklist, not an approval. Do not mark a gate passed based on metadata alone.

## Candidate identity and artifacts
- [ ] Confirm exact upstream repository and immutable commit SHA against upstream API.
- [ ] Capture license text at the pinned revision; hash the actual downloaded license bytes; store a relative evidence path and match the hash during preflight.
- [ ] Capture separate written output-training/distillation permission and independent legal-review artifacts, paths and SHA-256 hashes.
- [ ] Capture model configuration, tokenizer files and chat template hashes.
- [ ] Record the complete model artifact inventory; record hashes where obtainable.
- [ ] Review remote code and dependency requirements. Avoid remote-code execution unless explicitly reviewed and approved.
- [ ] Confirm architecture and target module compatibility with the intended LoRA implementation using a non-training inspection process.

## Permission and independent review
- [ ] Written output-generation permission is explicit and applicable to this candidate and use; its artifact path/hash is recorded and verified at preflight.
- [ ] Independent human legal review records its reviewer, date, scope, sources and decision.
- [ ] The weight license and generated-output training permission are evaluated separately.
- [ ] Do not infer permission from an open weights license or model-card statement alone.

## Data provenance
- [ ] Training-only dataset, distinct from development and sealed holdout.
- [ ] Per-record source/provenance and rights reviewed.
- [ ] Dataset file hash computed from exact bytes and matched in authorization.
- [ ] Data minimization, privacy and removal obligations reviewed.
- [ ] Dataset validation passes; duplicates and leakage reviewed.

## Compute and authorization
- [ ] Provider and session evidence verifies genuinely free, permitted compute.
- [ ] No paid resource, trial, quota circumvention or account rotation.
- [ ] Session GPU and memory are actually observed; not assumed from notebook settings.
- [ ] Operator authorization binds candidate revision, dataset hash, code commit, budgets and holdout policy.
- [ ] Total cumulative step/time budget and recovery budget explicitly defined.
- [ ] Holdout remains inaccessible.

## Decision
Training is blocked until every required item above is evidenced, independently reviewed where indicated and approved. The validator and authorization file alone do not establish authenticity of evidence.
