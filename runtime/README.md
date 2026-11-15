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

## Executable multi-teacher distillation

The runtime now includes:
- endpoint-based teacher qualification against role-specific benchmark tasks;
- selection of at least four distinct qualified teachers with competency coverage;
- OpenAI-compatible teacher calls, per-example peer review and provenance-preserving JSONL corpus generation;
- optional LoRA supervised fine-tuning of a selected student foundation;
- independent capability scoring, leave-one-teacher-out ablation hooks, teacher-disabled checks and a fail-closed release decision.

See [the executable pipeline guide](../docs/executable-multi-teacher-pipeline.md) for configuration and execution boundaries. Install optional training dependencies with `python -m pip install -e ".[training]"`.

These components do not select a production teacher or student foundation automatically. Exact model revisions, licenses, provider terms, training-output permissions, held-out evaluation suites, hardware and budget must be reviewed before a run. CI tests do not call providers or start training.

## Quick start

Python 3.11+ is required.

~~~bash
python -m pip install -e .
python -m unittest discover -s tests -v
~~~

See the [model family specification](../docs/model-family-specification.md), [identity contract](../docs/shared-identity-contract.md), [registry design](../docs/model-registry-and-capabilities.md), and [overall architecture](../docs/architecture.md).

## Important limitations

This is an initial reference implementation, not a production-ready autonomous agent platform. The registry and task state are in-memory and are lost on process restart. Durable storage, distributed workers, authentication/authorization, signed release metadata, health/availability integration, tenant isolation, policy-engine integration, approval UI, sandboxed tool execution, observability exporters, retries/deadlines, and production model adapters remain future work. Registry membership does not imply weights are present, loaded, released, or executable.
