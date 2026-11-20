# Infrastructure provider qualification register

**Assessment date:** 2026-11-17  
**Scope:** execution-environment qualification for Models by vectolith  
**Hard ceiling:** **USD $0**  
**Decision:** No GPU training provider or GPU session is currently verified for this project. Provider eligibility, account access, workload permissions and measured capacity must be verified before execution.

## Current no-cost options

| Environment | Published no-cost offer | Current project status | Permitted use |
|---|---|---|---|
| GitHub Actions standard hosted runners on this public repository | Standard public-repository runners are free and unlimited; `ubuntu-latest` is documented as 4 CPU, 16 GB RAM and 14 GB SSD | **Available for CPU CI; model-grading workload not yet load-tested** | Tests, metadata capture, small CPU checks and the pinned local grading pilot only if the workload fits |
| Kaggle Notebooks | GPU availability, queue and quotas are conditional | **Conditional; no Vectolith account/session or successful workload probe recorded** | Candidate inference or training only after the exact model loads and completes within a verified session with measured capacity |
| Google Colab free tier | GPU resources may be offered, but availability and usage limits vary and are not guaranteed | **Conditional; no Vectolith session or successful workload probe recorded** | Candidate inference or training only after account/session, hardware, quota and workload evidence are captured |

Official references:
- GitHub public runners and specifications: https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
- GitHub Actions billing: https://docs.github.com/en/actions/concepts/billing-and-usage
- Kaggle Notebooks: https://www.kaggle.com/docs/notebooks
- Google Colab resource limits: https://research.google.com/colaboratory/faq.html

A published free tier is not proof that a Vectolith workload is available. Before marking a GPU resource verified, capture the actual account/session, accelerator model/count, VRAM, system RAM, disk, queue, quota remaining, runtime limit, model-load result, completed workload, and evidence that no payment method, billing activation, trial credit or charge was used.

## Excluded paid or billing-dependent providers

| Provider | Disposition | Reason |
|---|---|---|
| RunPod Secure Cloud / Community Cloud | **Excluded by USD $0 policy** | Published GPU Pods are billed; no paid instance, storage volume, hosted service or API may be provisioned |
| Lambda Cloud | **Not qualified** | Account-level access, applicable terms, workload permissions and measured capacity have not been verified |
| NVIDIA DGX Cloud Lepton | **Not an available no-cost entitlement** | No verified free Vectolith workspace, GPU allocation or contractual entitlement exists |
| Any hosted inference API | **Excluded by USD $0 policy** | No paid or billing-enabled model API may be used for grading, teacher inference or foundation evaluation |

These entries are not procurement recommendations or future spend requests. No provider API has been called, no account has been connected, and no paid resource has been provisioned.

## Training-readiness implications

1. GitHub Actions public standard runners are suitable for CPU-only CI and bounded evaluation, not evidence of GPU training capacity.
2. Kaggle and Colab remain conditional until a real session and exact workload probe succeed. Do not assume GPU availability or rely on promotional access claims.
3. The selected foundation must fit the actual verified free resource. Do not substitute a different model, architecture, quantization or revision without a separate candidate record and explicit decision.
4. A run-specific execution manifest must bind the exact resource observation, environment approval and measured capacity.
5. If no suitable free accelerator is available, keep training blocked. Do not start a paid job, enable billing, or weaken the model/data/evaluation gates to fit an unverified resource.

**Qualification state:** CPU CI is available through public standard runners; local semantic grader capacity is not yet load-tested; no GPU training capacity is verified. Training remains blocked.
