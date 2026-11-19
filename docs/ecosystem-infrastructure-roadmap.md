# Vectolith-native ecosystem infrastructure roadmap

**Status:** Proposed engineering baseline  
**Scope:** Models by vectolith model lifecycle and ecosystem infrastructure. This is model infrastructure, not a mandatory shared runtime for other Vectolith products.

## Existing foundations

The repository already contains model-registry and capability-discovery documentation, a registry implementation and tests, the Vectolith Delegated Execution Contract, model-family identity and release guidance, and runtime/evaluation workflows. This roadmap extends those foundations; it does not replace them or imply they are absent.

## Design principles

- Model-agnostic: no hardcoded two-model assumption and no vendor-specific dependency.
- Registry membership is not qualification. Production dispatch requires explicit release eligibility and policy checks.
- Capability declarations are stable machine-readable identifiers, not prose.
- Delegation preserves intent, acceptance criteria, permission scope and resource limits.
- Model-generated tool requests and results are untrusted until application/runtime validation.
- Traceability must avoid storing secrets or unnecessary user data.
- Product runtimes remain independent; this repository does not impose a shared runtime dependency on other products.
- Changes to model definitions, qualification or release status are auditable and versioned.

## Capability layers

1. **Registry:** versioned model manifests, identity, specialization, modalities, capabilities, lifecycle state, interface versions and evidence references.
2. **Discovery and dispatch policy:** candidate discovery by required capability; explicit filtering for released/qualified status, compatibility, permissions, availability, latency and budget. Discovery must not silently choose a winner.
3. **Delegation protocol:** versioned task envelope and result envelope compatible with the existing VDEC; bounded scopes, clear ownership, status, acceptance criteria and verification evidence.
4. **Tool integration:** MCP-compatible discovery and adapters, tool identity/version, policy checks, input/output validation, timeouts, isolation and audit records. Tool permission never follows from model qualification.
5. **Evaluation and qualification:** capability, correctness, robustness, safety, tool behavior, collaboration, efficiency and regression tests; evidence tied to model revision and evaluation environment. Human grades remain human-generated.
6. **Observability:** structured execution spans/events, timestamps, model and interface revision, task lifecycle, tool calls, retries, errors, verification and outcome. Redact secrets and minimize personal data.
7. **Lifecycle:** development, evaluation, release, deprecation, retirement, rollback and reproducibility. Released students are independently loadable and do not require teacher inference.

## Proposed phased delivery

### Phase 0 — Consolidate existing contracts
- Reconcile registry schema and implementation.
- Verify registry persistence, atomic mutation, authentication, authorization and audit behavior; document gaps rather than claim them.
- Cross-link VDEC, registry, qualification, release and runtime docs.
- Establish conformance tests for schema compatibility and dispatch eligibility.

### Phase 1 — Registry manifest contract
- Publish a machine-readable manifest schema with stable IDs, version, capabilities, modality, lifecycle and evidence references.
- Reject malformed, duplicate, unknown or wildcard-like capability declarations.
- Define backwards compatibility and explicit replacement/versioning.

### Phase 2 — Qualification-aware dispatch
- Discovery returns candidates; a policy layer filters candidates.
- Production eligibility requires released status, evidence and policy compliance.
- Record selection rationale and reject unknown/insufficient qualification.

### Phase 3 — Delegation and trace interoperability
- Add structured task/result envelopes and event/span contracts.
- Preserve intent, constraints, acceptance criteria and approval requirements.
- Require explicit completion/partial/failure/cancelled status and evidence.

### Phase 4 — Tool gateway and security
- Add tool registry, scoped authorization, validation, timeouts and isolation.
- Prevent tool outputs or model outputs from altering permission scope.
- Include security and failure-mode tests.

### Phase 5 — Evaluation and observability
- Integrate structured traces with evaluation artifacts.
- Track quality, regressions, latency, resource use and failures.
- Add privacy-safe retention, access controls and incident workflows.

## Acceptance criteria

- Contracts are machine-readable, versioned and validated by automated tests.
- A development/evaluation/unknown/retired model cannot enter normal production dispatch.
- Candidate discovery and policy selection are separate and inspectable.
- Delegation cannot expand permissions or omit acceptance criteria.
- Trace evidence is bound to exact model/interface revisions.
- Failed, partial, unverified and cancelled work is not reported as completed.
- No external model provider or downstream product is a mandatory dependency.
- All claims of implementation, test results and qualification remain evidence-based.

## Non-goals

This roadmap does not propose copying Microsoft Foundry, adopting Azure as a required provider, creating a single ecosystem-wide product runtime, or replacing existing training/evaluation and independent product boundaries.
