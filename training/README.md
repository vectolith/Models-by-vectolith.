# Training ASH PRIME and FYR PRIMA

Two students, two panels, one reproducible pipeline. Everything here runs on free
Kaggle 2xT4 hardware with Apache-2.0 open-weight models. No paid API is called and no
credential is required: all checkpoints are ungated.

## Layout

- `curriculum/build_curriculum.py` builds `curriculum/tasks-v1.jsonl`, the fixed prompt set teachers answer.
- `kaggle/kernel.py` generates the teaching corpus, filters it, trains both students and evaluates them.
- `kaggle/kernel-metadata.json` describes the Kaggle run.
- `evaluation/export_persona_cases.py` flattens the persona cases the kernel evaluates against.

## Teacher panel

| Teacher | Model | Licence | Assigned competencies |
| --- | --- | --- | --- |
| granite-4.2-8b | ibm-granite/granite-4.2-8b | Apache-2.0 | reasoning, mathematics, engineering, writing |
| qwen2.5-coder-7b | Qwen/Qwen2.5-Coder-7B-Instruct | Apache-2.0 | coding, engineering, mathematics |
| qwen3-4b-instruct | Qwen/Qwen3-4B-Instruct-2507 | Apache-2.0 | conversation, personality_more, personality_consistency, writing |

Competency names above are the exact `competency` values in
`curriculum/tasks-v1.jsonl`; the kernel refuses to run if a curriculum task names a
competency no teacher is assigned.

Teachers are assigned by competency rather than asked everything. Each competency in the
curriculum is covered by at least one teacher, and every teacher contributes accepted
records to at least one student.

Known gap: `docs/executable-multi-teacher-pipeline.md` requires at least four distinct
qualified teachers per student, and the current kernel uses three teachers, with a
two-teacher panel for FYR PRIMA. The kernel is a single-session Kaggle pipeline; closing
the gap needs one more qualified Apache-2.0 teacher whose checkpoint fits alongside the
others in a 2xT4 session. Until then a run produces adapters and evidence, not a panel
that satisfies the four-teacher rule.

## Students

| Student | Foundation | Panel |
| --- | --- | --- |
| ASH PRIME | Qwen/Qwen3-4B-Instruct-2507 | all three teachers |
| FYR PRIMA | Qwen/Qwen3-1.7B | granite + qwen3-4b |

The students have different foundations, different panels, different seeds and separate
datasets. Neither adapter is reused for the other model.

## Running it

    pip install -q kaggle
    python3 training/curriculum/build_curriculum.py
    python3 training/evaluation/export_persona_cases.py
    python3 -m unittest training/kaggle/test_kernel_cpu.py -v
    kaggle kernels push -p training/kaggle

Both generators are byte-reproducible and the CPU suite verifies, without a GPU, the
kernel's curriculum schema and competency coverage, teacher-record provenance and hashes,
dataset assembly, metadata parsing, output paths and seed stability. The GPU stages
(corpus generation, fine-tuning, evaluation) are exercised only on Kaggle.

Adapters, per-teacher corpora, datasets, training manifests, evaluation outputs and
`run-summary.json` land in `/kaggle/working/out`; set `KAGGLE_WORKING_DIR` to run the
same code path elsewhere.

## What a run does and does not prove

A run produces adapters and evaluation text. It does not promote a model. Training start no
longer waits on human review: the owner waived the legal, human-grading, safety, holdout
custody, corpus attestation and training-output permission gates on 2026-11-24
(`docs/ash-prime-training-authorisation-owner-waiver.md`). Promotion is separate and still
needs the release checks in `docs/release-policy.md`; `human_review_status` in each
evaluation file stays `pending` because no person graded it, and waived gates are reported
as `review_basis: owner_waiver`, never as verified.
