# Historical blinded-review tooling

Status: optional legacy tooling. This document describes utilities that may be
used to inspect historical evaluation material; it does not define a current
teacher-qualification requirement or authorize training.

## Current Grading policy

The active qualification gate is **Grading**. It requires:

- a passed grading status;
- a positive expected response count;
- complete grading coverage of that response set;
- a SHA-256 digest for the grading report; and
- a documented rubric version.

The qualification gate does not require a minimum number of graders, reviewer
independence attestations, inter-grader agreement statistics or thresholds, or
third-party adjudication. None of those are release or training prerequisites.

The scripts `prepare_blinded_human_review.py`,
`prepare_human_adjudication.py`, and `summarize_human_grades.py` remain
available for optional historical analysis. Their outputs must not be
represented as mandatory qualification evidence. Existing source artifacts
and grade files should remain unchanged; preserve provenance and record any
new analysis as a separate artifact.

## Historical run 40 material

The run 40 public evidence set contains five preserved response artifacts:
Granite 3.1 3B-A800M, Granite 4.2 3B, MiniCPM5 2B, LFM2.5 2.6B, and
Phi-4-mini-instruct. Each successful artifact contains 180 cases, for 900
responses total. This is public-suite evaluation material, not a private
holdout and not, by itself, teacher qualification.

The legacy builder can validate immutable artifact ZIPs, JSON/JSONL parity,
provenance, suite coverage and rubric integrity. It can produce blinded
packages and a restricted identity key for optional review. If used, keep the
identity key, raw outputs, prompts, grades and private mappings in the
restricted evidence vault. Never commit them, attach them to a public pull
request, or expose them to pull-request CI.

## Evidence handling

- Preserve original model responses, prompts, rubrics and grade files.
- Keep private holdout datasets, scoring keys, raw outputs, access records and
  signed authorization material outside the public repository and CI.
- Store only approved non-sensitive references and digests in public records.
- A digest establishes byte identity only; it does not prove authenticity,
  legal permission, completeness or grading correctness.
- Legal review, explicit training-output permission, safety review, corpus
  integrity, protected holdout evaluation, foundation selection and run-specific
  execution authorization remain separate mandatory gates.

The current qualification policy is documented in
[Core Prime four-teacher qualification](core-prime-four-teacher-qualification.md)
and [Core Prime training evidence intake](core-prime-training-evidence-intake.md).
No training is authorized by the optional tools or by a Grading report.
