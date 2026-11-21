# Core Prime prepared training formats

Run `python scripts/prepare_core_prime_sft.py --output <directory>` to create:

- `sft-train.jsonl`: each assistant turn from train trajectories is represented as a context prefix ending in that assistant answer; train micro-scenarios are also included.
- `dpo-train.jsonl`: train preference pairs in prompt/chosen/rejected shape.
- `prepared-manifest.json`: counts and holdout exclusion totals.

Only records explicitly marked `train` are included. Holdout rows are never exported. Every prepared record carries its source ID. These are synthetic draft examples, not validated training data. The converter is dependency-free and is not a trainer; it produces files for a later framework-specific adapter-training step.
