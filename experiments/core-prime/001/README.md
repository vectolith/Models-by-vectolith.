# Core Prime Experiment 001 — foundation comparison and bounded fine-tuning

Status: experiment design / implementation track. No model is selected and no training is authorized by this plan.

## Objective
Compare exact, immutable small foundation-model revisions on a reproducible task suite; then fine-tune only the approved candidate and test for measurable task-level improvement.

## Phases
1. Candidate discovery and legal review. Capture exact Hub IDs/revisions, license and notices, output-use permissions (reviewed separately), gating, tokenizer/template, model config, weight inventory and hashes. A license label alone does not establish permission to use outputs as training data.
2. Compute feasibility. Measure available free hardware and runtime limits. Do not assume a Kaggle GPU quota or availability. No paid infrastructure, paid inference, trials, or quota circumvention.
3. Dataset preparation. Create training, development and protected holdout splits. Deduplicate and detect cross-split leakage. Record provenance and SHA-256 hashes. Holdout content and labels remain inaccessible to training and tuning.
4. Baseline evaluation. Run identical prompt templates and decoding settings across candidate revisions, record raw outputs and resource observations, and score each task separately. Repeat stochastic tasks where feasible.
5. Selection review. Select only with a documented evidence-backed decision; do not substitute checkpoints or quantization silently. Candidates that fail legal, access, compatibility, or resource checks remain blocked.
6. Bounded fine-tuning. Use a reviewed trainer/configuration, fixed seeds, adapter checkpoints and complete logs. Stop at declared budgets. No training job is started by this repository document.
7. Post-training evaluation. Evaluate base and tuned model against the same dev suite; run protected holdout only after the experiment configuration is frozen. Compare capability scores, regressions, validity, safety, latency, throughput and memory. Loss alone cannot qualify a model.
8. Report. Publish a run report, limitations, artifacts inventory and reproducibility instructions. Adapter publication and model promotion require separate approvals.

## Initial candidates
Candidates are discovery targets only; exact revisions and rights are pending. The existing foundation-selection policy and exact repository IDs govern candidate selection. Do not use this experiment to bypass that policy or alter the shortlist.

## Experiment budget
The first run is a bounded feasibility run, not a release training run. Before executing, record hardware/session evidence, wall-clock ceiling, storage and memory ceiling, dataset version, training steps/epochs and stop conditions. If any budget cannot be verified, stop and record the blocker.

## Minimum records
- Candidate manifest and revision/license evidence
- Dataset manifest and split hashes
- Baseline and post-training raw outputs
- Rubric and scorer version; blinded human grades where required
- Run config, seed, code commit, environment lock, hardware evidence
- Train/validation logs and adapter hashes
- Task-level comparison, failure analysis, regression and resource report

## Acceptance
A tuned candidate is an experiment result only. It is not Core Prime or a release unless separate promotion gates are passed.
