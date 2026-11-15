# Central model registry and capability discovery

## Responsibilities

The central registry is the runtime's model catalogue. It stores versioned manifests and provides discovery; it does not itself host weights, execute inference, grant tool permissions, or certify a model as safe.

A manifest declares:
- Stable model ID, display name, version, and specialization.
- Vectolith identity-contract version and safety-baseline identifier.
- Capabilities as machine-readable identifiers.
- Supported input and output modalities.
- Lifecycle/release state.
- Foundation and serving-adapter references where known.
- Optional metadata, evaluation record references, and resource constraints as the schema evolves.

## Discovery and routing

Callers request required capabilities and optional modality constraints. Discovery returns every compatible registered candidate, not a hidden single winner. The orchestrator then applies policy: release eligibility, evaluation evidence, latency/resource budgets, availability, permissions, and task-specific suitability.

Capability identifiers should be stable, namespaced where useful, and documented. Free-form marketing descriptions must not substitute for machine-readable capabilities. An empty or unknown capability set is not a wildcard.

## Lifecycle semantics

Experimental, development, and evaluation entries may be discoverable for development workflows but must not be routed to production by default. Only released entries are eligible for normal production routing. Deprecated entries may remain available for controlled migration; retired entries must not be selected.

## Governance and operational boundaries

Registration validates schema, unique IDs, and family identity compatibility. Updating an existing ID requires an explicit replacement operation and creates an auditable version change in persistent implementations. Registry membership never bypasses authorization or tool approval.

The initial Python registry is an in-memory reference implementation. A production backend must add durable storage, atomic updates, authentication/authorization, audit history, tenancy boundaries where applicable, health/availability integration, and signed or otherwise trusted release metadata.
