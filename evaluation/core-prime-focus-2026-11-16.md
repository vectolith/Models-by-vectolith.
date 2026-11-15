# Core Prime multi-teacher evaluation and training plan — 2026-11-16

## Scope decision

Core Prima is **paused**. Do not run, train, rank, or qualify Core Prima candidates in this evaluation cycle. Its teacher panel and evidence must be handled separately.

Core Prime will use a **multi-teacher approach**. The three active candidate models are all intended to contribute to Core Prime; this is not a winner-takes-all model-selection exercise:

1. IBM Granite 3.1 3B-A800M — teacher contribution sequence 1.
2. IBM Granite 4.2 3B — teacher contribution sequence 2.
3. OpenBMB MiniCPM5 2B — teacher contribution sequence 3.

No candidate is declared the winner, and none is discarded merely because another candidate scores higher. The purpose of evaluation is to understand each teacher's strengths, failure modes, coverage and resource profile, and to determine how to safely use and combine their contributions.

## Evidence collection

- Run all three pinned Prime candidates against the same Prime public suites and case order.
- Preserve each teacher's raw per-case outputs, logs, exact model revision, runtime settings, runner measurements and artifact hashes independently.
- Prepare a blinded Core Prime review packet containing the actual prompts, rubric and all three candidates' actual responses. Replace model names with anonymous candidate IDs in reviewer-facing material; keep the identity mapping in a separate restricted record.
- Obtain independent human grades. Do not invent or auto-generate human grades.
- Compare each teacher's response quality, competency coverage, errors, omissions, consistency and compute cost. These comparisons inform contribution controls and quality filtering; they do not select a single winner.

## Sequential teaching and combination

Teaching contributions must be staged, not generated as one undifferentiated simultaneous batch:

1. **Teacher 1 — Granite 3.1:** validate its actual outputs and provenance; accept only evidence-backed, quality-reviewed examples into a separately versioned contribution set.
2. **Teacher 2 — Granite 4.2:** evaluate its outputs independently, compare against the existing accepted set, resolve conflicts and duplicates, and add only accepted complementary examples to its own contribution set.
3. **Teacher 3 — MiniCPM5:** repeat the same independent validation and conflict-resolution process; preserve its contribution separately.
4. **Consolidation:** combine the three accepted contribution sets into one versioned Core Prime training corpus. Preserve per-example teacher provenance, source prompt, model revision, reviewer decision, rubric evidence and transformation history. Deduplicate without erasing provenance; retain disagreements and rejected examples in an audit record.
5. **Pre-training gate:** run corpus integrity, contamination, coverage, balance, safety, licensing and training-output-permission checks. Only then may a separately approved Prime training run begin.

The order above is the planned contribution order, not a quality ranking. A teacher's output must not be used to silently rewrite or validate another teacher's output. Each contribution is reviewed on its own evidence before consolidation.

## Evaluation controls

- Same pinned Prime public suites and case order.
- Same CPU-only BF16 inference, greedy decoding, chat template and 256-token cap for comparability with the established baseline.
- Maximum two concurrent inference jobs and two CPU math threads per job.
- Exact immutable model revisions are required.
- Preserve raw per-case outputs, logs, runner measurements and artifact hashes.
- Do not start student training during candidate inference or blinded review.
- Do not use publisher scores or model self-evaluation as qualification evidence.

## Required gates

No teacher contribution is training-authorized until independent human review, legal review and explicit training-output permission are established for that source. The existing four-qualified-teacher requirement, teacher provenance, contribution quality checks, ablations, repeated-run reliability, safety and release evidence remain in force. Three candidate models in this evaluation are not automatically three qualified teachers.

Core Prima remains pending and must have a separate teacher panel and separately governed evaluation cycle.
