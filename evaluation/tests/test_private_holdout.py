from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from evaluation.run_private_holdout import MANIFEST_SCHEMA, load_private_holdout


class PrivateHoldoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        if os.name == "posix":
            self.root.chmod(0o700)
        self.suite = self.root / "prime.jsonl"
        self.suite.write_text(json.dumps({
            "id": "private-001",
            "category": "reasoning",
            "messages": [{"role": "user", "content": "What is 2 + 2?"}],
            "rubric": ["Returns four"],
        }) + "\n", encoding="utf-8")
        self.manifest = self.root / "manifest.json"
        digest = hashlib.sha256(self.suite.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps({
            "schema_version": MANIFEST_SCHEMA,
            "dataset_version": "holdout-2026-01",
            "sha256": digest,
            "case_count": 1,
            "access_control": "restricted",
            "authorized_roles": ["ash_prime"],
        }), encoding="utf-8")
        if os.name == "posix":
            self.suite.chmod(0o600)
            self.manifest.chmod(0o600)

    def tearDown(self):
        self.temp.cleanup()

    def test_accepts_external_hash_pinned_restricted_suite(self):
        digest = hashlib.sha256(self.suite.read_bytes()).hexdigest()
        cases, metadata = load_private_holdout(
            self.suite, self.manifest, digest, "holdout-2026-01", "ash_prime"
        )
        self.assertEqual(len(cases), 1)
        self.assertEqual(metadata["dataset_version"], "holdout-2026-01")

    def test_rejects_wrong_hash(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            load_private_holdout(self.suite, self.manifest, "0" * 64, "holdout-2026-01", "ash_prime")

    def test_rejects_unauthorized_role(self):
        digest = hashlib.sha256(self.suite.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "not authorized"):
            load_private_holdout(self.suite, self.manifest, digest, "holdout-2026-01", "fyr_prima")

    def test_rejects_unrestricted_manifest(self):
        digest = hashlib.sha256(self.suite.read_bytes()).hexdigest()
        manifest = json.loads(self.manifest.read_text())
        manifest["access_control"] = "public"
        self.manifest.write_text(json.dumps(manifest))
        if os.name == "posix":
            self.manifest.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "access_control=restricted"):
            load_private_holdout(self.suite, self.manifest, digest, "holdout-2026-01", "ash_prime")


if __name__ == "__main__":
    unittest.main()
