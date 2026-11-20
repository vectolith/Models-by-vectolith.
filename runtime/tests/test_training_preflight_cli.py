from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "core_prime_training_preflight.py"


class TrainingPreflightCliTests(unittest.TestCase):
    def test_missing_evidence_fails_closed_and_writes_blocked_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "evidence" / "preflight.json"
            config = {
                "run_metadata": {"approved_by": "Maintainer", "date": "2026-11-17"},
                "model": {"base_model": "publisher/model"},
                "sft_hyperparameters": {
                    "max_sequence_length": 4096, "epochs": 3, "learning_rate": 0.000015,
                    "per_device_batch_size": 2, "gradient_accumulation_steps": 4,
                    "validation_fraction": 0.1, "seed": 42, "lora": {"enabled": True},
                },
            }
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            command = [
                sys.executable, str(SCRIPT),
                "--dataset", str(root / "missing.jsonl"),
                "--foundation-model", "publisher/model",
                "--foundation-revision", "b" * 40,
                "--foundation-selection", str(root / "foundation.json"),
                "--teacher-manifests", str(root / "teachers"),
                "--holdout-deployment", str(root / "holdout.json"),
                "--holdout-results", str(root / "holdout-results"),
                "--execution-manifest", str(root / "execution.json"),
                "--training-code-revision", "d" * 40,
                "--training-config", str(config_path),
                "--report", str(report),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 1)
            self.assertTrue(report.is_file())
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["authorization"], "not_granted")
            self.assertTrue(payload["errors"])
            self.assertNotIn("preflight", payload)

    def test_yaml_config_mapping_matches_trainer_contract(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML is not installed in this test environment")
        sys.path.insert(0, str(SCRIPT.parent))
        import core_prime_training_preflight as cli

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approved.yaml"
            path.write_text(
                "run_metadata:\n  approved_by: Maintainer\n  date: '2026-11-17'\n"
                "model:\n  base_model: publisher/model\n"
                "sft_hyperparameters:\n  max_sequence_length: 4096\n  epochs: 3\n"
                "  learning_rate: 0.000015\n  per_device_batch_size: 2\n"
                "  gradient_accumulation_steps: 4\n  validation_fraction: 0.1\n"
                "  seed: 42\n  lora:\n    enabled: true\n",
                encoding="utf-8",
            )
            config = cli._load_config(path, "publisher/model")
            self.assertEqual(config["max_seq_length"], 4096)
            self.assertEqual(config["epochs"], 3)
            self.assertTrue(config["use_lora"])


if __name__ == "__main__":
    unittest.main()
