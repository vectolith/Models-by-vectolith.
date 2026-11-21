# Running a real Core Prime character baseline (free/local)

The evaluation harness does not fake inference. Use a locally available model or a free notebook allocation; this script requires Python, PyTorch and Transformers, which are optional and are not added to project dependencies.

1. Select a model only after license, provenance, suitability and hardware review.
2. Install optional dependencies in a genuinely free environment. No paid API or hosted inference is used by this script.
3. Download/cache the model if the free environment permits; use `--offline` to require local assets.
4. Run:
   ```bash
   python scripts/generate_core_prime_eval_outputs.py --model /path/to/model --offline --output evaluation/runs/base-outputs.json
   ```
5. Candidate output format is a JSON object keyed by evaluation case ID, then condition name, then response text. The script creates the response set; blind sheet generation requires at least two conditions per case to make comparisons meaningful.
6. The evaluation sheet intentionally excludes the condition mapping. Keep `blind-label-map.json` with the coordinator, not evaluators.
7. After scoring, run `scripts/run_core_prime_blind_eval.py --scores scored.jsonl --output evaluation/runs/summary`.

This is an inference adapter—not a model selection or training approval. Evaluation cases should be protected and not included in training. The present 30 cases are public draft examples; establish a separate, protected holdout before formal evaluation. Preserve output files, exact model revision, tokenizer, runtime and configuration for reproducibility.
