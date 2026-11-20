from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vectolith_runtime.compute_probe import collect_resource_probe


class ComputeProbeTests(unittest.TestCase):
    def test_probe_is_no_training_and_contains_measured_resource_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = collect_resource_probe(tmp)
        self.assertEqual(report["schema_version"], "vectolith-core-prime-resource-probe/1.0")
        self.assertIn("available_bytes", report["memory"])
        self.assertIn("available_bytes", report["storage"])
        self.assertEqual(report["safety"], {
            "model_weights_downloaded": False,
            "inference_started": False,
            "training_started": False,
            "network_requests_made": False,
        })
        digest = report.pop("resource_probe_sha256")
        canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.assertEqual(digest, hashlib.sha256(canonical.encode("utf-8")).hexdigest())

    def test_probe_handles_missing_nvidia_smi(self):
        with patch("vectolith_runtime.compute_probe.subprocess.run", side_effect=FileNotFoundError):
            with tempfile.TemporaryDirectory() as tmp:
                report = collect_resource_probe(tmp)
        self.assertEqual(report["accelerators"]["gpu_count"], 0)
        self.assertEqual(report["accelerators"]["devices"], [])


if __name__ == "__main__":
    unittest.main()
