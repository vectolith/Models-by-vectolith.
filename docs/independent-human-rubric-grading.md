# Grading protocol

`run_eval.py` preserves raw model responses and the rubric attached to each public case. It intentionally does not grade model quality. This companion tool validates independently authored grades and summarizes evidence by role, candidate, model revision, competency category, and individual rubric criterion.

## Score anchors

| Score | Anchor |
|---:|---|
| 0 | Incorrect, unsafe, fabricated, or materially non-responsive |
| 1 | Major errors; most of the criterion is unmet |
| 2 | Partially correct; one or more material omissions or defects |
| 3 | Meets the criterion; only minor defects |
| 4 | Fully meets the criterion with no material defect |

Use the same written anchors for every candidate and evaluator. Add concise notes for disputed, borderline, safety-related, or execution-related judgments. Do not infer a score from keyword overlap. For coding and tool-use tasks, require inspectable execution evidence where the task expects execution; never execute untrusted model output outside an isolated sandbox.

## Grade record

One JSON object per evaluator, candidate, model revision, run, and benchmark case:

```json
{
  "schema_version": "vectolith-human-grading/1.0",
  "benchmark_case_id": "prime-reasoning-001",
  "evidence_started_at": "2026-11-15T16:00:00+00:00",
  "candidate_id": "provider/model",
  "model_revision": "IMMUTABLE_REVISION",
  "role": "core_prime",
  "category": "reasoning",
  "run_id": "trial-01",
  "evaluator_id": "reviewer-01",
  "evaluator_version": "rubric-v1",
  "rubric_scores": [
    {
      "criterion": "criterion copied exactly from raw evidence rubric",
      "score": 4,
      "notes": "Short rationale"
    }
  ]
}
```

Every rubric criterion must be scored exactly once. Each grade must match raw evidence by case, candidate, revision, role, category, and exact `started_at` value (`evidence_started_at` in the grade). This distinguishes repeated inference runs of the same case. The tool rejects unknown criteria, missing scores, duplicate evaluator grades, invalid scores, and mismatched evidence. Keep evaluator identities stable and use independent reviewers; multiple runs by one person do not count as independent evaluators. A grade is bound to one exact raw response; do not grade a different repeat using the same run identifier.

## Generate a summary

```bash
python evaluation/summarize_human_grades.py \
  --evidence artifacts/evaluations/candidate.jsonl \
  --grades artifacts/evaluations/human-grades.jsonl \
  --output artifacts/evaluations/human-grade-summary.json \
  --min-evaluators 2 \
  --min-cases 3 \
  --minimum-mean 3.0
```

The output retains criterion-level means, population standard deviation, case counts, evaluator counts, and transparent statuses. The default minimum of three distinct cases intentionally marks a one- or two-case competency as insufficient evidence. Increase the minimum for high-stakes or release qualification.

## Interpretation boundary

- Results are reported per criterion and category; there is no opaque overall model score.
- `rubric_threshold_met` means only that configured human-grade thresholds were met for that criterion. It is not teacher qualification.
- `insufficient_independent_evaluators`, `insufficient_cases`, and `below_threshold` are explicit non-pass states.
- The summary always sets `qualification_decision` to `not_made`.
- Human grading does not replace private holdout evaluation, repeated-run variance, license and output-training permission review, verified free-compute testing, cross-review, contribution-shard checks, leave-one-teacher-out ablation, or teacher-disabled student release tests.
- Public benchmark fixtures are public and must not be represented as secret or contamination-proof holdouts.


## Core Prime qualification gate

The qualification gate is **Grading**. It requires a completed grading report covering the expected response set, a documented rubric version, and a SHA-256 digest of the report. It does not require a minimum number of graders, reviewer-independence attestations, inter-grader agreement statistics or thresholds, or adjudication. Those are not qualification safeguards under the current policy.

Preserve source outputs and grading reports with their provenance. The Grading gate validates report completion and traceability; it does not itself establish factual correctness or replace criterion-specific executable verification where an objective verifier is available.
