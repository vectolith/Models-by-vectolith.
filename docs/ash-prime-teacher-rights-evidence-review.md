# ASH PRIME teacher-rights gate: evidence-based, not blanket-permission-based

## Policy
Do not require a bespoke permission letter from every teacher by default. Evaluate the actual terms and rights that apply to the specific model revision, use method, outputs, and intended student-model distribution. Written permission or counsel review remains required when terms prohibit, materially restrict, or leave unresolved the intended use.

This checklist is an evidence intake and risk-screening tool, not legal advice or a legal determination.

## Required record for each candidate
- Exact model name, repository/provider, immutable revision/commit, retrieval date.
- License file and model-card/terms snapshot; source URL and SHA-256.
- Classification: permissive license / custom license / provider service terms / unresolved.
- Terms review for automated generation, output retention, output training/distillation, competing-model restrictions, commercial use, redistribution, attribution, notice, acceptable-use, access/rate restrictions, and termination effects.
- Exact planned use: generating responses, retaining them, filtering/annotating, student training, evaluation, and eventual distribution.
- Restriction summary, evidence links, reviewer/date, conclusion and rationale.
- Mark any unresolved issue as BLOCKED; do not infer permission from output ownership or model independence.

## Decision labels
- **PASS** — evidence supports intended activity and all conditions are recorded and satisfied.
- **PASS WITH CONDITIONS** — use is supported only if recorded conditions are implemented and verified.
- **BLOCKED** — restriction, ambiguity, missing terms, or required review remains unresolved.
- **EXCLUDED** — candidate/use is not acceptable for this experiment.

## Scope distinctions
1. Model-weight license and rights to run/modify the teacher are distinct from rights/terms for generated outputs.
2. Output ownership or lack of teacher runtime dependency does not itself authorize training or distribution.
3. Public attribution is not a substitute for license compliance; absence from the student's runtime dependencies does not excuse upstream terms.
4. A permissive open-weight license is not automatically evidence that every output, input, dataset component, or annotation is cleared.
5. Terms are assessed for the exact revision and date of the activity; preserve the source evidence.

## Evidence intake template
| Field | Value |
|---|---|
| Candidate / revision | |
| Source URL(s) | |
| Retrieval date | |
| License / terms type | |
| License snapshot SHA-256 | |
| Output training clause | |
| Automated access / extraction terms | |
| Attribution / notice requirements | |
| Commercial / distribution conditions | |
| Other restrictions / safety requirements | |
| Intended use assessed | |
| Evidence files / hashes | |
| Decision | BLOCKED until populated and reviewed |
| Reviewer and date | |
| Conditions / rationale | |

## Experiment-wide rule
Do not start training while any teacher selected for the experiment is BLOCKED, or until dataset, protected holdout, student selection, free compute, and run-specific authorization gates have also passed. This policy change removes blanket bespoke-permission as a universal requirement; it does not waive substantive restrictions or evidence.
