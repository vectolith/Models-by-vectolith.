from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation import discover_hf_candidates, probe_compute


class CandidateDiscoveryTests(unittest.TestCase):
    def metadata(self):
        return {
            "sha": "a" * 40,
            "private": False,
            "gated": False,
            "pipeline_tag": "text-generation",
            "library_name": "transformers",
            "siblings": [
                {"rfilename": "README.md"},
                {"rfilename": "LICENSE"},
                {"rfilename": "config.json"},
                {"rfilename": "tokenizer.json"},
                {"rfilename": "model.safetensors"},
            ],
            "cardData": {"license": "apache-2.0", "architectures": ["ExampleForCausalLM"]},
            "tags": ["license:apache-2.0"],
            "safetensors": {"total": 1234},
        }

    def test_snapshot_retains_exact_revision_pinned_license_and_card_evidence(self):
        with patch.object(discover_hf_candidates, "get_json", return_value=self.metadata()), patch.object(
            discover_hf_candidates, "get_text", side_effect=["LICENSE BODY\n", "MODEL CARD BODY\n"]
        ) as get_text:
            record = discover_hf_candidates.snapshot("org/model")
        self.assertEqual(record["immutable_revision"], "a" * 40)
        self.assertEqual(record["license_tag"], "apache-2.0")
        self.assertEqual(record["license_file_text"], "LICENSE BODY\n")
        self.assertEqual(record["model_card_text"], "MODEL CARD BODY\n")
        self.assertEqual(record["license_file_sha256"], discover_hf_candidates.sha256_text("LICENSE BODY\n"))
        self.assertEqual(record["model_card_sha256"], discover_hf_candidates.sha256_text("MODEL CARD BODY\n"))
        self.assertIn("/resolve/" + "a" * 40 + "/LICENSE", record["license_file_url"])
        self.assertIn("config.json", record["config_files"])
        self.assertIn("tokenizer.json", record["tokenizer_files"])
        self.assertEqual(record["training_output_permission"], "not_verified")
        self.assertEqual(record["teacher_qualification"], "not_qualified")
        self.assertEqual(get_text.call_count, 2)

    def test_snapshot_rejects_non_immutable_revision(self):
        for revision in ("main", "a" * 39, "g" * 40, None):
            with self.subTest(revision=revision), patch.object(
                discover_hf_candidates, "get_json", return_value={"sha": revision}
            ):
                with self.assertRaises(ValueError):
                    discover_hf_candidates.snapshot("org/model")

    def test_catalog_discovery_paginates_and_encodes_search(self):
        pages = [
            ([{"id": "org/model-a", "pipeline_tag": "text-generation"}, {"id": "org/model-b", "pipeline_tag": "text-generation"}, {"id": "org/model-c", "pipeline_tag": "text-generation"}], "https://huggingface.co/api/models?cursor=next"),
            ([{"id": "org/model-d", "pipeline_tag": "text-generation"}], None),
        ]
        with patch.object(discover_hf_candidates, "get_json_page", side_effect=pages) as get_page:
            found = discover_hf_candidates.discover("small instruct", limit=4, pipeline_tag="text-generation")
        self.assertEqual([item["id"] for item in found], ["org/model-a", "org/model-b", "org/model-c", "org/model-d"])
        self.assertEqual(get_page.call_count, 2)
        self.assertIn("search=small+instruct", get_page.call_args_list[0].args[0])
        self.assertIn("pipeline_tag=text-generation", get_page.call_args_list[0].args[0])
        self.assertEqual(get_page.call_args_list[1].args[0], "https://huggingface.co/api/models?cursor=next")

    def test_catalog_discovery_rejects_invalid_limit(self):
        with self.assertRaises(ValueError):
            discover_hf_candidates.discover("models", limit=0)

    def test_missing_license_evidence_stays_unverified(self):
        metadata = self.metadata()
        metadata["siblings"] = [{"rfilename": "README.md"}]
        with patch.object(discover_hf_candidates, "get_json", return_value=metadata), patch.object(
            discover_hf_candidates, "get_text", return_value="card"
        ):
            record = discover_hf_candidates.snapshot("org/model")
        self.assertIsNone(record["license_file_text"])
        self.assertIsNone(record["license_file_sha256"])
        self.assertEqual(record["license_review"], "pending_human_legal_review")
        self.assertEqual(record["training_output_permission"], "not_verified")


class ComputeProbeTests(unittest.TestCase):
    def test_environment_markers_do_not_claim_quota(self):
        with patch.dict("os.environ", {"KAGGLE_KERNEL_RUN_TYPE": "Interactive"}, clear=True):
            self.assertEqual(probe_compute.detect_environment(), ["kaggle"])

    def test_generic_probe_source_keeps_account_status_unverified(self):
        source = Path(probe_compute.__file__).read_text(encoding="utf-8")
        self.assertIn('"provider_quota": "not_observable_from_generic_process"', source)
        self.assertIn('"account_eligibility": "not_verified"', source)
        self.assertIn('"billing_state": "not_verified"', source)


if __name__ == "__main__":
    unittest.main()
