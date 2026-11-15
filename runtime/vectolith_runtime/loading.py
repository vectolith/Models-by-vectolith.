"""Provider-neutral loading and execution of registered model backends."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Protocol
from .contracts import TaskRequest, TaskResult
from .engine import ModelExecutor
from .registry import ModelLifecycle, ModelManifest, ModelRegistry

class ModelLoader(Protocol):
    """Trusted adapter that resolves a manifest into an executable task handler."""
    async def load(self, manifest: ModelManifest) -> ModelExecutor: ...

class ModelLoaderRegistry:
    """Explicit allowlist of backend adapters; never imports code named by a manifest."""
    def __init__(self) -> None:
        self._loaders: dict[str, ModelLoader] = {}

    def register(self, backend_type: str, loader: ModelLoader, *, replace: bool = False) -> None:
        if not backend_type.strip():
            raise ValueError("backend_type must not be empty")
        if backend_type in self._loaders and not replace:
            raise ValueError(f"loader already registered: {backend_type}")
        self._loaders[backend_type] = loader

    def get(self, backend_type: str) -> ModelLoader:
        try:
            return self._loaders[backend_type]
        except KeyError as exc:
            raise LookupError(f"no trusted loader registered for backend: {backend_type}") from exc

@dataclass(frozen=True, slots=True)
class LoadedModel:
    manifest: ModelManifest
    executor: ModelExecutor
    backend_type: str

class ModelRuntime:
    """Loads approved manifests and dispatches tasks to executable adapters.

    Each manifest declares a backend_type metadata entry. The application must
    explicitly register that backend's trusted loader. Only RELEASED models load
    by default; development/evaluation loading requires an explicit opt-in.
    """
    def __init__(self, registry: ModelRegistry, loaders: ModelLoaderRegistry) -> None:
        self.registry = registry
        self.loaders = loaders
        self._loaded: dict[str, LoadedModel] = {}
        self._lock = asyncio.Lock()

    async def load_model(self, model_id: str, *, allow_non_released: bool = False) -> LoadedModel:
        async with self._lock:
            if model_id in self._loaded:
                return self._loaded[model_id]
            manifest = self.registry.get(model_id)
            if manifest.lifecycle in {ModelLifecycle.DEPRECATED, ModelLifecycle.RETIRED}:
                raise PermissionError(f"model lifecycle prevents loading: {manifest.lifecycle.value}")
            if manifest.lifecycle != ModelLifecycle.RELEASED and not allow_non_released:
                raise PermissionError(
                    "model is not released; pass allow_non_released=True for controlled evaluation"
                )
            backend_type = dict(manifest.metadata).get("backend_type")
            if not backend_type:
                raise ValueError(f"model manifest has no backend_type: {model_id}")
            loader = self.loaders.get(backend_type)
            executor = await loader.load(manifest)
            if not callable(executor):
                raise TypeError("model loader must return an async-compatible executor")
            loaded = LoadedModel(manifest, executor, backend_type)
            self._loaded[model_id] = loaded
            return loaded

    async def unload_model(self, model_id: str) -> bool:
        async with self._lock:
            return self._loaded.pop(model_id, None) is not None

    def loaded_models(self) -> tuple[str, ...]:
        return tuple(sorted(self._loaded))

    async def execute(
        self, model_id: str, task: TaskRequest, *, allow_non_released: bool = False
    ) -> TaskResult:
        loaded = await self.load_model(model_id, allow_non_released=allow_non_released)
        result = await loaded.executor(task)
        if not isinstance(result, TaskResult):
            raise TypeError("model executor must return TaskResult")
        if result.task_id != task.task_id:
            raise ValueError("model executor returned a mismatched task_id")
        return result
