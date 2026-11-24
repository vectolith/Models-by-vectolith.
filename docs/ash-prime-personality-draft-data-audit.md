# ASH PRIME draft split exposure audit

**Status: BLOCKED — the draft holdout rows remain compromised, and the replacement v2 holdout is split-isolated but not yet custodian-protected.**

Replacement in progress (2026-11-24): `data/personality/holdout/ash-prime-protected-holdout-v2.jsonl` (12 fresh original records, digest `b025cfbb769a5e7cb13652ca63e5acc7d8c5f4cbe9df64fa5da90af26d82f0e8`) was authored after this audit and is not derived from any training corpus, prompt fixture or prior draft row. It is hash-manifested in `ash-prime-protected-holdout-v2-manifest.json` and enforced by `scripts/validate_ash_prime_holdout.py`, which CI runs on every personality-data change; `scripts/tests/test_holdout_isolation.py` fails if any 8-word holdout shingle or holdout record ID appears in a non-holdout path. This closes the split-isolation engineering gap only. Because the file and digest sit in a public repository it is still not a blind protected holdout: the custody gate stays BLOCKED until a restricted private copy, separate custodian/evaluator identities and access controls exist.

Audit scope: public \`main\` snapshot and the ASH PRIME personality-draft datasets. This is a source-level audit, not a legal review, training authorization, or claim that a protected evaluation was run.

## Findings

The repository is public. The current synthetic draft files contain split-labeled records in the same tracked files as training records:

- Multiturn trajectories: 25 total; 20 marked train and 5 marked holdout.
- Contrastive preferences: 24 total; 19 marked train and 5 marked holdout.
- Micro scenarios: 20 total; 16 marked train and 4 marked holdout.

The split labels and export filters are useful for a development smoke test, but they do not establish custody or confidentiality. The records marked holdout have been exposed in a public repository and its accessible Git history. **They are compromised as protected holdout material.** Do not use those records to claim independent blind evaluation, tune against them, or qualify a candidate.

The public 30-case behavioral evaluation set is also a public benchmark and must not be represented as a private holdout.

## What CI currently verifies

The ASH PRIME personality-data workflow has checked the draft's schema/consistency, run unit tests, and smoke-tested the train-only exporter and SFT/DPO preparation. The observed smoke output excludes the marked holdout records from the generated training files. These checks establish pipeline behavior for the draft files only—not provenance, rights, data quality, secure custody, model quality, or permission to train.

## Required replacement and custody controls

1. Create a new holdout from independently authored or otherwise rights-cleared material, with provenance and permissions recorded.
2. Store it outside this public repository and its Git history, in a custodian-controlled private location. Restrict access to the custodian and authorized evaluator(s); never expose its content or labels to training, PR CI, candidate selection, tuning, or model developers.
3. Pin a version and SHA-256 digest for the exact holdout file; retain the access-control, custody, creation and independent-review evidence.
4. Pre-register a scoring rubric, blind procedure, candidate revisions, and run limits before evaluation. Keep the condition map separate; preserve raw results and audit records.
5. Have independent evaluators score the replacement holdout. Treat missing, compromised, or unauthorized evidence as a blocker, not as a pass.
6. Update the training preflight and manifests to bind the exact replacement holdout digest and its custody/evaluation evidence. Do not unlock training merely because this audit document exists.

## Decision

No training or inference was performed by this audit. The current holdout labels remain useful for development split-isolation checks only; their content is not suitable for protected evaluation. The training gate remains closed pending replacement holdout custody, all other legal/provenance/teacher/foundation/compute gates, and explicit authorization.
