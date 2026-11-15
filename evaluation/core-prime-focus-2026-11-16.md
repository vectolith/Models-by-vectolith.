# Core Prime evaluation focus — 2026-11-16

## Scope decision

Core Prima is **paused**. Do not run, train, rank, or qualify Core Prima candidates in this evaluation cycle. Its teacher panel and evidence must be handled separately; sharing the Prime teacher panel would violate the required independent-teacher separation.

The active inference matrix now contains only three Core Prime candidates:

1. IBM Granite 3.1 3B-A800M — existing baseline.
2. IBM Granite 4.2 3B — new comparable candidate.
3. OpenBMB MiniCPM5 2B — new compact candidate.

All existing Qwen outputs and previous Prima outputs remain preserved as historical evidence. They are not deleted and must not be misrepresented as part of the current active Prime shortlist.

## Evaluation controls

- Same pinned Prime public suites and case order.
- Same CPU-only BF16 inference, greedy decoding, chat template and 256-token cap for comparability with the established baseline.
- Maximum two concurrent jobs and two CPU math threads per job to avoid oversubscription.
- Exact immutable model revisions are required.
- Preserve raw per-case outputs, logs, runner measurements and artifact hashes.
- Do not start student training during this candidate comparison.
- Do not use publisher scores or model self-evaluation as qualification evidence.

## Decisions remain evidence-gated

The three candidates are under comparative evaluation only. No winner is declared until the full case-level outputs are consolidated and independently graded. Legal review, training-output permissions, teacher contributions, four qualified Prime teachers, ablations, repeated-run reliability and release/safety evidence remain required.

Core Prima remains pending and must have a separate teacher panel and separately governed evaluation cycle.
