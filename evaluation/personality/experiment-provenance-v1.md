# Reproducibility record for ASH PRIME prompt-only experiments

After running `scripts/generate_ash_prime_eval_outputs.py`, write a manifest recording the case, prompt and output hashes:

```bash
python scripts/record_ash_prime_experiment_provenance.py \
  --model /path/to/local/model \
  --outputs /tmp/ash-prime-paired-outputs.json \
  --manifest /tmp/ash-prime-run-manifest.json
```

The recorder does not perform inference, validate model weights, or prove generation settings. It records hashes of the inputs and outputs, run time, model label, platform and Python version so a run can be tracked and reproduced more carefully. Keep the manifest with the blind-score-sheet and restricted condition map. Never publish holdout cases or restricted mapping files.

The generator's current interface does not set an explicit random seed because it uses greedy decoding (`do_sample=False`). The recorder's seed field is informational only; it is not passed to inference.
