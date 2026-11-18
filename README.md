# Models by vectolith

Canonical upstream project for the vectolith model family. This repository owns model specifications, foundation selection, training pipelines, evaluation, artifacts, and releases. It is an independently operated model product. Other Vectolith products do not depend on this repository, its runtime, or its release schedule.

## Model family

**Models by vectolith is an extensible model family.** Core Prime and Core Prima are the first family members, not the only models.

| Model | Initial specialization |
|---|---|
| **Core Prime** | Unified general intelligence: reasoning, conversation, research, planning, writing, mathematics, coding, software engineering, architecture, debugging, testing, structured tool use, and verified technical execution |
| **Core Prima** | Paused initial specialist track; its planned engineering capabilities are being incorporated into Core Prime. Any future Prima release requires a separately justified role, teacher panel, training lineage, and evaluation cycle |
| **Future family models** | Additional specializations and modalities, each with its own training objectives, evaluations, and release lifecycle |

Every model has its own identity within the family, version, specialization, training objectives, evaluation criteria, and release lifecycle. Family-level identity and behavioural standards apply to these models; they do not impose shared runtime, deployment, storage, authentication, or release dependencies on other Vectolith products. Different model architectures and tokenizers are permitted when interoperability is proven at an explicitly adopted contract boundary.

## Delegated execution

Core Prime is the unified user-facing model and is intended to handle the full task lifecycle itself: understand requests, research, reason, plan, write, calculate, design software, code, debug, test, use approved tools, verify outcomes, and communicate evidence-backed results. Engineering work is no longer excluded from Prime's scope or dependent on a separate Prima handoff. Core Prima remains paused; it may later exist as an optional specialist only if a distinct need is demonstrated. Runtime tool permissions and approval gates remain external and cannot be expanded by model capability.

See the [delegated execution contract](docs/delegated-execution-contract.md) and [runtime architecture](docs/runtime-architecture.md).

## Runtime and integration boundaries

This repository defines model-side specifications and optional interfaces. It does not provide a mandatory shared runtime for other Vectolith products. Each product that uses a model is responsible for its own application runtime, authentication, authorization, data storage, orchestration, deployment, observability, and release lifecycle.

No product-to-product integration is part of the default architecture. A future consumer may use a released model only through an explicitly approved, documented and replaceable interface; the consuming product must remain buildable, deployable and useful without it. No Vectolith product is assumed to consume Core Prime, this repository, or any other Vectolith product.

- [Extensible family specification](docs/model-family-specification.md)
- [Shared identity contract](docs/shared-identity-contract.md)
- [Model registry and capability discovery](docs/model-registry-and-capabilities.md)
- [Architecture](docs/architecture.md)
- [Delegated execution contract](docs/delegated-execution-contract.md)
- [Model-side runtime and optional integration architecture](docs/runtime-architecture.md)
- [Foundation selection](docs/foundation-selection.md)
- [Independent foundation selection and global-English standard](docs/independent-foundation-selection-and-global-english.md)
- [Collective distillation](docs/collective-distillation.md)
- [Multi-teacher distillation and student independence](docs/multi-teacher-distillation-and-student-independence.md)
- [Teacher candidate efficiency review](docs/teacher-candidate-efficiency-review.md)
- [Training and promotion](docs/training-and-promotion.md)
- [Training infrastructure specification](docs/training-infrastructure-specification.md)
- [Teacher infrastructure contribution system](docs/teacher-infrastructure-contributions.md)
- [Infrastructure provider qualification register](docs/infrastructure-provider-qualification-register.md)
- [Release policy](docs/release-policy.md)

## Collective distillation

Teacher models are training-time dependencies only. Released students must run independently without teacher inference. Do not merge weights across different architectures. Use logit-level distillation only when tokenizer and output compatibility are proven.

## Current status

No foundation has been selected and no expensive training or release of student weights is claimed. Candidate selection must precede expensive training.

## Principles

1. Evidence before foundation selection; selection before expensive training.
2. Immutable model revisions and verified licenses.
3. Independent objectives, datasets, evaluations, and promotion for each model.
4. Consistent family identity and safety baseline within this model family; no cross-product runtime coupling.
5. Reproducible runs, auditable data lineage, and honest model cards.
6. Never commit credentials, private datasets, or large model weights to Git.
