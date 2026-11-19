# Free compute baseline run — Qwen3-0.6B

This is a reproducible execution procedure, not evidence that a run occurred. It uses the existing Kaggle notebook/session GPU only if actually available, without purchasing compute or bypassing quota. Stop if free GPU access is unavailable.

## Candidate
- Repository: Qwen/Qwen3-0.6B
- Revision: c1899de289a04d12100db370d81485cdf75e47ca
- Status: discovery / pending review. Pin is provisional pending direct Hub API confirmation and license/output permission review. Do not run if rights review is unresolved.

## In a Kaggle notebook with an available free GPU
1. Confirm GPU entitlement and remaining free quota in the account UI; do not assume.
2. Clone this PR branch or download the repository files; use the code and data exactly at the documented commit.
3. Install dependencies from requirements.txt, then record the resolved versions. That file is not yet a verified lockfile; do not treat the environment as frozen until exact package versions and platform details are captured and reviewed.
4. Run the validators on the development dataset and the candidate manifest.
5. Run inference with a 256-token output cap and seeded decoding. Deterministic kernels are not guaranteed; record the seed and resolved software/hardware. Save output artifacts outside git unless reviewed for publication.
6. Hash raw output and summary artifacts; preserve Kaggle session evidence and runtime measurements.

Example commands from repo root:

```bash
python experiments/core-prime/001/validate_tasks.py experiments/core-prime/001/tasks.dev.jsonl
python experiments/core-prime/001/validate_candidate.py experiments/core-prime/001/candidate-qwen3-0.6b.json
python experiments/core-prime/001/evaluate.py \
  --model Qwen/Qwen3-0.6B \
  --revision c1899de289a04d12100db370d81485cdf75e47ca \
  --tasks experiments/core-prime/001/tasks.dev.jsonl \
  --output /kaggle/working/cp001-qwen3-0.6b-dev \
  --max-new-tokens 256 \
  --temperature 0
```

If the candidate manifest validation or license/output-use review is unresolved, do not run. Candidate validation is structural only and does not approve legal rights. Inference is a baseline measurement, not training or release qualification.
