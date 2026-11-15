# Models by vectolith

Canonical upstream project for the vectolith model family. This repository owns model specifications, foundation selection, training pipelines, evaluation, artifacts, and releases. VELNOR and other products may consume approved family models through the shared runtime.

## Model family

**Models by vectolith is an extensible model ecosystem.** Core Prime and Core Prima are the first family members, not the only models.

| Model | Initial specialization |
|---|---|
| **Core Prime** | General-purpose reasoning, conversation, instruction following, planning, synthesis, and coordination |
| **Core Prima** | Coding, software engineering, architecture, debugging, technical design, testing, and technical execution |
| **Future family models** | Additional specializations and modalities, each with its own training objectives, evaluations, and release lifecycle |

Every model has its own identity within the family, version, specialization, training objectives, evaluation criteria, and release lifecycle. All models share vectolith identity, behavioural and safety standards, compatible task/message contracts, and collaboration protocols. Different model architectures and tokenizers are permitted when interoperability is proven at the contract boundary.

## Runtime architecture

A model-neutral registry publishes machine-readable capabilities and modality support. Capability discovery returns compatible candidates; orchestration applies release policy, evaluation evidence, resource constraints, availability, and permissions before execution. Registry membership alone does not imply that weights are available or that a model is released.

- [Extensible family specification](docs/model-family-specification.md)
- [Shared identity contract](docs/shared-identity-contract.md)
- [Model registry and capability discovery](docs/model-registry-and-capabilities.md)
- [Architecture](docs/architecture.md)
- [Foundation selection](docs/foundation-selection.md)
- [Independent foundation selection and global-English standard](docs/independent-foundation-selection-and-global-english.md)
- [Collective distillation](docs/collective-distillation.md)
- [Multi-teacher distillation and student independence](docs/multi-teacher-distillation-and-student-independence.md)
- [Teacher candidate efficiency review](docs/teacher-candidate-efficiency-review.md)
- [Training and promotion](docs/training-and-promotion.md)
- [Release policy](docs/release-policy.md)

## Collective distillation

Teacher models are training-time dependencies only. Released students must run independently without teacher inference. Do not merge weights across different architectures. Use logit-level distillation only when tokenizer and output compatibility are proven.

## Current status

No foundation has been selected and no expensive training or release of student weights is claimed. Candidate selection must precede expensive training.

## Principles

1. Evidence before foundation selection; selection before expensive training.
2. Immutable model revisions and verified licenses.
3. Independent objectives, datasets, evaluations, and promotion for each model.
4. Shared family identity, safety baseline, and interoperability.
5. Reproducible runs, auditable data lineage, and honest model cards.
6. Never commit credentials, private datasets, or large model weights to Git.
