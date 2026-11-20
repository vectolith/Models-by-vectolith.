# Source-backed repository audit — 2026-11-20

Scope: source-level inspection of the live `main` snapshot at commit `8d501088a8efba8acd7b5b50c64bd3d20f627be8`. This is a focused audit, not a claim that every file or deployment has been exhaustively verified. Protected holdout contents were not inspected.

## Implemented source areas

- Runtime contracts and lifecycle: `runtime/vectolith_runtime/contracts.py`, `engine.py`, `runtime/tests/test_runtime.py`.
- Registry, capability discovery and dispatch: `registry.py`, `dispatch_policy.py`, persistence `persistence.py`, tests in `runtime/tests/`.
- Model loader allowlist and execution: `loading.py`; manifests are not used for arbitrary code imports.
- Compute probe: `compute_probe.py`; hardware and environment observations, not proof of capacity.
- Teacher qualification and corpus generation: `teacher_pipeline.py`; qualifications remain gated by independent review and permissions.
- Dataset splitting and tokenization: `distillation_training.py`; deterministic prompt-group split and response-only loss masking.
- Holdout evidence validators: `protected_holdout.py`; validates evidence metadata/results, not holdout truth or custody by itself.
- Training preflight: `training_preflight.py`; evidence checks precede training dependencies.
- Experiment trainer and release evidence verifier: `experiments/core-prime/001/train_lora.py`, `evaluation_gate.py`, `verify_release_bundle.py`.
- Evaluation observation runner: `evaluation/run_eval.py`; captures outputs and provenance but is not itself independent semantic grading.

## Verified limitations / risks

1. Runtime is a reference orchestration implementation with an in-memory task store; durable task recovery is not demonstrated by that store.
2. Dispatch policy is deterministic and currently selects lexicographically, rather than using measured ranking/optimization.
3. Model loader infrastructure is adapter-dependent; successful real model deployment/inference for released family members was not verified.
4. Teacher endpoint response handling was identified as unbounded at the HTTP body read. A proposed hard limit is in PR #92.
5. TaskStore result-state integrity and reviewer truthiness were identified as hardening opportunities. Proposed fixes and regression tests are in PR #91.
6. The evaluation harness records observations; quality claims require appropriate criterion verifiers, independent grading and human review.
7. Holdout validators enforce metadata/evidence requirements. They do not independently establish that custody, reviewers, permissions or attestations are real.
8. The training and release pipeline remains blocked by real-world approval/evidence requirements; passing software validators is not a substitute for those requirements.

## External training/release blockers

- Independent grading of the required 900 teacher responses.
- Written, verifiable teacher output-training permissions and appropriate legal review.
- Foundation-model selection and approval based on evaluation.
- Approved provenance-checked dataset and corpus integrity.
- Protected holdout custody, leakage audit and independent evaluation; the protected data itself remains sealed.
- Legitimately free compute and measured capacity.
- Final training approval and successful preflight.

## CI observations

The repository has separate workflows for runtime/evaluation, experiment harness tests, teacher/candidate inference/qualification and capability-registry checks. This report does not claim that all workflow paths or model-serving integrations were exercised in this audit.

## Scope limitations

No model training, paid services, paid compute, paid APIs or holdout access were initiated. No legal or human-review attestations were fabricated. This report is an audit artifact for tracking and is not release approval.
