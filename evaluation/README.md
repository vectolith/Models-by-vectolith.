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


## Unified Core Prime curriculum v4

- `fixtures/prime_qualification_v4.jsonl`: 56 additional public cases across 14 competencies covering coding generation, debugging, code review, software architecture, testing, algorithms, data analysis, technical mathematics, tool calling, agentic planning, state recovery, research evidence, long-context retrieval, multilingual translation, security/privacy, safety policy, adversarial robustness, reliability calibration and technical documentation.
- `tests/test_core_prime_qualification_v4.py` validates category counts, rubric presence and unique IDs.
- The Prime multi-teacher inference workflow now includes v4 for every active teacher. All raw outputs, including failures and truncated answers, remain preserved.
- See [the v4 curriculum and proposed gates](core-prime-evaluation-curriculum-v4.md) and [additional teacher discovery register](additional-teacher-candidates-2026-11-16.md).
- The new teacher candidates are discovery-only until exact snapshots, compatibility tests, resource measurements, independent human grading and separate training-output permission review are complete.
- v4 is a public development suite, not a private holdout. No v4 responses or answers may be used for training.


## Sequential additive Prime teachers: immutable snapshot + inference

`snapshot_additional_teacher.py` resolves a public Hub model's current revision to a full immutable commit SHA, downloads that exact revision, validates the expected architecture and license identifier, and emits a manifest containing the complete file inventory, byte sizes and SHA-256 hashes. The manifest includes the Hub revision, config and license-file hashes. The workflow then passes that exact SHA to `run_real_candidate_eval.py`; it never runs inference against a moving `main` ref.

The workflow `.github/workflows/expanded-qualification-inference.yml` runs the full six-teacher chain sequentially: Granite 3.1 → Granite 4.2 → MiniCPM5 → SmolLM3-3B → LFM2.5-2.6B → Phi-4-mini-instruct, each over the same Prime public v1-v4 fixtures and the same deterministic generation cap. Per-candidate manifests, raw JSON/JSONL outputs, logs and compute observations are uploaded as separate artifacts. The actual model snapshot stays in the ephemeral runner cache; model weights are not committed to Git or copied into large CI artifacts. Re-fetching the recorded SHA and validating its file hashes reproduces the same snapshot.

Phi-4 is loaded with `trust_remote_code=False`; the pipeline will not execute model-repository Python code. A load failure is retained as evidence and does not silently relax this security boundary. LFM2.5's LFM Open License requires legal review, and its publisher notes it is not recommended for agentic coding or knowledge-heavy tasks. All training-output permissions remain unverified. No model is qualified and no training is performed by this workflow.

Run the snapshot registry tests with:

```bash
python -m unittest evaluation.tests.test_additional_teacher_snapshots -v
```

A passing unit test validates registry guardrails only. Actual loader compatibility, model generation, revision pinning and file hashes are established only by the real workflow artifacts.


## Verified Core Prime multi-teacher run 40 evidence

The 2026-11-16 run 40 evidence record contains the five successful real-response artifacts, the SmolLM3 snapshot-gate failure, exact immutable revisions, per-case provenance checks, suite counts, token-cap counts, hardware observations and SHA-256 digests. These artifacts are execution evidence only; no model is qualified and no generated output is authorized for training. See [Core Prime multi-teacher run 40 evidence](core-prime-multi-teacher-run-40-evidence-2026-11-16.md).


## Blinded Core Prime human review

The run 40 five-artifact evidence set contains 900 raw responses across the three existing additive teachers and two discovery-only candidates, including 56 v4 prompts per candidate. Build reviewer-specific, identity-separated packages and validate/unblind complete independent submissions with:

\`\`\`bash
python evaluation/prepare_blinded_human_review.py build --help
python evaluation/prepare_blinded_human_review.py unblind --help
\`\`\`

The builder verifies immutable artifact ZIPs, JSON/JSONL parity, provenance, exact suite coverage, and original rubric integrity. It writes separate reviewer ZIPs and a restricted private identity key that must never be shared with reviewers. The unblinding step requires at least two distinct evaluator IDs and complete grade coverage. Human grade summaries report pairwise weighted agreement but never make a teacher qualification decision. See [Core Prime blinded human-review operations](../docs/core-prime-blinded-human-review.md).


Additional verified follow-up artifacts from Core Prime runs 42 and 43 are recorded in [run 42/43 evidence](core-prime-multi-teacher-runs-42-43-evidence-2026-11-16.md). The blinded review builder supports repeated inference runs for the same candidate without overwriting or collapsing their provenance.


Human disagreement records are generated and validated separately with \`evaluation/prepare_human_adjudication.py\`; adjudication never overwrites the original reviewer grades. See the operations guide for the third-party adjudicator workflow.


## Fail-closed teacher qualification

Use `teacher_qualification_gates.py` to validate candidate evidence against ten independent gates and enforce the minimum four-teacher Core Prime cohort. Inference success is not qualification. Legal permission to use generated outputs for training is separate from the model-weight license. Human review requires two independent reviewers and completed adjudication; protected-holdout evidence, corpus integrity, safety, and resource evidence remain mandatory. The template is intentionally empty and no candidate is approved by default. See [Core Prime teacher qualification gates](../docs/core-prime-four-teacher-qualification.md).


## Controlled completion-budget study

The manual-only Core Prime completion study evaluates the same immutable candidates at 512, 768, or 1024 generated tokens while preserving per-response completion state (EOS, token-cap truncation, stopped-without-EOS, empty output, or error). It records one candidate per job, separate hardware observations, workflow provenance, raw outputs and hashes. It does not grade quality, rank candidates, or authorize training. Dispatch requires the workflow's explicit `confirm_study=true` input. See [completion-budget study protocol](../docs/core-prime-completion-budget-study.md).
