# Core Prime grading engine

This package separates deterministic criterion checks, local semantic grading, artifact ingestion and response-coverage verification. The grading path is **local-only and offline**: it does not call a hosted model API, transmit candidate responses to an inference provider, use credentials, or start training.

Every grade record binds the inference run, candidate ID and immutable revision, source artifact SHA-256, case ID, exact response SHA-256, canonical rubric SHA-256, rubric version, grader identity/version, criterion decisions, evidence excerpts, rationale and timestamp. Preserve raw grade JSONL, blinded request batches and grade ledgers in restricted evidence storage. Keep the candidate identity map and extracted responses outside Git.

## Deterministic and semantic grading

The deterministic engine runs only rubric objects that explicitly declare a supported check: `exact_match`, `decimal`, `max_words`, `min_words`, `bullet_count` or `required_literal`. Natural-language criteria are evaluated by the pinned local semantic grader. Unsupported or insufficiently evidenced criteria remain unscored and block a complete Grading report.

The semantic grader is pinned in [`local-grader-lock.json`](local-grader-lock.json):

- Model: `Qwen/Qwen3.5-2B`
- Immutable Hub revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- Published model-card license: Apache-2.0; exact-revision license capture and legal review remain pending.
- Runtime: Transformers 5.23.0 and CPU-only PyTorch; remote code disabled.
- Prompt: `core-prime-semantic-grader-v2-local`
- No remote endpoint, credential or model substitution.

This is a **provisional evaluation judge**, not a selected Vectolith foundation, teacher or training target. Its quality and CPU workload must be checked on the 30-response pilot before processing the remaining 870. A pilot mismatch or runtime failure must be recorded and investigated; do not silently change the grader. The model is not being used to generate student training examples.

## Execution target and runtime validation

The current CI job uses `ubuntu-latest`; GitHub documents the standard runner as 4 CPU, 16 GB RAM and 14 GB SSD. The exact Qwen workload has been smoke-tested on CPU with one synthetic request; the 30-response Run 42 pilot remains unexecuted. If it cannot load or complete within the runner's execution limits, stop and retain the Grading gate as pending. Do not silently substitute a different model or remote endpoint.

Official references:
- GitHub public-runner terms and hardware: https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
- Qwen3.5-2B model card at the pinned revision: https://huggingface.co/Qwen/Qwen3.5-2B/tree/15852e8c16360a2fea060d615a32b45270f8a8fc

Install the CPU-only local grader dependencies:

```bash
python -m pip install -r evaluation/requirements-local-grader.txt
```

The model is retrieved from its public Hugging Face repository at the immutable revision. No Hugging Face token is required for this public checkpoint. The runner verifies the lock, disables remote code, verifies each response digest, rejects silent input truncation, requires strict JSON, checks exact rubric coverage and validates every evidence excerpt against the original response.

## Run 42

Download the five original GitHub Actions ZIP artifacts into a restricted local workspace. Verify the SHA-256 values in the Run 42 artifact integrity audit. Keep ZIPs, extracted candidate responses, semantic request batches, identity maps and grade ledgers outside Git. The CLI refuses an output directory inside the repository checkout.

Example artifact arguments (use the exact Run 42 candidate IDs):

```text
--artifact granite-3.1-3b-a800m=/secure/run42/granite31.zip
--artifact granite-4.2-3b=/secure/run42/granite42.zip
--artifact minicpm5-2b=/secure/run42/minicpm5.zip
--artifact lfm2.5-2.6b=/secure/run42/lfm25.zip
--artifact phi-4-mini-instruct=/secure/run42/phi4.zip
```

**Phase 1 — grade the 30-response pilot first.** Prepare the 30 blinded requests:

```bash
python evaluation/grading/grade_run42.py \
  --phase pilot --out-dir /secure/run42/grading \
  --artifact granite-3.1-3b-a800m=/secure/run42/granite31.zip \
  --artifact granite-4.2-3b=/secure/run42/granite42.zip \
  --artifact minicpm5-2b=/secure/run42/minicpm5.zip \
  --artifact lfm2.5-2.6b=/secure/run42/lfm25.zip \
  --artifact phi-4-mini-instruct=/secure/run42/phi4.zip
```

Run the local grader on the pilot batch:

```bash
python evaluation/grading/local_semantic_grader.py \
  --input /secure/run42/grading/pilot/requests/batch-001.jsonl \
  --output /secure/run42/pilot-decisions.jsonl
```

Import the decisions to create 30 evidence-bound grade records and compare the new candidate/case aggregates with the historical pilot reference:

```bash
python evaluation/grading/grade_run42.py \
  --phase pilot --out-dir /secure/run42/grading \
  --decisions /secure/run42/pilot-decisions.jsonl \
  --grader-id local/Qwen/Qwen3.5-2B \
  --grader-version 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --graded-at 2026-11-17T00:00:00Z \
  --artifact granite-3.1-3b-a800m=/secure/run42/granite31.zip \
  --artifact granite-4.2-3b=/secure/run42/granite42.zip \
  --artifact minicpm5-2b=/secure/run42/minicpm5.zip \
  --artifact lfm2.5-2.6b=/secure/run42/lfm25.zip \
  --artifact phi-4-mini-instruct=/secure/run42/phi4.zip
```

Use the actual UTC grading timestamp. The historical pilot report contains aggregate scores but no 30 criterion-level grade records. The new engine therefore re-grades these 30 cases, creates criterion-level records, and compares the new aggregates with the historical reference. A mismatch is reported, not silently normalized. Review the comparison before continuing.

**Phase 2 — process the remaining 870.** Reuse the same output directory, exact model revision and prompt. Prepare the remaining 870 only after reviewing the pilot report:

```bash
python evaluation/grading/grade_run42.py \
  --phase remaining \
  --pilot-report /secure/run42/grading/pilot/run42-grading-population-report.json \
  --confirm-pilot-review \
  --pilot-review-note "Reviewed the local-grader pilot comparison; documented the observed differences and approved continuation." \
  --grader-id local/Qwen/Qwen3.5-2B \
  --grader-version 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --out-dir /secure/run42/grading \
  --artifact granite-3.1-3b-a800m=/secure/run42/granite31.zip \
  --artifact granite-4.2-3b=/secure/run42/granite42.zip \
  --artifact minicpm5-2b=/secure/run42/minicpm5.zip \
  --artifact lfm2.5-2.6b=/secure/run42/lfm25.zip \
  --artifact phi-4-mini-instruct=/secure/run42/phi4.zip
```

Grade each of the 29 candidate-balanced batches of 30 with the same local command, then concatenate the resulting decision JSONL files in batch order and import them using the same `--phase remaining` arguments plus `--decisions /secure/run42/remaining-decisions.jsonl` and the actual UTC `--graded-at` timestamp. The CLI verifies the completed pilot report, exact artifact hashes and unchanged grader/prompt versions before accepting the remaining phase.

The historical 30-response pilot did not preserve criterion-level records; it is a comparison reference, not ground truth. This machine-assisted grading engine is not the independent human qualification gate and cannot satisfy it. Core Prime qualification requires two distinct independent human reviewers, complete response coverage, reviewer-independence attestation, agreement and adjudication evidence. Specialized factuality, executable code verification, safety review, protected holdout and corpus-integrity evidence remain separate gates.

## Tests

```bash
python -m unittest evaluation.tests.test_grading_engine evaluation.tests.test_local_semantic_grader -v
```

A complete Grading report does not qualify a teacher, approve a foundation, grant teacher-output training permission or authorize training.
