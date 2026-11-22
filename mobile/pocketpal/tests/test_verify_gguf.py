import importlib.util
import tempfile
import os
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

    def test_manifest_creation_refuses_overwrite_and_is_private(self):
        import sys
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tiny.gguf"
            path.write_bytes(b"GGUFpayload")
            manifest = Path(directory) / "manifest.json"
            argv = ["verify_gguf.py", str(path), "--manifest", str(manifest)]
            with patch.object(sys, "argv", argv):
                MODULE.main()
            self.assertTrue(manifest.exists())
            if os.name == "posix":
                self.assertEqual(manifest.stat().st_mode & 0o777, 0o600)
            original = manifest.read_bytes()
            with patch.object(sys, "argv", argv):
                with self.assertRaises(SystemExit):
                    MODULE.main()
            self.assertEqual(manifest.read_bytes(), original)

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
