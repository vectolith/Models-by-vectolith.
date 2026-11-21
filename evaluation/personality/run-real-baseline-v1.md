# Running a real Core Prime character baseline (free/local)

The evaluation harness does not fake inference. Use a locally available model or a free notebook allocation; this script requires Python, PyTorch and Transformers, which are optional and are not added to project dependencies.

1. Select a model only after license, provenance, suitability and hardware review.
2. Install optional dependencies in a genuinely free environment. No paid API or hosted inference is used by this script.
3. Download/cache the model if the free environment permits; use `--offline` to require local assets.
4. Run:
   ```bash
   python scripts/generate_core_prime_eval_outputs.py --model /path/to/model --offline --output evaluation/runs/base-outputs.json
   ```
5. Candidate output format is a JSON object keyed by evaluation case ID, then condition name, then response text. The generator creates the response set; blind sheet generation requires exactly the two conditions per case.
6. Create the blind evaluator sheet and condition map in separate directories:
   ```bash
   python scripts/run_core_prime_blind_eval.py \
     --cases evaluation/personality/core-prime-evaluation-cases-v1.jsonl \
     --outputs evaluation/runs/base-outputs.json \
     --output evaluation/runs/evaluator-sheets \
     --map-output evaluation/runs/restricted-condition-map
   ```
   The condition order uses an unpredictable system-random permutation; there is no CLI seed. The sheet contains case IDs, prompts, rubric instructions and candidate responses, but not the condition names. The restricted map is created separately with POSIX directory/file permissions 0700/0600 and exclusive, no-follow writes where supported.
7. Give reviewers only the evaluator-sheet directory and the case/rubric material they need. Do not share the condition map, paired raw outputs, generator files or other information that could reveal candidate identity. Keep the map with the coordinator, not evaluators. A restricted map directory is not a substitute for separate reviewer access control.
8. After scoring, run `scripts/run_core_prime_blind_eval.py --scores scored.jsonl --output evaluation/runs/summary`. This produces a descriptive score summary; it does not establish independent review, statistical significance or model quality.

This is an inference adapter—not a model selection or training approval. Evaluation cases should be protected and not included in training. The present 30 cases are public draft examples; establish a separate, protected holdout before formal evaluation. Preserve output files, exact model revision, tokenizer, runtime and configuration for reproducibility. Do not use the current public draft cases for protected holdout evaluation.
