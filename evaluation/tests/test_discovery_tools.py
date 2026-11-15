from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation import discover_hf_candidates, probe_compute


class CandidateDiscoveryTests(unittest.TestCase):
    def test_snapshot_pins_revision_and_does_not_infer_training_permission(self):
        metadata = {
            "sha": "a" * 40,
            "private": False,
            "gated": False,
            "pipeline_tag": "text-generation",
            "library_name": "transformers",
            "siblings": [{"rfilename": "README.md"}, {"rfilename": "LICENSE"}, {"rfilename": "model.safetensors"}],
            "cardData": {"license": "apache-2.0", "architectures": ["ExampleForCausalLM"]},
            "tags": ["license:apache-2.0"],
        }
        with patch.object(discover_hf_candidates, "get_json", return_value=metadata), patch.object(
            discover_hf_candidates, "get_text", side_effect=["license text", "model card"]
        ):
            record = discover_hf_candidates.snapshot("org/model")
        self.assertEqual(record["immutable_revision"], "a" * 40)
        self.assertEqual(record["license_tag"], "apache-2.0")
        self.assertTrue(record["license_file_present"])
        self.assertEqual(record["training_output_permission"], "not_verified")
        self.assertEqual(record["teacher_qualification"], "not_qualified")

    def test_snapshot_rejects_mutable_or_missing_revision(self):
        with patch.object(discover_hf_candidates, "get_json", return_value={"sha": "main"}):
            with self.assertRaises(ValueError):
                discover_hf_candidates.snapshot("org/model")


class ComputeProbeTests(unittest.TestCase):
    def test_environment_markers_do_not_claim_quota(self):
        with patch.dict("os.environ", {"KAGGLE_KERNEL_RUN_TYPE": "Interactive"}, clear=True):
            self.assertEqual(probe_compute.detect_environment(), ["kaggle"])

    def test_probe_schema_keeps_account_status_unverified(self):
        self.assertEqual(probe_compute.detect_environment(), [])
        # Account-level entitlements cannot be inferred from local hardware.
        record = {"account_eligibility": "not_verified", "provider_quota": "not_observable_from_generic_process"}
        self.assertEqual(record["account_eligibility"], "not_verified")


if __name__ == "__main__":
    unittest.main()
