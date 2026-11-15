import unittest
from vectolith_runtime import (
    ModelLifecycle, ModelLoaderRegistry, ModelManifest, ModelRegistry,
    ModelRuntime, TaskRequest, TaskResult, TaskStatus, ModelRole,
)

def manifest(model_id="test-model", lifecycle=ModelLifecycle.RELEASED):
    return ModelManifest(
        model_id=model_id, display_name=model_id, version="1.0.0",
        specialization="test execution", capabilities=frozenset({"reasoning"}),
        lifecycle=lifecycle, metadata=(("backend_type", "fake"),),
    )

def task():
    return TaskRequest(
        task_id="load-1", requester_model=ModelRole.CORE_PRIME,
        assigned_model=ModelRole.CORE_PRIMA, user_request="run",
        objective="execute test task",
    )

class FakeLoader:
    def __init__(self):
        self.loaded = []
    async def load(self, model_manifest):
        self.loaded.append(model_manifest.model_id)
        async def execute(request):
            return TaskResult(request.task_id, TaskStatus.COMPLETED, "executed", evidence=("fake backend",))
        return execute

class ModelLoadingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.registry = ModelRegistry()
        self.loader = FakeLoader()
        self.loaders = ModelLoaderRegistry()
        self.loaders.register("fake", self.loader)
        self.runtime = ModelRuntime(self.registry, self.loaders)

    async def test_released_model_loads_and_executes(self):
        self.registry.register(manifest())
        result = await self.runtime.execute("test-model", task())
        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertEqual(self.runtime.loaded_models(), ("test-model",))
        self.assertEqual(self.loader.loaded, ["test-model"])

    async def test_non_released_requires_explicit_opt_in(self):
        self.registry.register(manifest(lifecycle=ModelLifecycle.DEVELOPMENT))
        with self.assertRaises(PermissionError):
            await self.runtime.load_model("test-model")
        await self.runtime.load_model("test-model", allow_non_released=True)

    async def test_retired_model_never_loads(self):
        self.registry.register(manifest(lifecycle=ModelLifecycle.RETIRED))
        with self.assertRaises(PermissionError):
            await self.runtime.load_model("test-model", allow_non_released=True)

    async def test_missing_backend_is_not_loaded(self):
        self.registry.register(ModelManifest(
            model_id="no-backend", display_name="No backend", version="1",
            specialization="test", capabilities=frozenset({"reasoning"}),
            lifecycle=ModelLifecycle.RELEASED,
        ))
        with self.assertRaises(ValueError):
            await self.runtime.load_model("no-backend")

    async def test_unknown_loader_is_not_loaded(self):
        self.registry.register(ModelManifest(
            model_id="unknown", display_name="Unknown", version="1",
            specialization="test", capabilities=frozenset({"reasoning"}),
            lifecycle=ModelLifecycle.RELEASED,
            metadata=(("backend_type", "not-installed"),),
        ))
        with self.assertRaises(LookupError):
            await self.runtime.load_model("unknown")

    async def test_unload(self):
        self.registry.register(manifest())
        await self.runtime.load_model("test-model")
        self.assertTrue(await self.runtime.unload_model("test-model"))
        self.assertFalse(await self.runtime.unload_model("test-model"))

if __name__ == "__main__":
    unittest.main()
