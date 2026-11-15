# Vectolith Runtime — reference implementation

This package is the first executable foundation for the reusable vectolith orchestration layer. It is model- and provider-neutral: integrations register model manifests and provider-specific executors rather than depending on a fixed model roster or vendor SDK.

## Current capabilities

- Versioned task request/result contracts.
- Extensible, thread-safe in-memory model registry.
- Shared family identity contract validation.
- Capability and modality discovery across any number of registered models.
- Model lifecycle filtering, including released-only discovery.
- Async model-executor routing.
- In-memory task lifecycle and event history.
- Tool registry with per-task allowlists and explicit approval gates.
- Completion evidence requirement and independent review hook.

## Quick start

Python 3.11+ is required.

~~~bash
python -m pip install -e .
python -m unittest discover -s tests -v
~~~

See [model family specification](../docs/model-family-specification.md), [identity contract](../docs/shared-identity-contract.md), [registry design](../docs/model-registry-and-capabilities.md), and [runtime architecture](../docs/runtime-architecture.md).

## Important limitations

This is an initial reference implementation, not a production-ready autonomous agent platform. The registry and task state are in-memory and are lost on process restart. Durable storage, distributed workers, authentication/authorization, signed release metadata, health/availability integration, tenant isolation, policy-engine integration, approval UI, sandboxed tool execution, observability exporters, retries/deadlines, and production model adapters remain future work. Registry membership does not imply weights are present, loaded, released, or executable.
