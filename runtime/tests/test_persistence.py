import tempfile
import unittest
from pathlib import Path
from vectolith_runtime import FamilyIdentity, ModelLifecycle, ModelManifest, SQLiteModelRegistry

def manifest(model_id="core-prime", **kwargs):
    values = {
        "display_name": model_id,
        "version": "1.2.0",
        "specialization": "reasoning",
        "capabilities": frozenset({"reasoning", "tool-use"}),
    }
    values.update(kwargs)
    return ModelManifest(model_id=model_id, **values)

class SQLiteRegistryTests(unittest.TestCase):
    def test_manifest_survives_close_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "models.sqlite3"
            registry = SQLiteModelRegistry(database)
            item = manifest(
                lifecycle=ModelLifecycle.RELEASED, foundation="foundation-x",
                adapter_id="adapter-123", modalities_in=frozenset({"text", "image"}),
                metadata=(("backend_type", "test"), ("endpoint", "local")),
            )
            registry.register(item)
            registry.close()
            reopened = SQLiteModelRegistry(database)
            self.assertEqual(reopened.get(item.model_id), item)
            reopened.close()

    def test_duplicate_requires_replace_and_replacement_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "models.sqlite3"
            registry = SQLiteModelRegistry(database)
            registry.register(manifest())
            replacement = manifest(version="2.0.0")
            with self.assertRaises(ValueError):
                registry.register(replacement)
            registry.register(replacement, replace=True)
            registry.close()
            reopened = SQLiteModelRegistry(database)
            self.assertEqual(reopened.get("core-prime").version, "2.0.0")
            reopened.close()

    def test_unregister_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "models.sqlite3"
            registry = SQLiteModelRegistry(database)
            registry.register(manifest())
            registry.unregister("core-prime")
            registry.close()
            reopened = SQLiteModelRegistry(database)
            self.assertEqual(reopened.list_models(), ())
            reopened.close()

    def test_foreign_identity_is_rejected_without_persisting(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = SQLiteModelRegistry(Path(directory) / "models.sqlite3")
            with self.assertRaises(ValueError):
                registry.register(manifest(identity=FamilyIdentity(family="foreign")))
            self.assertEqual(registry.list_models(), ())
            registry.close()

if __name__ == "__main__":
    unittest.main()
