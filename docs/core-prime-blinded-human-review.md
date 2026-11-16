# Core Prime blinded human-review operations

Status: implementation tooling is available; no human grades or qualification decisions are recorded by this document.

## Scope and review population

The run 40 evidence set contains five preserved Core Prime response artifacts: the three existing additive teachers (Granite 3.1 3B-A800M, Granite 4.2 3B, MiniCPM5 2B), plus the discovery-only LFM2.5-2.6B and Phi-4-mini-instruct candidates. Each successful artifact contains 180 cases: benchmark v1 (12), qualification v2 (20), qualification v3 (92), and qualification v4 (56). The review population is therefore 900 raw responses, including 280 v4 response records covering the same 56 v4 prompts across five candidates.

This is public-suite human review, not private holdout evaluation. It cannot independently establish contamination resistance or teacher qualification.

## 1. Retrieve and verify the immutable source artifacts

Download the five GitHub Actions artifacts from workflow run 43796213917:

- Artifact 14199574383: \`prime-teacher-granite-3.1-3b-a800m\`
- Artifact 14213985732: \`prime-teacher-granite-4.2-3b\`
- Artifact 14223103259: \`prime-teacher-minicpm5-2b\`
- Artifact 14238638626: \`prime-teacher-lfm2.5-2.6b\`
- Artifact 14260316025: \`prime-teacher-phi-4-mini-instruct\`

Keep the ZIPs unchanged. The package builder verifies the ZIP SHA-256, the JSON/JSONL pair, all per-response provenance, exact case coverage, and exact rubric/category matches against the supplied fixture files.

## 2. Build reviewer-specific blinded packages

Run from the repository root:

\`\`\`bash
python evaluation/prepare_blinded_human_review.py build \\
  --evidence artifacts/source/prime-teacher-granite-3.1-3b-a800m.zip \\
  --evidence artifacts/source/prime-teacher-granite-4.2-3b.zip \\
  --evidence artifacts/source/prime-teacher-minicpm5-2b.zip \\
  --evidence artifacts/source/prime-teacher-lfm2.5-2.6b.zip \\
  --evidence artifacts/source/prime-teacher-phi-4-mini-instruct.zip \\
  --suite evaluation/fixtures/prime_benchmark_v1.jsonl \\
  --suite evaluation/fixtures/prime_qualification_v2.jsonl \\
  --suite evaluation/fixtures/prime_qualification_v3.jsonl \\
  --suite evaluation/fixtures/prime_qualification_v4.jsonl \\
  --output-dir artifacts/human-review/run-40 \\
  --reviewers 2
\`\`\`

The tool writes separate \`reviewer-01-blind-review.zip\` and \`reviewer-02-blind-review.zip\` packages. Candidate aliases are independently randomized per reviewer, response order is shuffled, and stable blinded response IDs allow later reconciliation. Reviewer ZIPs contain original prompts, original rubric criteria, unmodified response text, and completion/truncation/error metadata. They omit candidate IDs, provider names, model revisions, run IDs, and source artifact names.

The private identity map is written separately to \`artifacts/human-review/run-40/private/identity-key.json\`. It reverses the blinding and must be held by the review administrator only. Never include it in a reviewer ZIP, shared reviewer folder, or public issue/PR. Reviewer ZIPs do not contain the identity key.

The builder requires five artifacts with exactly 180 responses each and exact agreement with the supplied 180 original fixture cases. It fails closed on missing/duplicate cases, altered rubrics, inconsistent provenance, JSON/JSONL disagreement, or incomplete artifacts. It does not edit source artifacts.

## 3. Conduct independent review

Assign each ZIP to a different qualified human reviewer. Confirm reviewer independence outside the tool; distinct evaluator IDs alone cannot prove that two people are independent. Reviewers must not exchange grades or discuss individual responses before submitting their completed files.

For each gradeable response, score every original rubric criterion from 0 to 4 using the anchors in the package README and record concise rationale in \`notes\`. Do not infer scores from model identity, provider reputation, latency, or token count. If a response appears to identify its provider, mark \`unblinding_observed=true\` and explain the observation; do not guess identity or adjust the score because of it. Entries marked \`not_gradeable_error\` remain preserved as error evidence and are not graded.

Keep each original reviewer submission unchanged. Do not overwrite the blank grade template; save completed submissions as separate files. Record evaluator IDs consistently and uniquely.

## 4. Validate completeness and unblind after both submissions

Only after both reviewers submit their complete files, run:

\`\`\`bash
python evaluation/prepare_blinded_human_review.py unblind \\
  --identity-key artifacts/human-review/run-40/private/identity-key.json \\
  --grades artifacts/human-review/run-40/reviewer-01-completed.jsonl \\
  --grades artifacts/human-review/run-40/reviewer-02-completed.jsonl \\
  --output artifacts/human-review/run-40/unblinded-human-grades.jsonl
\`\`\`

The tool requires at least two distinct evaluator IDs, exactly one grade per gradeable blinded response per reviewer, every original rubric criterion, and scores in the 0–4 range. It rejects unknown, duplicate, incomplete, non-gradeable, or mismatched records. The original blinded submissions and private identity key remain unchanged. The output uses the existing \`vectolith-human-grading/1.0\` schema and can be consumed by \`summarize_human_grades.py\`.

## 5. Summarize human grades and agreement

Combine the five original JSONL files without changing them:

\`\`\`bash
cat artifacts/source/*-core_prime.jsonl > artifacts/human-review/run-40/all-raw-evidence.jsonl
python evaluation/summarize_human_grades.py \\
  --evidence artifacts/human-review/run-40/all-raw-evidence.jsonl \\
  --grades artifacts/human-review/run-40/unblinded-human-grades.jsonl \\
  --output artifacts/human-review/run-40/human-grade-summary.json \\
  --min-evaluators 2 --min-cases 3 --minimum-mean 3.0
\`\`\`

The summary reports per-criterion distributions and pairwise quadratic-weighted Cohen's kappa, plus exact agreement rate where sufficient paired ratings exist. Agreement statistics are descriptive; they do not prove reviewer competence or independence. Disagreements, unblinding observations, safety-critical concerns, and borderline scores require human adjudication in a separate append-only record. Never replace either original grade.

The summary always sets \`qualification_decision=not_made\`. A rubric threshold or high agreement score is not teacher qualification.

## Data separation and release gates

- Raw model responses, original prompts, and original rubrics are immutable source evidence.
- Machine-generated completion, token-cap, error, latency, and resource metrics remain separate from human grades.
- Blinded reviewer packages contain no candidate identity mapping; the private key is access-restricted.
- Human grades and adjudication records are append-only. Corrections must retain the superseded record and reason.
- The three existing Prime teachers remain additive. LFM2.5 and Phi-4 remain discovery-only.
- Qwen3.5-2B, Gemma 4 E2B IT, and deferred Nemotron 3 Nano 4B remain discovery-only.
- SmolLM3 remains blocked by its missing LICENSE file. No license gate is weakened.
- Legal review and separate written training-output permission remain mandatory.
- The four-qualified-teacher, independent grading, safety, holdout, and corpus-integrity gates remain mandatory.
- Core Prima stays paused. No student training starts from this workflow.


## Additional run 42 and 43 response sets

Run 42 produced four completed artifacts (Granite 3.1, Granite 4.2, MiniCPM5, and LFM2.5), adding 720 responses. Run 43 produced those four plus a completed Phi-4 artifact, adding 900 responses. Together these runs add 1,620 raw responses. Run 42 Phi-4 remains in progress and has no artifact; run 43 Phi-4 completed and its 180 responses were downloaded and verified. SmolLM3 failed its missing-LICENSE gate in both runs and produced no artifact. Exact job IDs, artifact IDs, revisions, resource measurements, and recomputed ZIP/JSON/JSONL digests are in [follow-up run 42/43 evidence](../evaluation/core-prime-multi-teacher-runs-42-43-evidence-2026-11-16.md).

The blinded package builder accepts multiple inference artifacts for the same candidate, provided each candidate/revision/run tuple is unique and every artifact covers the same exact fixture set. It verifies all eight run 42/43 ZIP digests against their published values and retains each source workflow run, job, artifact, internal run ID, and hashes in the restricted identity key. Candidate aliases remain stable across repeat runs within one reviewer's package and are randomized separately for each reviewer.

Build the two-run follow-up review as a separate batch from the run 40 900-response batch:

\`\`\`bash
python evaluation/prepare_blinded_human_review.py build \\
  --evidence artifacts/source/run42-prime-granite-3.1-3b-a800m.zip \\
  --evidence artifacts/source/run42-prime-granite-4.2-3b.zip \\
  --evidence artifacts/source/run42-prime-minicpm5-2b.zip \\
  --evidence artifacts/source/run42-prime-lfm2.5-2.6b.zip \\
  --evidence artifacts/source/run43-prime-granite-3.1-3b-a800m.zip \\
  --evidence artifacts/source/run43-prime-granite-4.2-3b.zip \\
  --evidence artifacts/source/run43-prime-minicpm5-2b.zip \\
  --evidence artifacts/source/run43-prime-lfm2.5-2.6b.zip \\
  --evidence artifacts/source/run43-prime-phi-4-mini-instruct.zip \\
  --suite evaluation/fixtures/prime_benchmark_v1.jsonl \\
  --suite evaluation/fixtures/prime_qualification_v2.jsonl \\
  --suite evaluation/fixtures/prime_qualification_v3.jsonl \\
  --suite evaluation/fixtures/prime_qualification_v4.jsonl \\
  --output-dir artifacts/human-review/runs-42-43 \\
  --reviewers 2 --expected-artifacts 9 --workflow-run-id multi-run
\`\`\`

This creates 1,620 response entries per reviewer (3,240 total reviewer assignments), not 1,620 distinct prompts. The same 180 prompts are repeated for Granite 3.1, Granite 4.2, MiniCPM5 and LFM2.5 across both runs, plus one Phi-4 run-43 set. Keep this batch separate from run 40 so run-specific evidence and review provenance remain clear. When the run 42 Phi-4 job completes, its artifact must be independently downloaded and verified before being added to a new or explicitly extended review batch.
