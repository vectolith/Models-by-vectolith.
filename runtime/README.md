# Vectolith Runtime — reference implementation

This package provides a model- and provider-neutral orchestration layer. Applications register model manifests and explicitly trusted backend adapters rather than depending on a fixed model roster or vendor SDK.

## Current capabilities

- Versioned task request/result contracts.
- Extensible in-memory registry and durable SQLite model registry.
- Shared family identity validation and capability/modality discovery.
- Async model-executor routing and explicit backend loader registration.
- Lifecycle-gated model loading (released by default; controlled development/evaluation opt-in).
- Runtime model unload and execution with task-result validation.
- In-memory task lifecycle/event history and tool permission/approval gates.
- Completion evidence requirement and independent review hook.

## Quick start

Python 3.11+ is required.

~~~bash
python -m pip install -e .
python -m unittest discover -s tests -v
~~~

### Durable registry

~~~python
from vectolith_runtime import SQLiteModelRegistry

with SQLiteModelRegistry("data/models.sqlite3") as registry:
    # registry.register(manifest)
    print(registry.list_models())
~~~

The SQLite database persists model manifests across process restarts. Use a filesystem path for durability; the special in-memory SQLite database is intended for tests.

### Loading a registered backend

A manifest must include a `backend_type` metadata entry. The application registers the matching trusted adapter; manifests cannot cause arbitrary Python imports or execute arbitrary paths.

~~~python
from vectolith_runtime import ModelLoaderRegistry, ModelRuntime

loaders = ModelLoaderRegistry()
loaders.register("your-provider", your_provider_loader)
runtime = ModelRuntime(registry, loaders)
loaded = await runtime.load_model("model-id")  # released models only by default
result = await runtime.execute("model-id", task_request)
~~~

Development/evaluation models require `allow_non_released=True`. Deprecated and retired models cannot be loaded. A loader implements the async `load(manifest)` protocol and returns an async-compatible executor that accepts a `TaskRequest` and returns a `TaskResult`.

See the [model family specification](../docs/model-family-specification.md), [identity contract](../docs/shared-identity-contract.md), [registry design](../docs/model-registry-and-capabilities.md), and [overall architecture](../docs/architecture.md).

## Important limitations

This remains a reference implementation, not a production-ready agent platform. SQLite persistence covers model manifests only; task state remains in-memory. The repository does not yet ship a concrete Hugging Face, vLLM, llama.cpp, hosted API, or other model-provider adapter, nor does it download weights. Applications must supply and secure their own loaders. Authentication/authorization, signed release metadata, health/availability integration, tenant isolation, policy-engine integration, approval UI, sandboxed tool execution, observability exporters, retries/deadlines, and production deployment controls remain future work. Registry membership never implies that weights exist, are loaded, released, or executable.
