from __future__ import annotations
import json, unittest, hashlib
from pathlib import Path
from evaluation.grading.deterministic_checks import evaluate_rubric
from evaluation.grading.semantic_grader import assemble_grade_record, build_grading_request, validate_semantic_decision
from evaluation.grading.verify_coverage import canonical_json, verify_coverage, verify_grade_bindings
from evaluation.grading.pilot_aggregate_comparison import compare_pilot_aggregates

ROOT = Path(__file__).resolve().parents[1] / "grading"

class DeterministicTests(unittest.TestCase):
    def test_word_limit_and_bullet_count(self):
        result = evaluate_rubric("- one\n- two", [{"id": "words", "check": "max_words", "limit": 8}, {"id": "bullets", "check": "bullet_count", "count": 2}])
        self.assertEqual([x["status"] for x in result], ["passed", "passed"])
    def test_natural_language_criterion_stays_unscored(self):
        self.assertEqual(evaluate_rubric("A response", ["Explains why."])[0]["status"], "unscored")

class SemanticTests(unittest.TestCase):
    def test_exact_criterion_coverage(self):
        rubric = [{"id": "a"}, {"id": "b"}]
        decision = {"criteria": [{"criterion_id": "a", "status": "passed", "evidence_excerpt": "x", "rationale": "shown"}, {"criterion_id": "b", "status": "unscored", "evidence_excerpt": "", "rationale": "unclear"}]}
        self.assertEqual(len(validate_semantic_decision(decision, rubric)), 2)
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_semantic_decision({"criteria": decision["criteria"][:1]}, rubric)
    def test_request_binds_response_hash(self):
        import hashlib
        response = "candidate output"
        req = build_grading_request(candidate_alias="blind-01", case_id="case-1", response=response, rubric=[{"id": "c1"}], response_sha256=hashlib.sha256(response.encode()).hexdigest())
        self.assertEqual(req["response_sha256"], hashlib.sha256(response.encode()).hexdigest())

class CoverageTests(unittest.TestCase):
    def test_missing_duplicate_and_unexpected(self):
        expected = [{"candidate_id": "a", "case_id": "1"}, {"candidate_id": "a", "case_id": "2"}]
        self.assertEqual(verify_coverage(expected, [{"candidate_id": "a", "case_id": "1"}])["ungraded_response_count"], 1)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify_coverage(expected, [{"candidate_id": "a", "case_id": "1"}, {"candidate_id": "a", "case_id": "1"}])
        with self.assertRaisesRegex(ValueError, "unexpected"):
            verify_coverage(expected, [{"candidate_id": "a", "case_id": "3"}])

    def test_grade_rejects_rubric_content_drift_with_same_criterion_ids(self):
        original = [{"id": "criterion-1", "description": "Checks arithmetic."}]
        changed = [{"id": "criterion-1", "description": "Checks factual accuracy."}]
        source = {"candidate_id": "candidate-a", "case_id": "case-1",
                  "candidate_revision": "a" * 40, "source_artifact_sha256": "b" * 64,
                  "response_sha256": "c" * 64, "inference_run_id": "run-42", "rubric": original}
        grade = {"candidate_id": "candidate-a", "case_id": "case-1",
                 "candidate_revision": "a" * 40, "source_artifact_sha256": "b" * 64,
                 "response_sha256": "c" * 64,
                 "rubric_sha256": hashlib.sha256(canonical_json(original)).hexdigest(),
                 "inference_run_id": "run-42",
                 "criteria": [{"criterion_id": "criterion-1", "status": "passed"}]}
        self.assertTrue(verify_grade_bindings([source], [grade])["criterion_decisions_complete"])
        source["rubric"] = changed
        with self.assertRaisesRegex(ValueError, "rubric_sha256"):
            verify_grade_bindings([source], [grade])

    def test_grade_must_bind_exact_response_and_rubric(self):
        source = {"candidate_id": "candidate-a", "case_id": "case-1",
                  "candidate_revision": "a" * 40, "source_artifact_sha256": "b" * 64,
                  "response_sha256": "c" * 64, "inference_run_id": "run-42",
                  "rubric": [{"id": "criterion-1"}]}
        grade = {"candidate_id": "candidate-a", "case_id": "case-1",
                 "candidate_revision": "a" * 40, "source_artifact_sha256": "b" * 64,
                 "response_sha256": "c" * 64, "rubric_sha256": hashlib.sha256(canonical_json([{"id": "criterion-1"}])).hexdigest(),
                 "inference_run_id": "run-42",
                 "criteria": [{"criterion_id": "criterion-1", "status": "passed"}]}
        self.assertTrue(verify_grade_bindings([source], [grade])["criterion_decisions_complete"])
        grade["response_sha256"] = "d" * 64
        with self.assertRaisesRegex(ValueError, "response_sha256"):
            verify_grade_bindings([source], [grade])

class PilotReferenceTests(unittest.TestCase):
    def test_published_totals_reconcile(self):
        data = json.loads((ROOT / "pilot_reference.json").read_text())
        self.assertEqual(data["scope"]["response_count"], 30)
        self.assertEqual(sum(x["passed"] for x in data["candidate_totals"].values()), 80)
        self.assertEqual(sum(x["total"] for x in data["candidate_totals"].values()), 110)
        columns = [sum(row["passed"][i] for row in data["case_totals"].values()) for i in range(5)]
        self.assertEqual(columns, [17, 14, 17, 16, 16])
        self.assertEqual(sum(row["criteria"] for row in data["case_totals"].values()), 22)
        for row in data["case_totals"].values():
            self.assertEqual(len(row["passed"]), 5)
            self.assertTrue(all(0 <= score <= row["criteria"] for score in row["passed"]))

    def test_pilot_aggregate_comparison_reconciles_and_detects_drift(self):
        reference = json.loads((ROOT / "pilot_reference.json").read_text())
        grades = []
        for case_id, case in reference["case_totals"].items():
            for index, candidate in enumerate(reference["candidate_order"]):
                grades.append({"candidate_id": candidate, "case_id": case_id,
                               "score": {"passed": case["passed"][index], "total": case["criteria"]}})
        result = compare_pilot_aggregates(grades, reference)
        self.assertTrue(result["matches_historical_totals"])
        grades[0]["score"]["passed"] -= 1
        self.assertFalse(compare_pilot_aggregates(grades, reference)["matches_historical_totals"])

    def test_assembled_grade_record_binds_response_and_scores(self):
        response = "The result is 42."
        rubric = [{"id": "exact", "check": "required_literal", "literal": "42"},
                  {"id": "reason", "description": "Explains the reasoning"}]
        semantic = {"criteria": [
            {"criterion_id": "exact", "status": "passed", "evidence_excerpt": "42", "rationale": "literal is present"},
            {"criterion_id": "reason", "status": "unscored", "evidence_excerpt": "", "rationale": "semantic decision placeholder"}
        ]}
        record = assemble_grade_record(
            inference_run_id="run-42", candidate_id="candidate-a", candidate_revision="a" * 40,
            source_artifact_sha256="b" * 64, case_id="case-1", response=response,
            rubric=rubric, semantic_decision=semantic, rubric_version="rubric-v1",
            grader={"method": "hybrid", "grader_id": "grader-model", "grader_version": "rev-1", "prompt_version": "prompt-v1"},
            graded_at="2026-11-17T00:00:00Z")
        self.assertEqual(record["score"], {"passed": 1, "failed": 0, "unscored": 1, "total": 2})

if __name__ == "__main__": unittest.main()
