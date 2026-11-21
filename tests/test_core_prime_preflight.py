"""Regression tests for fail-closed Core Prime readiness validation."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "core_prime_preflight.py"
spec = importlib.util.spec_from_file_location("core_prime_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

GATES = ("rights", "grading", "dataset", "holdout", "student", "compute", "experiment", "authorization")

class PreflightTests(unittest.TestCase):
    def make_manifest(self, root, *, authorized=True):
        artifact = root / "evidence.txt"
        artifact.write_text("verified synthetic fixture", encoding="utf-8")
        sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
        gates = {g: {"status":"verified", "reviewer":"fixture-reviewer",
                      "verified_at":"2026-01-01T00:00:00Z",
                      "artifacts":[{"path":"evidence.txt","sha256":sha}]} for g in GATES}
        return {"schema_version":"core-prime-training-readiness/1.0",
                "training_authorized":authorized,"authorization_id":"fixture-auth",
                "gates":gates}

    def write(self, root, data):
        p=root/"manifest.json"
        p.write_text(json.dumps(data),encoding="utf-8")
        return p

    def test_pending_template_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=self.make_manifest(root,authorized=False)
            data["gates"]["rights"]["status"]="pending"
            errors=preflight.validate(self.write(root,data))
            self.assertTrue(any("rights: status" in e for e in errors))
            self.assertTrue(any("training_authorized" in e for e in errors))

    def test_complete_synthetic_fixture_passes_structure_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=self.make_manifest(root)
            self.assertEqual([],preflight.validate(self.write(root,data)))

    def test_missing_gate_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=self.make_manifest(root); del data["gates"]["compute"]
            self.assertTrue(any("compute: missing" in e for e in preflight.validate(self.write(root,data))))

    def test_digest_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=self.make_manifest(root)
            data["gates"]["rights"]["artifacts"][0]["sha256"]="0"*64
            self.assertTrue(any("digest mismatch" in e for e in preflight.validate(self.write(root,data))))

    def test_path_escape_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=self.make_manifest(root)
            data["gates"]["rights"]["artifacts"][0]["path"]="../outside"
            self.assertTrue(any("escapes" in e for e in preflight.validate(self.write(root,data))))

    def test_nonhex_digest_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); data=self.make_manifest(root)
            data["gates"]["rights"]["artifacts"][0]["sha256"]="z"*64
            self.assertTrue(any("hexadecimal" in e for e in preflight.validate(self.write(root,data))))

    def test_non_object_root_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/"manifest.json"; p.write_text("[]",encoding="utf-8")
            self.assertTrue(any("root must be an object" in e for e in preflight.validate(p)))

if __name__=="__main__":
    unittest.main()
