from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from evaluation.capture_teacher_rights import (
    CANDIDATES,
    build_capture_manifest,
    capture_candidate,
    extract_model_card_metadata,
    is_legal_file,
)


class TeacherRightsCaptureTests(unittest.TestCase):
    def test_model_card_frontmatter_license_metadata_is_extracted(self):
        metadata = extract_model_card_metadata(
            b"---\nlicense: nvidia-nemotron-open-model-license\nlicense_name: NVIDIA Nemotron Open Model License\n---\n"
        )
        self.assertEqual(
            metadata["license"],
            "nvidia-nemotron-open-model-license",
        )
        self.assertEqual(
            metadata["license_name"],
            "NVIDIA Nemotron Open Model License",
        )

    def test_zero_byte_repository_license_is_not_counted_as_license_text(self):
        manifest = build_capture_manifest(
            candidate_id="nemotron-test",
            expected={
                "repo_id": "nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16",
                "revision": "immutable-revision",
                "role": "teacher",
            },
            observed_revision="immutable-revision",
            card_data={"license": "nvidia-nemotron-open-model-license"},
            captured_files=[
                {
                    "path": "README.md",
                    "size_bytes": 31,
                    "sha256": "readme-digest",
                    "source_kind": "repository_revision",
                    "file_role": "model_card",
                },
                {
                    "path": "LICENSE",
                    "size_bytes": 0,
                    "sha256": "empty-digest",
                    "source_kind": "repository_revision",
                    "file_role": "empty_license_placeholder",
                },
                {
                    "path": "OFFICIAL_LICENSE_REFERENCES/license.pdf",
                    "size_bytes": 10,
                    "sha256": "license-digest",
                    "source_kind": "official_publisher_reference",
                    "file_role": "license_text",
                },
            ],
        )

        self.assertFalse(manifest["repository_license_file_present"])
        self.assertEqual(manifest["capture_status"], "captured_external_reference")
        self.assertEqual(len(manifest["empty_repository_license_files"]), 1)
        self.assertEqual(len(manifest["license_files"]), 1)
        self.assertEqual(
            manifest["license_files"][0]["source_kind"],
            "official_publisher_reference",
        )

    def test_all_five_run42_teacher_candidates_are_pinned(self):
        teacher_ids = {"granite-3.1-3b-a800m", "granite-4.2-3b", "minicpm5-2b", "lfm2.5-2.6b", "phi-4-mini-instruct"}
        self.assertTrue(teacher_ids.issubset(CANDIDATES))
        self.assertEqual(len(teacher_ids), 5)
        for candidate_id in teacher_ids:
            candidate = CANDIDATES[candidate_id]
            self.assertEqual(len(candidate["revision"]), 40)
            self.assertTrue(all(c in "0123456789abcdef" for c in candidate["revision"]))

    def test_active_prime_teacher_revisions_are_pinned(self):
        expected = {
            "qwen3.5-2b-teacher": "5bf1871105527bed0f47e8fa941d2fc5170f7b1d",
            "gemma-4-e2b-it": "4adf15748de9e1a0097b6274cee9c15836c41c37",
            "nemotron-3-nano-4b": "ef26eca1cb6b37ea5e5d5b7e01c087e63345aeec",
            "lfm2.5-2.6b": "7141b56cd4650af95c7c7b86983443aed050c96a",
        }
        for candidate_id, revision in expected.items():
            self.assertEqual(CANDIDATES[candidate_id]["revision"], revision)

    def test_nemotron_captures_both_governing_and_context_license_sources(self):
        sources = CANDIDATES["nemotron-3-nano-4b"]["external_license_sources"]
        self.assertTrue(any(source["file_role"] == "license_text" for source in sources))
        self.assertTrue(any(source["file_role"] == "context_reference" for source in sources))

    def test_local_grader_is_pinned_separately_from_teacher_candidates(self):
        grader = CANDIDATES["qwen3.5-2b-local-grader"]
        self.assertEqual(grader["repo_id"], "Qwen/Qwen3.5-2B")
        self.assertEqual(grader["revision"], "15852e8c16360a2fea060d615a32b45270f8a8fc")

    def test_only_legal_files_and_model_card_are_captured(self):
        self.assertTrue(is_legal_file("LICENSE"))
        self.assertTrue(is_legal_file("LICENSE.md"))
        self.assertTrue(is_legal_file("NOTICE"))
        self.assertTrue(is_legal_file("NOTICE.txt"))
        self.assertTrue(is_legal_file("COPYING"))
        self.assertFalse(is_legal_file("model.safetensors"))
        self.assertFalse(is_legal_file("config.json"))

    def test_manifest_keeps_legal_review_and_output_permission_pending(self):
        license_bytes = b"Apache License Version 2.0"
        files = [{
            "path": "LICENSE",
            "size_bytes": len(license_bytes),
            "sha256": hashlib.sha256(license_bytes).hexdigest(),
            "immutable_url": "https://example.invalid/LICENSE",
            "captured_path": "/secure/LICENSE",
            "file_role": "license_text",
            "source_kind": "repository_revision",
        }]
        manifest = build_capture_manifest(
            candidate_id="granite-3.1-3b-a800m",
            expected=CANDIDATES["granite-3.1-3b-a800m"],
            observed_revision=CANDIDATES["granite-3.1-3b-a800m"]["revision"],
            card_data={"license": "apache-2.0"},
            captured_files=files,
        )
        self.assertEqual(manifest["capture_status"], "captured")
        self.assertEqual(manifest["license_files"][0]["sha256"], files[0]["sha256"])
        self.assertEqual(manifest["legal_review"], "pending_authorized_review")
        self.assertEqual(manifest["training_output_permission"], "not_verified")
        self.assertFalse(manifest["weights_downloaded"])
        self.assertFalse(manifest["inference_performed"])
        self.assertFalse(manifest["training_started"])

    def test_capture_downloads_only_license_and_card_not_weights(self):
        candidate_id = "granite-3.1-3b-a800m"
        expected = CANDIDATES[candidate_id]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            license_cache = root / "LICENSE"
            card_cache = root / "README.md"
            license_cache.write_bytes(b"Apache License")
            card_cache.write_bytes(b"---\nlicense: apache-2.0\n---\nModel card")
            calls = []

            class FakeApi:
                def model_info(self, repo_id, revision, files_metadata):
                    self.assertions = (repo_id, revision, files_metadata)
                    return SimpleNamespace(
                        sha=expected["revision"],
                        gated=False,
                        private=False,
                        disabled=False,
                        siblings=[
                            SimpleNamespace(rfilename="LICENSE"),
                            SimpleNamespace(rfilename="README.md"),
                            SimpleNamespace(rfilename="model.safetensors"),
                            SimpleNamespace(rfilename="config.json"),
                        ],
                        card_data=SimpleNamespace(to_dict=lambda: {"license": "apache-2.0"}),
                    )

            def fake_download(**kwargs):
                calls.append(kwargs)
                return str(license_cache if kwargs["filename"] == "LICENSE" else card_cache)

            manifest = capture_candidate(candidate_id, root / "out", FakeApi(), fake_download)
            self.assertEqual(manifest["capture_status"], "captured")
            self.assertEqual({call["filename"] for call in calls}, {"LICENSE", "README.md"})
            self.assertTrue(all(call["token"] is False for call in calls))
            self.assertFalse(manifest["weights_downloaded"])
            saved = json.loads((root / "out" / candidate_id / "rights-capture.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["immutable_revision"], expected["revision"])


    def test_missing_repo_license_uses_pinned_spdx_text_without_mislabeling_it(self):
        candidate_id = "granite-3.1-3b-a800m"
        expected = CANDIDATES[candidate_id]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            card_cache = root / "README.md"
            card_cache.write_text("---\nlicense: apache-2.0\n---\nModel card", encoding="utf-8")

            class FakeApi:
                def model_info(self, repo_id, revision, files_metadata):
                    return SimpleNamespace(
                        sha=expected["revision"], gated=False, private=False, disabled=False,
                        siblings=[SimpleNamespace(rfilename="README.md")],
                        card_data=SimpleNamespace(to_dict=lambda: {"license": "apache-2.0"}),
                    )

            class FakeResponse:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def read(self):
                    return b"Apache License Version 2.0"

            def fake_download(**kwargs):
                self.assertEqual(kwargs["filename"], "README.md")
                self.assertIs(kwargs["token"], False)
                return str(card_cache)

            with patch("evaluation.capture_teacher_rights.urllib.request.urlopen", return_value=FakeResponse()) as opened:
                manifest = capture_candidate(candidate_id, root / "out", FakeApi(), fake_download)

            self.assertEqual(manifest["capture_status"], "captured_spdx_reference")
            self.assertFalse(manifest["repository_license_file_present"])
            self.assertEqual(manifest["license_files"][0]["source_kind"], "spdx_license_list")
            self.assertEqual(manifest["license_files"][0]["sha256"], hashlib.sha256(b"Apache License Version 2.0").hexdigest())
            self.assertIn("31ba1a50e5397e00a304dbadc76531740e89ee48", manifest["license_files"][0]["immutable_url"])
            self.assertTrue(opened.called)
            self.assertEqual(manifest["legal_review"], "pending_authorized_review")
            self.assertEqual(manifest["training_output_permission"], "not_verified")

    def test_revision_mismatch_fails_closed(self):
        candidate_id = "granite-3.1-3b-a800m"
        with tempfile.TemporaryDirectory() as tmp:
            class FakeApi:
                def model_info(self, repo_id, revision, files_metadata):
                    return SimpleNamespace(
                        sha="0" * 40, gated=False, private=False, disabled=False,
                        siblings=[], card_data=None,
                    )
            with self.assertRaisesRegex(RuntimeError, "revision mismatch"):
                capture_candidate(candidate_id, Path(tmp), FakeApi(), lambda **kwargs: "")


if __name__ == "__main__":
    unittest.main()
