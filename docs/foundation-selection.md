# Foundation model selection

**Status: OPEN — no foundation selected.** The candidate set remains under comparative evaluation. Verification is continuous work, not a sequence of approval gates or artificial phase barriers.

## Exact research shortlist

The current research shortlist is:

- `Qwen/Qwen3.5-9B` — Prime and Prima comparator.
- `ibm-granite/granite-4.2-8b` — Prima priority; Prime comparator.
- `google/gemma-4-E4B` — Prime efficiency and multimodal comparator.
- `mistralai/Mistral-Small-4` — high-capability reference candidate.

These are exact repository identifiers, not family-level permission to substitute another checkpoint. Candidate roles are hypotheses for allocating evaluation effort, not rankings or selections. A model may be evaluated for either or both student roles.

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

Keep Prime and Prima scorecards separate. Apply a common controlled curriculum and comparable settings, with role-specific tasks:

- Reasoning, factual synthesis, mathematics, instruction following, uncertainty calibration, and reliability.
- Coding, repository-level implementation, debugging, testing, code review, and secure engineering.
- Structured tool selection, schema-valid arguments, multi-step execution, error recovery, and truthful reporting.
- Global-English quality, regional registers, multilingual comprehension, translation, and code-switching.
- Context retention, repeated-run variance, refusal correctness, and output validity.
- Time-to-first-token, tokens/second, throughput, concurrency, cold start, peak RAM/VRAM, storage, and measured cost.

Preserve raw outputs, per-case scores, grading rubrics, evaluator identity/version, disagreements, run configuration, and prompt/dataset hashes. Report dimensions separately; do not hide trade-offs in a single unqualified aggregate score. Provider benchmarks and model-card claims are discovery evidence, not VELNOR measurements.

## Selection and training policy

Foundation selection remains open until the available comparative evidence supports a documented decision for the relevant student. Publish the rationale, limitations, and exact immutable checkpoint identity. Prime and Prima may select different architectures.

Do not begin expensive foundation-specific training before a foundation is selected and the relevant rights, execution evidence, and training compatibility are established. Bounded discovery, metadata capture, licensing review, environment checks, and controlled compatibility probes are evaluation work and may proceed while other evidence is pending.

No candidate is currently recorded as a selected foundation. Do not describe any candidate as qualified, benchmarked, or approved without corresponding evidence.