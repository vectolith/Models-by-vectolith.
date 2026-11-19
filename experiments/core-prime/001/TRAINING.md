# Guarded LoRA trainer

Training is intentionally blocked unless the candidate manifest and independent authorization evidence pass. Candidate status must be verified; output-training permission verified; human legal review approved; compatibility compatible. Authorization must match exact candidate revision, dataset SHA-256 and code commit, include hashed evidence files for license, written output permission, independent legal review, model config, chat template, dataset provenance and free-compute session, document budgets, and keep holdout sealed/denied. Preflight checks evidence file hashes and confines relative paths to the evidence directories. Operator must also pass --authorize-training. No CPU or paid compute.

Dataset is a separate JSONL file of records with task_id, prompt, response, provenance and split=train only. Development/holdout records are rejected. Do not reuse the development evaluation set as training material.

Install PEFT alongside the harness dependencies in the verified environment. Example:
```bash
python experiments/core-prime/001/train_lora.py --candidate candidate.json --authorization training-authorization.json --dataset train.jsonl --output /kaggle/working/cp001-adapter --max-steps 100 --max-wall-seconds 1800 --code-commit FULL_SHA --authorize-training
```
The authorization file is controlled evidence, not a generated approval. Example pending fields are intentionally insufficient. The runner emits an adapter and SHA-256 inventory. Evaluation, holdout use, grading, and promotion are separate.


The training loop starts its wall-clock budget before model/tokenizer initialization, refuses to start training if that budget has already expired, and stops at the approved ceiling (or earlier if the step budget is reached). Every Trainer checkpoint is sealed with an SHA-256 inventory after saving; recovery requires the manifest, exact file inventory and hashes and falls back only to a valid sealed checkpoint. Training manifests capture a sorted full package/version inventory and its hash.

## Evaluation configuration freeze

Before baseline or post-training evaluation, prepare an evaluation freeze manifest based on `evaluation-freeze.template.json`. Bind the exact immutable model revision, exact task-file SHA-256, seed, generation settings, remote-code policy, limit and selected-task IDs hash/count. The evaluator requires `--freeze-manifest` and compares all bound fields before model initialization. It records the manifest SHA-256 and selected-task hash/count in the run summary, including dependency-blocked runs. Negative limits and non-finite temperatures are rejected. Holdout split is blocked regardless of the deprecated `--allow-holdout` option. Do not evaluate protected holdout with this runner.


Candidate preflight now binds the SHA-256 of the exact candidate-record file and the pre-import installed package inventory, checks that the `--code-commit` matches the Git checkout, and requires a fully hash-verified staged model snapshot. Training uses that local snapshot only (`local_files_only=True`, remote code disabled); it does not fetch model files during the authorized run. The snapshot inventory must enumerate every file in the staged snapshot. Authorization is pending until those values and evidence are independently verified.
