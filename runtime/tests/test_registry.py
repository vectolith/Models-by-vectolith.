import unittest
from vectolith_runtime import FamilyIdentity, ModelLifecycle, ModelManifest, ModelRegistry
from vectolith_runtime.registry import CORE_PRIME_TARGET_CAPABILITIES

def manifest(model_id="core-prime", *, capabilities=frozenset({"reasoning", "conversation"}), **kwargs):
    return ModelManifest(
        model_id=model_id, display_name=model_id.replace("-", " ").title(),
        version="0.1.0", specialization="general-purpose reasoning",
        capabilities=capabilities, **kwargs,
    )

class ModelRegistryTests(unittest.TestCase):
    def test_prime_target_profile_includes_former_prima_engineering_scope(self):
        required = {
            "coding.generation", "software.architecture.design",
            "software.debugging", "software.testing", "software.review",
            "tools.structured_use", "agents.task_execution",
            "verification.results", "reasoning.mathematical",
        }
        self.assertTrue(required.issubset(CORE_PRIME_TARGET_CAPABILITIES))
        self.assertIn("research.evidence_synthesis", CORE_PRIME_TARGET_CAPABILITIES)

    def test_register_and_get_model(self):
        registry = ModelRegistry()
        item = manifest()
        registry.register(item)
        self.assertEqual(registry.get("core-prime"), item)

    def test_registry_is_not_limited_to_prime_and_prima(self):
        registry = ModelRegistry()
        for model_id in ("core-prime", "core-prima", "vision-specialist", "math-specialist"):
            registry.register(manifest(model_id))
        self.assertEqual(len(registry.list_models()), 4)

    def test_duplicate_registration_requires_explicit_replace(self):
        registry = ModelRegistry()
        registry.register(manifest())
        with self.assertRaises(ValueError):
            registry.register(manifest(capabilities=frozenset({"coding"})))
        registry.register(manifest(capabilities=frozenset({"coding"})), replace=True)
        self.assertEqual(registry.get("core-prime").capabilities, frozenset({"coding"}))

    def test_foreign_identity_is_rejected(self):
        registry = ModelRegistry()
        with self.assertRaises(ValueError):
            registry.register(manifest(identity=FamilyIdentity(family="other-family")))

    def test_capability_discovery_requires_all_requested_capabilities(self):
        registry = ModelRegistry()
        registry.register(manifest("reasoner", capabilities=frozenset({"reasoning", "conversation"})))
        registry.register(manifest("coder", capabilities=frozenset({"coding", "tool-use"})))
        found = registry.discover(frozenset({"coding", "tool-use"}))
        self.assertEqual([item.model_id for item in found], ["coder"])

    def test_discovery_filters_modalities_and_release_state(self):
        registry = ModelRegistry()
        registry.register(manifest("text-model", lifecycle=ModelLifecycle.RELEASED))
        registry.register(manifest(
            "vision-model", modalities_in=frozenset({"text", "image"}),
            lifecycle=ModelLifecycle.DEVELOPMENT,
        ))
        self.assertEqual([m.model_id for m in registry.discover(input_modality="image")], ["vision-model"])
        self.assertEqual([m.model_id for m in registry.discover(include_non_released=False)], ["text-model"])

    def test_lifecycle_listing_and_unregister(self):
        registry = ModelRegistry()
        registry.register(manifest("a", lifecycle=ModelLifecycle.RELEASED))
        registry.register(manifest("b", lifecycle=ModelLifecycle.EXPERIMENTAL))
        self.assertEqual([m.model_id for m in registry.list_models(lifecycle=ModelLifecycle.RELEASED)], ["a"])
        self.assertEqual(registry.unregister("a").model_id, "a")
        with self.assertRaises(KeyError):
            registry.get("a")

    def test_manifest_requires_capabilities(self):
        with self.assertRaises(ValueError):
            manifest(capabilities=frozenset())

if __name__ == "__main__":
    unittest.main()
