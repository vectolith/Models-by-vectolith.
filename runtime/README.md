# Vectolith Runtime — reference implementation

This package is the first executable foundation for the reusable vectolith orchestration layer. It is model- and provider-neutral: integrations register model manifests and provider-specific executors rather than depending on a fixed model roster or vendor SDK.

## Current capabilities

- Versioned task request/result contracts.
- Extensible in-memory registry and durable SQLite model registry.
- Shared family identity contract validation.
- Capability and modality discovery across any number of registered models.
- Model lifecycle filtering and released-only loading by default.
- Async model-executor routing and explicit trusted backend loader registration.
- Runtime model load/unload and task-result validation.
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

## Durable registry

SQLite persists model manifests across process restarts. Use a filesystem path for durability; `:memory:` is intended for tests.

```python
from vectolith_runtime import SQLiteModelRegistry

with SQLiteModelRegistry("data/models.sqlite3") as registry:
    print(registry.list_models())
```

## Loading a registered backend

A manifest must declare a `backend_type` metadata entry. The application must register the matching trusted loader; manifests cannot trigger dynamic imports or execute arbitrary paths. Released models load by default. Development/evaluation loading requires explicit opt-in, and deprecated or retired models cannot load.

```python
from vectolith_runtime import ModelLoaderRegistry, ModelRuntime

loaders = ModelLoaderRegistry()
loaders.register("your-provider", your_provider_loader)
runtime = ModelRuntime(registry, loaders)
loaded = await runtime.load_model("model-id")
result = await runtime.execute("model-id", task_request)
```

A loader implements the async `load(manifest)` protocol and returns an async-compatible executor accepting a `TaskRequest` and returning a `TaskResult`.

## Quick start

Python 3.11+ is required.

~~~bash
python -m pip install -e .
python -m unittest discover -s tests -v
~~~

See the [model family specification](../docs/model-family-specification.md), [identity contract](../docs/shared-identity-contract.md), [registry design](../docs/model-registry-and-capabilities.md), and [overall architecture](../docs/architecture.md).

## Important limitations

This remains a reference implementation, not a production-ready agent platform. SQLite persistence covers model manifests only; task state remains in-memory. The repository does not yet ship a concrete Hugging Face, vLLM, llama.cpp, hosted API, or other model-provider adapter, nor does it download weights. Applications must supply and secure their own loaders. Authentication/authorization, signed release metadata, health/availability integration, tenant isolation, policy-engine integration, approval UI, sandboxed tool execution, observability exporters, retries/deadlines, and production deployment controls remain future work. Registry membership never implies that weights exist, are loaded, released, or executable.
