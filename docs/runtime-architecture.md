# Vectolith runtime architecture

## Purpose

The vectolith runtime is a reusable execution and integration layer shared by downstream products. It allows Core Prime, Core Prima, or both to serve an application through stable interfaces without exposing or coupling consumers to internal model architectures.

The runtime is separate from model weights. A model proposes and reasons about actions; the runtime enforces permissions and executes tools, APIs, workflows, and state transitions.

## Required capabilities

1. **Model gateway and routing:** select Core Prime, Core Prima, or a coordinated workflow based on task responsibility, capability, availability, and policy.
2. **Model-to-model delegation:** support structured, bidirectional handoffs, clarification requests, bounded subtasks, returns for revision, and escalation.
3. **Task orchestration:** maintain task IDs, ownership, dependencies, status, retries, cancellation, deadlines, and resource limits.
4. **Shared context and state:** pass versioned conversation and task-state envelopes while respecting tenant boundaries and data minimisation.
5. **Tool and API execution:** expose registered tools through typed schemas, validated arguments, scoped credentials, and controlled execution.
6. **Permission and approval enforcement:** evaluate user, application, and policy permissions before every consequential action; require explicit approval where policy demands it.
7. **Verification:** collect test output, tool results, artifact checksums, provenance, and other evidence needed to support completion claims.
8. **Observability and audit:** record model handoffs, tool invocations, permission decisions, state transitions, errors, and evidence references without unnecessarily logging secrets.
9. **Recovery:** handle timeouts, partial completion, tool failures, retries, cancellation, and safe escalation without falsely marking work complete.
10. **Downstream adapters:** provide stable APIs/SDKs and integration contracts so VELNOR and future products can adopt the runtime without rebuilding orchestration.

## Task lifecycle

A task should move through explicit states such as received, understood, planned, delegated, running, awaiting approval, verifying, completed, partially completed, failed, or cancelled. State transitions must be validated and auditable.

## Structured delegation envelope

At minimum, a delegation request carries:

- Task ID and parent task ID where applicable.
- Requester model, assigned model, and task owner.
- Original user request and preserved intent.
- Task objective, requirements, constraints, and acceptance criteria.
- Relevant conversation/task context or secure references to it.
- Allowed tools, permission scope, and approval requirements.
- Dependencies, resource limits, and timeout policy.
- Schema and contract versions.

A result carries the task ID, status, summary, deliverables or artifact references, actions performed, tests run and their outcomes, verification evidence, unresolved issues, and any required next decision.

These are conceptual contract fields; implementation schemas must be versioned and validated before use.

## Security boundaries

- Models do not receive unrestricted credentials.
- Tool execution occurs in the runtime under least-privilege scopes.
- User and application permissions cannot be expanded by a model during delegation.
- Consequential or irreversible actions require the configured approval gate.
- Context and artifacts remain isolated by user, tenant, and integration.
- Audit records must distinguish proposed actions from actions actually executed.

## Completion semantics

A model cannot mark a task completed solely because it generated a plausible response. Completion requires the task's acceptance criteria to be checked and required evidence to be recorded. If verification is unavailable or fails, the runtime must preserve a non-complete status and expose the limitation.

## Integration readiness

The runtime is not integration-ready until contract tests cover direct model use, Prime-to-Prima delegation, Prima-to-Prime delegation, tool success and failure, permission denial, approval-required actions, cancellation, timeout, partial completion, retry, context preservation, and evidence-backed completion.
