# Repository audit and coverage pass — 2026-11-21

Scope: whole repository, top to bottom — runtime, evaluation, tooling, docs, and CI.
Delivered as PR #88 (test coverage + audit tooling) and PR #89 (hygiene enforced through CI test discovery).

## What was missing

Two runtime modules were entirely untested:

- `runtime/vectolith_runtime/distillation_training.py`
- `runtime/vectolith_runtime/protected_holdout.py`

Both encode correctness rules that decide whether a distillation run or a holdout report can be trusted, so an untested line in either is an unverified claim.

## Tests added (27)

### distillation_training

- Prompt-group splitting: no prompt group leaks across the train/eval boundary.
- Label masking: only assistant tokens carry loss; prompt and padding tokens are masked out.
- Truncation guards: over-length sequences are rejected or truncated exactly as documented.
- `train_student` preflight guards: missing config, mismatched tokenizer vocab, and bad dataset shapes fail loudly before any training step.
- Tokenizer and dataset fixture round-trips.

### protected_holdout

- Custody rules: access events are recorded and non-authorized reads are refused.
- Execution rules: reports cannot be executed outside an authorized window.
- Audit rules and report binding: a report is bound to the holdout digest it was produced against.
- Digest checks: mutated fixtures and tampered reports are rejected.

## Metrics

| Metric | Before | After |
| --- | --- | --- |
| Runtime test suite | 104 tests | 131 tests |
| Runtime coverage | 81% | 85% |
| Markdown files link-checked | none | 76 |

## Tooling

- `tools/repo_audit.py` — fails on broken relative markdown links and on tracked build artifacts (caches, compiled output, `.egg-info`, coverage files).
- `make audit` — runs the audit locally.
- Hygiene is also enforced inside CI through test discovery (`runtime/tests/test_repo_hygiene.py`), so the existing workflow catches lockfile drift, untracked build junk, broken doc links, and a failing `vectolith_runtime` selfcheck without any workflow-file change.

## Cleanup

- Removed the committed `*.egg-info` directory from version control and added it, plus coverage output and audit scratch files, to `.gitignore`.

## Verified on main after merge

- Runtime suite: 131 tests, all passing.
- Evaluation suite: 142 tests, all passing.
- `vectolith_runtime selfcheck`: passing.
- `python3 tools/repo_audit.py`: clean.
- 76 markdown files, zero broken relative links.

## Known follow-up

The CI workflow still triggers only on `runtime/**` and `evaluation/**` paths. Widening the triggers to `models/`, `schemas/`, `data/`, `tools/`, `Makefile` and `pytest.ini` is prepared on branch `ci/full-repo-checks` but requires a GitHub token with the `workflow` scope, which needs an interactive authorization by the account owner.
