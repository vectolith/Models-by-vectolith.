# Model family architecture

## Canonical topology

- **Models by vectolith** is the canonical model-development source.
- **VELNOR** is a downstream product/integration repository.
- **Core Prime** and **Core Prima** are the first independently trained, versioned, evaluated, and released family members. They are not the only permitted models.

## Extensible family

The family is open-ended. Each model has its own stable ID, specialization, training objectives, data lineage, evaluation suite, foundation/architecture declaration, and release lifecycle. New models must be addable through registration and capability declarations rather than runtime rewrites.

See [the family specification](model-family-specification.md), [shared identity contract](shared-identity-contract.md), and [registry/capability discovery](model-registry-and-capabilities.md).

## Shared family contract

All family members share vectolith identity, instruction hierarchy, safety baseline, disclosure conventions, versioned task/message/result formats, and collaboration protocols. They preserve user intent and context across handoffs and report uncertainty, failures, and verification evidence honestly.

Interoperability is validated at interface and behavioural levels. Identical architecture, tokenizer, or internal representation is not required.

## Initial specializations

**Core Prime:** general-purpose conversation, instruction following, reasoning, planning, synthesis, and user-facing coordination.

**Core Prima:** coding, software engineering, architecture, debugging, technical design, testing, and technical execution.

These are initial roles, not an exhaustive model catalogue. Future specializations are unrestricted subject to the family contract and release gates.

## Teacher/student separation

Teachers supervise training only. Released students must be independently loadable with their own weights, configuration, tokenizer/processor, and runtime requirements.

## Architecture neutrality

Do not assume Qwen or any single vendor. The initial trainer may support only reviewed decoder-only causal-LM layouts. Mark unsupported architectures incompatible until the harness is extended and tested; never silently force a candidate through an incompatible trainer.
