import json
import unittest
from pathlib import Path

MANIFEST = Path(__file__).parents[1] / "fixtures" / "teacher_panel_candidates_v1.json"


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

    def test_candidates_are_not_prequalified_by_manifest(self):
        for panel in self.manifest["students"].values():
            for candidate in panel["candidates"]:
                self.assertEqual(candidate["qualification_status"], "not_qualified")
                self.assertEqual(candidate["training_output_permission"], "not_verified")
                self.assertEqual(candidate["license_review"], "pending")

    def test_qwen25_7b_is_retained_as_prime_comparator(self):
        candidates = self.manifest["students"]["core_prime"]["candidates"]
        qwen = next(item for item in candidates if item["id"] == "qwen2.5-7b-instruct")
        self.assertEqual(qwen["repo_id"], "Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(qwen["revision"], "a09a35458c702b33eeacc393d103063234e8bc28")
        self.assertEqual(qwen["qualification_status"], "not_qualified")


if __name__ == "__main__":
    unittest.main()
