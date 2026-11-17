# Criterion verification and protected holdout operations

This implementation adds deterministic exact-answer and decimal verifiers, signed
sandbox-attestation verification for code tasks, and source-backed factuality review
that requires independent human adjudication. These methods are not a universal
reasoning score. Select a verifier per case rubric and preserve unscored cases when
required evidence is absent.

| Competency | Accepted evidence | Limitation |
|---|---|---|
| Exact objective answer | Canonical expected answer and case-bound digest | Single-answer tasks only |
| Numeric reasoning | Strict decimal parse and explicit tolerance | Does not prove derivation |
| Software correctness | HMAC-authenticated report from a separately operated sandbox | This repository does not provide the sandbox service |
| Factual accuracy | Claim-level source URI/digest plus independent review and adjudication | Human source verification remains required |
| Open-ended reasoning | Blinded rubric grading, agreement analysis and adjudication | No keyword or generic lexical score |

## Protected holdout deployment

The protected-holdout manifest validator requires separate storage and key custody,
a distinct evaluator operator, a dedicated evaluator deployment, denial of pull-request
code and candidate egress, read-only dataset mounting, access logs, leakage and
provenance audits, and an auditor independent of the custodian and evaluator operator.

The validator does not provision cloud resources, inspect an external account, or make
a public fixture private. A holdout is not established until the custodian provisions
the external boundary and an independent auditor supplies real evidence. Keep all
holdout prompts, answers, labels, keys and source files out of Git and ordinary CI
artifacts. Never expose the holdout to candidate model code or pull-request workflows.

## Tests

    python -m unittest evaluation.tests.test_criterion_verifiers
    python -m unittest evaluation.tests.test_protected_holdout_manifest

Do not create qualification manifests from templates or test fixtures. Only real,
independently reviewed evidence may satisfy teacher gates.
