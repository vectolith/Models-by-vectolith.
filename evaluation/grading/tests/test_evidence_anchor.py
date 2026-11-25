"""Evidence must stay a verbatim slice of the response even when the grader paraphrases."""
from __future__ import annotations

from evaluation.grading.semantic_grader import anchor_evidence, assemble_grade_record, evidence_is_verbatim

RESPONSE = (
    "Sure, I can make it lighter. However, I need more context to provide an accurate response. "
    "Weight, colour tone and file size all change the answer."
)


def test_anchor_finds_verbatim_sentence_for_paraphrase():
    excerpt = "Sure, I can make it lighter. However, I need more context to provide an accurate response."
    assert evidence_is_verbatim(excerpt, RESPONSE)
    anchored = anchor_evidence("I can make it lighter, though I need more context for accuracy.", RESPONSE)
    assert anchored is not None
    assert anchored in RESPONSE


def test_anchor_returns_none_for_unrelated_text():
    assert anchor_evidence("Completely unrelated statement about quantum chromodynamics.", RESPONSE) is None


def test_assemble_repairs_excerpt_instead_of_failing():
    rubric = ["Actually recognises the ambiguity in 'lighter'", "Asks for the missing context"]
    decision = {"criteria": [
        {"criterion_id": "criterion-01", "status": "passed",
         "evidence_excerpt": "Weight, colour tone and file size all change the answer.",
         "rationale": "Names the competing readings."},
        {"criterion_id": "criterion-02", "status": "passed",
         "evidence_excerpt": "However, I need more context to provide an accurate response",
         "rationale": "Requests context."},
    ]}
    record = assemble_grade_record(
        inference_run_id="43820188813", candidate_id="granite-3.1-3b-a800m",
        candidate_revision="a" * 40, source_artifact_sha256="b" * 64,
        case_id="prime-ambiguity-001", response=RESPONSE, rubric=rubric,
        semantic_decision=decision, rubric_version="run42-embedded-rubric-v1",
        grader={"method": "model_assisted", "grader_id": "Qwen/Qwen3.5-2B",
                "grader_version": "15852e8c16360a2fea060d615a32b45270f8a8fc",
                "prompt_version": "ash-prime-semantic-grader-v2-local"},
        graded_at="2026-11-25T00:00:00Z")
    for row in record["criteria"]:
        assert row["evidence_excerpt"] in RESPONSE
