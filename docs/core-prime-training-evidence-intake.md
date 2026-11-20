# Core Prime training evidence intake

**Current decision: BLOCKED. No training authorization is granted by this checklist or by a passing preflight report.**

This document is the intake record for the evidence consumed by
`runtime/vectolith_runtime/training_preflight.py`. It distinguishes evidence
that must be produced by its accountable owner from declarations that merely
claim a gate has passed.

## Evidence handling rules

- Keep the private holdout dataset, scoring keys, raw candidate outputs, private
  evaluation reports, access logs, and signed authorization material in the
  restricted evaluation vault. Do not commit them, attach them to a public PR,
  or expose them to pull-request CI.
- Store only non-sensitive evidence references, immutable artifact identifiers,
  and SHA-256 digests in the approval records. A digest does not prove that the
  underlying artifact is authentic, lawful, complete, or correctly reviewed.
- Preserve the exact bytes of each source artifact. Any correction creates a
  new version and digest; do not overwrite evidence after approval.
- Legal permission, grading, security review, foundation
  selection, compute approval, and software validation are separate decisions.
  One must not be inferred from another.
- Never fill a missing field with a synthetic value, test fixture, placeholder
  digest, or unverified assertion.

## Intake register

| Gate | Required source evidence | Accountable producer | Current state |
|---|---|---|---|
| Dataset provenance | Non-empty corpus artifact, exact SHA-256, source/creator records, license text and authority to use the contents for training | Dataset owner + rights reviewer | BLOCKED |
| Teacher qualification | Four or more distinct teacher manifests, each tied to an immutable revision and passing every required qualification gate | Teacher qualification owner | BLOCKED |
| Teacher rights | Exact license review, legal reviewer, dated decision, evidence URI, and separate explicit training-output permission document for each teacher | Authorized rights holder + legal reviewer | BLOCKED |
| Teacher evaluation | Real inference artifacts, resource measurements, safety review, a completed grading report covering the full response set, with rubric version and report digest | Evaluation lead | BLOCKED |
| Protected holdout deployment | Actual restricted dataset, verified byte digest, case count, custody and key separation, evaluator isolation, access logs, provenance and leakage audits | Independent dataset custodian + security auditor | BLOCKED |
| Protected teacher results | One validated candidate result per teacher, bound to the deployment digest, exact teacher revision, evaluator identity/image and complete scoring counts | Independent evaluator | BLOCKED |
| Foundation selection | Comparative report and evidence for required categories, explicit approved decision, exact model ID and immutable 40-character revision | Authorized model-selection approver | BLOCKED |
| Training configuration | Exact configuration approved for this run; configuration must match the execution manifest | Lead maintainer / training approver | BLOCKED |
| Execution approval | Run ID, approval document, dataset and code digests, exact foundation revision, approved config, compute provider/project/region, runtime image digest, software versions, resource probe and cost/runtime caps | Authorized training approver + infrastructure owner | BLOCKED |
| Preflight record | CLI report, exit code, exact input digests, validated row count, qualified teacher IDs and source commit | CI/evaluation operator | NOT RUN |

## Existing evidence inventory — reusable, not qualification

The following public inference artifacts already exist in GitHub Actions. Their
presence provides candidate snapshot/inference and execution observations only;
it does not satisfy legal review, grading,
safety review, protected holdout, corpus integrity, or training-output permission.
Keep the source artifacts unchanged and retain their run/commit identities.

| Run | Candidate artifacts available | Workflow outcome | Qualification disposition |
|---|---|---|---|
| 40 — `43796213917` | Granite 3.1, Granite 4.2, MiniCPM5, LFM2.5, Phi-4 | Failure overall: SmolLM3 failed its missing-LICENSE gate; five other candidate jobs succeeded | All five unqualified |
| 42 — `43820188813` | Granite 3.1, Granite 4.2, MiniCPM5, LFM2.5, Phi-4 | Failure overall: SmolLM3 failed its missing-LICENSE gate; all five other candidate jobs are now completed successfully | All five unqualified |
| 43 — `43821046671` | Granite 3.1, Granite 4.2, MiniCPM5, LFM2.5, Phi-4 | Failure overall: SmolLM3 failed its missing-LICENSE gate; five other candidate jobs succeeded | All five unqualified |

The run 40 and run 42/43 evidence reports record immutable candidate revisions,
response artifacts, per-run resource observations and artifact digests. Run 42
Phi-4 completed after the earlier report was written; its artifact is
`14280614317`, with GitHub-reported SHA-256
`9b34e52ef661236741bae16b7de0ce9b04b065fdb223e2aec3bfb4d812cbac4c`.
Its ZIP contents have not yet been independently re-inspected in this intake
update. Run 42's workflow remains a failure overall because SmolLM3's snapshot
gate failed; the Phi-4 job itself succeeded.

The reusable inference evidence therefore covers five candidates, but **there
are still zero qualified teachers**. The candidate manifest template remains
empty/pending; do not copy inference metadata into a qualification status or
treat model-weight license tags as permission to train on generated outputs.

Existing grading evidence is separate: the two supplied AI-generated
grading files cover 900 blinded response IDs and 2,765 rubric entries each
(1,800 AI score entries in total). The user checked and approved those AI
scores. These files are AI-generated scores that the user reviewed and approved;
they are not a substitute for grading teacher responses. The files contain 391
cross-file criterion differences. Preserve both originals and their provenance;
these historical differences are descriptive and do not require adjudication
under the current Grading policy. The current evidence package v2 contains the
originals, a difference queue, and its manifest/README.

The GitHub Actions artifacts are time-limited and should be retained in the
restricted evidence vault before expiry. Do not copy private holdout material,
scoring keys, or private identity mappings into GitHub Actions or this public
repository.

## Protected holdout: required artifacts

The proposed 500-sample holdout count is a target declaration only until the
actual restricted artifact is provisioned and independently checked. The
authoritative deployment validator accepts a positive case count; it does not
prove that a claimed count corresponds to a real dataset. The custodian must
verify the dataset bytes and record the resulting digest and exact count.

The runtime expects:

1. A deployment manifest using schema
   `vectolith-protected-holdout-deployment/1.0`, validated against the actual
   private suite. It must include custody, independent key custody, separate
   evaluator identity, evaluator image digest, denied pull-request code and
   network egress, read-only dataset mounting, separated result channel,
   access-log digest, leakage-audit digest, provenance-report digest, public
   fixture overlap check, zero unauthorized access, and an independent auditor.
2. A protected evaluation result at
   `<holdout-results>/<teacher-id>.json` for every teacher. Each result must
   bind to the deployment digest and exact candidate ID/revision; match the
   evaluator identity/image and case count; account for every case with zero
   unscored cases; meet the declared pass threshold; and record suite version,
   timestamp and evaluator run ID.
3. Each teacher qualification manifest must repeat and match the deployment,
   result, case-count and leakage-audit digests.

The repository's public test fixtures are tests of validator behavior only.
They are not private holdout evidence and must never be promoted into the
production evidence register.

## Teacher qualification: minimum four distinct teachers

Each of at least four teacher manifests must independently pass all gates
enforced by `validate_teacher_manifest`:

- immutable snapshot;
- approved license review;
- loader compatibility and remote-code disposition;
- real inference with complete response counts and artifact digest;
- measured compute/resource record;
- a completed grading report covering the required response set, with rubric version and report digest;
- safety review;
- protected holdout result;
- corpus integrity and provenance;
- explicit training-output permission.

The accepted dataset must bind every row to a qualified teacher ID and exact
teacher revision. Each row's content digest is SHA-256 of
`prompt + NUL + response`. At least four distinct qualified teacher IDs must
actually occur in the accepted dataset.

## Foundation and run-specific execution

The foundation-selection record must use
`vectolith-foundation-selection/1.0`, state `approved`, bind the exact model
ID and immutable revision, identify the approver and approval time, and include
digests for candidate metadata, license review, training-output permission,
loader compatibility, resource measurement, capability evaluation, protected
holdout and baseline comparison.

The training execution record must use
`vectolith-training-execution-approval/1.0` and bind:

- student ID `core-prime`;
- exact foundation ID and immutable revision;
- exact accepted dataset SHA-256;
- exact training-code commit;
- complete normalized training configuration;
- run ID, approval document digest, approver and approval timestamp;
- execution-environment approval reference and maximum runtime;
- provider, account/project, region, runner, accelerator count/type, immutable
  runtime image digest and required software versions;
- measured available RAM/VRAM/storage, estimated peak requirements and
  resource-probe digest.

An `approved_by` string in a YAML file is not, by itself, approval evidence.

## Authorization boundary

A successful call to `validate_training_preflight` establishes only that the
specified machine-verifiable evidence passed the current validators. It does
not independently establish legal rights, validate the truth of a reviewer's
attestation, or authorize a training run. Training must remain disabled until
the authorized project owner has reviewed the complete evidence package and
explicitly approved the run through the project's separate authorization
process.

## Candidate seed corpus — non-empty, not production-approved

A 16-record original-authored candidate seed has now been added at
`data/core-prime-seed-v0.1.jsonl`, with a separate provenance record at
`evidence/core-prime-seed-v0.1-provenance.json`. Its recorded SHA-256 is
`43a3e7fd3a6c955c4b28dbd5e54adfd6c7c005ad4f27ffbf964942896550f250`
and its UTF-8 byte length is 10,272. The records are illustrative authored
examples, not teacher-generated outputs. Owner acceptance, technical/factual
review, safety review and rights approval remain pending. This seed is not
eligible for the authoritative training dataset and does not satisfy the
four-qualified-teacher or teacher-output provenance requirements. See
[seed corpus provenance and limitations](core-prime-seed-corpus-v0.1.md).

## Current known blockers

- The legacy provenance digest
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  is the SHA-256 of empty bytes and cannot authenticate a non-empty corpus.
  The new seed corpus has a non-empty digest but remains a candidate seed only;
  it is not an approved teacher-response training corpus.
- The previously supplied 500-case holdout manifest is not the runtime's
  protected deployment manifest and is not proof that the suite exists,
  is private, or has passed a leakage audit.
- The previously supplied teacher record names one teacher only and does not
  provide the full qualification gates or separate training-output permission
  document.
- The foundation-selection document currently states that no foundation has
  been selected.
- The supplied YAML's maintainer label is not a run-specific execution
  authorization and lacks the required compute, capacity and execution-environment binding
  evidence.
- The authoritative preflight has not been run against real evidence.

Update this register only when the underlying artifact has been obtained,
verified and its owner has accepted responsibility for the attestation.


## Restricted evidence manifest

A separate restricted-evidence manifest must be maintained beside the private
holdout and grading records in the approved access-controlled evidence vault.
It must not be committed to this repository, attached to a pull request, or
made available to public CI. The public repository documents the required
metadata fields only; actual identifiers, storage locations, digests, access
records and authorization references belong in the restricted copy.

The restricted manifest should use schema
`vectolith-restricted-evidence-manifest/1.0` and record, for each artifact:

- opaque artifact ID and evidence category (holdout dataset, scoring key,
  grading package, raw outputs, access log, authorization, audit report);
- restricted storage reference, custodian, access-control policy and
  authorized roles (never credentials or secret values);
- immutable version, byte size, media type, creation/retention timestamps and
  SHA-256 digest computed over the exact stored bytes;
- provenance/source reference, producing identity, collection method and
  chain-of-custody events;
- associated model/candidate ID and immutable revision, evaluation/run ID,
  evaluator identity or pseudonymous reviewer ID, and relevant suite version;
- grading status, rubric version and grade-report digest where applicable;
- access-log reference and digest, last integrity-verification timestamp,
  verifier identity, and any integrity or custody exceptions;
- authorization record reference and digest, approver, scope and validity
  period where applicable.

Do not place API keys, passwords, signing secrets, private keys, raw scoring
keys, holdout prompts, expected answers, or personally identifying reviewer
mappings in the manifest. Store those separately under the vault's secret and
data-access controls. The manifest itself is sensitive metadata and must
inherit the vault's access restrictions.

A digest verifies byte identity only when recomputed against the exact
artifact. It does not establish authenticity, lawful rights, completeness,
correct scoring, or valid authorization. Record those as separate reviewed
claims with supporting evidence references.
