# Candidate research log — Experiment 001

Status: discovery only. No candidate is approved, no licenses are legally reviewed, and no exact revision is pinned.

## Shortlist to investigate

| Family / target | Purpose | Status |
|---|---|---|
| HuggingFaceTB/SmolLM2-360M-Instruct | Very small, accessible inference baseline | Pending revision and license evidence capture |
| Qwen 0.5B–1B instruct candidate | Compact dense model comparison | Exact repository and revision pending |
| HuggingFaceTB/SmolLM3-3B | Larger compact comparison | Exact repository, revision, compatibility pending |
| MiniCPM 1B–2B candidate | Alternative efficiency architecture | Exact repository, revision and license pending |
| LFM 1B class candidate | Alternative architecture and efficiency | License terms and exact repository/revision pending |

The shortlist is not a ranking. Candidate selection must be based on measured results under the same prompt suite and verified hardware constraints.

## Evidence required for each candidate

- Exact Hugging Face repository identifier and immutable 40-character commit SHA
- Commit SHA and model files inventory (hashes, where practical)
- License text and license identifier captured at that exact revision; independent human review
- Separate assessment of permission to use model outputs for training/distillation; no inference from weights license alone
- Model architecture, parameter count, tokenizer revision, chat template and context window
- Dependency requirements, remote-code requirement and code review if applicable
- Hardware and memory feasibility (measured, not estimated as a guarantee)
- Reproducible download and inference instructions
- Status and reasons for blocking or rejection

## Sources / discovery references

- SmolLM2-360M-Instruct model card: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
- SmolLM3-3B model card: https://huggingface.co/HuggingFaceTB/SmolLM3-3B
- Hugging Face model hub search for Qwen candidates: https://huggingface.co/models?search=Qwen%20instruct%200.5B
- Hugging Face model hub search for MiniCPM candidates: https://huggingface.co/models?search=MiniCPM
- Hugging Face model hub search for LFM candidates: https://huggingface.co/models?search=LFM

These links are discovery entry points, not evidence that any particular candidate passes. Capture the exact model card, license and revision during verification.

## Selection rule

Do not approve a candidate based on popularity, vendor benchmark scores, model size, or a license label alone. Run a common baseline suite, preserve per-task outputs and resource measurements, then review evidence before selection.
