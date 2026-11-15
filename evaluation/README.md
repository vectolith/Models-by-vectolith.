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

CI downloads Qwen3-0.6B at an immutable revision and runs both public Prime and Prima smoke suites through the real tokenizer and model using Transformers on CPU. It records raw outputs, prompt hashes, rubric text, input/output token counts, per-case latency, runtime versions, architecture and peak RSS. These public smoke fixtures are execution-path checks, not secret holdouts and not a capability score. This is not a comparison across model families, a GPU/free-provider test, or training.

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

`fixtures/real_cpu_candidates_v1.json` pins exact immutable revisions for Qwen3-0.6B, Qwen3-4B, IBM Granite 3.1 3B-A800M, Ministral 3B, and a gated Gemma 3-270M candidate. CI downloads and runs every ungated checkpoint sequentially on one GitHub-hosted CPU runner. This avoids comparing throughput across separate runner machines. The gated Gemma entry is explicitly recorded as skipped; no access gate is bypassed.

`run_real_candidate_eval.py` records download time, model-load time, generation time, checkpoint disk size, per-case latency and token counts, CPU capability, visible CPU count, peak process memory, immutable revision, runtime versions and raw model outputs. `summarize_real_candidate_results.py` creates JSON and Markdown reports from those real artifacts. The report intentionally does not invent a capability score or quality ranking.

This remains an execution/resource comparison, not a foundation selection. The run uses CPU only and does not predict GPU performance or establish free GPU-provider access. Public smoke-suite outputs require independent rubric grading and are not a hidden holdout.

Every candidate remains `license_review=pending_human_legal_review`, `training_output_permission=not_verified`, and `teacher_qualification=not_qualified`. No student training is performed.


## Independent human grading

Raw outputs are never automatically treated as quality scores. Use [`docs/independent-human-rubric-grading.md`](../docs/independent-human-rubric-grading.md) for the human grading protocol and `summarize_human_grades.py` to validate independent rubric grades and produce per-criterion evidence summaries. The report never makes a foundation or teacher qualification decision.


## Expanded competency suites and private holdout

- `fixtures/prime_qualification_v2.jsonl`: 20 additional Core Prime public cases with explicit competency rubrics.
- `fixtures/prima_qualification_v2.jsonl`: 21 additional Core Prima public cases with explicit competency rubrics.
- Public fixtures are not hidden holdouts and do not qualify teachers by themselves.
- `run_private_holdout.py` runs an externally mounted, hash-pinned, access-restricted suite and writes raw outputs outside the public checkout. See [private holdout operations](../docs/private-holdout-operations.md).
- No private prompts, answer keys or holdout data are committed to this public repository.


## Balanced qualification suites v3

The v3 public suites add four independently worded cases per competency category. Combined with benchmark v1 and qualification v2, the validator requires at least five cases in every category and globally unique case IDs:

- `fixtures/prime_qualification_v3.jsonl`: 92 additional Core Prime cases across 23 competencies.
- `fixtures/prima_qualification_v3.jsonl`: 80 additional Core Prima cases across 20 competencies.
- Run `python -m unittest evaluation.tests.test_balanced_qualification_v3 -v` to validate category coverage and fixture integrity.

These are public development/evaluation fixtures, not a secret holdout. The v3 suites have now been executed against four pinned CPU candidates in both roles (eight candidate/role runs); raw outputs and resource records are preserved as workflow artifacts. The outputs have not been independently human-graded. Fixture validation establishes schema and coverage only; successful inference establishes execution, not model qualification.
