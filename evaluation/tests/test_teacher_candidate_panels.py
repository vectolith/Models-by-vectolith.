import json
import unittest
from pathlib import Path

MANIFEST = Path(__file__).parents[1] / "fixtures" / "teacher_panel_candidates_v1.json"
SNAPSHOTTED_REPO_IDS = {
    "Qwen/Qwen3.5-9B", "Qwen/Qwen3.5-4B", "Qwen/Qwen3.8-27B",
    "Qwen/Qwen3.6-27B", "Qwen/Qwen3.6-35B-A3B",
    "google/gemma-4-E2B-it", "google/gemma-4-E4B-it",
    "google/gemma-4-12B-it", "google/gemma-4-26B-A4B-it",
    "google/gemma-4-31B-it", "ibm-granite/granite-4.2-8b",
    "openai/gpt-oss-20b", "Qwen/Qwen2.5-7B-Instruct",
    "mistralai/Devstral-Small-2-24B-Instruct-2512",
    "Qwen/Qwen3-Coder-Next", "Qwen/Qwen2.5-Coder-7B-Instruct",
}


class TeacherCandidatePanelManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_each_student_has_at_least_four_distinct_candidates(self):
        self.assertEqual(self.manifest["required_qualified_teachers_per_student"], 4)
        for student, panel in self.manifest["students"].items():
            ids = [candidate["id"] for candidate in panel["candidates"]]
            self.assertGreaterEqual(len(ids), 4, student)
            self.assertEqual(len(ids), len(set(ids)), student)

    def test_every_panel_candidate_has_a_pinned_snapshot_target(self):
        for student, panel in self.manifest["students"].items():
            for candidate in panel["candidates"]:
                self.assertIn(candidate["repo_id"], SNAPSHOTTED_REPO_IDS, (student, candidate["repo_id"]))

    def test_gemma_instruction_candidate_matches_the_snapshotted_repo_id(self):
        for panel in self.manifest["students"].values():
            candidate = next(item for item in panel["candidates"] if item["id"] == "gemma-4-e4b-it")
            self.assertEqual(candidate["repo_id"], "google/gemma-4-E4B-it")

    def test_candidates_are_not_prequalified_by_manifest(self):
        for panel in self.manifest["students"].values():
            for candidate in panel["candidates"]:
                self.assertEqual(candidate["qualification_status"], "not_qualified")
                self.assertEqual(candidate["training_output_permission"], "not_verified")
                self.assertEqual(candidate["license_review"], "pending")

    def test_qwen25_7b_is_retained_as_prime_comparator(self):
        candidates = self.manifest["students"]["ash_prime"]["candidates"]
        qwen = next(item for item in candidates if item["id"] == "qwen2.5-7b-instruct")
        self.assertEqual(qwen["repo_id"], "Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(qwen["revision"], "a09a35458c702b33eeacc393d103063234e8bc28")
        self.assertEqual(qwen["qualification_status"], "not_qualified")


if __name__ == "__main__":
    unittest.main()
