from __future__ import annotations

import hashlib
import io
import tempfile
import unittest
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

from evaluation.download_and_prepare_historical_reviews import download_verified_artifact


def sample_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("evaluations/sample.json", "{}")
    return buffer.getvalue()


class HistoricalArtifactDownloaderTests(unittest.TestCase):
    def test_script_entrypoint_imports_from_outside_repository_root(self):
        script = Path(__file__).resolve().parents[1] / "download_and_prepare_historical_reviews.py"
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=20,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--reviewers", result.stdout)

    def test_downloads_and_persists_only_matching_zip_digest(self):
        payload = sample_zip()
        expected = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "source.zip"
            with patch(
                "evaluation.download_and_prepare_historical_reviews.urllib.request.urlopen",
                return_value=io.BytesIO(payload),
            ):
                result = download_verified_artifact(123, "source.zip", expected, destination)
            self.assertTrue(destination.is_file())
            self.assertEqual(destination.read_bytes(), payload)
            self.assertEqual(result["status"], "downloaded_and_verified")

    def test_rejects_non_zip_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "source.zip"
            with patch(
                "evaluation.download_and_prepare_historical_reviews.urllib.request.urlopen",
                return_value=io.BytesIO(b"not a zip"),
            ):
                with self.assertRaisesRegex(ValueError, "did not return a ZIP"):
                    download_verified_artifact(123, "source.zip", "0" * 64, destination)
            self.assertFalse(destination.exists())

    def test_refuses_to_overwrite_existing_artifact_with_wrong_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "source.zip"
            destination.write_bytes(b"preserve this")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                download_verified_artifact(123, "source.zip", "0" * 64, destination)
            self.assertEqual(destination.read_bytes(), b"preserve this")


if __name__ == "__main__":
    unittest.main()
