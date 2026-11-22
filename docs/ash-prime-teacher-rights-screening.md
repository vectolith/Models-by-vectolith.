# ASH PRIME teacher rights screening — 2026-11-17

**Status: research only. No teacher has an approved legal gate or verified training-output permission.**

The public model cards identify the following license declarations for the exact candidate families already used in public inference runs. These are screening observations, not legal conclusions. The rights-capture artifact has now been downloaded and reconciled: all five candidate manifests and every captured file digest are recorded in the machine-readable register. Authorized, dated legal review and separate written training-output permission remain pending for every candidate.

| Candidate | Pinned revision in existing inference evidence | Public license declaration | Rights disposition |
|---|---|---|---|
| IBM Granite 3.1 3B-A800M-Instruct | `a02780686e08a03fe0d2679a293b5c74a90efa89` | Apache-2.0 | Exact-revision model card and pinned canonical SPDX Apache-2.0 reference captured and hashed. The repository has no LICENSE/COPYING file; the SPDX text is not represented as repository-supplied. Authorized legal review and output permission remain pending. |
| IBM Granite 4.2 3B | `4e9c275e232f10211ec88644d106a1f6a1b60e06` | Apache-2.0 | Exact-revision model card and pinned canonical SPDX Apache-2.0 reference captured and hashed. The repository has no LICENSE/COPYING file; authorized legal review and output permission remain pending. |
| OpenBMB MiniCPM5-2B | `42433e90dad95123ab87729fd7011e7110629556` | Apache-2.0 | Exact-revision model card and pinned canonical SPDX Apache-2.0 reference captured and hashed. The repository has no LICENSE/COPYING file; authorized legal review and output permission remain pending. |
| LiquidAI LFM2.5-2.6B | `7141b56cd4650af95c7c7b86983443aed050c96a` | LFM Open License v1.0 (custom) | Exact-revision model card and LICENSE bytes captured and hashed. Authorized review of the full custom terms for the actual project entity/use and separate output permission remain pending. |
| Microsoft Phi-4-mini-instruct | `cfbefacb99257ffa30c83adab238a50856ac3083` | MIT | Exact-revision model card, LICENSE and NOTICE bytes captured and hashed. Authorized legal review and separate output permission remain pending. |

## Capture artifact and digest reconciliation

- Workflow run: [44296033163](https://github.com/vectolith/Models-by-vectolith./actions/runs/44296033163)
- Downloaded artifact: `14422519458`
- ZIP SHA-256: `3c8ba24c66b862d3142d6e5677d93439e5d56a06652b746ee4b0ed6bfea9d9eb`
- `capture-summary.json` SHA-256: `b813c058e371e30392586678bbc92578b5feeac2412d84c22bafe3d3fdc4a862`
- Captured at: `2026-11-18T11:35:27.641526+00:00`
- Result: 6 model manifests captured (5 Run 42 teachers + 1 local evaluation grader), 0 capture failures. The capture job downloaded no model weights; a separate grader-smoke job downloads the pinned Qwen checkpoint and performs one synthetic evaluation. No teacher inference or training was started.

| Candidate | Model-card SHA-256 | License/reference SHA-256 | NOTICE SHA-256 | Manifest SHA-256 |
|---|---|---|---|---|
| Granite 3.1 3B-A800M-Instruct | `5a875520c70d9faae1255eb9aad66fdacf023db595d5e57a9c70026d0ffc0f77` | SPDX Apache-2.0: `074e6e32c86a4c0ef8b3ed25b721ca23aca83df277cd88106ef7177c354615ff` | — | `486691687528759513eb8073c6cce3001cd16dea43775035e25103657a6c945b` |
| Granite 4.2 3B | `8f22ddce440f0c15ecb58fc9f8501b882baf5f2b7ab0d13872fe77d88c1ad792` | SPDX Apache-2.0: `074e6e32c86a4c0ef8b3ed25b721ca23aca83df277cd88106ef7177c354615ff` | — | `2fc91739d0ea02ae804738707a5343cbaf24c179077c7ae7d7b5e65c2439fbb9` |
| MiniCPM5-2B | `59e93770502358d56b30b8e2ef7e744cf7fc91bfb923c7c787876defac35cdbe` | SPDX Apache-2.0: `074e6e32c86a4c0ef8b3ed25b721ca23aca83df277cd88106ef7177c354615ff` | — | `476530f69a8be26f6945f2e7667ace9eee0f49d8c7cd7b1b3491926c12c70e2b` |
| LFM2.5-2.6B | `206383f9e7d86fb44fb260474c5a0793830c5691b5ca6f7d5f955058de320886` | Repository LICENSE: `4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c` | — | `63b032c8e1da3a0b6da9626b2319dad6952c50082774e59087a8e2dc288000eb` |
| Phi-4-mini-instruct | `c4f34916182a3ee87d95d00c92847cfa687ab21dc338a577275f0c34cf0e1dfd` | Repository LICENSE: `fa8235e5b48faca34e3ca98cf4f694ef08bd216d28b58071a1f85b1d50cb814d` | `a3386cc7125ec75ed34d4f0a340c47782982095e251d322e01d8ecab22d87ba4` | `8e82b0b59870e204739a33b560c24788f6d8d3e32e5d776f04c1e7722a22a5d5` |

The per-file paths, byte lengths, immutable URLs, source kinds and hashes are stored in [`evidence/teacher-rights-register.json`](../evidence/teacher-rights-register.json). The Apache-2.0 entries use a canonical SPDX text snapshot because those model repositories do not contain a license file; this distinction is explicit in the register.

### Local evaluation grader (not a teacher)

- Model: `Qwen/Qwen3.5-2B`
- Immutable revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- Model-card SHA-256: `c0e83a849c776e6fa843d011f023132d942a0f0140d903205bf1c363adad2275`
- Repository LICENSE SHA-256: `bbedc3fda3305820b977265f01b8619d87570a6739de3a5582c3464840f1e57a`
- Rights manifest SHA-256: `6848ad5a2e8bf13f941bf66bfb9901f84010189a09a9dc57bb1a5ed2ef53bd55`
- Role: evaluation-only grader; not a teacher, foundation candidate, training dependency or source of training targets
- Capture: exact-revision README and LICENSE captured; authorized legal review remains pending

## Official screening sources

- [Granite 3.1 model card](https://huggingface.co/ibm-granite/granite-3.1-3b-a800m-instruct/blob/a02780686e08a03fe0d2679a293b5c74a90efa89/README.md) — declares Apache 2.0.
- [Granite 4.2 3B model card](https://huggingface.co/ibm-granite/granite-4.2-3b/blob/4e9c275e232f10211ec88644d106a1f6a1b60e06/README.md) — declares Apache 2.0.
- [MiniCPM5-2B model card](https://huggingface.co/openbmb/MiniCPM5-2B/blob/42433e90dad95123ab87729fd7011e7110629556/README.md) — declares Apache 2.0.
- [LFM2.5-2.6B model card](https://huggingface.co/LiquidAI/LFM2.5-2.6B/blob/7141b56cd4650af95c7c7b86983443aed050c96a/README.md) — declares the custom `lfm1.0` license.
- [Phi-4-mini-instruct model card](https://huggingface.co/microsoft/Phi-4-mini-instruct/blob/cfbefacb99257ffa30c83adab238a50856ac3083/README.md) and [MIT LICENSE](https://huggingface.co/microsoft/Phi-4-mini-instruct/blob/main/LICENSE).

The model-card declaration is not a substitute for retrieving the license and notices from the exact pinned commit and hashing those exact bytes. The LFM Open License is not interchangeable with Apache 2.0; review the original license text, including commercial conditions, before any intended use. An open model-weight license does not by itself satisfy this project's separate requirement for documented permission to use generated outputs in student training. Liquid AI's published LFM Open License v1.0 summary states that commercial-use rights under the free license are conditioned on the relevant legal entity remaining below US$10 million annual revenue; commercial use by an entity at or above that threshold is not licensed under the free agreement and requires a separate enterprise license. The license defines the legal entity to include controlled/affiliated entities and defines commercial use broadly as direct or indirect commercial advantage or monetary compensation. A qualified non-profit exemption is limited to non-commercial or research use. The exact agreement and the actual project entity, affiliates, revenue status, jurisdiction and intended use must be reviewed by authorized counsel; do not infer eligibility from the model-card tag. See [Liquid AI's LFM License and full text](https://www.liquid.ai/lfm-license).

## Exact-revision license capture

The repository includes `evaluation/capture_teacher_rights.py` to capture public LICENSE, NOTICE/COPYING and README bytes for the five exact Run 42 revisions without downloading model weights or running inference. It uses anonymous public Hub access and writes all evidence outside the checkout. Where a repository has no license file but its exact-revision model card declares a recognized SPDX identifier, it additionally captures the canonical SPDX text from an immutable SPDX License List commit. The manifest explicitly distinguishes that canonical reference from a repository-supplied license file; it must not be described as an exact-revision file from the model repository.

```bash
python -m pip install -r evaluation/requirements-model-evidence.txt
python evaluation/capture_teacher_rights.py --out-dir /secure/vectolith/teacher-rights/run-42
```

The output contains per-candidate exact revision confirmation, byte lengths, SHA-256 digests and immutable source URLs, plus a capture summary. Missing license files and unsupported custom license identifiers remain explicit in the capture record; exact model revision mismatches fail closed. Canonical SPDX fallback is limited to recognized identifiers and does not replace review of repository-specific notices, model terms, or upstream data/output restrictions. The captured files and manifests belong in restricted evidence storage; do not commit populated capture output or private legal review records. A successful capture is not legal approval and does not establish training-output permission. An authorized reviewer must still examine the exact license terms and record a dated decision for the actual project entity and intended use.

## Required completion record per candidate

1. Preserve exact-revision model cards and repository-supplied `LICENSE`, `NOTICE`/`COPYING` files outside public CI; where a repository has no license file, preserve a canonical SPDX text reference tied to the model-card identifier and mark it as not repository-supplied. Record source URLs, commit SHA, byte lengths and SHA-256 digests.
2. Record the legal entity, jurisdiction, intended use, distribution/deployment model and commercial status relevant to the license.
3. Obtain an authorized legal review with reviewer identity, timestamp, conclusion, scope and evidence URI.
4. Obtain a separate written output-generation/training permission record identifying the model, immutable revision, output-generation context, ASH PRIME training use, scope, authorizer, timestamp and document digest.
5. Only then update the teacher qualification manifest. Do not copy a model-card license string into an approval field.

The machine-readable register is [teacher-rights-register.json](../evidence/teacher-rights-register.json). It intentionally leaves all legal and output-permission fields pending.


## Research-only specialist teacher candidates: NVIDIA Nemotron Labs

NVIDIA has released a set of domain-specialized Nemotron teacher checkpoints intended for synthetic-data generation, grading and multi-teacher distillation. They are useful research candidates for vectolith's task/domain-based teacher routing, but they are not part of the five Run 42 candidates, have no Run 42 inference artifacts, and do not satisfy any teacher qualification gate.

| Specialist checkpoint | Intended specialization documented by NVIDIA | Published terms | Current disposition |
|---|---|---|---|
| [Teacher-STEM](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-STEM) | Multi-step reasoning across math, code, sciences and humanities; knowledge-intensive QA | OpenMDW 1.1 | Research-only; exact revision, license capture, legal review, output permission and inference evidence pending |
| [Teacher-General-Reasoning](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-General-Reasoning) | General reasoning across math, logic and multi-step problems | OpenMDW 1.1 | Research-only; same gates pending |
| [Teacher-Instruction-Following](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Instruction-Following) | Constraint satisfaction, structured outputs and format adherence | OpenMDW 1.1 | Research-only; same gates pending |
| [Teacher-Competition-Coding](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Competition-Coding) | Competitive programming, algorithmic reasoning and verified coding traces | OpenMDW 1.1 | Research-only; same gates pending |
| [Teacher-Chat](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Chat) | Multi-turn conversation, helpfulness, tone and preference-aligned generation | OpenMDW 1.1 | Research-only; same gates pending |

The published model cards describe these teacher models as 550B total / 55B active LatentMoE models with up to 1M context and a stated minimum GPU profile of 4xGB200/4xB200 or 8xH100-class hardware (depending on checkpoint). That is a substantial serving footprint even though only a fraction of parameters are active per token. They should therefore be evaluated as remote/high-capability specialists or via approved provider endpoints before considering self-hosted deployment.

NVIDIA's model cards state that these specialists were developed as part of the Nemotron 3 Ultra multi-teacher on-policy distillation pipeline. This is a useful reference for specialization and orchestration, not evidence that their architecture or recipe should be copied wholesale. Vectolith must independently evaluate each teacher, preserve specialization boundaries, verify generated outputs, and retain independent evaluation of ASH PRIME and FYR PRIMA.

The OpenMDW 1.1 license is a custom model license, not Apache-2.0. Capture the exact license text and model-card/NOTICE files at an immutable checkpoint revision and obtain authorized legal review. Do not infer that the public statement "ready for commercial and non-commercial use" removes the need to check all OpenMDW terms or grants project-specific output-generation permission.

Sources:
- [NVIDIA Nemotron 3.5 Super and Lightning](https://research.nvidia.com/labs/nemotron/Nemotron-3.5-Super-and-Lightning/) — NVIDIA's architecture, teacher-distillation and training report.
- [Teacher-STEM model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-STEM) — specialized STEM reasoning and OpenMDW 1.1.
- [Teacher-General-Reasoning model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-General-Reasoning) — general reasoning.
- [Teacher-Instruction-Following model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Instruction-Following) — structured instruction adherence.
- [Teacher-Competition-Coding model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Competition-Coding) — verified coding.
- [Teacher-Chat model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Labs-Teacher-Chat) — conversational specialization.
