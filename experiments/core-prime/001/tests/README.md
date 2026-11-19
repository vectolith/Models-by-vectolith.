# Harness validator tests

Run from repository root:

```bash
python -m unittest discover -s experiments/core-prime/001/tests -v
```

These tests exercise parsing and deterministic checks. They do not load a model, establish licensing, measure capability, or constitute benchmark results.
