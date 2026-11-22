# Executable multi-teacher pipeline

This is an opt-in training workflow. Importing the package does not contact model providers or start training. Calls to teacher endpoints and student training occur only when an operator explicitly runs the corresponding functions.

## Teacher discovery and selection policy

The initial discovery shortlist contains the Qwen, IBM Granite, Google Gemma, and Mistral Ministral model families. These are starting points, not an exclusive allowlist. The registry must remain open to additional model families and future releases.

Evaluate multiple eligible checkpoint sizes and variants within each family. Do not appoint a family by reputation or choose its smallest checkpoint by default. Compare candidates on a common, versioned evaluation protocol covering:

- reasoning and multi-step problem solving;
- coding and software engineering;
- structured tool use and agentic task execution;
- multilingual comprehension and generation;
- reliability, instruction following, and factuality;
- knowledge quality and task-specific competency.

Record measured peak memory/VRAM requirements, throughput and latency, quantization compatibility, and the actual availability and limits of the execution environment. Distinguish downloadable weights from runnable checkpoints: open weights do not establish loader, hardware or runtime compatibility.

Select at least four distinct, qualified teachers for each student. Panels may overlap, but each must collectively cover that student's required competencies and every appointed teacher must make a measurable accepted contribution. Select on demonstrated quality and practical execution feasibility, not parameter count alone.

Teacher identities, families, sizes, providers, and revisions are registry data, not student-architecture constants. A teacher can be replaced or upgraded by registering and qualifying a new immutable revision, then regenerating or extending the teaching corpus and re-running the relevant evaluations. The student architecture and inference contract must not need to change merely because its teachers change.

The four initial families and their sizes are a discovery shortlist only. Candidate discovery must be repeatable and able to admit other eligible families without code changes to the student architecture.

## Stages

### 1. Qualify candidates

Use `qualify_teacher()` only to collect raw, case-bound inference evidence at an exact immutable revision, together with latency observations and license/output-permission metadata. It deliberately returns `qualification_passed=false` and no quality score. Keyword/rubric-term matching is not used to qualify or rank teachers.

A candidate becomes eligible only after the separate fail-closed qualification manifest is completed: independent blinded human grading and adjudication, criterion-specific executable/factual verification, protected-holdout evidence, safety review, corpus integrity, legal review, explicit training-output permission, and positive leave-one-teacher-out contribution. Preserve raw response evidence and its hashes for that pipeline.

Candidate identities and public model-card claims are not proof of output-training permission. Check the exact model license and any provider terms for the actual inference route. A self-hosted open-weight model and a hosted API serving that model may have different data and output terms.

### 2. Select a complementary panel

`select_teacher_panel()` requires:
- at least four distinct qualified teacher identities;
- verified output-training permission evidence;
- exact matching immutable revisions between qualification and endpoint;
- minimum quality score;
- coverage of every requested student competency.

The result is a pre-training assignment panel. It is intentionally distinct from the post-training `TeacherPanel`, which records accepted contributions and ablation evidence.

### 3. Generate and cross-review teaching data

`generate_teaching_corpus()` asks every selected teacher to independently answer every task. A peer teacher reviews each answer against the task rubric. Only accepted records are written to JSONL, with teacher/reviewer IDs, immutable revisions, competency, timing, review outcome, and content hash.

A peer review is not ground truth. For code, math and other objectively checkable work, add executable tests or trusted reference checks before accepting records. The generator refuses to write a completed corpus if any selected teacher has zero accepted examples.

The endpoint adapter uses the OpenAI-compatible `/chat/completions` route. Configure each endpoint and API-key environment variable in a protected training environment. Do not put credentials in manifests, datasets, checkpoints, or source control.

### 4. Distil into the student

Install optional dependencies:

~~~bash
python -m pip install -e ".[training]"
~~~

Call `train_student()` only after an approved foundation-selection manifest and at least four individually qualified teacher manifests exist. Pass `foundation_selection_manifest` and `teacher_qualification_manifest_dir` alongside the dataset. Training preflight revalidates the exact foundation ID/revision, all ten teacher gates, each dataset row's teacher identity/revision, and the row content digest before importing the training stack or loading model weights. It writes a digest-backed `training-preflight.json` and refuses non-empty output directories. Without the approved foundation decision and completed independent human/holdout/legal evidence, training is blocked.

Prime and Prima must use separate foundations, curricula, datasets, training configurations, and held-out evaluations. Do not reuse one student's adapter as the other student's model.

### 5. Evaluate independently and ablate

`run_capability_suite()` executes a caller-supplied student inference function against a versioned evaluation suite. It never scores keyword overlap. Without a criterion-specific verifier carrying digest-backed evidence, every case remains unscored and requires independent human review; no pass rate is emitted. Use isolated sandbox reports for code, deterministic reference checks for objective mathematics, source-claim review for factual tasks, and blinded expert rubrics/adjudication for reasoning that lacks a formal oracle.

`leave_one_teacher_out()` accepts a controlled retraining/evaluation callback. It compares the full-panel student against one retrained student per teacher with that teacher's examples removed. Every teacher must show a positive held-out score delta. This is computationally expensive and is not run automatically. `train_student()` returns accepted example counts and token counts measured with the student's tokenizer; pass these, the dataset shard ID and the ablation report to `finalize_teacher_panel()` to create the post-training contribution record.

### 6. Teacher-disabled release gate

`run_teacher_disabled_check()` removes configured teacher endpoint and credential environment variables, hashes the student checkpoint, and validates zero observed teacher calls, passing capability checks, and an empty teacher-dependency list.

`evaluate_release()` combines capability thresholds, at least four distinct contribution records, complete positive ablation coverage, and teacher-disabled evidence. Any missing or failed evidence blocks release.

The caller must run the independence test in an isolated process/container with network egress denied to teacher services and with no teacher credentials mounted. The helper validates supplied isolation evidence; it cannot itself prove that an arbitrary external process had no hidden network route.

## Example orchestration outline

~~~python
# 1. Discover multiple sizes/variants across the initial families and beyond.
# 2. Benchmark candidates on the same versioned, role-specific suite.
# 3. Record measured resource use, memory, latency, and execution availability.
# 4. Qualify candidates and build one assignment panel (>=4 teachers) per student.
# 5. Generate accepted JSONL corpora independently.
# 6. Fine-tune each student's own selected foundation.
# 7. Run capability suites with teacher services unavailable.
# 8. Retrain once per teacher with that teacher's data removed.
# 9. Finalize contribution records and evaluate the fail-closed release gate.
~~~

## Current execution boundary

The repository contains the endpoint adapter, qualification and panel selection, provenance-preserving corpus generation, optional LoRA SFT, capability/ablation helpers, and a fail-closed release decision. It does not yet appoint real teachers or launch a run. Exact teacher revisions, license/terms evidence, student foundation selection, evaluation datasets, verified execution access and resource approvals remain prerequisites. CI does not start provider calls, model downloads or training jobs.


### Training-run safeguards added

The SFT runner now requires the immutable training-code commit SHA and records it
with the exact foundation revision, selection-manifest digest, dataset digest,
teacher-manifest digests, seed, hyperparameters, and data-split provenance in
`training-run-manifest.json`.

Before loading weights, the runner creates a deterministic validation partition
grouped by prompt digest. Every teacher response to the same prompt stays on the
same side of the split, preventing one teacher's answer to a prompt from leaking
into validation while another teacher's answer to that prompt remains in training.
The split must retain every teacher in training and at least two distinct prompt
groups in validation. Datasets too small to satisfy these conditions are rejected.

The trainer evaluates at each epoch, retains the best checkpoint by validation
loss, and records final validation metrics. Validation loss is only a training
diagnostic; it does not replace the independent capability suite, protected
holdout, or human review. Use a fresh, empty output directory for every run.


The training preflight also consumes a protected deployment manifest and a separate
candidate-specific evaluation report for every teacher (`holdout_deployment_manifest`
and `holdout_evaluation_results_dir`). Each report must bind to the deployment digest,
exact candidate revision, dedicated evaluator identity/image, full case count, zero
unscored cases, and a declared pass-rate threshold. The teacher qualification manifest
must carry the matching deployment and report digests. A boolean `holdout: passed` flag
alone is insufficient.


Before any model weights are loaded, `train_student()` also requires a run-specific
`training_execution_manifest`. It must approve the exact ASH PRIME foundation and
revision, dataset digest, training-code commit, and complete hyperparameter set. It
must record the compute account/project, region, accelerator, runtime image and
software versions, measured available VRAM/RAM/storage, peak resource estimates,
pricing evidence, maximum USD cost, maximum runtime, and named approval provenance.
The preflight rejects a configuration mismatch, missing budget evidence, or resource
estimates above measured capacity. This approval is specific to one run; it does not
authorize future runs or a different configuration.
