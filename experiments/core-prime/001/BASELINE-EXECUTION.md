# Free compute baseline run — Qwen3-0.6B

This is a gated execution procedure, not evidence that a run occurred. No baseline inference or training may run until written output-training permission, independent legal review, candidate artifact evidence and genuinely free compute are verified and authorization/freeze artifacts are approved. Stop if free GPU access is unavailable.

## Candidate
- Repository: Qwen/Qwen3-0.6B
- Revision: c1899de289a04d12100db370d81485cdf75e47ca
- Status: discovery / pending review. Pin is provisional pending direct Hub API confirmation and license/output permission review. Do not run if rights review is unresolved.

## In a Kaggle notebook with an available free GPU
1. Confirm GPU entitlement and remaining free quota in the account UI; do not assume.
2. Clone this PR branch at the exact authorized code commit. Stage the candidate snapshot locally; the candidate record must inventory every snapshot file, including config and tokenizer/template files, with SHA-256 hashes.
3. Install dependencies from the corrected requirements files, then capture the package inventory. The evaluation freeze and authorization bind the exact package-inventory SHA-256; this is an environment snapshot, not a claim of a pip lockfile.
4. Run validators on the development dataset and candidate manifest. Confirm the candidate's local snapshot inventory, license/output-training permission, independent legal review and compatibility gate.
5. Only after all authorization gates pass, run development-only inference with the authorized output-token and wall-clock ceilings. Deterministic kernels are not guaranteed; record the seed and resolved software/hardware. Save output artifacts outside git unless reviewed for publication.
6. Hash raw output and summary artifacts; preserve Kaggle session evidence and runtime measurements.

Example commands from repo root:

```bash
python experiments/core-prime/001/validate_tasks.py experiments/core-prime/001/tasks.dev.jsonl
python experiments/core-prime/001/validate_candidate.py experiments/core-prime/001/candidate-qwen3-0.6b.json
python experiments/core-prime/001/evaluate.py \
  --model Qwen/Qwen3-0.6B \
  --revision c1899de289a04d12100db370d81485cdf75e47ca \
  --tasks experiments/core-prime/001/tasks.dev.jsonl \
  --candidate-record candidate-qwen3-0.6b.json \
  --authorization evaluation-authorization.json \
  --freeze-manifest evaluation-freeze.json \
  --code-commit REPLACE_WITH_GIT_HEAD_SHA \
  --output /kaggle/working/cp001-qwen3-0.6b-dev \
  --max-new-tokens 256 \
  --temperature 0
```

If the candidate manifest validation or license/output-use review is unresolved, do not run. Candidate validation is structural only and does not approve legal rights. Inference is a baseline measurement, not training or release qualification.
