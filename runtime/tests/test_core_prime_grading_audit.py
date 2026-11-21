"""Synthetic tests for human grading audit utility; no actual grades included."""
import importlib.util
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[2]/"scripts"/"core_prime_grading_audit.py"
spec=importlib.util.spec_from_file_location("grading_audit",SCRIPT); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
def test_agreement_and_coverage():
    data={"ratings":[{"blind_case_id":"b1","reviewer_id":"r1","score":4},{"blind_case_id":"b1","reviewer_id":"r2","score":4},{"blind_case_id":"b2","reviewer_id":"r1","score":3},{"blind_case_id":"b2","reviewer_id":"r2","score":2}]}
    out=module.audit(data,min_cases=2)
    assert not out["errors"]
    assert out["summary"]["cases_with_two_or_more_reviewers"]==2
    assert out["summary"]["exact_agreement_first_two_reviewers_per_case"]==0.5
def test_cohort_overlap_detected():
    data={"ratings":[{"blind_case_id":"b1","reviewer_id":"teacher","score":4},{"blind_case_id":"b1","reviewer_id":"r2","score":3}]}
    assert any("overlaps teacher cohort" in e for e in module.audit(data,{"teacher"})["errors"])
def test_duplicate_rating_detected():
    data={"ratings":[{"blind_case_id":"b1","reviewer_id":"r1","score":4},{"blind_case_id":"b1","reviewer_id":"r1","score":2}]}
    assert any("duplicate" in e for e in module.audit(data)["errors"])
def test_missing_second_review_blocks_minimum():
    data={"ratings":[{"blind_case_id":"b1","reviewer_id":"r1","score":4}]}
    assert any("minimum is 2" in e for e in module.audit(data,min_cases=2)["errors"])
def test_invalid_score_rejected():
    data={"ratings":[{"blind_case_id":"b1","reviewer_id":"r1","score":9}]}
    assert any("0..5" in e for e in module.audit(data)["errors"])
