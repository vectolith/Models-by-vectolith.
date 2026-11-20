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
- [ ] Every teacher used for data generation has a separate terms/rights record covering output collection and student distillation; a teacher's weights license alone is not a permission to train on its outputs.
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


## Additional reproducibility gates

- A verified candidate must have a staged local snapshot directory whose complete file inventory and hashes match the candidate record. Baseline evaluation loads that snapshot locally (`local_files_only`), not from an unverified live download.
- Authorization binds the candidate-record SHA-256, dataset SHA-256, exact Git HEAD, pre-import package inventory SHA-256 and genuinely free compute evidence. The actual checkout HEAD and package inventory are checked before ML imports.
- Baseline evaluation is development-split only. Holdout remains blocked. Evaluation authorization binds the freeze-manifest hash, candidate revision, selected task budget, output-token ceiling, wall-clock ceiling, free compute evidence and package inventory.
- These are integrity controls, not legal opinions or proof of evidence authenticity. Independent legal review and written output-training permission remain required.


A pending training authorization structure is provided in `training-authorization.template.json`; it is not a completed approval. The template must be populated only with real evidence and the actual free compute session details.


Use `capture_environment.py` to capture the checkout/package inventory and `capture_snapshot_inventory.py` to capture the staged snapshot's actual file inventory. Both are evidence-capture utilities only and cannot approve licensing, free compute or model qualification.
