# Model family architecture

## Canonical topology

- **Models by vectolith** is the canonical model-development source.
- Other Vectolith repositories are separate products. None is a downstream requirement, deployment target, or runtime dependency of this model product.
- **Core Prime** and **Core Prima** are the first independently trained, versioned, evaluated, and released family members. They are not the only permitted models.

## Extensible family

The family is open-ended. Each model has its own stable ID, specialization, training objectives, data lineage, evaluation suite, foundation/architecture declaration, and release lifecycle. New models must be addable through registration and capability declarations rather than runtime rewrites.

See [the family specification](model-family-specification.md), [shared identity contract](shared-identity-contract.md), and [registry/capability discovery](model-registry-and-capabilities.md).

## Shared family contract

All family members share vectolith identity, instruction hierarchy, safety baseline, disclosure conventions, versioned task/message/result formats, and collaboration protocols. They preserve user intent and context across handoffs and report uncertainty, failures, and verification evidence honestly.

Interoperability is validated at interface and behavioural levels. Identical architecture, tokenizer, or internal representation is not required.

## Initial specializations

**Core Prime:** unified general intelligence and end-to-end task ownership: conversation, instruction following, reasoning, research, evidence synthesis, planning, writing, mathematics, data analysis, coding, software engineering, architecture, debugging, technical design, testing, structured tool use, agentic execution, and verification.

**Core Prima:** paused. The former Prima engineering capability set is being absorbed into Prime. A future Prima would need a distinct specialization and independent evidence; it is not currently a required delegate.

These are initial roles, not an exhaustive model catalogue. Future specializations are unrestricted subject to the family contract and release gates.

## Model-family delegation and interoperability

Core Prime is expected to own software delivery end to end: preserve the original request, define requirements and acceptance criteria, design, implement, test, debug, verify, and report evidence. It may use approved external tools or optional future specialist models when available, but must not depend on Core Prima to perform engineering work. Any delegation is an optimization, not a capability prerequisite.

Every handoff uses a versioned task envelope containing task identity, requester and assignee, original intent, requirements, constraints, acceptance criteria, context references, permission scope, and resource limits. Results carry explicit status, deliverables, tests, verification evidence, limitations, and unresolved issues.

Delegation never expands permissions. Runtime components in this repository's model-development workflows enforce their own least-privilege and evidence requirements. Any external application that consumes a released model owns its own authorization, approvals, tenant boundaries, tool execution, auditability and truthful task status. No external application or Vectolith product is required. See [the delegated execution contract](delegated-execution-contract.md) and [model-side runtime architecture](runtime-architecture.md).

## Teacher/student separation

Teachers supervise training only. Released students must be independently loadable with their own weights, configuration, tokenizer/processor, and runtime requirements.

## Architecture neutrality

Do not assume Qwen or any single vendor. The initial trainer may support only reviewed decoder-only causal-LM layouts. Mark unsupported architectures incompatible until the harness is extended and tested; never silently force a candidate through an incompatible trainer.
