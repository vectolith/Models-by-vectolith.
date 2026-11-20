# Foundation model selection

**Status: OPEN — no foundation selected.** The candidate set remains under comparative evaluation. Verification is continuous work, not a sequence of approval gates or artificial phase barriers.

## Exact research shortlist

Core Prime is the only active student foundation-selection track. Its unified scope includes general reasoning, knowledge, writing, multilingual comprehension, mathematics, coding, software engineering, architecture, debugging, testing, structured tool use and verified execution.

The current research shortlist is:

- `Qwen/Qwen3.5-9B` — broad reasoning, multilingual and general-capability comparator.
- `ibm-granite/granite-4.2-8b` — dense reasoning and tool-use comparator.
- `google/gemma-4-E4B` — efficiency and multimodal comparator.
- `mistralai/Mistral-Small-4` — high-capability reference candidate.
- `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16` — hybrid/MoE architecture comparator; total checkpoint footprint and OpenMDW 1.1 terms remain explicit constraints.

These are exact repository identifiers, not family-level permission to substitute another checkpoint. Candidate roles are hypotheses for allocating evaluation effort, not rankings or selections. No candidate is selected. Core Prima is paused: its historical candidate material is retained, but no Prima foundation search, comparison run or training campaign is active. A future specialist model, including a reactivated Prima, requires a distinct approved scope and its own independent selection record.

## Current hardware feasibility evidence

The Kaggle session is user-attested to have two independent 15 GiB Tesla T4 GPUs. The preliminary candidate screen records the important T4 constraint: compute capability 7.5 supports FP16 Tensor Core acceleration but not BF16 Tensor Core acceleration. It also compares the existing 8B/9B/119B candidates with smaller 2B/3B alternatives and the current trainer's loader limitations. See [the 2026-11-18 hardware screen](foundation-candidate-hardware-screen-2026-11-18.md). This does not select a foundation or authorize model execution.

## Continuous verification and execution

Work on identity, licensing, checkpoint availability, infrastructure, evaluation preparation, compatibility, and measured execution in parallel wherever practical. Update each candidate's evidence record as facts become available. Do not wait for an artificial phase transition to investigate or resolve an issue.

For every candidate, preserve:

- Exact Hugging Face repository ID, publisher, model architecture, parameter metadata, and modality.
- Immutable 40-character Hub commit SHA; exact config, tokenizer, processor, chat-template, and weight-file inventory.
- SHA-256 hashes for downloaded checkpoint files and retained legal/model-card evidence.
- License text at that exact revision, additional terms/notices, gating/access status, and a separately recorded human legal assessment.
- Whether model outputs may be used for training/distillation; never infer this permission from an open-weight or Apache license label.
- Actual compute provider/session evidence, hardware, memory, quota, runtime limits, storage/egress constraints, and whether the workload ran without charge.
- Exact serving/training software versions, load logs, inference settings, raw outputs, evaluation data hashes, scores, failures, latency, throughput, and memory observations.

Use explicit evidence states such as `verified`, `measured`, `pending`, `blocked`, and `not_applicable`. A missing or unresolved fact stays visible as pending or blocked; it is never silently inferred. Distinguish provider-published claims, repository metadata, locally observed facts, and independent evaluation results.

## Substitution prohibition

The exact candidate identity is immutable within an evaluation record. Do not silently replace a repository, model family, parameter size, architecture, checkpoint revision, tokenizer, processor, quantization, or serving artifact. Do not fall back to a smaller model, quantized build, mirror, API model, or different revision because the requested artifact is inconvenient or unavailable.

If an exact artifact is inaccessible or incompatible, record that candidate's status and continue useful work on the other unchanged candidates. A proposed alternative must be recorded as a separate candidate with its own identity and evidence; it must not inherit the original candidate's results. Any change to an already authorized evaluation target requires explicit user approval.

## Comparative evaluation

Use one active Core Prime scorecard and a common controlled curriculum. Include the full unified Prime scope, with separate competency-level results for:

- Reasoning, factual synthesis, mathematics, instruction following, uncertainty calibration, and reliability.
- Coding, repository-level implementation, debugging, testing, code review, and secure engineering.
- Structured tool selection, schema-valid arguments, multi-step execution, error recovery, and truthful reporting.
- Global-English quality, regional registers, multilingual comprehension, translation, and code-switching.
- Context retention, repeated-run variance, refusal correctness, and output validity.
- Time-to-first-token, tokens/second, throughput, concurrency, cold start, peak RAM/VRAM, storage, and measured resource consumption.

Preserve raw outputs, per-case scores, grading rubrics, evaluator identity/version, disagreements, run configuration, and prompt/dataset hashes. Report dimensions separately; do not hide trade-offs in a single unqualified aggregate score. Provider benchmarks and model-card claims are discovery evidence, not measurements from this repository's own controlled runs.

## Selection and training policy

Core Prime foundation selection remains open until comparative evidence supports a documented decision. Publish the rationale, limitations and exact immutable checkpoint identity. Core Prima is paused; if it is reactivated, its foundation must be selected independently and must not inherit Prime's decision.

Do not begin foundation-specific training before a foundation is selected and the relevant rights, execution evidence and training compatibility are established. Use only a verified and approved execution environment with measured capacity; do not substitute an unverified provider or relax evaluation requirements. Bounded discovery, metadata capture, licensing review, environment checks and controlled compatibility probes may proceed while other evidence is pending.

No candidate is currently recorded as a selected foundation. Do not describe any candidate as qualified, benchmarked, or approved without corresponding evidence.