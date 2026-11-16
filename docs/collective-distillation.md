# Collective distillation

Use diverse, independently evaluated teachers to build auditable training corpora for two distinct students.

## Pipeline

1. Design task specifications and difficulty tiers separately for Prime and Prima.
2. Generate independent teacher responses; record exact teacher revision, prompt, settings, and timestamp.
3. Normalize message and tool-call formats without erasing meaningful differences.
4. Filter for correctness, relevance, completeness, safety, citation integrity, executable validity, and format.
5. Analyze disagreements; preserve useful disagreement as uncertainty/comparison data rather than blindly majority-voting.
6. Adjudicate with deterministic validators, trusted references, execution, and qualified human review where needed.
7. Deduplicate and screen for evaluation leakage.
8. Build separate Prime and Prima curricula, splits, and objective mappings.
9. Publish manifests, lineage, filtering statistics, hashes, and license/provenance records.

## Teacher pool and signal use

The initial candidate pool is Granite, Gemma, Ministral, and Qwen. Exact checkpoints remain subject to selection and license review. Do not merge weights across architectures. Response-level distillation is the default. Logit-level distillation is allowed only when tokenizer spaces and output semantics are demonstrably compatible.

Teacher consensus is not proof. Verify factual claims externally and test code where feasible. Exclude personal data, secrets, and data without a documented lawful and license-compatible basis.

**Core Prime data and objectives:** one unified curriculum spanning broad instruction following, conversation, research decomposition, source comparison, evidence synthesis, factual reasoning, mathematics, writing, planning, coding, software architecture, debugging, testing, technical diagnosis, structured tool use, agentic execution, traceable claims, calibrated uncertainty, and verified task completion. Former Prima-only engineering examples are assigned to Prime's curriculum and evaluation coverage. Core Prima is paused; do not generate a separate Prima corpus in this cycle.
