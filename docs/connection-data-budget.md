# VELNOR model-download and execution safeguards

**Status:** Operational policy for evaluation and development

## Default behavior

1. Model-weight downloads are disabled by default. Continue repository work, metadata inspection, source and license review, compatibility preparation, and evaluation design without fetching full checkpoints.
2. Every model artifact must be tied to an immutable repository revision.
3. Before a download, identify the exact files, format, quantization, tokenizer, configuration assets, and expected transfer size. Do not add alternative formats or duplicate weight layouts to the same transfer estimate.
4. Avoid repository-wide snapshots when a smaller, verified file manifest is sufficient.
5. No automatic or background model downloads. A workflow that fetches weights must be explicitly selected for a specific, approved run.
6. Prefer metadata-only inspection first. Select one candidate at a time and record the reason the artifact is needed.
7. Stop safely if the file inventory changes, unexpected shards appear, transfer accounting is unavailable, or the execution environment cannot be verified.
8. Keep download execution separate from evaluation orchestration. Documentation changes and static tests must not accidentally launch model-loading or snapshot-download jobs.

## Per-run manifest

Before any model download, record:

- candidate ID and source repository;
- immutable revision;
- exact selected files and format/quantization;
- expected transfer size and required auxiliary assets;
- execution environment and available storage/memory;
- purpose and evaluation suite;
- explicit approval for that specific run.

If any required field is unknown, keep the download blocked.

## Execution and workflow safeguards

- Distinguish local execution from hosted CI execution; each has separate network, compute, storage, and policy implications.
- Hosted runners are not assumed to have sufficient memory, storage, or throughput for a candidate merely because a workflow can start.
- Do not launch broad multi-teacher or chained inference workflows as a side effect of routine repository changes.
- Weight-fetching workflows must use deliberate manual dispatch or an equivalent explicit run gate, validate the selected candidate and immutable revision, and fail closed when required inputs are missing.
- Record actual inference results separately from estimates, metadata audits, and dry runs.

## Current development scope

Permitted without model-weight downloads:

- repository documentation and code changes;
- source, license, revision, and file-inventory checks;
- compatibility and evaluation preparation;
- static tests that do not invoke model loading or snapshot downloads.

A candidate is not qualified until its required legal, compatibility, runtime, and role-specific evaluation gates have been verified with reproducible evidence.
