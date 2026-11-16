from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from evaluation.snapshot_additional_teacher import EXPECTED, main


REVISION = "0123456789abcdef0123456789abcdef01234567"


class AdditionalTeacherSnapshotTests(unittest.TestCase):
    def test_three_additional_candidates_have_explicit_architecture_expectations(self):
        self.assertEqual(set(EXPECTED), {"smollm3-3b", "lfm2.5-2.6b", "phi-4-mini-instruct"})
        self.assertEqual(EXPECTED["smollm3-3b"]["repo"], "HuggingFaceTB/SmolLM3-3B")
        self.assertEqual(EXPECTED["smollm3-3b"]["model_type"], "smollm3")
        self.assertEqual(EXPECTED["lfm2.5-2.6b"]["repo"], "LiquidAI/LFM2.5-2.6B")
        self.assertEqual(EXPECTED["lfm2.5-2.6b"]["license"], "lfm1.0")
        self.assertEqual(EXPECTED["phi-4-mini-instruct"]["repo"], "microsoft/Phi-4-mini-instruct")
        self.assertEqual(EXPECTED["phi-4-mini-instruct"]["license"], "mit")

    def test_every_candidate_has_an_explicit_model_architecture(self):
        for candidate in EXPECTED.values():
            self.assertTrue(candidate["model_type"])
            self.assertTrue(candidate["architectures"])
            self.assertEqual(len(candidate["architectures"]), 1)

    def _run_snapshot(self, root: Path, include_license: bool):
        snapshot = root / REVISION
        snapshot.mkdir()
        (snapshot / "config.json").write_text(json.dumps({
            "model_type": "smollm3",
            "architectures": ["SmolLM3ForCausalLM"],
        }), encoding="utf-8")
        (snapshot / "weights.safetensors").write_bytes(b"test-weights")
        if include_license:
            (snapshot / "LICENSE").write_text("Apache License", encoding="utf-8")

        card_data = SimpleNamespace(to_dict=lambda: {"license": "apache-2.0"})
        info = SimpleNamespace(
            sha=REVISION,
            gated=False,
            private=False,
            disabled=False,
            card_data=card_data,
            last_modified=None,
        )

        class FakeApi:
            def model_info(self, repo, revision, files_metadata):
                self.request = (repo, revision, files_metadata)
                return info

        hub = types.ModuleType("huggingface_hub")
        hub.HfApi = FakeApi
        hub.snapshot_download = lambda **kwargs: str(snapshot)
        output = root / "artifacts" / "smollm3.json"
        argv = [
            "snapshot_additional_teacher.py",
            "--candidate-id", "smollm3-3b",
            "--output", str(output),
            "--cache-dir", str(root / "cache"),
        ]
        with patch.dict(sys.modules, {"huggingface_hub": hub}), patch.object(sys, "argv", argv):
            exit_code = main()
        return exit_code, output

    def test_missing_license_file_preserves_immutable_manifest_and_blocks_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, output = self._run_snapshot(Path(tmp), include_license=False)
            self.assertEqual(exit_code, 1)
            self.assertTrue(output.exists())
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["immutable_revision"], REVISION)
            self.assertTrue(manifest["snapshot_is_immutable"])
            self.assertEqual(manifest["license_tag"], "apache-2.0")
            self.assertEqual(manifest["license_file_status"], "missing")
            self.assertEqual(manifest["license_files"], [])
            self.assertEqual(manifest["snapshot_validation_status"], "blocked_missing_license_file")
            self.assertEqual(manifest["license_review"], "pending_human_legal_review")
            self.assertEqual(manifest["training_output_permission"], "not_verified")
            self.assertEqual(manifest["teacher_qualification"], "not_qualified")
            self.assertFalse(manifest["training_started"])
            self.assertGreater(manifest["file_count"], 0)

    def test_license_file_presence_completes_snapshot_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            exit_code, output = self._run_snapshot(Path(tmp), include_license=True)
            self.assertEqual(exit_code, 0)
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(manifest["license_file_status"], "present")
            self.assertEqual(manifest["snapshot_validation_status"], "complete")
            self.assertEqual(len(manifest["license_files"]), 1)
            self.assertFalse(manifest["training_started"])


if __name__ == "__main__":
    unittest.main()
