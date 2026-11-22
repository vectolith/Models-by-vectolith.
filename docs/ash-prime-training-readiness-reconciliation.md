# ASH PRIME training readiness: reconciled prerequisites

This document reconciles the conflicting grading qualification language and describes the operational evidence required before any training run. It is a workflow aid, not an approval or evidence substitute.

## Hard gate
Training is permitted only when every item is verified by an accountable human and the run authorization binds the approved artifacts, student revision, configuration, and compute allocation. Validators must fail closed. No validator can manufacture legal permissions, independent grading, restricted custody, free compute, or human authorization.

## Evidence gates
1. **Teacher-output rights:** preserve source, model name and immutable revision, license evidence captured at that revision, applicable output-use terms, written permission evidence where needed, and independent legal review. Unresolved restrictions or missing evidence exclude the teacher's output from training.
2. **Provenance/integrity:** hash each source artifact and row set; record collection method, timestamps, revision, transformations and exclusions; preserve originals. Hashes alone do not prove permission or authenticity.
3. **Independent grading:** require the expected response set to be covered; rubric version and grade report digest; at least two independent reviewers per response (or an approved documented sampling protocol); reviewer-independence attestation; agreement statistics and report; adjudication record for disputes. Truncated/token-limit outputs remain incomplete and cannot be silently treated as full answers. The grading report is not teacher qualification until the pre-registered criteria are applied.
4. **Teacher qualification:** apply pre-registered criteria to independently graded evidence; document accepted/rejected teachers and any ablation evidence. Do not choose or reweight teachers after seeing protected holdout results.
5. **Dataset assembly:** exclude rights-ineligible data; preserve auditability; deduplicate; verify split isolation and hashes; define serialization and sample weights; version manifest. Never include the exposed public draft holdout in protected evaluation.
6. **Protected holdout:** provision an independently authored or rights-cleared evaluation suite under restricted custody outside this public repository. Record custodian, access controls, leakage prevention, version, hash, pre-registered metrics and thresholds. The public draft holdout is contaminated/exposed and must not be reused as secret holdout.
7. **Student foundation:** approve an exact foundation model and tokenizer revision, source and license; document model size, architecture, context length, training method, baseline and memory fit.
8. **Free compute:** verify a specific genuinely free resource, GPU/VRAM, storage, runtime limits, availability, environment, dependencies and interruption/checkpoint strategy. No paid service, trial, quota circumvention, account rotation or assumed resource.
9. **Experiment plan:** freeze dataset hashes, model/tokenizer revision, config, seeds, metrics, stopping policy, checkpoint policy and reproducibility instructions before run.
10. **Authorization:** an explicit human approval must bind the above manifest and exact experiment run. Preflight must fail if any evidence is absent, stale, mismatched or unverified.

## Known collection status (historical, reverify)
The prior integrity audit described five teacher artifacts, 180 responses each (900 total), with 480 token-limit records. This is integrity/collection evidence only, not grading or eligibility. A sixth candidate's snapshot lacked license evidence. The public draft holdout was exposed. These conditions must be reverified against current artifact bytes and external evidence; this document does not mark them complete.

## Parallel work that may proceed
Build validators, test schemas, prepare dataset transforms on synthetic or rights-cleared examples, environment/container locks, training scripts, checkpoint/recovery, logging, baseline harness, and run manifest. Do not run inference/training against the teacher collection or start training until the gates and authorization are satisfied.
