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
| qwen3-4b-instruct | Qwen/Qwen3-4B-Instruct-2507 | Apache-2.0 | conversation, personality, writing |

Teachers are assigned by competency rather than asked everything. Each competency in the
curriculum is covered by at least one teacher, and every teacher contributes accepted
records to at least one student, which is what the panel rules in
`docs/executable-multi-teacher-pipeline.md` require in substance.

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
    kaggle kernels push -p training/kaggle

Adapters, per-teacher corpora, datasets, training manifests, evaluation outputs and
`run-summary.json` land in /kaggle/working/out.

## What a run does and does not prove

A run produces adapters and evaluation text. It does not promote a model. Promotion still
requires blinded human grading, the protected holdout, and the release checks in
`docs/release-policy.md`; `human_review_status` in each evaluation file stays `pending`
until a person grades it.
