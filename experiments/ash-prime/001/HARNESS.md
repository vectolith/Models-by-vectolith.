# Executable baseline harness

This directory contains an inference CLI, JSONL task validator, candidate-record validator, and automated tests. The example JSONL record is a harness fixture, not benchmark, training data, or evaluation evidence.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r experiments/ash-prime/001/requirements.txt
# Training stack (only after authorization gates pass):
python -m pip install -r experiments/ash-prime/001/requirements-training.txt
```
The direct dependency versions are pinned. The full transitive dependency set is not yet hash-locked; capture and hash the resolved package inventory for each authorized run. The CI compatibility job installs the CPU PyTorch wheel and checks imports, exact direct versions and `pip check`; it does not load weights, run inference or train.


## Tests
```bash
python -m unittest discover -s experiments/ash-prime/001/tests -v
```
Tests cover parsing, duplicate IDs, normalized prompt duplicates and cross-split leakage, prompt hash integrity, candidate checks, and evaluator input handling. They do not load a model.

## Task validation
```bash
python experiments/ash-prime/001/validate_tasks.py tasks.jsonl
```
Records require task_id, category, prompt, split, rubric_id, provenance. Optional content_sha256 must match SHA-256 of the exact prompt UTF-8 bytes. Detects exact normalized prompt duplicates, including cross-split contamination; semantic or answer-level leakage is out of scope.

## Candidate validation
```bash
python experiments/ash-prime/001/validate_candidate.py candidate.json
```
Requires a full 40-character lowercase commit SHA and validates fields, evidence hashes, and prerequisites for verified status. Structural validation is not independent verification of license, authenticity, or compatibility.

## Baseline inference

The evaluator is gated: candidate artifact and permission evidence, independent legal-review evidence, a verified local snapshot, an authorization record tied to the exact task/freeze/code/package hashes, and genuine free-compute/session evidence must all be present before it imports ML runtimes or creates run outputs. The repository does not provide or infer those approvals.

```bash
python experiments/ash-prime/001/evaluate.py \\
  --model VERIFIED_REPOSITORY_ID \\
  --revision IMMUTABLE_REVISION_SHA \\
  --tasks tasks.dev.jsonl \\
  --output experiment-results \\
  --candidate-record candidate.json \\
  --authorization evaluation-authorization.json \\
  --freeze-manifest evaluation-freeze.json \\
  --code-commit "$(git rev-parse HEAD)" \\
  --max-new-tokens 256 \\
  --temperature 0
```

The model must be loaded from the verified local snapshot; network downloads and remote custom code are disabled. The `--qwen3-thinking` option is accepted only when the snapshot's verified `config.json` identifies a Qwen3-family model. The deprecated `--allow-holdout` flag cannot unlock holdout evaluation. Holdout inference is blocked by this harness.

Remaining limitations: model-specific templates, multi-GPU benchmarking, independent grading, semantic leakage detection, GPU peak-memory instrumentation and statistical comparison.
