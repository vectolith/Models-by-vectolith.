# Foundation evaluation runner

A dependency-free, provider-neutral runner for OpenAI-compatible `/v1/chat/completions` endpoints. It lets the same pinned prompt suites run against different foundation candidates and serving engines.

## Requirements

- Python 3.11+
- An already-running inference endpoint that implements OpenAI-compatible chat completions.
- A model revision pinned to an immutable commit/revision. The runner does not download weights, select models, or provision GPU resources.

## Run a smoke suite

Start the candidate's serving engine separately, then run:

```bash
python evaluation/run_eval.py \
  --suite evaluation/fixtures/prime_smoke.jsonl \
  --output artifacts/evaluations/prime-candidate-a.jsonl \
  --base-url http://localhost:8000/v1 \
  --model served-model-name \
  --role core_prime \
  --candidate-id provider/model-name \
  --revision IMMUTABLE_MODEL_REVISION
```

For Prima, change the suite and role to `core_prima`. If the endpoint requires authentication, set the key in an environment variable; the runner reads `VECTOLITH_INFERENCE_API_KEY` by default. Never put API keys in command-line arguments, fixture files, or repository files.

The output records raw response text, tool calls, refusal, finish reason, token usage, latency, prompt hash, candidate/revision metadata, and the human-evaluation rubric. It deliberately does not assign a model-quality score. Reviewers must grade outputs against the rubric, record evaluator identity/version, and retain the raw JSONL evidence.

## Evidence discipline

- Use the exact same fixture revision and generation settings for every candidate in a comparison.
- Pin model weights, tokenizer, server, parser, quantization, and runtime versions in the experiment record.
- Run repeated trials for variance; do not infer performance from a single response.
- Record hardware, peak memory, tokens/sec, time-to-first-token, concurrency, and cost separately. This basic runner measures per-request latency and returns provider-reported token usage only.
- The candidate ID and revision are metadata supplied by the operator; they are not independently verified by the inference runner. The discovery integration tests independently query Hugging Face and pin the revision returned by its API.
- Keep evaluation suites held out from training. Do not add benchmark answers to training data.
- Do not expose the endpoint publicly without authentication and network controls.

## Suites

- `fixtures/prime_smoke.jsonl` and `fixtures/prima_smoke.jsonl` validate the execution path only.
- `fixtures/prime_benchmark_v1.jsonl` and `fixtures/prima_benchmark_v1.jsonl` are broader public qualification suites. They are not secret holdouts and must not be treated as contamination-proof.
- Keep a separate access-restricted holdout dataset outside this public repository. Record its dataset version and SHA-256 in the experiment record; never train on its answers.

See [automated discovery and qualification](FOUNDATION_DISCOVERY.md) for immutable Hugging Face metadata snapshots, compute evidence, benchmark methodology, and teacher gates.

## Candidate and compute discovery

```bash
python evaluation/discover_hf_candidates.py \\
  --repo Qwen/Qwen3.5-9B \\
  --repo ibm-granite/granite-4.2-8b \\
  --repo google/gemma-4-E4B \\
  --repo mistralai/Mistral-Small-4-119B-2603 \\
  --output artifacts/candidates/huggingface-snapshot.jsonl

python evaluation/probe_compute.py --output artifacts/compute/observation.json
```

Catalog search returns discovery leads, not qualified candidates. Snapshots pin immutable revisions and retain exact retrieved license/model-card text, source URLs and SHA-256 hashes. Missing license evidence remains missing; legal suitability and training-output permission require human review. The compute probe reports process-visible hardware, not account quota, billing state or guaranteed free access. See `FOUNDATION_DISCOVERY.md` for the evidence and stop conditions.

## Tests

The ordinary unit suite uses deterministic fixtures for edge cases. The live integration suite makes real HTTPS requests to the public Hugging Face Hub, performs catalog searches, and snapshots a real public checkpoint's metadata/model card.

CI downloads exact immutable checkpoints and runs both public Prime and Prima smoke suites through the real tokenizer and models using Transformers on CPU. The candidate comparison runs sequentially on one GitHub-hosted CPU runner, so CPU model, CPU instruction capability, RAM, PyTorch and Transformers versions are verified identical before latency is compared. It records raw outputs, prompt hashes, rubric text, input/output token counts, per-case latency, architecture, dtype and peak RSS. These public smoke fixtures are execution-path checks, not secret holdouts and not a capability score. This is not a GPU/free-provider test or training.

Run the real checkpoint suite locally (requires torch, transformers, accelerate and network access):

```bash
python evaluation/run_real_checkpoint_suite.py \
  --suite evaluation/fixtures/prime_smoke.jsonl \
  --suite evaluation/fixtures/prima_smoke.jsonl \
  --max-new-tokens 64
```

```bash
python -m unittest discover -s evaluation/tests -v

# Run real public Hugging Face API integration tests (requires network access):
VECTOLITH_RUN_LIVE_TESTS=1 python -m unittest evaluation.tests.test_live_huggingface -v
```


## Real multi-family CPU comparison

`fixtures/real_cpu_candidates_v1.json` pins an initial comparison set: two Qwen sizes, one IBM Granite checkpoint and one Ministral checkpoint. CI loads each exact revision sequentially on the same GitHub-hosted CPU runner, uses BF16, and runs the same Prime/Prima smoke fixtures. The matrix runner verifies identical CPU model/capability, core count, system RAM, PyTorch and Transformers versions, plus identical case IDs and prompt hashes, before it marks latency metrics comparable. Raw outputs, token counts, latency, runtime/model metadata and peak RSS are uploaded as one comparison artifact.

This is a constrained execution comparison, not a foundation selection. It measures CPU execution only and does not predict GPU latency. Gemma is discovered but not included in this run because the selected official Gemma checkpoints are manually gated; no account acceptance or access token is available to this workflow. A gated model must not be bypassed.

Every candidate remains `license_review=pending_human_legal_review`, `training_output_permission=not_verified`, and `teacher_qualification=not_qualified`. Public smoke-suite outputs require independent rubric grading and are not a hidden holdout. No student training is performed.
