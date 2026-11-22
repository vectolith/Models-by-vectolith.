import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "verify_gguf.py"
SPEC = importlib.util.spec_from_file_location("verify_gguf", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class VerifyGGUFTests(unittest.TestCase):
    def test_valid_magic_and_manifest_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiny.gguf"
            path.write_bytes(b"GGUF" + b"test payload")
            result = MODULE.verify(path, "example/model", "a" * 40, "Q4_K_M")
            self.assertEqual(result["format"], "GGUF")
            self.assertEqual(result["size_bytes"], 12)
            self.assertEqual(result["model_id"], "example/model")
            self.assertEqual(len(result["sha256"]), 64)

    def test_rejects_wrong_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.gguf"
            path.write_bytes(b"NOPE")
            with self.assertRaises(ValueError):
                MODULE.verify(path, None, None, None)

    def test_rejects_too_small_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiny.gguf"
            path.write_bytes(b"GG")
            with self.assertRaises(ValueError):
                MODULE.verify(path, None, None, None)

    def test_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.gguf"
            with self.assertRaises(ValueError):
                MODULE.verify(path, None, None, None)


if __name__ == "__main__":
    unittest.main()
