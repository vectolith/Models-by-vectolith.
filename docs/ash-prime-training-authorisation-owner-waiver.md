# ASH PRIME training authorisation: owner waiver

**Date:** 2026-11-24
**Owner:** ganiyu (repository owner, vectolith/Models-by-vectolith.)
**Machine-readable record:** [evaluation/owner_waivers.json](../evaluation/owner_waivers.json)
**Enforced by:** [evaluation/teacher_qualification_gates.py](../evaluation/teacher_qualification_gates.py), [evaluation/prime_candidate_policy_gate.py](../evaluation/prime_candidate_policy_gate.py)

The owner has removed the following review gates as prerequisites for teacher qualification and training start. A waiver is an owner decision, not a review. No item below has been reviewed, approved, attested or signed by an independent party, and none may be reported as verified.

## Waived

| Gate | Consequence the owner accepts |
| --- | --- |
| `license_review` | Model-weight and output licence risk accepted without independent legal review; derived-weight redistribution may carry unresolved licence risk. |
| `grading` | Two independent human graders are not required; the locked local Qwen3.5-2B grader is the only grading in use, so some teacher responses may score as correct when a human would reject them. |
| `safety_review` | No separate independent safety pass exists over teacher outputs before distillation. |
| `holdout` | Custody sign-off waived; leakage auditing remains automated in `scripts/validate_ash_prime_holdout.py`. |
| `corpus_integrity` | Human corpus attestation waived; digests and duplicate counts are computed by tooling only. |
| `training_output_permission` | Written permission from each teacher rights holder is not required before training; distilled weights may lack explicit written permission. |

## Still enforced

Revision-bound mechanical gates are unchanged and can never be waived: `snapshot`, `loader_compatibility`, `real_inference`, `resource_measurement`. A candidate with an invalid immutable revision, incomplete inference coverage, inference errors or unmeasured resources stays `not_qualified`.

## Reporting rules

- Any qualification or authorisation report produced under these waivers must set `review_basis: "owner_waiver"` and list the gates in `waived_gates`.
- Such reports must keep `training_started` accurate. A waiver unblocks the gate; it does not record a training run.
- Running the gate CLI with `--strict` ignores every waiver, which is how to reproduce the pre-waiver fail-closed result.
