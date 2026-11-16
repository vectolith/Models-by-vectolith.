`snapshot_additional_teacher.py` resolves a public Hub model's current revision to a full immutable commit SHA, downloads that exact revision, validates the expected architecture and license identifier, and emits a manifest containing the complete file inventory, byte sizes and SHA-256 hashes. The manifest includes the Hub revision, config and license-file hashes. The workflow then passes that exact SHA to `run_real_candidate_eval.py`; it never runs inference against a moving `main` ref.

The workflow `.github/workflows/expanded-qualification-inference.yml` runs the full six-teacher chain sequentially: Granite 3.1 → Granite 4.2 → MiniCPM5 → SmolLM3-3B → LFM2.5-2.6B → Phi-4-mini-instruct, each over the same Prime public v1-v4 fixtures and the same deterministic generation cap. Per-candidate manifests, raw JSON/JSONL outputs, logs and compute observations are uploaded as separate artifacts. The actual model snapshot stays in the ephemeral runner cache; model weights are not committed to Git or copied into large CI artifacts. Re-fetching the recorded SHA and validating its file hashes reproduces the same snapshot.

Phi-4 is loaded with `trust_remote_code=False`; the pipeline will not execute model-repository Python code. A load failure is retained as evidence and does not silently relax this security boundary. LFM2.5's LFM Open License requires legal review, and its publisher notes it is not recommended for agentic coding or knowledge-heavy tasks. All training-output permissions remain unverified. No model is qualified and no training is performed by this workflow.

Run the snapshot registry tests with:

```bash
python -m unittest evaluation.tests.test_additional_teacher_snapshots -v
```

A passing unit test validates registry guardrails only. Actual loader compatibility, model generation, revision pinning and file hashes are established only by the real workflow artifacts.