"""Opt-in integration tests against the real public Hugging Face Hub.

These tests make live HTTP requests and never mock the discovery client. Enable
with VECTOLITH_RUN_LIVE_TESTS=1 in a network-enabled environment.
"""
from __future__ import annotations

import os
import re
import unittest

from evaluation import discover_hf_candidates


@unittest.skipUnless(
    os.environ.get("VECTOLITH_RUN_LIVE_TESTS") == "1",
    "set VECTOLITH_RUN_LIVE_TESTS=1 to run real Hugging Face integration tests",
)
class HuggingFaceLiveIntegrationTests(unittest.TestCase):
    def test_real_catalog_search_returns_public_model_records(self):
        records = discover_hf_candidates.discover("Qwen3", limit=5, sort="downloads", pipeline_tag="text-generation", author="Qwen")
        self.assertTrue(records, "Hugging Face catalog search returned no models")
        self.assertTrue(
            all(isinstance(record.get("id"), str) and "/" in record["id"] and record.get("pipeline_tag") == "text-generation" and record.get("author") == "Qwen" for record in records),
            "Hub search returned records without valid repository IDs",
        )

    def test_real_repository_snapshot_pins_revision_and_preserves_card_evidence(self):
        record = discover_hf_candidates.snapshot("google-bert/bert-base-uncased")
        self.assertEqual(record["repo_id"], "google-bert/bert-base-uncased")
        self.assertRegex(record["immutable_revision"], re.compile(r"^[0-9a-f]{40}$"))
        self.assertIn(record["immutable_revision"], record["model_card_url"])
        self.assertTrue(record["model_card_text"], "Expected the live model card to be retrievable")
        self.assertEqual(
            record["model_card_sha256"],
            discover_hf_candidates.sha256_text(record["model_card_text"]),
        )
        self.assertEqual(record["training_output_permission"], "not_verified")
        self.assertEqual(record["teacher_qualification"], "not_qualified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
