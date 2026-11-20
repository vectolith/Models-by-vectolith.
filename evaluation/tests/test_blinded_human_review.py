from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from evaluation.prepare_blinded_human_review import (
    ARTIFACT_PROVENANCE,
    BLIND_GRADE_SCHEMA,
    build_review_packages,
    unblind_grade_files,
)


class BlindedHumanReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.suite = self.root / "suite.jsonl"
        self.cases = [
            {
                "id": f"prime-v4-test-{n}",
                "category": "reasoning",
                "messages": [
                    {"role": "system", "content": "Be accurate."},
                    {"role": "user", "content": f"Question {n}?"},
                ],
                "rubric": ["Correctness", "Completeness"],
            }
            for n in range(2)
        ]
        self.suite.write_text(
            "\n".join(json.dumps(x) for x in self.cases) + "\n", encoding="utf-8"
        )
        self.artifacts = []
        for index, candidate in enumerate(("secret-model-alpha", "secret-model-beta")):
            revision = (str(index + 1) * 40)
            run_id = f"run-secret-{index}"
            rows = []
            for n, case in enumerate(self.cases):
                rows.append({
                    "suite": "evaluation/fixtures/prime_qualification_v4.jsonl",
                    "role": "core_prime",
                    "case_id": case["id"],
                    "benchmark_case_id": case["id"],
                    "candidate_id": candidate,
                    "model_revision": revision,
                    "run_id": run_id,
                    "started_at": f"2026-11-16T00:00:0{n}+00:00",
                    "category": case["category"],
                    "prompt_sha256": hashlib.sha256(case["id"].encode()).hexdigest(),
                    "rubric": case["rubric"],
                    "max_new_tokens": 256,
                    "generation_cap_reached": False,
                    "generation_status": "eos_or_early_stop",
                    "generated_tokens": 12,
                    "response_text": f"Answer response {n}",
                    "error": None,
                })
            record = {
                "candidate_id": candidate,
                "immutable_revision": revision,
                "run_id": run_id,
                "case_count": len(rows),
                "results": rows,
            }
            artifact = self.root / f"source-{index}.zip"
            with zipfile.ZipFile(artifact, "w") as archive:
                archive.writestr("evaluations/result.json", json.dumps(record))
                archive.writestr(
                    "evaluations/result.jsonl",
                    "\n".join(json.dumps(x) for x in rows) + "\n",
                )
            self.artifacts.append(artifact)

    def tearDown(self):
        self.tmp.cleanup()

    def test_historical_provenance_registry_covers_all_fifteen_artifacts(self):
        self.assertEqual(len(ARTIFACT_PROVENANCE), 15)
        item = ARTIFACT_PROVENANCE["run42-prime-phi-4-mini-instruct.zip"]
        self.assertEqual(item["workflow_run_id"], "43820188813")
        self.assertEqual(item["artifact_id"], 14280614317)
        self.assertEqual(item["job_id"], 133549417510)
        self.assertEqual(
            item["sha256"],
            "9b34e52ef661236741bae16b7de0ce9b04b065fdb223e2aec3bfb4d812cbac4c",
        )

    def test_builds_two_blinded_packages_and_keeps_identity_key_separate(self):
        output = self.root / "review"
        summary = build_review_packages(
            self.artifacts, [self.suite], output,
            reviewer_count=2, expected_artifacts=2, expected_cases=2, workflow_run_id="test-run",
        )
        self.assertEqual(summary["response_count"], 4)
        self.assertEqual(summary["gradeable_response_count"], 4)
        self.assertEqual(summary["reviewer_package_count"], 2)
        key_path = output / "private" / "identity-key.json"
        self.assertTrue(key_path.exists())
        key = json.loads(key_path.read_text(encoding="utf-8"))
        self.assertEqual(len(key["records"]), 4)
        for package in summary["reviewer_packages"]:
            with zipfile.ZipFile(output / package["reviewer_package"]) as archive:
                self.assertNotIn("identity-key.json", archive.namelist())
                raw = archive.read("review-items.jsonl").decode()
                self.assertNotIn("secret-model-alpha", raw)
                self.assertNotIn("secret-model-beta", raw)
                self.assertNotIn("1" * 40, raw)
                self.assertNotIn("2" * 40, raw)
                self.assertNotIn("run-secret", raw)
                self.assertIn("Answer response", raw)
                self.assertEqual(len(raw.splitlines()), 4)

    def test_accepts_multiple_runs_for_the_same_candidate_without_overwriting(self):
        first = self.artifacts[0]
        with zipfile.ZipFile(first) as archive:
            record = json.loads(archive.read("evaluations/result.json"))
        second_run_id = "run-secret-alpha-second"
        for row in record["results"]:
            row["run_id"] = second_run_id
            row["started_at"] = row["started_at"].replace("2026-11-16", "2026-11-17")
        record["run_id"] = second_run_id
        second = self.root / "source-alpha-second.zip"
        with zipfile.ZipFile(second, "w") as archive:
            archive.writestr("evaluations/result.json", json.dumps(record))
            archive.writestr(
                "evaluations/result.jsonl",
                "\n".join(json.dumps(x) for x in record["results"]) + "\n",
            )
        output = self.root / "repeat-review"
        summary = build_review_packages(
            [first, second], [self.suite], output,
            reviewer_count=2, expected_artifacts=2, expected_cases=2,
            workflow_run_id="multi-run",
        )
        self.assertEqual(summary["response_count"], 4)
        self.assertEqual(summary["candidate_artifact_count"], 2)
        self.assertEqual(summary["unique_candidate_count"], 1)
        key = json.loads(
            (output / "private" / "identity-key.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(key["records"]), 4)
        self.assertEqual(
            {row["run_id"] for row in key["records"].values()},
            {"run-secret-0", second_run_id},
        )

    def test_unblinds_only_complete_distinct_reviewer_submissions(self):
        output = self.root / "review"
        build_review_packages(
            self.artifacts, [self.suite], output,
            reviewer_count=2, expected_artifacts=2, expected_cases=2, workflow_run_id="test-run",
        )
        grade_paths = []
        for index in range(1, 3):
            package = output / f"reviewer-{index:02d}-blind-review.zip"
            grade_path = self.root / f"grades-{index}.jsonl"
            with zipfile.ZipFile(package) as archive:
                grades = [
                    json.loads(line)
                    for line in archive.read("grade-template.jsonl").decode().splitlines()
                ]
            for grade in grades:
                grade["evaluator_id"] = f"human-reviewer-{index}"
                grade["rubric_scores"] = [
                    {"criterion": score["criterion"], "score": 3, "notes": "Reviewed independently."}
                    for score in grade["rubric_scores"]
                ]
            grade_path.write_text(
                "\n".join(json.dumps(x) for x in grades) + "\n", encoding="utf-8"
            )
            grade_paths.append(grade_path)

        identity_key = output / "private" / "identity-key.json"
        canonical = unblind_grade_files(identity_key, grade_paths)
        self.assertEqual(len(canonical), 8)
        self.assertEqual({x["evaluator_id"] for x in canonical}, {"human-reviewer-1", "human-reviewer-2"})
        self.assertTrue(all(x["schema_version"] == "vectolith-human-grading/1.0" for x in canonical))
        self.assertTrue(all(len(x["rubric_scores"]) == 2 for x in canonical))

    def test_rejects_incomplete_reviewer_submission(self):
        output = self.root / "review"
        build_review_packages(
            self.artifacts, [self.suite], output,
            reviewer_count=2, expected_artifacts=2, expected_cases=2, workflow_run_id="test-run",
        )
        grade_paths = []
        for index in range(1, 3):
            with zipfile.ZipFile(output / f"reviewer-{index:02d}-blind-review.zip") as archive:
                grades = [
                    json.loads(line)
                    for line in archive.read("grade-template.jsonl").decode().splitlines()
                ]
            for grade in grades:
                grade["evaluator_id"] = f"reviewer-{index}"
                grade["rubric_scores"] = [
                    {"criterion": score["criterion"], "score": 3, "notes": ""}
                    for score in grade["rubric_scores"]
                ]
            if index == 1:
                grades.pop()
            path = self.root / f"grades-{index}.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in grades) + "\n", encoding="utf-8")
            grade_paths.append(path)
        with self.assertRaisesRegex(ValueError, "incomplete review"):
            unblind_grade_files(output / "private" / "identity-key.json", grade_paths)

    def test_rejects_same_reviewer_identity_twice(self):
        output = self.root / "review"
        build_review_packages(
            self.artifacts, [self.suite], output,
            reviewer_count=2, expected_artifacts=2, expected_cases=2, workflow_run_id="test-run",
        )
        grade_paths = []
        for index in range(1, 3):
            with zipfile.ZipFile(output / f"reviewer-{index:02d}-blind-review.zip") as archive:
                grades = [
                    json.loads(line)
                    for line in archive.read("grade-template.jsonl").decode().splitlines()
                ]
            for grade in grades:
                grade["evaluator_id"] = "same-human"
                grade["rubric_scores"] = [
                    {"criterion": score["criterion"], "score": 3, "notes": ""}
                    for score in grade["rubric_scores"]
                ]
            path = self.root / f"grades-{index}.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in grades) + "\n", encoding="utf-8")
            grade_paths.append(path)
        with self.assertRaisesRegex(ValueError, "distinct evaluator_id"):
            unblind_grade_files(output / "private" / "identity-key.json", grade_paths)


if __name__ == "__main__":
    unittest.main()
