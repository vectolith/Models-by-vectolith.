# Kaggle runtime validation — 2026-11-18

## What was actually verified

The user ran the resource probe inside a Kaggle Interactive notebook after selecting the GPU accelerator and Internet setting.

| Resource | Observed value |
|---|---:|
| GPU | 2 × NVIDIA Tesla T4 |
| VRAM | 15 GiB per GPU; devices are independent, not pooled |
| System RAM | 31.35 GiB total; 29.74 GiB available at probe |
| Working storage | 19.52 GiB total; 19.50 GiB available at probe |
| CPU | 4 |
| Python | 3.13.16 |
| PyTorch | 2.11.0+cu130 |
| CUDA runtime | 13.0 |
| Transformers | 5.20.2 |
| Accelerate | 1.15.0 |
| Datasets | 4.8.5 |
| PEFT | 0.21.2 |

The probe recorded 31,266,439,168 bytes aggregate free VRAM at observation time, but this is not one addressable memory pool. The largest single-GPU free VRAM observation was 15,633,219,584 bytes.

Remaining quota hours were not supplied; account-level session availability must be checked before a substantial workload.

## Runtime test evidence

The user ran the complete repository test suite in the Kaggle clone:

```bash
python -m pytest -q
```

Result:

```text
84 passed in 1.65s
```

This followed the root `pytest.ini` import-path correction (commit `3a1759191c8525964f886c3dd7d141d5146a1fa5`). The subsequent compute-attestation commit `3479a4ade59fa95555994c500af849ee4c5eac75` has two successful GitHub Actions runs associated with it:
- Vectolith Runtime: run 44268744772 — success
- ASH PRIME runtime and evaluation tests: run 44268744726 — success

## Safety boundary

At the original resource-probe observation:
- No model weights were downloaded.
- No model inference was started.
- No training was started.
- No network requests were made by the probe.

## What this evidence does and does not establish

It establishes that the Kaggle session hardware/software were user-attested and that the repository's 84-test suite passed in that environment. It does **not** establish that any foundation model fits, that the remaining GPU quota is sufficient, or that training is authorized.

Before a substantial GPU workload, recheck remaining Kaggle quota and session time. A run-specific execution approval must bind the exact code, foundation revision, dataset digest, configuration, measured capacity and finite runtime/resource limits.

Foundation selection, exact-checkpoint legal review, teacher-output training permissions, independent human grading/adjudication, four qualified teachers, approved dataset, and protected holdout remain separate gates. No model training is claimed by this report.
