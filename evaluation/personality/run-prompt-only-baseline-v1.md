# Running the Core Prime prompt-only baseline

This experiment compares the same locally available foundation model with and without the Core Prime character system prompt. It is a prompt-only comparison—not fine-tuning, and not a trained-model claim.

## Conditions
- `base`: model chat template, user prompt and case context only.
- `character_prompt`: identical model and generation settings, plus `evaluation/personality/core-prime-character-system-prompt-v1.txt` as the system message.

The generation helper requires a tokenizer chat template; it intentionally refuses fallback formats that could silently alter condition parity.

## Zero-budget execution
Run in a free local or genuinely free compute environment with the model already available locally. Use `--offline` to prevent model downloads. Do not use paid inference or compute, paid trials, quota bypass, or account rotation. No foundation model is selected by this script.

Example (from repo root, model must already be cached):
```bash
python scripts/generate_core_prime_eval_outputs.py \
  --model /path/to/local/model \
  --offline \
  --character-prompt evaluation/personality/core-prime-character-system-prompt-v1.txt \
  --output /tmp/core-prime-paired-outputs.json
```

## Blinding
```bash
python scripts/run_core_prime_blind_eval.py \
  --outputs /tmp/core-prime-paired-outputs.json \
  --output /tmp/core-prime-blind
```
The harness writes a blinded response sheet and a separate label map. Keep the mapping inaccessible to evaluators until scoring is complete. Record the model revision, generation settings, case-set revision, environment, and run date alongside results. Never include holdout cases in training.

## Limitations
- Generation is not run by CI; CI tests code only.
- A model must be available locally and compatible with its Transformers tokenizer/model implementation.
- A character prompt can change style without changing model weights; results cannot establish trained-model personality.
- Blind scoring, evaluator agreement, gate flags, and capability regressions remain to be assessed.
