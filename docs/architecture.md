# Model family architecture

## Canonical topology

- **Models by vectolith** is the canonical model-development and release source.
- **Core Prime** and **Core Prima** are the two models in the vectolith family.
- **VELNOR** is one downstream product/integration repository. Future products and external integrations are also first-class consumers.
- The reusable vectolith runtime provides common execution and integration capabilities without making downstream products depend on model internals.

## Model responsibilities

### Core Prime — general-purpose intelligence

Core Prime is primarily responsible for understanding user intent and providing general-purpose assistance: conversation, instruction following, reasoning, everyday and professional assistance, writing, learning, planning, broad information synthesis, and communicating outcomes.

### Core Prima — technical intelligence and execution

Core Prima is primarily responsible for coding, software engineering, system architecture, product and UI design, debugging, testing, technical investigation, tool use, and autonomous task completion.

These are primary responsibilities, not artificial capability walls. Both models must remain independently useful and may handle work outside their primary specialization when appropriate.

## Shared vectolith family contract

Both models must share:

- One vectolith identity.
- One behavioural and safety contract.
- Compatible conversation and task-state formats.
- Interoperable, bidirectional delegation protocols.
- Consistent user experience across VELNOR and future integrations.

The contract covers instruction hierarchy, safety boundaries, disclosure of uncertainty and limitations, tool-call semantics, task status, handoff metadata, and user-facing interaction principles.

## Delegation and interoperability

Models communicate through versioned, structured task envelopes. A handoff carries the original user intent, task description, constraints, acceptance criteria, relevant context references, permission scope, task ID, and deadline or resource limits where applicable. Results include status, deliverables, test and verification evidence, limitations, and references to actions taken.

Delegation is bidirectional. Either model may ask the other for clarification, request a bounded subtask, return work for revision, or escalate a blocked task. A model must not silently discard requirements or broaden its permission scope.

## Teacher/student separation

Teachers supervise training only. Released students must be independently loadable with their own weights, configuration, tokenizer/processor, and runtime requirements.

## Architecture neutrality

Do not assume Qwen or any single vendor. The initial trainer may support only reviewed decoder-only causal-LM layouts. Mark unsupported architectures incompatible until the harness is extended and tested; never silently force a candidate through an incompatible trainer.
