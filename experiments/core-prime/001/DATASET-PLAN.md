# Dataset construction and evaluation protocol

No scored dataset or protected holdout is approved yet. This plan describes the data that must be constructed before baseline inference.

## Dataset design

Construct a small, self-authored, task-balanced evaluation set, with each prompt labeled as original experiment content and each task recorded with source/provenance. It is not to be presented as a standardized benchmark.

Suggested first pass: 60 development tasks (6 categories × 10 tasks) plus a separately stored 30-task holdout (same category coverage). Keep holdout prompts and any reference answers outside model-development access until configuration freeze. These sizes are proposed targets, not existing counts.

Categories:
- Instruction following and constraints
- Reading comprehension and summarization
- Reasoning (explicitly state task assumptions; avoid trivia-dependent scoring)
- Arithmetic and practical quantitative reasoning
- Structured output / JSON validity
- Coding comprehension and small, self-contained programming tasks

## Task provenance and record format

Each task record must include task_id, category, prompt, split, rubric_id, provenance. Optionally include reference_answer, expected_constraints and content_sha256. Record exact prompt SHA-256, and source materials separately when a task is derived from a source. Keep source licensing and citation records for any sourced content.

Use the task validator before evaluation. It detects exact normalized prompt duplicates and prompt hash mismatches, but does not detect semantic, answer-level, or paraphrase leakage. A human must inspect leakage and dataset quality.

The dataset provenance review evidence record must be JSON and bind `dataset_sha256` to the exact JSONL bytes; include `review_status: reviewed`, reviewer identifier, scope, and timezone-qualified review timestamp. The verifier checks structure, hash binding and path integrity only—it does not authenticate the reviewer or prove that the review was substantive.

## Scoring

Use category-specific rubrics, and record criterion-level scores with evidence and rationale. A deterministic checker may score mechanically verifiable constraints (e.g., valid JSON, exact arithmetic), but it must not claim to assess general reasoning. Blind human grading should use candidate-neutral IDs, shuffled outputs, and a separate identity key. Do not generate or invent human grades.

## Holdout controls

- Store holdout in a separately controlled location and do not commit it publicly.
- Do not use holdout tasks for prompt tuning, training, candidate selection, or repeated feedback.
- Freeze candidate, template, decoding parameters, scorer, code and development set before first holdout evaluation.
- Use one controlled holdout pass per frozen configuration; document any unavoidable exposure.
- Never place holdout examples in training or development files.

## Current state

No dataset files have been created or scored from this protocol. The counts are design targets only. Dataset construction and human review remain pending.
