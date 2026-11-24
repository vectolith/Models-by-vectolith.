"""CPU tests for training/build_run42_corpus.py."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "training" / "build_run42_corpus.py"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def grade_record(candidate: str, case: str, response: str, passed: int, failed: int, unscored: int = 0) -> dict:
    return {
        "schema_version": "vectolith-ash-prime-grade/1.0",
        "inference_run_id": "43820188813",
        "candidate_id": candidate,
        "candidate_revision": "0" * 40,
        "source_artifact_sha256": "1" * 64,
        "case_id": case,
        "response_sha256": sha(response),
        "rubric_sha256": "2" * 64,
        "rubric_version": "prime-benchmark-v1",
        "grader": {
            "method": "model_assisted",
            "grader_id": "local/Qwen/Qwen3.5-2B",
            "grader_version": "15852e8c16360a2fea060d615a32b45270f8a8fc",
            "prompt_version": "vectolith-semantic-grader-1.1.0",
        },
        "criteria": [{"criterion_id": "criterion-01", "status": "passed", "evidence_excerpt": "x",
                      "rationale": "looks right", "method": "semantic", "confidence": 0.9}],
        "score": {"passed": passed, "failed": failed, "unscored": unscored, "total": passed + failed + unscored},
        "graded_at": "2026-11-24T00:00:00Z",
    }


class CorpusBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.cases = self.dir / "cases.jsonl"
        write_jsonl(self.cases, [
            {"id": "case-a", "category": "reasoning", "rubric": ["one"],
             "messages": [{"role": "system", "content": "sys-a"}, {"role": "user", "content": "ask-a"}]},
            {"id": "case-b", "category": "coding", "rubric": ["one"],
             "messages": [{"role": "system", "content": "sys-b"}, {"role": "user", "content": "ask-b"}]},
        ])
        self.responses = {"good-a": "answer one", "failed-b": "answer two", "ungraded-a": "answer three",
                          "mismatch-b": "answer four"}
        self.index = self.dir / "index.jsonl"
        write_jsonl(self.index, [
            {"candidate_id": "t1", "candidate_revision": "a" * 40, "case_id": "case-a",
             "response_text": "answer one", "response_sha256": sha("answer one"), "source_artifact_sha256": "3" * 64},
            {"candidate_id": "t2", "candidate_revision": "b" * 40, "case_id": "case-b",
             "response_text": "answer two", "response_sha256": sha("answer two"), "source_artifact_sha256": "4" * 64},
            {"candidate_id": "t1", "candidate_revision": "a" * 40, "case_id": "case-b",
             "response_text": "answer three", "response_sha256": sha("answer three"), "source_artifact_sha256": "5" * 64},
            {"candidate_id": "t2", "candidate_revision": "b" * 40, "case_id": "case-a",
             "response_text": "answer four", "response_sha256": sha("answer four"), "source_artifact_sha256": "6" * 64},
        ])
        self.grades = self.dir / "grades.jsonl"
        write_jsonl(self.grades, [
            grade_record("t1", "case-a", "answer one", passed=3, failed=0),
            grade_record("t2", "case-b", "answer two", passed=2, failed=1),
            grade_record("t2", "case-a", "answer four", passed=1, failed=0, unscored=2),
        ])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_builder(self, *extra: str) -> subprocess.CompletedProcess:
        out = self.dir / "corpus.jsonl"
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--response-index", str(self.index),
             "--grade-records", str(self.grades), "--cases", str(self.cases), "--out", str(out), *extra],
            capture_output=True, text=True, check=False,
        )

    def rows(self, path: Path) -> list[dict]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_only_all_passed_responses_are_accepted(self):
        result = self.run_builder()
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {(row["teacher"], row["case_id"]): row for row in self.rows(self.dir / "corpus.jsonl")}
        self.assertTrue(rows[("t1", "case-a")]["accepted"])
        self.assertIsNone(rows[("t1", "case-a")]["rejection_reason"])
        self.assertEqual(rows[("t2", "case-b")]["rejection_reason"], "failed_criteria")
        self.assertEqual(rows[("t1", "case-b")]["rejection_reason"], "ungraded")
        self.assertEqual(rows[("t2", "case-a")]["rejection_reason"], "unscored_criteria")

    def test_corpus_carries_prompts_and_provenance(self):
        self.run_builder()
        rows = {(row["teacher"], row["case_id"]): row for row in self.rows(self.dir / "corpus.jsonl")}
        row = rows[("t1", "case-a")]
        self.assertEqual(row["system"], "sys-a")
        self.assertEqual(row["prompt"], "ask-a")
        self.assertEqual(row["response"], "answer one")
        self.assertEqual(row["response_sha256"], sha("answer one"))
        self.assertEqual(row["source_artifact_sha256"], "3" * 64)
        self.assertEqual(row["grade"]["grader_id"], "local/Qwen/Qwen3.5-2B")
        self.assertEqual(row["grade"]["total"], 3)

    def test_accepted_only_and_manifest(self):
        result = self.run_builder("--accepted-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = self.rows(self.dir / "corpus.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertTrue(all(row["accepted"] for row in rows))
        manifest = json.loads((self.dir / "corpus.manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["indexed_responses"], 4)
        self.assertEqual(manifest["graded_responses"], 3)
        self.assertEqual(manifest["accepted_responses"], 1)
        self.assertEqual(manifest["rejected_reasons"],
                         {"failed_criteria": 1, "ungraded": 1, "unscored_criteria": 1})

    def test_coverage_is_enforced_when_requested(self):
        result = self.run_builder("--require-coverage")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("carry a grade record", result.stderr)

    def test_digest_mismatch_is_rejected(self):
        bad = grade_record("t1", "case-a", "answer one", passed=3, failed=0)
        bad["response_sha256"] = sha("something else")
        write_jsonl(self.grades, [bad, grade_record("t2", "case-b", "answer two", passed=1, failed=0)])
        result = self.run_builder()
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {(row["teacher"], row["case_id"]): row for row in self.rows(self.dir / "corpus.jsonl")}
        self.assertEqual(rows[("t1", "case-a")]["rejection_reason"], "response_digest_mismatch")

    def test_unknown_case_in_index_fails_loudly(self):
        rows = self.rows(self.index)
        rows[0]["case_id"] = "case-z"
        write_jsonl(self.index, rows)
        result = self.run_builder()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown case", result.stderr)


if __name__ == "__main__":
    unittest.main()
