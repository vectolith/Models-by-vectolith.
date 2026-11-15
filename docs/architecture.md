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

## Delegation and interoperability

Prime-to-Prima software delivery is the canonical delegated workflow: Prime preserves the original request, gathers requirements and acceptance criteria, and delegates implementation; Prima designs, implements, tests, and verifies; Prime independently reviews the evidence and communicates the result. Either model may request clarification, delegate a bounded subtask, return work for revision, or escalate a blocker.

Every handoff uses a versioned task envelope containing task identity, requester and assignee, original intent, requirements, constraints, acceptance criteria, context references, permission scope, and resource limits. Results carry explicit status, deliverables, tests, verification evidence, limitations, and unresolved issues.

Delegation never expands permissions. The runtime enforces least privilege, approval requirements, tenant boundaries, auditability, and truthful task status. Proposed actions must be distinguished from actions actually executed. See [the delegated execution contract](delegated-execution-contract.md) and [runtime architecture](runtime-architecture.md).

## Teacher/student separation

Teachers supervise training only. Released students must be independently loadable with their own weights, configuration, tokenizer/processor, and runtime requirements.

## Architecture neutrality

Do not assume Qwen or any single vendor. The initial trainer may support only reviewed decoder-only causal-LM layouts. Mark unsupported architectures incompatible until the harness is extended and tested; never silently force a candidate through an incompatible trainer.
