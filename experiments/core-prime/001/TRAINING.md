# Guarded LoRA trainer

Training is intentionally blocked unless the candidate manifest and independent authorization evidence pass. Candidate status must be verified; output-training permission verified; human legal review approved; compatibility compatible. Authorization must match exact candidate revision, dataset SHA-256 and code commit, document verified free GPU provider/session and budgets, and keep holdout sealed/denied. Operator must also pass --authorize-training. No CPU or paid compute.

Dataset is a separate JSONL file of records with task_id, prompt, response, provenance and split=train only. Development/holdout records are rejected. Do not reuse the development evaluation set as training material.

Install PEFT alongside the harness dependencies in the verified environment. Example:
```bash
python experiments/core-prime/001/train_lora.py --candidate candidate.json --authorization training-authorization.json --dataset train.jsonl --output /kaggle/working/cp001-adapter --max-steps 100 --max-wall-seconds 1800 --code-commit FULL_SHA --authorize-training
```
The authorization file is controlled evidence, not a generated approval. Example pending fields are intentionally insufficient. The runner emits an adapter and SHA-256 inventory. Evaluation, holdout use, grading, and promotion are separate.


The training loop also installs a wall-clock callback and stops at the approved runtime ceiling (or earlier if the step budget is reached).

## Evaluation configuration freeze

Before baseline or post-training evaluation, prepare an evaluation freeze manifest based on `evaluation-freeze.template.json`. Bind the exact immutable model revision, exact task-file SHA-256, seed, generation settings, remote-code policy, limit and selected-task IDs hash/count. The evaluator requires `--freeze-manifest` and compares all bound fields before model initialization. It records the manifest SHA-256 and selected-task hash/count in the run summary, including dependency-blocked runs. Negative limits and non-finite temperatures are rejected. Holdout split is blocked regardless of the deprecated `--allow-holdout` option. Do not evaluate protected holdout with this runner.
