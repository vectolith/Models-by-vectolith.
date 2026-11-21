# Core Prime blinded grading audit utility

This utility summarizes independently supplied human scores; it does not generate scores or grade responses. Use blinded case IDs, keep identity/condition mapping separately and securely, and provide reviewer IDs checked against the teacher cohort.

Input JSON shape:
```json
{"ratings":[{"blind_case_id":"blind-001","reviewer_id":"reviewer-A","score":4}]}
```
Scores are numeric on a 0–5 scale. Each case should have at least two distinct reviewers. Run:
```sh
python scripts/core_prime_grading_audit.py ratings.json --cohort teacher_reviewer_conflicts.json --minimum-cases 900 --output agreement-report.json
```
The cohort file is a JSON array of reviewer IDs that must not participate (e.g. teacher/model cohort conflict IDs). The report summarizes coverage, duplicate records, reviewer-cohort conflicts, exact agreement, and Cohen's kappa using the first two lexically sorted reviewer IDs per case.

The script is a helper, not a qualification decision: agreement statistics are descriptive, reviewer independence and rubric validity require human verification, missing/invalid ratings block, and the report is not legal or permission evidence. Synthetic tests do not constitute grading the actual 900 responses. Do not place sensitive identity mappings or protected evaluation content in this public repository.
