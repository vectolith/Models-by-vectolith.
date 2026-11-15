# Multi-teacher distillation and student independence

## Decision

Every student model in Models by vectolith MUST be taught by a panel of at least four qualified teacher models. This applies to Core Prime, Core Prima, and every future model family member. All four or more teachers assigned to a student MUST make a measurable contribution to that student's training. A teacher panel is not satisfied by listing four candidates, querying only one teacher, or using the others as optional fallbacks.

Teachers are training-time contributors. A released student MUST perform its declared capabilities independently and MUST NOT require, call, route to, or depend on its former teachers during ordinary inference or task execution.

This is a multi-teacher knowledge-distillation architecture, not a permanent ensemble architecture.

## 1. Student and teacher separation

- A **student** is a vectolith model being trained and released: Core Prime, Core Prima, or a future registered model.
- A **teacher** is an independently developed model temporarily used to generate, critique, verify, explain, or demonstrate training targets.
- A **teacher panel** is the minimum four distinct teacher models assigned to one student for a defined training run.
- A **training contribution** is a traceable, quality-controlled artifact from a teacher that is incorporated into the student's training corpus or optimization process.
- A **student release** is an independently evaluated model artifact that can run without teacher services or teacher credentials.

Teacher models are not automatically foundations. Student foundation selection and teacher-panel selection are separate decisions. A foundation may be considered as a teacher only if it independently passes the teacher qualification gates and its contribution is appropriately differentiated.

## 2. Minimum panel size and contribution requirements

Each student MUST have at least four distinct teacher model identities per approved teaching run. Prefer complementary architectures, training lineages, and strengths rather than four near-identical checkpoints from one family.

Every teacher must contribute to the student. Before training begins, the run manifest must specify for each teacher:

1. immutable model identifier and revision;
2. provider, architecture, modality, tokenizer and serving interface where applicable;
3. license, terms of service, data-use permissions and output-retention constraints;
4. assigned competencies and the types of examples it will produce or review;
5. sampling plan, contribution quota, dataset shard IDs and provenance;
6. measured quality, disagreement rate, cost, latency and failure rate;
7. acceptance criteria and replacement conditions.

A teacher's contribution is valid only when its outputs pass automated checks and sampled human or trusted independent review, are retained with provenance, and are actually included in the training run. Merely calling a teacher or storing its response does not count.

Use balanced contribution quotas by competency, not necessarily equal raw token counts. The training report must show each teacher's accepted examples, accepted-token share, competency coverage, rejection rate, and measured effect in ablation tests. No teacher may be silently ignored or contribute only low-value filler to meet the four-teacher rule.

A panel may contain more than four teachers. Four is the floor, not a ceiling.

## 3. Role-specific teacher panels

The following are initial candidate pools for evaluation, not final appointments or a claim that they have already taught the students. The exact checkpoint and immutable revision must be recorded. Candidates may be replaced if they fail quality, license, access, cost, latency, or compatibility gates.

### Core Prime — general intelligence

Core Prime's panel must collectively cover general reasoning, knowledge synthesis, instruction following, planning, global-English communication, multilingual comprehension, explanation, and uncertainty calibration.

Initial candidates to benchmark:

1. **OpenAI gpt-oss-120b** — general reasoning, instruction following and agentic/tool-use demonstrations. Model card: https://huggingface.co/openai/gpt-oss-120b
2. **Qwen Qwen3.8-27B** — broad general-purpose reasoning, multilingual and multimodal demonstrations, and long-horizon task examples. Model card: https://huggingface.co/Qwen/Qwen3.8-27B
3. **Google Gemma 4 31B** — independent generalist and multimodal perspective, language and knowledge tasks. The exact checkpoint and applicable license must be verified before use.
4. **DeepSeek-V4.1-Flash** — reasoning, mathematical and multilingual examples, plus a distinct architecture and efficient active-compute profile. Model card: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash

### Core Prima — engineering and execution

Core Prima's panel must collectively cover software architecture, code generation, debugging, testing, mathematics, repository-level changes, tool calling, terminal workflows, planning, and verified task completion.

Initial candidates to benchmark:

1. **DeepSeek-V4.1-Flash** — coding, mathematical reasoning and agentic execution examples. Model card: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash
2. **Z.ai GLM-5.3-Flash** — software engineering, coding and tool-oriented agent workflows. Model card: https://huggingface.co/zai-org/GLM-5.3-Flash
3. **Qwen Qwen3.8-27B** — code, debugging, multi-step agent execution and broad technical reasoning. Model card: https://huggingface.co/Qwen/Qwen3.8-27B
4. **OpenAI gpt-oss-120b** — independent reasoning, structured tool-use and technical problem-solving examples. Model card: https://huggingface.co/openai/gpt-oss-120b

These two lists deliberately overlap where a model may contribute useful cross-domain knowledge. Overlap does not make the panels identical: each student's competency plan, prompt sets, accepted examples, weighting and evaluation must be distinct. A candidate is not appointed solely because it appears in this document.

## 4. Teacher qualification and selection

Before appointment, run every candidate against a common, versioned teacher qualification suite and the student's role-specific suite. Evaluate:

- task accuracy and reasoning validity, including difficult and adversarial cases;
- factuality, calibration, abstention and error correction;
- global-English clarity across dialects, registers and writing styles;
- multilingual quality where relevant;
- role-specific performance (general intelligence for Prime; software engineering and execution for Prima);
- structured output, tool-call correctness and protocol compliance;
- consistency across repeated runs and resistance to prompt injection;
- latency, throughput, context cost, token cost and total dataset-generation cost;
- serving availability, revision stability and operational reliability;
- checkpoint license and permission to use generated outputs for training, retention, modification and commercial release.

Do not treat vendor-reported benchmark scores as directly comparable unless the benchmark, prompt, scoring method, tool harness and evaluation conditions match. Reproduce results where possible. Record unknowns explicitly. Reject candidates whose license or provider terms do not permit the intended training use.

The panel is selected by complementary measured contribution and cost-effectiveness, not popularity, parameter count, or one aggregate leaderboard score. A lower-cost teacher is preferred only when quality remains above the required threshold.

## 5. How all teachers teach the student

Use a staged, provenance-preserving pipeline:

1. **Independent generation:** Each teacher receives competency-specific prompts and independently produces demonstrations, explanations, plans, code, critiques or structured solutions.
2. **Cross-review:** Other panel teachers review selected outputs without seeing the originating teacher's identity where feasible. They identify errors, missing steps, unsafe assumptions and alternative solutions.
3. **Adjudication:** Conflicts are resolved through executable tests, deterministic tools, trusted references, explicit rubric scoring, or independent review. Do not decide truth by majority vote alone.
4. **Dataset construction:** Accepted examples retain teacher provenance, task category, difficulty, rubric scores, review outcomes, license lineage and split assignment.
5. **Student training:** The student learns from the combined accepted corpus using its own role-specific curriculum and objectives. Where technically and legally feasible, include response-level distillation, preference comparisons, critique-revision pairs, tool traces and outcome-based reinforcement.
6. **Ablation:** Evaluate the student trained with the full panel against controlled runs with each teacher's contribution removed. Every assigned teacher must demonstrate measurable value or be replaced and the run repeated.
7. **Release evaluation:** Test the student alone, without access to teacher APIs, weights, prompts, credentials, caches or hidden fallback routes.

The pipeline must prevent teacher contamination of held-out evaluation data. Teacher-generated content must not be represented as ground truth without validation. Preserve negative examples and disagreement metadata where useful for uncertainty training.

## 6. Student independence is a release gate

A student is not considered taught merely because training completed. Before release, verify:

- the student loads and performs from its own approved checkpoint and runtime;
- all required capabilities work with teacher endpoints disabled and credentials absent;
- no inference-time teacher routing, delegation, retrieval, cache, or hidden remote dependency exists;
- the student can explain uncertainty, correct mistakes and complete representative tasks independently;
- role-specific quality meets the release thresholds;
- ablations confirm meaningful contributions from every teacher;
- reproducibility, provenance, security and license checks pass.

The production runtime may use vectolith's own explicitly registered peer models when the product's delegation design calls for it. That is separate from teacher dependence: a student must never need its former training teachers to function. Core Prime and Core Prima may delegate to each other under the VELNOR delegation contract, but neither may silently substitute an external teacher for its own missing capability.

## 7. Future model onboarding

The four-teacher minimum is a family-wide invariant. When a new model is added to the central model registry:

1. define its specialization and capability boundaries;
2. create a dedicated teacher-selection record and role-specific benchmark suite;
3. qualify at least four distinct teacher model identities;
4. assign complementary teaching responsibilities and contribution quotas;
5. create a new versioned dataset and training manifest;
6. run full-panel training and per-teacher ablations;
7. test the student independently with teacher access disabled;
8. publish its model card, provenance, evaluation report and release decision.

Do not automatically reuse Prime's or Prima's panel for a future model. Reuse is permitted only after a fresh suitability and license review, and all four teachers must contribute to the new student's own training.

## 8. Run manifest and audit record

Each teaching run must produce a machine-readable manifest containing at minimum:

- student model ID, version, specialization and foundation revision;
- teacher identities, immutable revisions, providers and licenses;
- competency assignments and per-teacher contribution quotas;
- dataset IDs, hashes, provenance and train/validation/test separation;
- generation, review, adjudication and filtering configurations;
- compute, latency, token usage and cost;
- per-teacher acceptance, rejection, quality and ablation results;
- student training configuration, checkpoint hashes and reproducibility metadata;
- teacher-disabled independence test results;
- approval status, known limitations and release decision.

Credentials for teacher services belong only in the protected training environment. They must not be embedded in student checkpoints, manifests, inference configuration or public artifacts.

## 9. Current status

- This document defines the required architecture and initial teacher candidate pools.
- No teacher panel is yet formally appointed.
- No teacher-generated training corpus or distillation run is claimed complete.
- The candidate checkpoints, exact revisions, terms and training-output permissions still require verification.
- No student is certified independent until it passes the teacher-disabled release gate.
- No expensive training or paid teacher usage is authorized by this design document.

## 10. References

Candidate model cards:
- https://huggingface.co/openai/gpt-oss-120b
- https://huggingface.co/Qwen/Qwen3.8-27B
- https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash
- https://huggingface.co/zai-org/GLM-5.3-Flash

Model cards, revisions, licenses and provider terms can change. Re-verify them at the time of panel appointment and record immutable revisions in the run manifest.
