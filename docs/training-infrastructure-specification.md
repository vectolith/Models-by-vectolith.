# Vectolith training infrastructure specification

**Status:** normative architecture and interface specification  
**Version:** 1.0  
**Applies to:** Models by vectolith (canonical upstream model family)

This document consolidates the training contracts already implemented across `runtime/` and `evaluation/`, identifies what is implemented versus still required, and defines the stable boundaries for future training backends. It is deliberately model- and provider-neutral.

## 1. Current product and model scope

- **ASH PRIME** is the active unified model. It owns the complete user task lifecycle, including reasoning, research, planning, software engineering, tool use, execution, and evidence-backed completion.
- **FYR PRIMA** is paused. Do not launch a Prima foundation search, teacher qualification campaign, training run, or duplicate execution pipeline while the pause remains in force. Its existing candidate and qualification material is retained as historical/re-activation planning. Reconsider Prima only when a distinct specialist role is justified by measured Prime limitations and a separate release case.
- Future family members may use different architectures and tokenizers. They must implement the shared identity, task, safety, and interoperability contracts at the boundary.

Teacher models are training-time resources only. A released student must run without teacher endpoints, credentials, weights, or inference dependencies. The registry is not a weight store, inference server, safety certification, or permission grant.

## 2. Architecture and implementation map

| Boundary | Current implementation | Contract / responsibility |
|---|---|---|
| Model identity and capability manifest | `runtime/vectolith_runtime/registry.py` | Stable model ID, version, specialization, capabilities, modalities, lifecycle, family identity |
| Persistent registry | `runtime/vectolith_runtime/persistence.py` | SQLite-backed manifest persistence; production service still needs auth, audit history, tenancy and concurrency policy |
| Model loading and serving adapters | `runtime/vectolith_runtime/loading.py` | Model-neutral loader registration and runtime loading |
| Task/message interface | `runtime/vectolith_runtime/contracts.py` | Versioned task request/result and lifecycle status |
| Teacher qualification and routing | `runtime/vectolith_runtime/teacher_pipeline.py` | Immutable teacher revisions, explicit license/output permission evidence, competency coverage and panel selection |
| Teaching corpus generation | `teacher_pipeline.py` | Independent generation, peer review, provenance and content hashes |
| Student SFT | `runtime/vectolith_runtime/distillation_training.py` | Explicitly invoked optional LoRA/full-parameter SFT; at least four teacher identities represented |
| Contribution and independence evidence | `runtime/vectolith_runtime/distillation.py` | Per-teacher contribution, positive ablation and teacher-independent inference evidence |
| Student evaluation and release gate | `runtime/vectolith_runtime/independent_evaluation.py` | Capability report, leave-one-teacher-out evidence and fail-closed release decision |
| Foundation discovery/evaluation | `evaluation/` | Pinned candidates, raw outputs, deterministic/local semantic grading, compute observations and immutable evidence |
| Training and promotion policy | `docs/training-and-promotion.md` | Reproducibility, independent evaluation, safety and release gates |

The current Python runtime is a reference implementation, not yet a hosted multi-tenant training control plane. Do not describe a documented or planned interface as a deployed service.

## 3. Canonical contracts

All persisted records must be versioned, attributable to an immutable run or artifact, and serializable without provider-specific secrets. Breaking changes require a new contract version and an explicit migration path. Unknown required fields or unsupported versions fail closed.

### 3.1 Model manifest

The current `ModelManifest` is the canonical model catalogue record:

- `model_id`: stable, globally unique family identifier.
- `display_name`, `version`, `specialization`.
- `capabilities`: non-empty stable identifiers, not marketing prose.
- `modalities_in`, `modalities_out`.
- `identity`: family, identity-contract version, behavioural principles and safety baseline.
- `lifecycle`: experimental, development, evaluation, released, deprecated or retired.
- `foundation`, `adapter_id`, and non-secret metadata where known.

Registry discovery returns all compatible candidates. The orchestrator applies release eligibility, evaluation evidence, resource constraints, availability and permissions. Only `released` models are production-eligible by default. A manifest never implies that weights exist or that a model has passed evaluation.

### 3.2 Teacher qualification and assignment

The existing `TeacherQualification` and `TeacherAssignmentPanel` are the source interfaces. A qualification record must bind to:

- exact teacher ID, provider, immutable 40-character checkpoint revision and license identifier;
- retained evidence that the exact model and inference route permit output use for the intended student training;
- declared teaching competencies and the versioned qualification suite;
- measured quality, latency, cost and pass/fail disposition;
- exact endpoint identity and revision matching the qualification record.

Teacher selection is competency coverage, not popularity or model count. For any student activated for training, the panel must contain at least four distinct qualified teachers, cover every required competency, and use exact revisions that match the qualification evidence. Every teacher must later contribute accepted examples and show a positive held-out leave-one-teacher-out effect. A candidate, shortlist entry, successful download, or keyword score is not a qualified teacher.

**Qualification limitation:** the current built-in keyword/rubric score is a screening signal only. Appointment requires retained raw outputs, grading report completion, factuality review, executable verification for objective tasks, license/terms review, and measured resource evidence. Provider-hosted APIs and self-hosted weights must be assessed separately for data handling and output-training permission.

Current state: no teacher is presumed qualified merely because it appears in a candidate manifest. FYR PRIMA's qualification activity remains dormant while the model is paused.

### 3.3 Teaching example and dataset contract

The current teaching corpus is JSONL. Each accepted row emitted by `generate_teaching_corpus()` carries:

| Field | Meaning |
|---|---|
| `schema_version` | Row contract version |
| `student_model_id`, `run_id` | Intended student and immutable training run identity |
| `task_id`, `competency` | Task and capability attribution |
| `prompt`, `response` | Training input and proposed target |
| `teacher_id`, `teacher_revision` | Exact generating teacher identity and revision |
| `reviewer_id`, `review` | Peer reviewer and structured review outcome |
| `teacher_latency_ms`, `review_latency_ms` | Observed generation/review latency |
| `content_sha256` | SHA-256 over prompt, separator and response |
| `accepted` | Explicit acceptance flag; only true rows enter SFT |

A peer review is not ground truth. Add executable tests, trusted references, or criterion-specific verification where the competency permits. Keep rejected examples and review evidence in a separately retained audit artifact; never silently convert a rejected row into accepted training data.

Every dataset release must also have a **dataset manifest** containing: dataset ID and semantic version; schema version; target student; purpose and competency coverage; source/task-suite revisions; row and token counts; accepted/rejected counts; per-teacher contribution counts; split designation (train/validation/public benchmark/private holdout); provenance and license references; deduplication/contamination checks; creation timestamp and pipeline commit; storage URI; and SHA-256 of the exact immutable dataset bytes.

Train, validation, public benchmark, and private holdout data must be distinct. Private holdout data and answers stay outside this public repository and must never enter training or teacher prompts used to construct training answers.

### 3.4 Training run manifest and trainer interface

Every training invocation must produce a machine-readable run manifest before work begins and finalize it with observed results. Minimum fields:

- `schema_version`, unique `run_id`, student `model_id`, lifecycle state and timestamps;
- foundation repository/model ID, immutable weight revision, tokenizer revision and configuration hash;
- dataset ID/version/hash and explicit train/validation split references;
- trainer adapter/name/version, source commit, method (SFT, PEFT, RLVR, preference optimization, or distillation), full hyperparameter/config snapshot and random seed;
- hardware/runtime inventory, precision, distributed topology, memory observations and approved USD $0 resource ceiling;
- output checkpoint/artifact URI and hashes, logs, metrics, evaluation report references and known limitations;
- stop reason, failure details, rollback parent and operator identity.

The trainer interface is an explicit operation: validate inputs and approvals → resolve pinned artifacts → run a bounded job → emit immutable logs/checkpoints/metrics → evaluate → request promotion. Importing the package or registering a trainer must never contact providers, download weights, allocate compute, or start training.

Trainer adapters must expose capability metadata (supported architectures, tokenizers, methods, modalities, quantization and hardware), preflight validation, run submission, status/log retrieval, cancellation, artifact export and reproducibility metadata. Backend-specific options remain inside the adapter configuration; the family-level run manifest remains stable.

### 3.5 Evaluation report and promotion gates

Every evaluation report must identify the exact student checkpoint hash, foundation lineage, tokenizer, inference adapter/version, suite and fixture revisions, split type, generation settings, environment/hardware, raw output artifact hashes, grading method, evaluator identity/version, per-case/per-competency outcomes, aggregate metrics and limitations.

Keyword matching and smoke suites are execution checks, not release-quality judgments. Grading reports must cover the declared response set, identify the rubric version, and be retained with provenance. Reviewer counts, agreement thresholds, and adjudication are not qualification requirements. Objective coding/math/tool tasks should use isolated sandboxes and deterministic verifiers. Public suites are not private holdouts.

Promotion is fail-closed. Required gates:

1. Foundation, tokenizer, training code and dataset revisions are immutable and license-reviewed.
2. Dataset provenance, split integrity, contamination checks and training-run reproducibility pass.
3. Role-specific held-out capability thresholds pass with per-competency reporting.
4. No unacceptable regression against the foundation or prior approved release.
5. Safety, instruction hierarchy, uncertainty and tool/serialization conformance pass.
6. Every appointed teacher has accepted contribution evidence and a positive, reproducible leave-one-teacher-out delta.
7. Student-only inference passes with teacher endpoints and credentials absent, zero teacher calls observed, and teacher services/artifacts absent from inference dependencies.
8. Deployment/resource smoke tests, model card, artifact hashes and rollback metadata are complete.

A failed or missing gate blocks promotion. Training loss, a successful training process, or a teacher panel with four names is never sufficient.

### 3.6 Distillation interface

Distillation is a training-time adapter boundary, not a student inference dependency. The common request must identify student foundation/revision, teacher panel/revisions, dataset or prompt stream, tokenizer compatibility, method, objective, hyperparameters, verified free resource and USD $0 ceiling, and evaluation plan. The result must identify student checkpoint/hash, source run, accepted teacher contributions, metrics, ablations, and limitations.

Supported maturity must be stated accurately:

- **Implemented:** accepted response-based teaching corpus generation and supervised LoRA/full-parameter SFT.
- **Evidence/validation layer implemented:** teacher contribution records, leave-one-teacher-out callback interface, teacher-disabled checks and fail-closed release evaluation.
- **Not yet implemented as a production trainer:** token-logit MOPD, multi-teacher on-policy distillation, cross-tokenizer probability alignment, distributed RLVR/GRPO orchestration, reward-model serving and production job scheduling.

Do not label MOPD or RLVR as implemented in Vectolith until executable adapters, tests and reproducible runs exist. Logit distillation requires compatible tokenization and output semantics, or an independently validated alignment method. Never merge weights across incompatible architectures.

## 4. Training lifecycle

The canonical state progression is:

`proposed → preflight → approved → queued → running → checkpointed → evaluated → promotion_ready → released`

Terminal alternatives are `blocked`, `failed`, `cancelled`, `rejected` and `rolled_back`. State changes must be auditable and monotonic except for an explicit new run or rollback event. A failed run is not silently resumed under the same identity; resumed work records a parent run and new run ID.

For the active ASH PRIME track: foundation comparison and selection precede expensive training; then data preparation, baseline evaluation, teacher qualification, accepted corpus generation, SFT, optional RL/post-training, distillation experiments, independent evaluation and promotion. Do not schedule a run until the execution environment and compute capacity have been verified.

FYR PRIMA remains paused and is excluded from active scheduling. If reactivated, it receives a separate role justification, foundation decision, curriculum, teacher panel, dataset, run lineage, evaluation and release gate.

## 5. Teacher infrastructure contributions

Teacher and provider infrastructure contributions are governed by the [Teacher Infrastructure Contribution System](teacher-infrastructure-contributions.md). Model-teacher qualification and infrastructure-contribution qualification are independent decisions. Providers may contribute compute, training frameworks, orchestration, data/evaluation systems, serving, observability or engineering references; no access, compute capacity, credits or service entitlement is presumed. All integrations must pass contribution-specific legal, security, compatibility, operations, cost and data-governance checks through replaceable Vectolith-owned adapters.

## 6. Nemotron / NeMo integration policy

Use NVIDIA NeMo/Nemotron as a reference and optional backend integration, not as a required dependency or the definition of Vectolith's architecture.

The portable ideas are modular data curation, explicit artifacts/configurations, SFT, verifiable-reward RL, specialist routing, on-policy distillation, evaluation and reproducible run metadata. NeMo RL currently documents multiple backends and methods including SFT, GRPO, PPO, DPO, reward models and MOPD; availability and hardware requirements must be checked for the exact pinned release before an adapter is implemented.

An adapter must pass Vectolith's own contract and parity tests. Core registry, manifests, task contracts, safety/permission boundaries and release policy remain provider-neutral. NVIDIA hardware, NeMo services, hosted teacher APIs and any specific model family must remain optional.

References:
- [Nemotron training asset hub](https://github.com/NVIDIA-NeMo/Nemotron)
- [NeMo RL documentation](https://docs.nvidia.com/nemo/rl/latest/index.html)
- [NeMo RL Nemotron guides](https://docs.nvidia.com/nemo/rl/latest/guides/models/nemotron/index.html)

## 7. Implementation backlog and acceptance criteria

| Priority | Work | Acceptance criteria |
|---|---|---|
| P0 | Contract/schema hardening | Versioned JSON schemas and fixtures for dataset rows/manifests, run manifests, qualification records and evaluation reports; invalid or unknown versions fail closed |
| P0 | Qualification evidence hardening | Keyword score cannot alone appoint a teacher; grading/executable evidence, license and endpoint permission evidence are mandatory |
| P0 | Run-manifest lifecycle | Preflight, approval, status, cancellation, immutable artifacts, reproducibility and audit records are emitted for each run |
| P1 | Dataset manifest tooling | Build, validate, hash, split, deduplicate and audit immutable datasets without exposing holdouts |
| P1 | Evaluation report tooling | Standard per-case raw evidence, deterministic/local semantic grading, executable verifier output, regression comparison and holdout integrity |
| P1 | Trainer adapter interface | Capability discovery and lifecycle methods with a deterministic mock adapter and no import-time side effects |
| P2 | NeMo RL adapter prototype | Pinned optional adapter; smoke tests on small supported models; no assumed GPU provisioning |
| P2 | MOPD/RLVR implementation | Only after foundation, data, compute and reward-verifier gates; reproducible unit/integration tests and student-independence proof |

P0 and P1 work must not launch expensive training. The first implementation milestone should validate contracts and mock orchestration on CPU. Real model runs are separate, explicitly approved experiments.

## 8. Non-negotiable operational rules

- No credentials, private data, hidden holdouts, model weights or paid-provider assumptions in source control.
- No training or provider call on import; all network and compute actions require explicit operator invocation.
- No unpinned model, tokenizer, dataset, trainer or evaluation suite in a qualification or release record.
- No automatic appointment based on candidate lists, public benchmark claims or keyword scores.
- No teacher at student inference; no teacher endpoint or key in release runtime configuration.
- No model release without independent held-out evaluation, safety gates, reproducibility and rollback evidence.
- Preserve the current FYR PRIMA pause and all existing foundation-selection and execution-environment constraints.
