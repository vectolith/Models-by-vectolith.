# Core Prime generation completion and recovery policy

## Completion is a verified event

A generation attempt is complete only when the returned sequence contains the configured EOS token at its terminal position, the response decodes to nonempty text, and available stop metadata is consistent. Tokenizer, model configuration and generation configuration EOS IDs must agree. Unknown or contradictory stop metadata is rejected.

The explicit `--max-new-tokens` budget is a run-level resource limit, not a universal default. Select and record a budget for the task, model, context, resource envelope and expected answer. Budget exhaustion is **incomplete**, not a successful answer. Do not silently trim, splice, accept or grade incomplete output.

## Artifacts and preservation

- The paired output JSON is published only if every case/condition attempt is complete.
- A sidecar `<output>.audit.jsonl` is created exclusively and appended after every attempt. It preserves partial response text, raw generated token IDs, token and response hashes, prompt-token hash, EOS sources, budget, status, errors and run identity.
- The audit ledger is restricted to the local operator; it contains condition labels and partial/full response data and must not be handed to evaluators.
- Completed output is exclusive-published. The audit summary binds the output bytes by SHA-256. Existing output or ledger files are never overwritten.
- The blinded evaluator verifies the output hash, exact case-file hash and count, normalized character-prompt hash, run/model-load provenance, known ledger record types and every case/condition completion record before producing evaluator sheets. Incomplete, mismatched or conflicting records cannot be blinded.
- Generation artifacts are created in private mode-0700 directories, with mode-0600 files, and POSIX no-follow directory traversal checks. The evaluator must receive the exact case file and character-prompt file used by the run.

## Retry and continuation protocol (not automated)

Retries or continuation require a separately approved protocol and a new run path. There is no automatic retry or continuation in this generator.

1. Preserve the incomplete attempt and audit ledger as-is.
2. Record the failure class: budget exhaustion, configuration conflict, native stop metadata conflict, decoding error, or infrastructure failure.
3. Review whether retrying the original prompt with a task-appropriate larger budget is warranted. Do not change the model, tokenizer, prompt, or budget silently.
4. If continuation is explicitly approved, it must be a new, linked attempt with its own input hash, source attempt/run ID, model/tokenizer revision, budget, raw token IDs and stop metadata. Continuation text must not be silently concatenated with or replace the original.
5. A reviewer or approved deterministic policy must adjudicate which attempt, if any, is accepted. All attempts remain retained; no deletion or in-place repair.
6. Only accepted, EOS-complete paired responses with validated audit bindings can enter a blinded package.

## Experiment safeguards

No inference, regeneration, grading, holdout unblinding or training is authorized by this policy or by CI. The historic incomplete response set must remain preserved; this policy does not authorize regenerating it. The publicly visible draft holdout is not protected evaluation material.
