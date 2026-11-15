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
- The candidate ID and revision are metadata supplied by the operator; they are not independently verified by the runner.
- Keep evaluation suites held out from training. Do not add benchmark answers to training data.
- Do not expose the endpoint publicly without authentication and network controls.

## Suites

The included files are smoke fixtures to validate the execution path and rubrics, not a release benchmark. Expand them with licensed, provenance-tracked, held-out datasets before making a foundation decision.

## Tests

```bash
python -m unittest discover -s evaluation/tests -v
```
