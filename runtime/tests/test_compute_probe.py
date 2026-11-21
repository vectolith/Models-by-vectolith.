"""Behavioural tests for the Kaggle resource probe.

The probe is what qualifies a compute provider, so the invariants worth
locking down are: it never leaks credentials from the environment, it
degrades instead of crashing when nvidia-smi or /proc/meminfo are absent or
malformed, and its self-digest actually matches the payload it describes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vectolith_runtime import compute_probe


def _digest(payload: dict) -> str:
    """Recompute the probe digest exactly the way the module defines it."""
    body = {key: value for key, value in payload.items() if key != "resource_probe_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class MemoryProbeTests(unittest.TestCase):
    def test_parses_kibibytes_from_proc_meminfo(self):
        text = "MemTotal:       16384000 kB\nMemFree:  100 kB\nMemAvailable:    8192000 kB\n"
        meminfo = mock.Mock()
        meminfo.is_file.return_value = True
        meminfo.read_text.return_value = text
        with mock.patch.object(compute_probe, "Path", lambda *_: meminfo):
            memory = compute_probe._memory_bytes()
        self.assertEqual(memory["total_bytes"], 16384000 * 1024)
        self.assertEqual(memory["available_bytes"], 8192000 * 1024)

    def test_falls_back_when_lines_lack_kilobyte_units(self):
        meminfo = mock.Mock()
        meminfo.is_file.return_value = True
        meminfo.read_text.return_value = "MemTotal: 12 MB\nHugePages_Total: 0\n"
        with mock.patch.object(compute_probe, "Path", lambda *_: meminfo), \
             mock.patch.object(compute_probe.os, "sysconf", side_effect=[4096, 100, 50]):
            memory = compute_probe._memory_bytes()
        self.assertEqual(memory["total_bytes"], 4096 * 100)
        self.assertEqual(memory["available_bytes"], 4096 * 50)

    def test_falls_back_to_sysconf_when_meminfo_missing(self):
        missing = mock.Mock()
        missing.is_file.return_value = False
        with mock.patch.object(compute_probe, "Path", lambda *_: missing), \
             mock.patch.object(compute_probe.os, "sysconf", side_effect=[4096, 1024, 256]):
            memory = compute_probe._memory_bytes()
        self.assertEqual(memory["total_bytes"], 4096 * 1024)
        self.assertEqual(memory["available_bytes"], 4096 * 256)

    def test_reports_none_when_sysconf_unavailable(self):
        missing = mock.Mock()
        missing.is_file.return_value = False
        with mock.patch.object(compute_probe, "Path", lambda *_: missing), \
             mock.patch.object(compute_probe.os, "sysconf", side_effect=OSError):
            memory = compute_probe._memory_bytes()
        self.assertEqual(memory, {"total_bytes": None, "available_bytes": None})


class GpuProbeTests(unittest.TestCase):
    def _run_with_stdout(self, stdout: str):
        completed = mock.Mock(stdout=stdout)
        with mock.patch.object(compute_probe.subprocess, "run", return_value=completed):
            return compute_probe._gpu_devices()

    def test_parses_multiple_devices(self):
        devices = self._run_with_stdout(
            "NVIDIA T4, 15360, 15000, 535.104.05\nNVIDIA P100, 16384, 12000, 535.104.05\n"
        )
        self.assertEqual([d["name"] for d in devices], ["NVIDIA T4", "NVIDIA P100"])
        self.assertEqual(devices[0]["total_vram_bytes"], 15360 * 1024 * 1024)
        self.assertEqual(devices[1]["free_vram_bytes"], 12000 * 1024 * 1024)
        self.assertEqual(devices[0]["driver_version"], "535.104.05")

    def test_skips_rows_with_wrong_column_count(self):
        self.assertEqual(self._run_with_stdout("NVIDIA T4, 15360, 15000\n"), [])

    def test_skips_rows_with_non_numeric_memory(self):
        self.assertEqual(self._run_with_stdout("NVIDIA T4, [N/A], 15000, 535\n"), [])

    def test_returns_empty_when_nvidia_smi_missing(self):
        with mock.patch.object(compute_probe.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(compute_probe._gpu_devices(), [])

    def test_returns_empty_when_nvidia_smi_fails(self):
        failure = subprocess.CalledProcessError(9, ["nvidia-smi"], stderr="boom")
        with mock.patch.object(compute_probe.subprocess, "run", side_effect=failure):
            self.assertEqual(compute_probe._gpu_devices(), [])

    def test_returns_empty_on_timeout(self):
        with mock.patch.object(compute_probe.subprocess, "run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 10)):
            self.assertEqual(compute_probe._gpu_devices(), [])


class PackageVersionTests(unittest.TestCase):
    def test_returns_version_when_installed(self):
        with mock.patch.object(compute_probe.importlib.metadata, "version", return_value="2.4.1"):
            self.assertEqual(compute_probe._package_version("torch"), "2.4.1")

    def test_returns_none_when_missing(self):
        error = compute_probe.importlib.metadata.PackageNotFoundError("torch")
        with mock.patch.object(compute_probe.importlib.metadata, "version", side_effect=error):
            self.assertIsNone(compute_probe._package_version("torch"))


class ResourceProbeTests(unittest.TestCase):
    def test_never_serialises_kaggle_secret_token(self):
        secret = "kaggle-secret-value-123"
        env = {
            "KAGGLE_KERNEL_RUN_TYPE": "Interactive",
            "KAGGLE_USER_SECRETS_TOKEN": secret,
            "KAGGLE_URL_BASE": "https://www.kaggle.com",
        }
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.dict(compute_probe.os.environ, env, clear=False):
            payload = compute_probe.collect_resource_probe(tmp)
            serialised = json.dumps(payload)
        self.assertNotIn(secret, serialised)
        self.assertNotIn("KAGGLE_USER_SECRETS_TOKEN", payload["environment"]["kaggle"])
        self.assertEqual(payload["environment"]["kaggle"]["KAGGLE_KERNEL_RUN_TYPE"], "Interactive")

    def test_payload_shape_and_digest_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = compute_probe.collect_resource_probe(tmp)
            self.assertTrue(Path(payload["storage"]["path"]).is_dir())
        self.assertEqual(payload["schema_version"], "vectolith-core-prime-resource-probe/1.0")
        self.assertEqual(payload["resource_probe_sha256"], _digest(payload))
        self.assertGreater(payload["storage"]["total_bytes"], 0)

    def test_digest_changes_when_payload_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = compute_probe.collect_resource_probe(tmp)
        tampered = dict(payload, provider="other")
        self.assertNotEqual(tampered["resource_probe_sha256"], _digest(tampered))

    def test_declares_no_destructive_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = compute_probe.collect_resource_probe(tmp)
        self.assertEqual(payload["safety"], {
            "model_weights_downloaded": False,
            "inference_started": False,
            "training_started": False,
            "network_requests_made": False,
        })
        self.assertTrue(payload["account_and_cost"]["quota_must_be_verified_in_kaggle_account_settings"])

    def test_creates_missing_storage_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / "a" / "b"
            payload = compute_probe.collect_resource_probe(nested)
            self.assertTrue(nested.is_dir())
            self.assertEqual(Path(payload["storage"]["path"]), nested.resolve())

    def test_aggregates_gpu_memory(self):
        devices = [
            {"name": "T4", "total_vram_bytes": 100, "free_vram_bytes": 40, "driver_version": "1"},
            {"name": "P100", "total_vram_bytes": 200, "free_vram_bytes": 70, "driver_version": "1"},
        ]
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(compute_probe, "_gpu_devices", return_value=devices):
            payload = compute_probe.collect_resource_probe(tmp)
        accelerators = payload["accelerators"]
        self.assertEqual(accelerators["gpu_count"], 2)
        self.assertEqual(accelerators["total_vram_bytes"], 300)
        self.assertEqual(accelerators["aggregate_free_vram_bytes"], 110)
        self.assertEqual(accelerators["largest_single_gpu_free_vram_bytes"], 70)

    def test_no_gpu_reports_zero_not_null(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(compute_probe, "_gpu_devices", return_value=[]):
            payload = compute_probe.collect_resource_probe(tmp)
        self.assertEqual(payload["accelerators"]["gpu_count"], 0)
        self.assertEqual(payload["accelerators"]["largest_single_gpu_free_vram_bytes"], 0)


class MainEntrypointTests(unittest.TestCase):
    def test_writes_report_and_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nested" / "probe.json"
            with mock.patch.object(compute_probe.sys, "argv", ["compute_probe", "--output", str(output)]), \
                 mock.patch("builtins.print"):
                self.assertEqual(compute_probe.main(), 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["resource_probe_sha256"], _digest(payload))

    def test_storage_path_flag_is_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "probe.json"
            storage = Path(tmp) / "storage"
            argv = ["compute_probe", "--output", str(output), "--storage-path", str(storage)]
            with mock.patch.object(compute_probe.sys, "argv", argv), mock.patch("builtins.print"):
                compute_probe.main()
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(Path(payload["storage"]["path"]), storage.resolve())


if __name__ == "__main__":
    unittest.main()
