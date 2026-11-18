# Foundation Candidate Research — 2026-11-15

**Decision state:** Research shortlist only. No candidate is selected for Core Prime or Core Prima.
**Evidence rule:** Provider-published claims are discovery evidence, not independent proof. The capability scores remain unscored until the same pinned evaluation suite is executed against the exact checkpoint revisions.

## Executive result

The initial candidate pool should be expanded beyond one model family. The best current research candidates have different trade-offs:

- **Qwen3.5-9B** is a high-priority cross-role candidate because its model card documents 201 languages/dialects, multimodal pretraining, 262K native context, and explicit SGLang/vLLM OpenAI-compatible serving and tool-call parsers. Its hybrid Gated DeltaNet/Gated Attention architecture means generic decoder-only LoRA tooling must be validated, not assumed.
- **IBM Granite 4.2 8B** is a high-priority Prima candidate and Prime comparator: reasoning-augmented tool calling, agentic workflows, Apache 2.0, 128K native context, and a conventional dense decoder-only `GraniteForCausalLM` architecture. IBM documents tested support for 12 languages, not broad dialect coverage. Current vLLM instructions require recent versions and a model-specific reasoning parser.
- **Gemma 4 E4B** is a high-priority Prime efficiency candidate and multimodal comparator: Apache 2.0, 128K context, audio/image input, and multilingual support described as 35+ supported languages / pretraining across 140+ languages. Its per-layer embeddings and hybrid attention require explicit trainer and serving compatibility checks.
- **Mistral Small 4** belongs in a high-capability reference tier, not the first constrained deployment tier. It unifies reasoning, coding, agentic and multimodal capabilities under Apache 2.0, but its 119B total / 6B active (8B including embedding and output layers) and stated 4x H100-class minimum infrastructure make its total memory and operational resource requirements materially different from the smaller candidates.

These are candidate hypotheses, not rankings. No model has been benchmarked by vectolith in this repository yet.

## Candidate comparison

| Exact checkpoint | Candidate role | Architecture and size | Context / modalities | License | Documented strengths | Main risks / validation work |
|---|---|---|---|---|---|---|
| `Qwen/Qwen3.5-9B` | Prime and Prima | 9B language model, hybrid Gated DeltaNet + Gated Attention, vision encoder | 262,144 native; vision-language; vendor claims 201 languages and dialects | Apache 2.0 (verify exact revision) | Broad language coverage, reasoning, coding, agents, tool use; SGLang and vLLM OpenAI-compatible server recipes | Newer hybrid architecture; validate PEFT target modules, quantization, model loading, tokenizer/chat template, tool-call parsing and runtime maturity |
| `ibm-granite/granite-4.2-8b` | Prima primary candidate; Prime comparator | 8B dense decoder-only, `GraniteForCausalLM` | 128K native; text | Apache 2.0 | Reasoning, coding, reasoning-augmented tool calling, agentic workflows; documented vLLM serving | Vendor lists 12 tested languages; no claimed broad dialect benchmark. Validate custom reasoning parser and QLoRA target modules |
| `google/gemma-4-E4B` | Prime primary candidate; Prima comparator | 4.5B effective / 8B with embeddings; hybrid attention and per-layer embeddings | 128K; text, image, audio input | Apache 2.0 | Edge/consumer efficiency, reasoning, function calling, multimodal input, 35+ supported languages / 140+ pretraining languages | Effective parameter count is not full memory size; validate PLE/hybrid-attention compatibility with trainer, quantization and serving engine |
| `mistralai/Mistral-Small-4` | High-capability reference candidate for both roles | 119B total / 6B active (8B including embedding and output layers) MoE | Multimodal text/image; verify exact context on checkpoint | Apache 2.0 | Unifies instruct, reasoning, multimodal and agentic coding; available in vLLM, llama.cpp, SGLang, Transformers | Provider states minimum infrastructure of 4x H100 / 2x H200 / 1x DGX B200. Likely inappropriate for first low-cost deployment; verify exact checkpoint and total memory |

### Official evidence

- Qwen3.5-9B model card and serving instructions: https://huggingface.co/Qwen/Qwen3.5-9B
- IBM Granite 4.2 8B model card: https://huggingface.co/ibm-granite/granite-4.2-8b
- IBM Granite 4.2 documentation and vLLM parser guidance: https://www.ibm.com/granite/docs/models/granite4-2
- Gemma 4 model card: https://gemma.ai/models/gemma-4/model-card/
- Gemma 4 memory and model overview: https://ai.google.dev/gemma/docs/core
- Mistral Small 4 announcement and infrastructure guidance: https://mistral.ai/news/mistral-small-4/
- Mistral model comparison and license information: https://docs.mistral.ai/getting-started/models/compare?models=mistral-small-4-0-26-03

## Role-specific shortlist — provisional

### Core Prime

1. Qwen3.5-9B — first candidate for global-language breadth and general capability.
2. Gemma 4 E4B — first efficiency and multimodal candidate.
3. Granite 4.2 8B — dense reasoning and language-quality comparator.
4. Mistral Small 4 — high-end reference only, pending infrastructure feasibility.

Prime must be evaluated on global-English quality, general reasoning, instruction following, writing, synthesis, long-context tasks, multilingual comprehension, calibration, and safe everyday assistance. Vendor language coverage is not a substitute for testing World Englishes and regional registers.

### Core Prima

1. Granite 4.2 8B — first candidate for dense reasoning, coding, and tool-use workflows.
2. Qwen3.5-9B — first candidate for agentic coding, structured tool use, and broad language coverage.
3. Mistral Small 4 — high-end agentic-coding reference, subject to substantial infrastructure requirements.
4. Gemma 4 E4B — efficiency and multimodal technical-work comparator.

Prima must be evaluated on repository-level changes, bug localization, debugging, tests, code review, secure coding, command/tool execution, recovery from failed actions, and truthful completion reporting. A high score on code-generation question-answer benchmarks is insufficient.

## What the public evidence does and does not establish

| Question | Current evidence state |
|---|---|
| License | All four providers publish Apache 2.0 for these candidate releases; verify license file and any additional notices at the exact immutable checkpoint revision before approval |
| Global English | All are English-capable; none is proven by the cited model cards to handle all World Englishes, regional idioms, or dialectal transcripts to vectolith's standard |
| Multilingual | Qwen claims 201 languages/dialects; Gemma documents 35+ supported and 140+ pretraining languages; Granite lists 12 tested languages; Mistral requires a separate exact checkpoint language audit |
| Coding and agentic execution | Providers document capabilities, but vectolith has no independent repository-level execution results yet |
| Tool calling | Qwen, Granite, Gemma and Mistral document tool/function calling; parser, schema fidelity, refusal behaviour and multi-turn tool reliability remain untested here |
| Training compatibility | No candidate has yet passed a pinned PEFT/QLoRA smoke test with the repository's actual trainer |
| Serving compatibility | Official server recipes exist for all candidates or their serving stacks, but exact pinned versions and production reliability have not been validated in VELNOR |
| Latency, VRAM, resource use | No vectolith measurements exist; do not estimate from parameter count alone |
| Final selection | Not made |

## Execution availability

A candidate is not considered practically executable merely because its weights are downloadable. Before scheduling an evaluation, record the available accelerator, memory, session duration, queue conditions, model-size limits, storage and egress constraints, account and regional eligibility, workload restrictions, and the exact runtime configuration. Distinguish a documented service offer from a session that has actually started and completed the intended workload. If a candidate cannot be evaluated in a verified environment, record it as pending rather than substituting vendor benchmark claims for measured results.

## Reproducible evaluation protocol

For each role, run all shortlisted checkpoints through the same role-appropriate test harness. Store the exact model revision SHA, tokenizer revision, inference-engine version, quantization, hardware, context length, sampling settings, prompt-set hash, dataset versions, raw outputs, scores, and run logs.

### Shared evaluation dimensions

- Global English: grammar, clarity, register adaptation, spelling variation, idioms, dialect robustness, ambiguity handling, and culturally neutral communication.
- Multilingual: comprehension, translation, code-switching, and consistency across the languages each candidate claims to support.
- Reasoning: multi-step reasoning, math, factual synthesis, uncertainty calibration, and contradiction handling.
- Instruction following: multi-constraint prompts, format adherence, and preservation of user intent.
- Tool use: schema-valid calls, correct tool selection, argument accuracy, recovery, and no fabricated tool outcomes.
- Reliability: repeated-run variance, latency distribution, invalid output rate, context degradation, and refusal correctness.
- Deployment: peak memory, tokens/sec, time-to-first-token, concurrency, throughput and resource utilization under the same workload, cold start, and operational complexity.
- Training: immutable revision loading, model class, tokenizer compatibility, target-module discovery, adapter save/reload, and quantized training smoke test.

### Role-specific suites

Prime: general knowledge and reasoning, long-form writing, summarization, instruction hierarchy, everyday planning, education, professional communication, multilingual and World Englishes tasks.

Prima: SWE-bench-style repository tasks, controlled issue-to-PR tasks, unit/integration test generation and execution, bug fixing, code review, security review, shell/tool operation, multi-step recovery, and evidence-based completion. Use isolated sandboxes and hold out repository tasks from training.

### Decision process

1. Freeze exact candidate revisions and license snapshots.
2. Run shared smoke tests and remove incompatible candidates only with recorded evidence.
3. Run role-specific evaluations independently.
4. Measure inference on the intended deployment hardware and a representative hosted-GPU profile.
5. Run bounded trainer compatibility tests; do not start full training.
6. Score with the role-specific weights in the independent foundation policy.
7. Publish raw results and a decision record; select Prime and Prima independently.

## Current recommendation

Do **not** select either foundation yet. Prioritize a reproducible first-round comparison of Qwen3.5-9B, Granite 4.2 8B, and Gemma 4 E4B. Keep Mistral Small 4 as a high-capability reference if a suitable execution environment becomes available.

This is the most defensible next step: the available evidence is enough to narrow the first test batch, but not enough to establish which foundation is best for either model. No weights have been downloaded, no training has started, and no training run is authorized by this research note.
