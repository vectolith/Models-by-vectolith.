# Executable baseline harness

This directory contains a minimal real inference and task-validation CLI. The example JSONL record is a harness smoke-test fixture, not a benchmark, training example, or evaluation evidence.

## Requirements and setup
Use a disposable environment and install the requirements listed here. Hardware availability is determined at runtime.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r experiments/core-prime/001/requirements.txt
```

## Validate task files
```bash
python experiments/core-prime/001/validate_tasks.py tasks.jsonl
```

Task JSONL records require task_id, category, prompt, split, rubric_id, and provenance. Keep holdout data isolated and do not pass it to evaluation until the run configuration is frozen.

## Run a baseline
```bash
python experiments/core-prime/001/evaluate.py \
  --model MODEL_REPOSITORY_OR_LOCAL_PATH \
  --revision IMMUTABLE_REVISION_SHA \
  --tasks tasks.jsonl \
  --output experiment-results \
  --max-new-tokens 256
```

Use an immutable revision, not a moving tag. On a Hub model, the revision must be the full commit hash. For a local model path, provide a stable identifier for the revision/artifact in the run record; local path handling does not itself verify provenance. If remote custom model code is required, enable it only after reviewing it, using `--trust-remote-code`.

Holdout inference is blocked by default. After the run configuration is frozen, use `--allow-holdout` for an authorized holdout run. This flag is not a substitute for access controls; holdout files must be protected operationally.

The evaluator records prompt and response hashes, raw outputs, token counts, timing, software versions, device and hardware, task-file hash and run status. It does not grade responses or select/promote models. Raw results are sensitive if prompts contain private data; keep datasets public or appropriately secured and never commit private prompts, credentials or outputs.

This initial harness is a bounded baseline tool, not a production evaluator: it does not yet implement schema-level candidate manifest validation, robust model-specific chat templates, multi-GPU benchmarking, independent grading, dataset leakage detection, GPU peak-memory instrumentation, or automated statistical comparison. Those remain subsequent engineering tasks.
