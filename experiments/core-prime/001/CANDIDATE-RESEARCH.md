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

## Additional candidate discovery (2026-11-19)

| Candidate | Discovery observation | Status |
|---|---|---|
| Qwen/Qwen3-0.6B | Model card declares Apache-2.0; compact candidate for baseline measurement | Pending immutable revision, license artifact capture, output-permission review and inference |
| HuggingFaceTB/SmolLM3-3B | Model card declares Apache-2.0; 3B candidate for capability/resource comparison | Pending immutable revision, license artifact capture, output-permission review and inference |

Discovery references (not approvals):
- https://huggingface.co/Qwen/Qwen3-0.6B
- https://huggingface.co/HuggingFaceTB/SmolLM3-3B

License metadata alone is not output-training permission. Neither candidate has been downloaded, pinned, legally reviewed, or measured for this experiment as of this entry.


## Qwen3-0.6B license and output-use review (2026-11-19)

- Candidate revision: `c1899de289a04d12100db370d81485cdf75e47ca`; the revision-specific upstream LICENSE page identifies Apache License 2.0 and shows the license text. This is upstream evidence of the declared weight/model license, not an independent legal approval.
- Source: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE and revision commit page: https://huggingface.co/Qwen/Qwen3-0.6B/commit/c1899de289a04d12100db370d81485cdf75e47ca
- Apache-2.0 text grants rights for the licensed Work subject to its terms; the retrieved text does not specifically grant or adjudicate rights to use generated outputs as distillation/training data. Treat output-use permission as a separate unresolved legal question; do not infer it from the weight license.
- Artifact verification attempt: direct download/hash capture was attempted from this environment but outbound DNS/network access failed. Therefore no local license bytes or SHA-256 were captured, and no model/config/tokenizer/weight hashes are claimed. The manifest remains pending.
- Legal review: not completed. No inference or training performed.
- Research references: revision-specific LICENSE page (above); Apache License text shown on the upstream page; PyPI/Hugging Face package documentation used only to assess environment compatibility, not to select an untested lockfile.
