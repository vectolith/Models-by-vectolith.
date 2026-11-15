# Private holdout operations

## Security boundary

Public benchmark fixtures are not holdouts. Do not place private prompts, expected answers, labels, scoring keys, raw holdout outputs, or private manifests in this repository, its issues, pull requests, CI logs, or public artifacts.

`evaluation/run_private_holdout.py` accepts only suite and manifest files outside the repository. On POSIX systems it requires owner-only file permissions (0600/0400) and an owner-only parent directory (0700). It verifies the exact suite SHA-256 against both a protected expected digest and the external manifest, checks the dataset version and authorized student role, validates unique case IDs, and writes raw outputs to an owner-only file outside the repository. The command prints metadata only; it does not print prompts or responses.

These checks prevent accidental use of public fixtures as a hidden holdout. They do not replace operating-system access controls, encrypted storage, access logging, evaluator blinding, or a trusted dataset custodian.

## External manifest

Store a JSON manifest beside the private JSONL suite, outside the repository:

```json
{
  "schema_version": "vectolith-private-holdout-manifest/1.0",
  "dataset_version": "holdout-2026-01",
  "sha256": "64-character-sha256-of-the-jsonl-file",
  "case_count": 100,
  "access_control": "restricted",
  "authorized_roles": ["core_prime", "core_prima"]
}
```

The dataset and manifest must be readable only by the evaluation identity. Keep the expected version and SHA-256 in protected environment variables or a secrets manager, not in the public repository. The manifest is metadata, not a substitute for protecting the dataset.

## Run

Mount or copy the suite and manifest into a restricted directory outside the checkout. Set:

- `VECTOLITH_PRIVATE_HOLDOUT_PATH`
- `VECTOLITH_PRIVATE_HOLDOUT_MANIFEST`
- `VECTOLITH_PRIVATE_HOLDOUT_SHA256`
- `VECTOLITH_PRIVATE_HOLDOUT_VERSION`
- `VECTOLITH_INFERENCE_API_KEY` only when the local endpoint requires authentication

Then run the private runner for each role and candidate:

```bash
python evaluation/run_private_holdout.py \
  --output /secure/evaluation/core-prime-candidate-a.jsonl \
  --base-url http://127.0.0.1:8000/v1 \
  --model served-model-name \
  --candidate-id provider/model \
  --revision IMMUTABLE_REVISION \
  --role core_prime
```

Use a separate owner-only output directory. Do not upload raw holdout output to public CI artifacts. Preserve the holdout hash, version, exact model revision, tokenizer/server/quantization details, decoding parameters, hardware and run timestamp in a restricted experiment record.

## Current status

The public repository contains the loader, integrity checks, execution wrapper and tests only. It does not contain the private dataset or secret scoring key. A holdout evaluation is not complete until a dataset custodian provisions a genuinely access-restricted external suite and the protected version/hash values are supplied to the runner. Never describe the public v2 suites as private.
