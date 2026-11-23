# ASH PRIME four-teacher qualification gates

Status: gate validator and empty manifest template are implemented. No candidate is qualified by this document or by inference success.

## Candidate-level evidence gates

Every candidate requires a completed, revision-pinned manifest based on [the qualification manifest template](../evaluation/teacher-qualification-manifest-template.json). The validator fails closed unless all ten qualification gates pass:

1. **Immutable snapshot:** manifest digest and snapshot revision match the candidate's full immutable revision.
2. **Legal/license review:** exact license text digest, named legal reviewer, timestamp, and evidence URI; status must be approved.
3. **Loader compatibility:** the same immutable revision was loaded successfully, with model class and runtime versions recorded. Remote code must be disabled or separately audited with a source digest.
4. **Real inference:** completed run and internal run IDs, artifact digest, exact expected response coverage, zero inference errors, and matching revision.
5. **Resource measurement:** runner/device, peak RSS, mean latency, and compute-record digest.
6. **Grading:** complete coverage of the expected response set by at least two distinct independent human reviewers; the report must bind the rubric version and report digest, reviewer-independence attestation, inter-grader agreement report, and adjudication report (including a documented no-disagreement disposition where applicable).
7. **Safety review:** named reviewer and report digest, with an explicit pass.
8. **Private holdout:** non-empty holdout evaluation, passed leakage audit, and audit digest.
9. **Corpus integrity:** corpus digest, zero duplicate records, and verified provenance.
10. **Separate training-output permission:** signed/authorized permission document digest, authorizer, and timestamp. License approval does not imply training-output permission.

A real inference artifact is necessary but never sufficient. Model-card license tags, loader success, token-cap rates, machine-generated evaluation metrics, or reviewer score averages cannot substitute for missing gate evidence.

## Validate one candidate

Copy the empty template for a candidate and fill every field only from real, verifiable evidence. Do not invent reviewer IDs, legal approval, permissions, safety findings, holdout results, or corpus attestations.

\`\`\`bash
python evaluation/teacher_qualification_gates.py validate \\
  --manifest qualification-manifests/candidate-id.json \\
  --output qualification-reports/candidate-id.json
\`\`\`

The command exits non-zero unless every gate passes. The report records failed gates and does not rank or select candidates.

## Validate the four-teacher cohort

Place one candidate manifest per JSON file in a directory:

\`\`\`bash
python evaluation/teacher_qualification_gates.py cohort \\
  --manifest-dir qualification-manifests/ \\
  --required-teachers 4 \\
  --output qualification-reports/ash-prime-cohort.json
\`\`\`

The cohort gate passes only when at least four unique candidates individually pass all ten gates. Duplicate candidate IDs block the cohort. The output is a count and gate disposition only; it does not rank, select, discard, or designate a winner. It never starts training.

## Current disposition

- Granite 3.1 3B-A800M, Granite 4.2 3B, and MiniCPM5 2B remain the three existing additive Prime teachers. Their real response evidence is preserved, but legal approval, grading, safety, holdout, corpus, and training-output permission gates are not complete.
- LFM2.5-2.6B and Phi-4-mini-instruct remain discovery-only despite repeated successful inference. They are not qualified.
- Qwen3.5-2B is used only as the provisional local semantic grader and is not a teacher or foundation candidate. Gemma 4 E2B IT remains discovery-only pending immutable revision, license, loader, inference, resource, Grading and permission evidence.
- Nemotron 3 Nano 4B remains deferred.
- SmolLM3 has no LICENSE file in its published snapshot; it runs only on tag-only model-card evidence, recorded with an explicit caveat and a pending legal review. Every other candidate stays on the hard license-file gate.

No training is authorized by a passing report alone. FYR PRIMA remains paused. The four-qualified-teacher, legal, human grading, safety, holdout, corpus-integrity, and separate written training-output permission gates remain mandatory.
