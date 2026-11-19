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


## Separate model-output / distillation rights screening (2026-11-19)

This screening is discovery only; no teacher is approved and no generated teacher outputs have been collected.

| Family / artifact | Upstream license/terms observed | Output-to-training status for this project |
|---|---|---|
| Qwen3-0.6B at `c1899de289a04d12100db370d81485cdf75e47ca` | Revision-specific LICENSE page shows Apache-2.0. | The weight license is not a separate explicit grant to use generated outputs from this or other models as distillation data. Unresolved; no legal approval. |
| SmolLM2-360M-Instruct | Model card identifies Apache-2.0. | No explicit output-training permission located in this screening; unresolved. |
| Phi-4-mini-instruct | Model card metadata identifies MIT; 3.8B parameter model. | No separate explicit output-distillation permission located; unresolved. |
| Granite 4.2 | IBM documentation describes Apache-2.0 models, including 8B/30B variants. | No separate output-distillation permission located; unresolved. Larger variant is not a lightweight compute assumption. |
| Gemma | Terms define a Model Derivative to include models transferred from Gemma outputs, including synthetic-output distillation; Outputs are not themselves deemed Model Derivatives. | Must assess terms for the resulting student and enforce applicable restrictions; do not treat output ownership statement as unrestricted distillation authorization. Unresolved. |
| MiniCPM-V 2.6 (not a text shortlist choice) | Model card refers to a separate model license and registration/questionnaire for commercial-use access. | Demonstrates that weight terms may differ from code license; not selected or used. |

Sources for this screening (discovery references, not legal opinions):
- Qwen3-0.6B pinned LICENSE: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE
- SmolLM2-360M-Instruct model card: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
- Phi-4-mini-instruct model card: https://huggingface.co/microsoft/Phi-4-mini-instruct
- IBM Granite 4.2 documentation: https://www.ibm.com/granite/docs/models/granite4-2
- Gemma Terms of Use: https://ai.google.dev/gemma/terms
- MiniCPM-V 2.6 model card: https://huggingface.co/openbmb/MiniCPM-V-2_6

For teacher outputs, each teacher's exact revision, license, provider/model terms, permitted collection method, privacy and output-to-training/distillation scope must be separately documented and reviewed. Do not collect or train on teacher outputs from hosted services or open-weight models until those permissions and any restrictions are genuinely cleared. This screening found no basis to mark any teacher output permission verified.


## Version-specific license distinctions discovered (2026-11-19)

This update distinguishes model-family versions instead of treating all Gemma or Granite releases as having identical terms. It remains discovery research, not legal review or an output-training permission grant.

| Exact family/variant observed | Upstream license signal | Output-distillation status |
|---|---|---|
| Qwen/Qwen3-0.6B (pinned LICENSE revision above) | Apache-2.0 on the upstream revision-specific LICENSE page. | No explicit output-training grant located in the LICENSE; unresolved. |
| HuggingFaceTB/SmolLM2-360M-Instruct | Model card and file pages show Apache-2.0 metadata. | No separate explicit output-training grant located; unresolved. |
| microsoft/Phi-4-mini-instruct | Model card links an MIT license. This observation applies to this variant only, not its sibling models. | No separate explicit output-training grant located; unresolved. |
| ibm-granite/granite-4.2-3b / 8b / 30b | Model cards and IBM release documentation describe Apache-2.0. Size and hardware suitability must be separately measured. | No separate explicit output-training grant located in this screening; unresolved. |
| Gemma 4 (distinct from older Gemma models covered by the April 2026 Gemma Terms of Use) | Gemma 4 license documentation and model cards identify Apache-2.0. Do not apply the older Gemma ToU wholesale to Gemma 4, or assume Gemma 4's terms apply to older variants. | Apache-2.0 does not itself resolve output rights, provenance or other legal questions; explicit permission and independent review remain required for this project's teacher-output use. Unresolved. |
| Older Gemma families covered by the April 1, 2026 Gemma Terms of Use | Custom terms define Model Derivatives to include models trained from Gemma outputs, including synthetic-output distillation; the terms also distinguish Outputs from Model Derivatives. | Terms must be independently reviewed for the exact model and contemplated student use; not cleared. |

Sources (retrieved during discovery; no bytes or hashes captured in this run):
- Qwen3-0.6B model card and pinned LICENSE: https://huggingface.co/Qwen/Qwen3-0.6B and https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE
- SmolLM2-360M-Instruct: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
- Phi-4-mini-instruct: https://huggingface.co/microsoft/Phi-4-mini-instruct
- Granite 4.2 3B and 8B: https://huggingface.co/ibm-granite/granite-4.2-3b and https://huggingface.co/ibm-granite/granite-4.2-8b
- Granite 4.2 release overview: https://huggingface.co/blog/ibm-granite/granite-4-2
- Gemma 4 license: https://ai.google.dev/gemma/docs/gemma_4_license
- Older Gemma Terms (last modified April 1, 2026): https://ai.google.dev/gemma/terms

No license artifacts, revisions, output permissions, human legal review, dataset provenance, compute evidence or student model results were verified by this update. No inference or training was performed.


## Additional primary-source screening (2026-11-20)

This is public-document screening only; not independent legal review and no output permission or model is approved.

- **Qwen/Qwen3-0.6B (revision `c1899de289a04d12100db370d81485cdf75e47ca`)**: the revision-specific Hugging Face LICENSE page declares Apache-2.0 and displays the license. Source: https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/LICENSE. This does not specifically address the contemplated output-to-training use; unresolved.
- **HuggingFaceTB/SmolLM2-360M-Instruct**: its official model card/file metadata identifies Apache-2.0. Source: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct. No separate explicit output-to-training grant was located in this screening; unresolved.
- **microsoft/Phi-4-mini-instruct**: the official model card identifies MIT. Source: https://huggingface.co/microsoft/Phi-4-mini-instruct. No separate explicit output-to-training grant was located in this screening; unresolved.
- **IBM Granite 4.2**: IBM's official documentation describes the 3B/8B/30B family as Apache-2.0. Source: https://www.ibm.com/granite/docs/models/granite4-2. This does not itself resolve rights in generated text or student training; unresolved.
- **Gemma version distinction**: Gemma 4's official overview/license materials describe an Apache-2.0 release (https://ai.google.dev/gemma/docs/gemma_4_license; https://ai.google.dev/gemma/docs/core). Older Gemma versions listed in the April 1, 2026 Gemma Terms remain under custom terms; the terms expressly define model derivatives to include student models created by synthetic-output distillation and require use restrictions to accompany distribution. Source: https://ai.google.dev/gemma/terms. Do not apply older terms to Gemma 4 or Gemma 4 Apache-2.0 to older versions.

The screening did not find an explicit, separate output-to-training permission statement for Qwen3-0.6B, SmolLM2-360M-Instruct, Phi-4-mini-instruct or Granite 4.2. This is not a finding that such use is prohibited or permitted; it is a legal question requiring review of exact candidate/teacher revisions, provider terms, source material rights, privacy, jurisdiction and contemplated student distribution. No output generation, training or inference was performed.
