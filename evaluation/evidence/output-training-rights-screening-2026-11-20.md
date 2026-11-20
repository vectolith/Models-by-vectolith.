# Preliminary model-output training rights screening — 2026-11-20

**Status: research only. No legal review, output-training permission, teacher qualification, or inference authorization is approved.**

This note records current public-source corroboration for the pinned teacher candidates and distinguishes model-weight licenses from permission to train Core Prime on generated outputs. It is not legal advice and does not substitute for an authorized reviewer.

## Existing five teacher candidates

The exact-revision capture records in artifact #14422519458 remain the source of captured file bytes and hashes. The current public source checks below corroborate license declarations; they were not independently downloaded and re-hashed at those exact revisions during this screening.

| Candidate | Captured revision | Public declaration | Screening observation |
|---|---|---|---|
| IBM Granite 3.1 3B-A800M-Instruct | `a02780686e08a03fe0d2679a293b5c74a90efa89` | Apache-2.0 | No separate written output-training permission record found. |
| IBM Granite 4.2 3B | `4e9c275e232f10211ec88644d106a1f6a1b60e06` | Apache-2.0 | No separate written output-training permission record found. |
| OpenBMB MiniCPM5-2B | `42433e90dad95123ab87729fd7011e7110629556` | Apache-2.0 | No separate written output-training permission record found. |
| LiquidAI LFM2.5-2.6B | `7141b56cd4650af95c7c7b86983443aed050c96a` | LFM Open License v1.0 (custom) | The license includes a $10M annual-revenue threshold for commercial use; project entity/use requires authorized review. No separate output-training permission record found. |
| Microsoft Phi-4-mini-instruct | `cfbefacb99257ffa30c83adab238a50856ac3083` | MIT | No separate written output-training permission record found. |

Pinned model-card sources:

- [Granite 3.1](https://huggingface.co/ibm-granite/granite-3.1-3b-a800m-instruct/blob/a02780686e08a03fe0d2679a293b5c74a90efa89/README.md)
- [Granite 4.2](https://huggingface.co/ibm-granite/granite-4.2-3b/blob/4e9c275e232f10211ec88644d106a1f6a1b60e06/README.md)
- [MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B/blob/42433e90dad95123ab87729fd7011e7110629556/README.md)
- [LFM2.5-2.6B](https://huggingface.co/LiquidAI/LFM2.5-2.6B/blob/7141b56cd4650af95c7c7b86983443aed050c96a/README.md) and its [LICENSE](https://huggingface.co/LiquidAI/LFM2.5-2.6B/blob/7141b56cd4650af95c7c7b86983443aed050c96a/LICENSE)
- [Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct/blob/cfbefacb99257ffa30c83adab238a50856ac3083/README.md)

## Additional captured teacher candidates

The separate rights-capture artifact #14429024357 records the following exact revisions. The artifact ZIP was not downloaded or re-hashed during this screening.

| Candidate | Captured revision | Public source | Screening observation |
|---|---|---|---|
| Qwen3.5-2B teacher | `5bf1871105527bed0f47e8fa941d2fc5170f7b1d` | [Pinned model card](https://huggingface.co/Qwen/Qwen3.5-2B/blob/5bf1871105527bed0f47e8fa941d2fc5170f7b1d/README.md) | The captured Apache-2.0 declaration does not provide a separate explicit output-training permission record. |
| Gemma 4 E2B IT | `4adf15748de9e1a0097b6274cee9c15836c41c37` | [Pinned model card](https://huggingface.co/google/gemma-4-E2B-it/blob/4adf15748de9e1a0097b6274cee9c15836c41c37/README.md); [official license](https://ai.google.dev/gemma/docs/gemma_4_license) | The current card declares Apache-2.0; output-training permission remains unverified. |
| NVIDIA Nemotron 3 Nano 4B BF16 | `ef26eca1cb6b37ea5e5d5b7e01c087e63345aeec` | [Pinned model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/blob/ef26eca1cb6b37ea5e5d5b7e01c087e63345aeec/README.md) | The recorded NVIDIA Nemotron Open Model License includes a clause stating NVIDIA does not claim ownership of generated outputs. That is relevant, but still requires authorized review of the exact candidate, applicable terms, third-party rights and the proposed training use. |

The Qwen3.5-2B local evaluation grader is a separate role and revision (`15852e8c16360a2fea060d615a32b45270f8a8fc`). It is not a teacher, training dependency or teacher-output source. The teacher capture above uses revision `5bf1871105527bed0f47e8fa941d2fc5170f7b1d`; do not conflate them.

## License-source observations

- Apache-2.0 and MIT are permissive weight/artifact licenses, but this screening did not locate a separate written permission record specifically authorizing generated teacher outputs to be used as Core Prime training targets. The intended use, underlying data, applicable law and output rights remain for authorized review.
- The [LFM Open License](https://www.liquid.ai/lfm-license) is Apache-based with a commercial-use threshold. It is not interchangeable with Apache-2.0. The actual project entity, revenue and use must be reviewed against the complete terms.
- The [NVIDIA Nemotron Open Model License (12-12-25)](https://www.nvidia.com/content/dam/en-zz/Solutions/license-agreements/enterprise-software/NVIDIA-Nemotron-Open-Model-License-12-12-25.pdf) states that NVIDIA does not claim ownership of outputs generated using its Works or Derivative Works. This clause is noted, not treated as a completed legal review or as a blanket clearance of third-party rights.
- OpenMDW-1.1 is a distinct license. Its terms must not be substituted for the recorded license of Nemotron 3 Nano 4B or transferred across model revisions/families without verifying the exact model's governing terms.

## Evidence boundaries

- Artifact #14422519458: five teacher revision captures plus the separate local-grader capture, as previously recorded.
- Artifact #14429024357: nine captures from the separate candidate rights-capture job, as previously recorded.
- This note creates no permission document, legal-review record, license-byte hash, inference output, human grade, or compute evidence.
- All output-training permission and authorized legal-review gates remain pending. No inference or training was run; the protected holdout remains untouched.
