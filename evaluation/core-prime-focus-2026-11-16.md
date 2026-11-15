# Core Prime multi-teacher knowledge accumulation plan — 2026-11-16

## Scope

Core Prima is **paused**. Do not run, train, rank, or qualify Core Prima in this cycle. Its planned software-engineering, coding, architecture, debugging, testing, and technical-execution abilities are now part of Core Prime's target capability scope. Do not create a separate Prima corpus in this cycle.

Core Prime is being developed as a unified generalist capable of both broad cognitive tasks and specialist-level technical work. The Prime curriculum and future evaluation must cover research, mathematics, writing, data analysis, coding, software architecture, debugging, testing, structured tool use, agentic execution, and evidence-backed completion. The current 124-case response collection is not, by itself, proof of coverage or competence across this expanded scope; additional Prime cases and evaluation gates are required before training or release claims.

Core Prime will learn from all three active teacher models, in sequence:

1. IBM Granite 3.1 3B-A800M.
2. IBM Granite 4.2 3B.
3. OpenBMB MiniCPM5 2B.

This is not a competition, ranking, or winner-selection exercise. The goal is to accumulate complementary knowledge, explanations, approaches and perspectives from all three teachers to improve Core Prime.

## Preserve every real response

- Run all three pinned Prime candidates against the same Prime public suites and case order.
- Preserve **every actual generated response** from every teacher, including incomplete, incorrect, conflicting, repetitive and token-capped responses. Never silently omit or overwrite a response.
- Keep the immutable raw response archive separate from any curated or transformed training dataset.
- Every response must retain its source prompt and case ID, teacher identity, exact model revision, role, generation settings, timestamp, run ID, raw output, completion/cap status, and artifact/hash provenance.
- If a response is duplicated, retain its raw record and mark the duplicate relationship; do not erase its provenance.
- If teachers disagree, retain all original responses and record the disagreement. Do not automatically treat majority agreement or any one teacher as ground truth.

## Sequential contribution

1. **Granite 3.1:** collect and preserve its complete real response set. Review and annotate it; establish the first versioned contribution layer.
2. **Granite 4.2:** collect and preserve its complete response set. Add its distinct knowledge and approaches as a separately traceable contribution layer; link overlaps and disagreements to the earlier layer without replacing it.
3. **MiniCPM5:** collect and preserve its complete response set. Add its contribution as a third traceable layer, retaining complementary approaches and disagreements.
4. **Unified Prime corpus:** consolidate all three contribution layers into one versioned corpus. Preserve per-example and per-span teacher provenance and the link back to the immutable raw response. Keep conflicting answers and uncertainty visible in structured records.
5. **Training preparation:** convert the accumulated material into training examples without changing or losing the source evidence. Where correctness matters, independently verify claims and label uncertainty, errors and disagreements. Do not teach Prime that an unverified or contradictory answer is certainly true.

The planned order is a contribution sequence, not a quality ranking. All three teachers contribute. Review exists to improve reliability and annotate knowledge—not to choose a winning teacher or discard a teacher's response set.

## Blinded review

Prepare a blinded Prime review packet using the real prompts, rubrics and actual responses. Reviewer-facing material must conceal teacher identities; preserve the identity mapping separately. Human reviewers assess factual correctness, reasoning validity, completeness, clarity, safety and uncertainty. Grades must be genuinely supplied by independent humans; never invent or auto-generate human grades.

Blinding is for unbiased assessment, not model selection. The purpose is to identify what each response contributes, what needs verification, and how disagreements should be represented in Prime's learning material.

## Evaluation controls

- Same pinned Prime public suites and case order.
- Same CPU-only BF16 inference, greedy decoding, chat template and 256-token cap for comparability with the established baseline.
- Maximum two concurrent inference jobs and two CPU math threads per job.
- Exact immutable model revisions are required.
- Preserve raw per-case outputs, logs, runner measurements and artifact hashes.
- Do not begin student training during inference collection or review.
- Public suites are not private holdouts.

## Authorization and safety gates

Preserving and reviewing raw outputs does not itself grant permission to train on them. Before any response is used for training, establish legal review and explicit training-output permission for its source, plus independent review, provenance, corpus integrity, contamination, competency coverage, balance and safety checks.

The existing four-qualified-teacher requirement remains in force; these three candidate models are not automatically three qualified teachers. Training begins only after the applicable teacher, data-permission and safety gates are satisfied.

Core Prima remains pending and must have a separate teacher panel and separately governed evaluation cycle.
