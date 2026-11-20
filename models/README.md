# Models by vectolith — extensible model family

The model family is not limited to Core Prime and Core Prima. Those are orchestration/general engineering anchors; specialist variants are independently defined by role, capability contract, availability, permissions and lifecycle.

## Initial specialization map (contracts, not deployed model claims)

- **Core Prime** — generalist orchestration, planning, synthesis and verification.
- **Core Prima** — engineering orchestration, implementation planning and engineering verification.
- **Core Research** — source-grounded research and citation auditing.
- **Core Code** — software engineering, review, debugging, test and security workflows.
- **Core Reason** — decomposition, reasoning consistency and verification.
- **Core Safety** — safety, privacy and risk review; advisory, not an approval authority.
- **Core Creative** — ideation, creative writing and design briefs.
- **Core Data** — statistics, analysis, validation and visualization planning.
- **Core Vision** — visual interpretation, enabled only with an actual verified visual backend.
- **Core Audio** — audio/transcription/audio generation, enabled only with actual verified backend capability.
- **Core Agent** — tool/workflow orchestration, bounded by permission and audit records.

The machine-readable registry lives in `registry/registry.json`. The runtime helper validates IDs, capability sets and delegation allowlists, and selects only explicitly available implementations. The registry status `planned` is not a claim that weights, endpoints or services are deployed.

## Delegation contract

1. The orchestrator declares the task, required capabilities, budget, scope, deadline and output schema.
2. Routing uses capability matching and an explicit availability list; planned models are not presumed callable.
3. Delegation targets must be allowlisted by the calling model's registry record.
4. Delegates return results, evidence, limitations and status; they do not silently acquire permissions.
5. The orchestrator validates the result and independently checks critical claims/actions.
6. Safety/privacy/security constraints and user authorization remain in force across delegation.
7. Record model ID/version, task ID, delegated scope, inputs/outputs hashes where appropriate, tool actions and verification outcome.

## Adding a variant

Add a unique registry record with explicit role, capability names, allowlisted delegation targets and constraints; validate it and add tests. Separate capability contract from foundation-model selection, deployment status and model training. Model-specific training/evaluation and release gates remain independent.
