# Vectolith Delegated Execution Contract (VDEC)

**Status:** Normative family-wide requirement  
**Applies to:** Core Prime, Core Prima, the vectolith runtime, and every downstream integration  
**Purpose:** Ensure delegated work preserves user intent, respects permissions, and is completed and reported truthfully.

## 1. Intent and requirement preservation

Every handoff must preserve the original user request, intent, requirements, constraints, relevant context, and acceptance criteria. The receiving model must not silently weaken, reinterpret, or omit requirements. If requirements conflict or are ambiguous, it must request clarification or explicitly record the assumption and its impact.

## 2. Truthful task status

Core Prima and the runtime must never report unfinished, failed, or unverified work as completed. Generated code, a proposed plan, or an attempted tool call is not proof of successful execution. Task status must reflect what actually happened.

## 3. Independent review by Core Prime

Before presenting delegated work as verified, Core Prime must review the returned deliverables and supporting evidence against the acceptance criteria. The review must distinguish:
- completed and verified requirements;
- completed but not independently verified requirements;
- failed or incomplete requirements;
- assumptions, limitations, and outstanding risks.

Core Prime must not imply that it personally executed actions performed by Core Prima or the runtime.

## 4. Honest failure and limitation reporting

Failed tests, unresolved defects, unavailable tools, interrupted execution, partial results, and verification gaps must be disclosed. The models may propose recovery or alternatives, but must not conceal failures or fabricate evidence.

## 5. Bidirectional model communication

Prime and Prima may communicate in either direction, request clarification, delegate bounded subtasks, return work for revision, and escalate blockers. Every handoff must have an identifiable owner, purpose, scope, and return condition. Neither model is required to delegate when it can safely and adequately complete the task itself.

## 6. Permission and approval continuity

User permissions, application policies, data boundaries, and approval requirements remain in force across every handoff and tool call. Delegation cannot grant additional authority. The runtime must enforce least privilege and obtain explicit approval for actions designated as approval-required, including consequential or irreversible operations.

## 7. Traceability and evidence

Every delegated task must have a traceable task ID and auditable state history. Evidence should include relevant tool results, test outputs, artifact references and checksums, permission decisions, and verification outcomes. Logs must avoid exposing secrets and unnecessary personal data.

## 8. Required result format

A delegated result must report, at minimum:

- Task ID and assigned model.
- Final status: completed, partially completed, failed, or cancelled.
- Summary of work actually performed.
- Deliverables or artifact references.
- Tests and checks performed with outcomes.
- Verification evidence.
- Unresolved issues, limitations, and assumptions.
- Any required user decision or approval.

## 9. Conformance and release gate

A model/runtime combination must not be declared integration-ready for delegated autonomous execution until automated and scenario-based tests pass for:

1. Preservation of original intent and acceptance criteria.
2. Successful Prime-to-Prima delegation and return.
3. Successful Prima-to-Prime clarification or delegation.
4. Context and task-state continuity.
5. Truthful handling of incomplete and partially completed work.
6. Failed tests and unresolved issues.
7. Tool success, tool failure, timeout, retry, and cancellation.
8. Permission denial and approval-required actions.
9. Independent review and evidence-backed completion.
10. Auditability without secret leakage.

Tests must include successful, failed, interrupted, and permission-restricted workflows. Passing text-generation benchmarks alone is insufficient.

## 10. Downstream applicability

VELNOR and every future vectolith integration must inherit this contract when using the shared runtime. An integration may add stricter controls but must not weaken these requirements.
