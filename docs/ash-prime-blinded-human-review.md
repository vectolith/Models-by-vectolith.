# Historical blinded-review tooling

Status: optional package-building tooling. Independent human grading remains
mandatory for teacher qualification.

## Current Grading policy

The qualification gate requires complete coverage of the expected response
set by at least two distinct independent human reviewers. It also requires
the grade-report digest, rubric version, reviewer-independence attestation,
inter-grader agreement report, and adjudication report (including a
documented no-disagreement disposition where applicable). Machine-only or
single-pass AI grading does not satisfy the gate.

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
[ASH PRIME four-teacher qualification](ash-prime-four-teacher-qualification.md)
and [ASH PRIME training evidence intake](ash-prime-training-evidence-intake.md).
No training is authorized by the optional tools or by a Grading report.
