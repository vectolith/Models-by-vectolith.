# Core Prime training readiness and execution plan

**Status: BLOCKED — no foundation is selected, no teacher is qualified for training, and no approved training dataset or run authorization exists. Kaggle T4 x2 hardware has been observed in the user's session; remaining quota and session availability must be rechecked. No training run has started.**

This is the active Core Prime track. Core Prima remains paused. The purpose of this document is to turn the existing training infrastructure into an executable, evidence-backed run without bypassing execution, licensing, data-rights, or quality gates.

## Vectolith historical review — 2026-11-18

A Vectolith-authorized, AI-assisted independent evaluation pass has been recorded in [`docs/core-prime-vectolith-independent-review-2026-11-18.md`](core-prime-vectolith-independent-review-2026-11-18.md). It screened all 2,700 preserved response records and inspected representative rubric cases. The review found a 52.96% generation-cap hit rate, a critical fabricated tool-deletion claim, a false tool-completion claim, multilingual and coding defects, and a safety instruction concern. No teacher is qualified and no historical output is authorized for training. The report is not represented as a second human's grading or adjudication.

## Current evidence-backed disposition

| Gate | Current evidence | Disposition |
|---|---|---|
| Foundation selection | `docs/foundation-selection.md` explicitly says OPEN; no approved immutable foundation manifest exists | **Blocked** |
| Foundation license and terms | Candidate-specific review and permission evidence are incomplete | **Blocked** |
| Foundation loader/trainer compatibility | Current SFT path loads `AutoModelForCausalLM`; selected foundation architecture is not yet approved or pinned | **Blocked** |
| Teacher inference | Historical outputs from five teachers are integrity-verified; new candidate inference remains legally gated | **Evidence preserved; not qualification** |
| Teacher legal review | No complete human legal-review records for the exact teacher checkpoints/routes | **Blocked** |
| Teacher output-training permission | Separate written permissions are not verified | **Blocked** |
| Teacher human grading | Two independent reviewers, complete grading, agreement and adjudication evidence are not complete | **Blocked** |
| Teacher safety and protected holdout | No complete teacher qualification manifests with all ten gates and protected-holdout reports | **Blocked** |
| Qualified teacher cohort | At least four distinct qualified teachers with accepted examples are required; current qualified count is zero | **Blocked** |
| Training corpus | Historical raw response artifacts are not an authorized or adjudicated training dataset. No approved immutable Core Prime training dataset/manifest exists | **Blocked** |
| Compute availability | Kaggle Interactive session observed 2 × Tesla T4 (15 GiB each), 31.35 GiB system RAM and 19.52 GiB working storage; session resource limits and remaining quota are not independently confirmed. T4 is compute capability 7.5: FP16 Tensor Core path is available, BF16 Tensor Core path is not. Current trainer has no explicit dtype override, uses `device_map=auto`, and lacks QLoRA/gradient-checkpointing configuration. Remaining quota is unknown | **Hardware observed; training dtype/loader and run approval blocked** |
| Training execution approval | No run-specific approval bound to foundation, dataset, code SHA, config, measured capacity and finite resource/runtime limits exists | **Blocked** |
| Independent student evaluation | Private holdout and baseline comparison must be deployed before training | **Preparation required** |

The corpus generator's peer-review `accepted` flag is only a screening signal. Each row must also carry two independent human reviewer identities, a completed adjudication record and immutable review/adjudication evidence digests before it can enter the training dataset. Peer reviewers must be distinct qualified teachers; human reviewers must be independent of the teacher cohort.\n\nA successful inference run, permissive model-weight license, model-card label, or historical integrity report does not grant permission to train on the outputs. Historical teacher artifacts remain immutable historical contributions until the required legal, human, safety, holdout and corpus gates are independently completed.

## Execution environment availability

Kaggle Notebooks is a candidate execution environment for bounded experiments. Kaggle's current notebook documentation describes T4 GPU options, finite weekly GPU quota and notebook session limits, but availability may be queued or unavailable at busy times. These are provider-published limits, not proof that this project's account has quota or that a specific model fits. The user ran the resource probe inside a Kaggle Interactive notebook and observed 2 × NVIDIA Tesla T4, 15 GiB VRAM per GPU (VRAM is not pooled), 31.35 GiB system RAM, 19.52 GiB working storage, Python 3.13.16 and PyTorch 2.11.0+cu130. This records hardware/software observations only; remaining GPU quota hours and training authorization were not established.

- Official notebook resource documentation: https://www.kaggle.com/docs/notebooks
- Official GPU quota/usage guidance: https://www.kaggle.com/docs/efficient-gpu-usage
- Kaggle's P100 retirement notice (15 September 2026) and T4 x2 recommendation: https://www.kaggle.com/product-announcements/735239

Colab is a secondary candidate execution environment: Google states GPU availability and limits fluctuate, and notebook sessions may run for at most 12 hours. Verify account eligibility, accelerator availability, session limits and resource quotas before use.

- Official Colab resource limits: https://research.google.com/colaboratory/faq.html

The hardware observation is recorded. Before each substantial GPU workload, recheck remaining quota and session time in the provider account. The two T4 GPUs are independent devices; do not treat their VRAM as one pooled 30 GiB allocation. A run-specific approval must still bind measured available capacity, estimated peak usage, exact code/foundation/dataset/config hashes and finite resource/runtime limits. Do not circumvent provider quotas or session limits. NVIDIA's CUDA capability table identifies T4 as compute capability 7.5, with FP16 Tensor Core support but BF16 Tensor Core support starting at 8.0. The current trainer must gain an explicit model-dtype field and hardware compatibility check before a run; the exact model must be tested in FP16 or another validated mode. See `docs/foundation-candidate-hardware-screen-2026-11-18.md`.

## Training strategy

The first student-training milestone is **supervised fine-tuning (SFT) with LoRA**, not pretraining from random initialization. The foundation remains the pinned pretrained checkpoint; the first experiment produces a separate adapter/checkpoint and retains full foundation lineage.

QLoRA may be evaluated as a memory-reduction option only after the chosen foundation architecture and a verified compatible accelerator are verified. Quantized training support is backend- and hardware-specific; it must not be assumed to work on CPU. Do not claim that LoRA eliminates full-parameter model memory requirements or that 4-bit training will fit an arbitrary accelerator.

Do not begin with RLVR/GRPO, MOPD, logit distillation, or large-scale continued pretraining. Those are later experiments after SFT data quality, reward verifiers, compute and evaluation have been demonstrated. The existing infrastructure specification correctly records MOPD and production RLVR orchestration as not yet implemented.

## Work that can proceed before training execution

1. Fix and test the teacher-corpus digest contract. The corpus generator and training preflight must hash the exact same UTF-8 byte sequence: `prompt + NUL + response`.
2. Complete foundation comparison using immutable metadata, published license text, exact architecture, tokenizer/chat-template compatibility, CPU/resource observations and candidate-specific evaluation evidence. Do not select a foundation from model-family reputation.
3. Keep all historical teacher artifacts preserved. The blinded-review and adjudication tooling plus a one-command historical artifact downloader now exist (`evaluation/download_and_prepare_historical_reviews.py`, `evaluation/prepare_blinded_human_review.py`, `evaluation/prepare_human_adjudication.py`). The downloader verifies all 15 pinned ZIP digests and builds two reviewer-specific packages from the original four suites without model inference. Obtain genuine independent grades and third-party adjudication; prepare exact-checkpoint legal-review packages in parallel. Do not treat historical outputs as training-ready.
4. Complete teacher qualification manifests only from actual independent evidence. The ten required gates remain separate and fail closed; do not create synthetic reviewer identities, grades, legal approvals, or training-output permissions.
5. Prepare a Core Prime-only task curriculum and dataset builder. Preserve competency, task, teacher, revision, reviewer, accepted/rejected status, provenance and hashes. Separate train/validation/public benchmark/private holdout data.
6. Improve trainer compatibility for the exact selected architecture. The current generic SFT path uses `AutoModelForCausalLM`; multimodal or hybrid architectures need an explicit, tested adapter rather than an unsafe generic fallback.
7. Build a dry-run training package that validates every manifest, split, tokenizer, model class, configuration and measured resource estimate without loading model weights or starting a job.
8. Verify the actual execution session and resource limits. Public service descriptions or generic runner hardware probes are not proof of available GPU quota. Do not bypass provider quotas or session limits.
9. Only then create a run-specific training execution approval with finite resource limits and a runtime cap, exact code/foundation/dataset/config hashes, software image digest and measured resource capacity.
10. Run one bounded SFT experiment, preserve every checkpoint/log/metric, then evaluate against the untouched foundation using private holdout and independent role-specific tests.

## First real training run: required manifest bindings

The first run must bind all of the following before model weights are loaded:

- Core Prime model ID and an approved exact foundation repository plus immutable revision.
- Foundation tokenizer/processor/chat-template revision and loader compatibility evidence.
- Immutable, rights-cleared training dataset and manifest, with disjoint train/validation groups and no private holdout contamination.
- At least four individually qualified, revision-matched teachers if teacher-generated data is used.
- Written output-training permission for each contributing teacher and route.
- Training-code commit SHA, dependency/runtime image digest, complete configuration and deterministic seed.
- Actual provider/account/session evidence, hardware and measured RAM/VRAM/storage.
- Finite resource and runtime limits.
- Protected holdout deployment and independent baseline evaluation evidence.
- Fresh, empty output directory and rollback parent metadata.

The existing `train_student()` entry point already validates many of these bindings before importing the training stack or loading weights. Keep this fail-closed behavior; do not weaken it to force an early run.

## Training completion is not release approval

A completed SFT job is an experimental checkpoint, not a released Core Prime. Promotion still requires reproducibility, independent held-out capability evidence, safety and instruction-hierarchy checks, regression comparisons, teacher contribution/ablation evidence, and teacher-disabled inference with no teacher credentials or endpoints.

## Immediate blockers requiring real-world evidence

- Human legal review of exact foundation and teacher licenses/terms.
- Explicit written permission for teacher outputs to be used for Core Prime training.
- Two independent reviewers and adjudication of the preserved teacher responses.
- A protected private holdout and independent evaluator.
- A selected, pinned foundation with compatible training loader.
- A verified training accelerator/session with sufficient quota and session time. No such entitlement is assumed.

No person, reviewer, rights-holder, account, approval, hardware session, or permission may be fabricated to satisfy these gates.
