### Evaluation-only model comparison

Use the manually dispatched `.github/workflows/manual-candidate-evaluation.yml` workflow to choose a Hugging Face repo, exact immutable commit SHA, model-family label, and Prime or Prima role. This workflow does not enforce license, qualification, or teacher-gate checks. It records the selected model and its evaluation results as a plain capability comparison.

The snapshot script preserves Hub metadata without failing when a model has no LICENSE file, and the outcome artifact is labeled `teacher_qualification: not_evaluated` and `license_review: not_evaluated`.

This is the intended no-gate evaluation path for the founder-level comparison of candidate foundations.
