# Repository-wide engineering remediation plan

**Status:** Proposed execution baseline  
**Scope:** Canonical `vectolith/Models-by-vectolith.` repository only  
**Active student:** Core Prime  
**Paused track:** Core Prima  
**Operating rule:** No teacher qualification, foundation selection, training, or release claim without the evidence specified below.

## 1. Objective and exit condition

Move the repository from a model-development preparation platform to a defensible Core Prime development and operation pipeline. The work is complete only when the repository can:

1. Evaluate candidates against a genuinely protected holdout whose prompts and answer material are unavailable to training and ordinary repository/CI workflows.
2. assess reasoning, factuality, mathematics, code, tool use, safety, and instruction following with criterion-specific evidence rather than keyword overlap;
3. produce blinded, independently authored human grades, resolve disagreements through documented adjudication, and preserve immutable provenance;
4. qualify teachers only when every independent gate passes, including legal permission to use outputs for training;
5. select a Core Prime foundation using comparable, reproducible capability and operational evidence; and
6. execute a governed training run and serve the resulting student checkpoint independently of teacher inference.

Public fixtures remain useful for development and regression testing. They are not a protected holdout and cannot establish contamination resistance.

## 2. Priority order and dependency graph

| Order | Workstream | Depends on | Exit artifact |
|---|---|---|---|
| P0-A | Repair and reconcile existing PR backlog | Current main and branch diffs | Clean, rebased, reviewed PR sequence |
| P0-B | Evidence integrity and protected holdout | P0-A | Restricted holdout release, access audit, signed/hash-pinned run records |
| P0-C | Evaluation quality and executable verification | P0-A | Criterion-level reports with calibrated automated checks and human review |
| P0-D | Human grading and adjudication | P0-B, P0-C | Blinded review batch, independent grades, adjudication record, agreement report |
| P0-E | Teacher qualification | P0-B through P0-D | Candidate-specific gate report; no inferred approvals |
| P1-A | Core Prime foundation decision | P0-B through P0-E plus comparable candidate evidence | Signed selection record and reproducible comparison |
| P1-B | Governed training implementation | P1-A | Immutable run manifest, dataset lineage, approved training job, checkpoint |
| P1-C | Model serving and runtime product | P1-B | Authenticated inference API, model adapter, persistent task lifecycle, operational tests |

P0 work is evidence engineering, not another provider integration or candidate-discovery campaign. Do not start expensive training while the foundation and required data/teacher gates remain unresolved.

## 3. PR backlog repair

The open backlog at the time of this plan contains #35, #38, #39, #40, #41, and #42.

### 3.1 Required disposition

- **#39 — run-40 snapshot integrity and evidence:** review first against current `main`. Confirm the evidence file is present, linked from `evaluation/README.md`, and all recorded hashes, artifact IDs, revisions, response counts, and blocked-candidate states agree. Fix any discrepancy before accepting dependent work.
- **#40 — blinded human review:** reconstruct on top of the accepted #39 changes and current `main`. Preserve separate reviewer packages and the restricted identity key. Do not treat package generation as completed human grading.
- **#41 — completion-budget experiment:** review as an independent optional experiment after #39. It must not block or overwrite the existing run-40 evidence. Dispatch only through its explicit manual confirmation path; no experiment is implied by merging code.
- **#42 — four-teacher qualification gates:** reconstruct after #39 and integrate the final #40 review evidence contract. Keep qualification fail-closed; a cohort count is not evidence that any candidate qualifies.
- **#38 — continuous foundation verification:** review independently against current foundation-selection policy. Keep it separate from teacher qualification and do not let discovery observations become selection evidence.
- **#35 — checkpoint/memory audit:** review independently for source accuracy and ensure it is explicitly labelled as planning evidence, not measured runtime evidence.

### 3.2 Branch hygiene and acceptance

The current #40–#42 branches are stacked on stale #39 ancestry. Do not merge them as-is. Rebase or reconstruct one PR at a time against the latest accepted base; inspect the resulting diff and run the complete relevant test suites after each reconstruction. Preserve original PRs and evidence references until their replacements are reviewed. Close superseded PRs only after replacement PRs exist and their contents have been verified.

**Acceptance:** no unexplained commits-behind state; no duplicate/conflicting changes; no missing evidence files; clean diff against current `main`; full runtime and evaluation CI green; manual-only workloads remain undispatched unless separately authorized.

## 4. P0-B — protected holdout and evidence integrity

### Source files to inspect or change

- `evaluation/run_private_holdout.py`
- `evaluation/README.md`
- `docs/private-holdout-operations.md`
- `evaluation/run_eval.py`
- `evaluation/tests/`
- `.github/workflows/` (add a safe evaluation test workflow or extend existing workflow triggers)
- New implementation modules as needed: `evaluation/holdout_access.py`, `evaluation/holdout_manifest.py`, and `evaluation/holdout_audit.py`.

### Required implementation

1. Store prompts, reference answers, scoring rubrics, and hidden test assets outside the public Git repository in an access-controlled store. The repository contains only a schema, non-sensitive manifest metadata, and operational instructions.
2. Require explicit authenticated identity and least-privilege authorization for holdout release and execution. Separate roles for dataset custodian, experiment operator, reviewer, and administrator. A candidate operator must not be able to read the hidden prompt/answer corpus.
3. Keep holdout data out of ordinary CI, pull-request checkout, debug output, exception traces, logs, generated reports, model artifacts, and training-data exports. Do not expose secrets to untrusted fork PRs.
4. Pin every holdout release by immutable dataset version and cryptographic digest. Record the evaluator version, candidate/model revision, tokenizer, serving stack, generation settings, run ID, access principal, timestamps, and result artifact digest.
5. Use a controlled execution service or custodian-mediated evaluation. The model receives only the prompts required for a run; the operator receives aggregate/criterion-level results and approved evidence, not the full answer key.
6. Add access logging and anomaly detection for repeated queries, bulk extraction, unauthorized access, and suspicious result access. Define rotation and incident procedures for a compromised holdout.
7. Define contamination checks: overlap against public fixtures and training corpora where available, provenance review, canary items, and controlled refresh/retirement. A hash proves identity, not secrecy or non-contamination.
8. Add a holdout release policy: one sealed release per candidate/checkpoint/configuration unless a documented repeatability protocol permits more; record all attempts so repeated tuning against the holdout is visible.
9. Add a separation test that verifies the public repository, CI artifacts, and training export contain no holdout prompts, references, rubrics, credentials, or identity mapping.
10. Keep a public development suite and a private final holdout separate. Public fixture scores are never substituted for holdout evidence.

### Tests

- Unit tests for manifest schema, immutable digest verification, authorization decisions, role separation, access denial, audit event creation, and release-state transitions.
- Integration tests using a temporary encrypted/local test store and fake identity provider; verify an unauthorized operator cannot fetch prompt or answer payloads.
- Leakage tests scanning generated artifacts, logs, exceptions, and training exports for sentinel canary strings.
- Replay tests proving a changed dataset, model revision, tokenizer, generation configuration, or evaluator version changes the run identity and cannot overwrite an earlier record.
- CI tests proving untrusted pull requests never receive holdout credentials or access.

### Acceptance criteria

- No holdout content is present in Git, public workflow artifacts, or ordinary logs.
- Every run is traceable to an immutable holdout release and exact candidate/runtime configuration.
- Access is authenticated, role-scoped, logged, and denied by default.
- A controlled red-team leakage test fails the build when a canary appears in a prohibited output.
- A reviewer can reproduce the integrity check without being granted access to the hidden corpus.
- The holdout custodian can rotate or retire a compromised release without rewriting historical run records.

**Important:** a private file mounted into an ordinary CI job is not sufficient by itself. The trust boundary must prevent pull-request code and candidate operators from exfiltrating the dataset.

## 5. P0-C — evaluation beyond keyword scoring

### Source files to inspect or change

- `runtime/vectolith_runtime/independent_evaluation.py`
- `evaluation/run_eval.py`
- `evaluation/summarize_human_grades.py`
- `evaluation/README.md`
- `evaluation/tests/`
- `docs/independent-human-rubric-grading.md`
- `docs/core-prime-evaluation-curriculum-v4.md)

### Required implementation

1. Separate evaluation dimensions. At minimum: task correctness, reasoning validity, factual support, completeness, instruction adherence, safety, calibration, and operational reliability. Each case declares which dimensions apply and how each is evidenced.
2. Retain exact prompt, model output, tool traces, citations/source snapshots, executable artifacts, environment identity, and evaluator outputs. Hash raw records before scoring; scoring must never mutate raw evidence.
3. Replace keyword matching as a quality decision with calibrated criterion-specific evaluators:
   - **Code:** compile/type-check, unit and integration tests, hidden tests, static analysis, security checks, and execution in a network-disabled sandbox with resource/time limits.
   - **Math:** exact or tolerance-aware symbolic/numeric verification, units/dimensional checks, and independent derivation review for non-computable proofs.
   - **Factual/research:** claim extraction, source authority and date checks, citation-to-claim entailment, contradictory-source handling, and independent fact checking. A citation's presence alone is not correctness.
   - **Reasoning/planning:** rubric dimensions for validity of intermediate steps, constraint satisfaction, counterexample handling, and final-answer consistency; use expert review and verifiable outcomes where possible.
   - **Tool use:** validate structured arguments against schemas, execute only in a mock/sandbox environment, verify side effects and final state, and test permission boundaries.
   - **Safety:** adversarial and policy-specific cases graded against explicit expected safe behavior, not lexical refusal markers alone.
4. Keep automated evaluators as evidence contributors, not universal judges. Record evaluator version, thresholds, calibration set, known failure modes, and confidence. Model-graded outputs require validation against human labels and must not be the sole basis for teacher qualification or foundation selection.
5. Report per-case and per-criterion results, confidence intervals where sample sizes support them, error taxonomy, completion/truncation status, and subgroup/category breakdowns. Do not collapse all dimensions into a single opaque score.
6. Add evaluator calibration and adversarial tests, including paraphrase invariance, valid alternative answers, false-positive keywords, adversarial prompt injection, partial correctness, and deliberately plausible but incorrect answers.
7. Maintain a strict distinction between public regression results and protected holdout results.

### Tests

- False-positive/false-negative fixtures for every evaluator family.
- Equivalent correct answers with different wording must pass.
- Keyword-rich but incorrect answers must fail.
- Code evaluator tests for compilation failure, failing tests, timeouts, resource exhaustion, network access denial, and sandbox cleanup.
- Math evaluator tests for equivalent forms, rounding, units, edge cases, and incorrect intermediate claims.
- Factual evaluator tests for stale, low-quality, contradictory, and irrelevant citations.
- Tool evaluator tests for malformed arguments, unauthorized side effects, replay, and incorrect final state.
- Evaluator determinism tests and raw-evidence immutability tests.

### Acceptance criteria

- No keyword-only score can qualify or disqualify a teacher or select a foundation.
- Each scored dimension is linked to a versioned rubric and auditable evidence.
- Executable tasks are actually executed in a controlled environment.
- Human labels are used to measure evaluator agreement and failure rates before model-graded metrics can be used as supporting evidence.
- Reports preserve failures, timeouts, truncated responses, and missing evidence; missing evidence never becomes a pass.

## 6. P0-D — independent human grading and adjudication

### Source files to inspect or change

- `evaluation/build_blinded_review.py` (or the actual builder path introduced by PR #40)
- `evaluation/summarize_human_grades.py`
- `evaluation/tests/`
- `docs/independent-human-rubric-grading.md`
- `evaluation/README.md`
- Restricted review storage and identity-key handling described in the private-holdout operations documentation.

### Required implementation

1. Freeze each review batch before distribution: exact candidate revisions, response artifacts, prompt/rubric versions, raw-file hashes, coverage expectations, and reviewer assignment manifest.
2. Randomize candidate aliases and response order independently per reviewer. Reviewers must not see model names, provider, revision, prior grades, or other reviewers' submissions.
3. Require at least two independent qualified reviewers for every response. Reviewers disclose relevant conflicts and grade against criterion-level anchors with evidence notes. Do not allow a model/provider author to be the sole reviewer of its own output.
4. Validate reviewer identity, batch membership, assignment, complete case coverage, rubric version, grade range, and submission digest. Reject duplicate, incomplete, altered, or out-of-assignment submissions.
5. Compute agreement by criterion, not just a single aggregate: weighted Cohen's kappa for two raters where appropriate, Krippendorff's alpha for missing/multiple-rater designs where appropriate, exact agreement, score-distance distribution, and confidence intervals where statistically justified. Report prevalence/imbalance caveats; kappa alone can mislead.
6. Predefine adjudication triggers (for example, material score disagreement, correctness/safety disagreement, or low agreement). An independent adjudicator reviews the blinded evidence, both rationales, and executable/source evidence where applicable, then records a reasoned final disposition.
7. Preserve original blinded grades, reviewer rationales, adjudication changes, identity mapping, and final report as separate immutable records. Unblinding occurs only after grades and adjudication are locked.
8. Publish aggregate outcomes and process metadata without exposing reviewer identities, private holdout content, or restricted identity keys.
9. Track reviewer qualification and calibration using a shared anchor set; periodically re-check drift and disagreement.
10. Explicitly distinguish review-pipeline completion from teacher qualification. A completed review package is not a completed review; a completed review is not an approval.

### Tests

- Blinding tests proving identity fields and source artifact names are absent from reviewer packages.
- Independent randomization tests and deterministic reproducibility under a recorded seed.
- Assignment and identity-key access-control tests.
- Complete/incomplete/duplicate/altered submission tests.
- Agreement-statistic tests against hand-calculated examples, including missing ratings and prevalence imbalance.
- Adjudication tests proving original grades remain unchanged and final decisions cite evidence.
- End-to-end test with synthetic candidates, synthetic reviewers, deliberate disagreements, and a separate adjudicator.

### Acceptance criteria

- Every qualification-bound response has two independent valid grades or a documented exception that blocks qualification.
- All triggered disagreements are adjudicated by an independent reviewer.
- Criterion-level agreement and disagreement are reported with limitations.
- The final report is digest-backed and reproducible from the locked source artifacts.
- No candidate is unblinded before the review lock and no reviewer can access the identity key during grading.

## 7. P0-E — teacher qualification and cohort gate

### Source files to inspect or change

- `runtime/vectolith_runtime/teacher_pipeline.py`
- `runtime/vectolith_runtime/independent_evaluation.py`
- `evaluation/validate_teacher_qualification.py` (or the actual qualification validator path from PR #42)
- `evaluation/teacher-qualification-manifest.schema.json` (or the actual schema path from PR #42)
- `evaluation/tests/`
- `docs/multi-teacher-distillation-and-student-independence.md`
- `docs/executable-multi-teacher-pipeline.md`

### Required implementation

- Validate each response against a teacher manifest pinned to the exact model revision, tokenizer, serving configuration, license evidence, and competency scope. Do not accept a teacher ID string as proof of qualification.
- Keep model-weight license approval and permission to use generated outputs for training as separate human-reviewed gates.
- Require immutable snapshot and provenance, successful real inference, loader compatibility, resource/cost evidence, safety review, protected-holdout evidence, completed independent human review/adjudication, corpus integrity, and explicit training-output permission.
- Require demonstrated positive leave-one-teacher-out contribution on held-out criteria before a teacher contributes to a training cohort. Contribution is competency-specific; a teacher may qualify for one domain and not another.
- Retain rejected, blocked, and failed evidence. Never silently omit a candidate or convert missing evidence into a pass.
- Keep the existing minimum of four distinct qualified teachers for an active student training cohort, but do not lower the standard or count four unqualified candidates.
- Enforce qualification again at dataset construction and training preflight, not only in a report-generation script.

### Tests and acceptance

- Mutation tests for every gate, revision mismatch, expired/revoked approval, incomplete review, holdout absence, negative/neutral ablation, and output-permission denial.
- Dataset builder rejects any response from an unqualified or out-of-scope teacher.
- Training preflight rejects a cohort with fewer than four qualified teachers or any failed gate.
- No current candidate is described as qualified until real human, legal, holdout, and contribution evidence exists.

## 8. P1-A — defensible Core Prime foundation decision

### Source files to inspect or change

- `docs/foundation-selection.md`
- `evaluation/FOUNDATION_DISCOVERY.md`
- `evaluation/discover_hf_candidates.py`
- `evaluation/run_real_candidate_eval.py`
- `evaluation/run_real_checkpoint_suite.py`
- `evaluation/summarize_real_candidate_results.py`
- `evaluation/probe_compute.py`
- `evaluation/fixtures/real_cpu_candidates_v1.json`
- `evaluation/tests/`

### Required implementation

1. Freeze a small, evidence-backed shortlist from already observed candidates. Do not launch another broad discovery campaign as a substitute for comparison.
2. Pin immutable model and tokenizer revisions and archive exact license/model-card evidence. Obtain explicit legal review of weight terms and output-training permission separately.
3. Compare identical task suites, prompt templates, generation settings, serving stack where feasible, and evaluation procedures. Separate CPU feasibility tests from GPU performance claims.
4. Include Core Prime's full competency scope: reasoning, coding, debugging, architecture, mathematics, research/factuality, tool use, multilingual capability, safety, long-context behavior, and reliability.
5. Record peak memory, load time, time-to-first-token, tokens/sec, latency distribution, concurrency, context capacity, quantization, hardware, power/cost, serving compatibility, and operational constraints.
6. Use protected holdout results only after the P0 controls pass. Do not use public smoke/benchmark scores as hidden-holdout results.
7. Produce a decision matrix with evidence confidence and unresolved risks. A selection requires an explicit rationale and human approval; do not infer a winner from download count, parameter count, CPU throughput, or one benchmark.
8. If no candidate passes, record no selection and specify the minimum missing evidence. Do not force a decision.

### Tests and acceptance

- Reproducibility tests for pinned revisions, prompt/template hashes, evaluator versions, and run manifests.
- Candidate report validation rejects missing or mismatched evidence.
- Selection record cites immutable run IDs and evidence digests and documents license, output permission, quality, resource, deployment, and risk trade-offs.
- No expensive training starts before the decision record is approved.

## 9. P1-B — governed Core Prime training

### Source files to inspect or change

- `runtime/vectolith_runtime/distillation_training.py`
- `runtime/vectolith_runtime/distillation.py`
- `runtime/vectolith_runtime/teacher_pipeline.py`
- `runtime/vectolith_runtime/infrastructure.py`
- `runtime/vectolith_runtime/infrastructure_persistence.py`
- `docs/training-infrastructure-specification.md`
- `runtime/tests/`

### Required implementation

- Introduce validated dataset manifests with source provenance, rights, teacher/revision qualification, rubric/evidence status, split membership, content hashes, deduplication, contamination checks, and explicit exclusions.
- Enforce train/validation/test separation and ensure private holdout material and answers cannot enter any training split.
- Replace the current basic SFT helper's loose teacher-ID counting with a preflight that validates every row against immutable qualification records and cohort policy.
- Persist a complete immutable run manifest: foundation/tokenizer revisions, code commit, dataset manifest and digest, training method/configuration, seed, hardware/precision, budget, checkpoint hashes, metrics, evaluator versions, stop/failure state, and parent lineage.
- Add deterministic/resumable run state, checkpoint validation, failure recovery, resource limits, explicit approval, and artifact lineage.
- Keep teacher inference out of student runtime. A released Core Prime checkpoint must be loadable and usable without any teacher service.
- Start with governed SFT/distillation. Add RLVR/GRPO only after reward definitions, verifiable tasks, evaluator calibration, and safety gates are implemented and validated.

### Tests and acceptance

- Dataset mutation, source revocation, teacher qualification, split leakage, and holdout canary tests.
- Reproducibility and checkpoint round-trip tests.
- Interrupted/resumed run and budget-exhaustion tests.
- Training preflight refuses any missing lineage, rights, teacher, foundation, or approval evidence.
- A small, explicitly approved smoke training run produces a verifiable checkpoint and evaluation report before any scale-up.

## 10. P1-C — operational serving and runtime product

### Source files to inspect or change

- `runtime/vectolith_runtime/registry.py`
- `runtime/vectolith_runtime/contracts.py`
- `runtime/vectolith_runtime/loading.py`
- `runtime/vectolith_runtime/engine.py`
- `runtime/vectolith_runtime/infrastructure.py`
- `runtime/vectolith_runtime/infrastructure_persistence.py`
- `runtime/README.md`
- `docs/runtime-architecture.md`
- `docs/delegated-execution-contract.md`
- `.github/workflows/runtime.yml`

### Required implementation

- Replace hard-coded family role assumptions with extensible model IDs and capability/policy routing while preserving Core Prime as the active default and Core Prima as paused.
- Add a real, tested serving adapter for the selected foundation/checkpoint and a model-neutral inference gateway. Do not bind runtime contracts to one provider.
- Add durable task storage, validated lifecycle transitions, restart recovery, deadlines, cancellation, retry policy, and idempotency.
- Replace caller-supplied approval booleans with principal-bound, scoped, expiring authorization evidence for tools and side effects.
- Add API authentication, tenant isolation, rate/resource limits, audit events, observability, health checks, and operational runbooks.
- Add integration tests for success, failure, permission denial, malformed tool calls, timeout, retry, cancellation, restart, and independent model operation.
- Extend CI so evaluation tests run when evaluation code, fixtures, schemas, or workflows change; protect secrets from untrusted fork pull requests. Keep heavyweight live model tests explicitly gated and manual/scheduled where appropriate.

### Tests and acceptance

- Contract tests across registry, gateway, serving adapter, task store, authorization, and tool execution.
- Restart/recovery and multi-tenant isolation tests.
- Security tests for privilege escalation, replay, expired approval, data leakage, and untrusted tool output.
- End-to-end authenticated inference and delegated-task execution against a small local/test checkpoint.
- A documented deployable service with measured latency, resource profile, failure behavior, and rollback procedure.

## 11. Cross-cutting CI and evidence policy

Update CI coverage for the files it actually validates. The existing runtime workflow is path-filtered to `runtime/**`; evaluation-only changes therefore need their own workflow or an expanded workflow with separate jobs. Do not run protected holdout jobs on untrusted pull-request code.

All evidence reports must include:
- repository commit and workflow run/attempt;
- candidate, immutable model and tokenizer revisions;
- prompt suite or holdout release ID and digest;
- generation and serving configuration;
- evaluator and rubric versions;
- raw artifact hashes and completion/error status;
- reviewer/adjudicator provenance where relevant;
- explicit gate outcomes and unresolved limitations.

Never commit credentials, protected holdout content, reviewer identity keys, private training data, or model weights. Public reports must be redacted by construction, not manually cleaned after a leak.

## 12. Execution board and stop conditions

### Immediate sequence

1. Reconcile #39 and the independent #35/#38 reviews against current main.
2. Reconstruct #40, #41, and #42 in dependency order; validate the exact diff and tests for each.
3. Implement protected holdout controls and leakage tests.
4. Implement criterion-specific evaluation and executable verifiers.
5. Complete real blinded human grading and adjudication for the existing response batches; preserve any insufficient or disputed result as such.
6. Enforce teacher gates against actual evidence and perform leave-one-teacher-out contribution analysis.
7. Make the Core Prime foundation decision from the resulting comparable evidence.
8. Implement governed training and a real serving path around the selected foundation.

### Stop conditions

Stop and record a blocked state if:
- protected holdout access cannot be isolated from operators or CI code;
- a candidate's immutable revision, license, or output-training permission is missing;
- reviewer independence or adjudication cannot be demonstrated;
- the evaluation method cannot verify the claimed competency;
- evidence artifacts do not match their recorded hashes;
- a teacher has no positive measured contribution for the proposed competency;
- no foundation candidate satisfies the decision gates; or
- training/serving cost or safety limits are not approved.

A blocked state is a valid result. Do not manufacture progress by relaxing gates.

## 13. Definition of done

The repository has closed the preparation-to-production gap only when Core Prime has:

- an approved, evidence-backed foundation selection;
- a reproducible and governed training run with complete data/model lineage;
- a checkpoint independently evaluated on public regression suites and a protected holdout;
- documented human review and adjudication for all human-scored qualification claims;
- a serving adapter and authenticated runtime that operate without teacher inference;
- passing automated, integration, security, recovery, and evaluation CI; and
- a release record that states actual capabilities and limitations without extrapolating beyond the evidence.

Until then, Core Prime remains in development and no production capability or teacher qualification is implied by this plan.
