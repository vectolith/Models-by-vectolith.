# Executable baseline harness

This directory contains an inference CLI, JSONL task validator, candidate-record validator, and automated tests. The example JSONL record is a harness fixture, not benchmark, training data, or evaluation evidence.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r experiments/core-prime/001/requirements.txt
```

## Tests
```bash
python -m unittest discover -s experiments/core-prime/001/tests -v
```
Tests cover parsing, duplicate IDs, normalized prompt duplicates and cross-split leakage, prompt hash integrity, candidate checks, and evaluator input handling. They do not load a model.

## Task validation
```bash
python experiments/core-prime/001/validate_tasks.py tasks.jsonl
```
Records require task_id, category, prompt, split, rubric_id, provenance. Optional content_sha256 must match SHA-256 of the exact prompt UTF-8 bytes. Detects exact normalized prompt duplicates, including cross-split contamination; semantic or answer-level leakage is out of scope.

## Candidate validation
```bash
python experiments/core-prime/001/validate_candidate.py candidate.json
```
Requires a full 40-character lowercase commit SHA and validates fields, evidence hashes, and prerequisites for verified status. Structural validation is not independent verification of license, authenticity, or compatibility.

## Baseline inference
```bash
python experiments/core-prime/001/evaluate.py \
  --model MODEL_REPOSITORY_OR_LOCAL_PATH \
  --revision IMMUTABLE_REVISION_SHA \
  --tasks tasks.jsonl \
  --output experiment-results \
  --max-new-tokens 256
```
Use a pinned revision. For local model paths, the revision string is only recorded and provenance is not automatically authenticated. Remote custom code should only be enabled after review with `--trust-remote-code`.

Holdout inference is blocked by default; use `--allow-holdout` only after configuration freeze and proper access control. The evaluator records prompts/responses, hashes, tokens, timing, versions, device/hardware and run status. Raw data can be sensitive; avoid committing private content.

Remaining limitations: model-specific templates, multi-GPU benchmarking, independent grading, semantic leakage detection, GPU peak-memory instrumentation and statistical comparison.
