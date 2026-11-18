# Independent Foundation Selection and Training Policy

**Status:** Evaluation policy; no foundation selected  
**Applies to:** Core Prime, Core Prima, and future vectolith models  
**Language target:** Global English

## 1. Non-negotiable selection rule

Core Prime and Core Prima are separate model products with different capability profiles. Select a foundation independently for each role. They may use different model families, architectures, tokenizers, context strategies, serving engines, and training recipes.

Do not select a foundation because it is popular, because it was used by an earlier experiment, or because it is shared by the other model. Do not begin expensive fine-tuning, continued pretraining, reinforcement learning, or distillation until the relevant candidate has passed the evaluation and deployment gates in this document.

A model card, vendor benchmark, or parameter count is evidence for shortlisting only. Final selection requires reproducible evaluation using vectolith's own task suites and target deployment constraints.

## 2. Role-specific foundation profiles

### Core Prime — general intelligence

Evaluate foundations for:
- General reasoning, factual synthesis, and calibrated uncertainty.
- Instruction following and preservation of multi-part user intent.
- Natural, clear global-English conversation and writing.
- Planning, explanation, learning support, and broad problem solving.
- Multilingual comprehension and reliable handling of code-switching.
- Context retention, summarization, and consistent behaviour across long conversations.
- Safe, predictable structured output and tool selection where needed.

Prime is not selected primarily for code-generation leaderboard performance. It must be a capable general assistant across everyday, educational, analytical, and professional tasks.

### Core Prima — technical intelligence and execution

Evaluate foundations for:
- Software engineering across languages, frameworks, and repository-scale tasks.
- Debugging, root-cause analysis, code review, testing, and secure implementation.
- Mathematical and formal reasoning relevant to engineering.
- Reliable structured output, schema adherence, and function/tool calling.
- Multi-step agentic execution, recovery from tool errors, and accurate task-state reporting.
- Technical research, architecture analysis, and documentation.
- Global-English technical communication: clear explanations, issue reports, plans, and handoffs.

Prima is not Prime with a larger coding dataset. Its objectives, training mixture, execution environments, and release evaluations must be deliberately more demanding and independently measured.

## 3. Global English standard

Both models must communicate in globally understandable English rather than being optimized for one national or regional variety.

The evaluation suite must cover:
- Major English varieties, including British, American, Nigerian, Indian, Australian, and other World Englishes.
- Formal and informal registers, professional writing, academic writing, conversational phrasing, and technical prose.
- Idioms, colloquialisms, spelling variation, punctuation conventions, dates, units, and culturally situated references.
- Diverse accents and speech transcripts if/when speech input is supported.
- Ambiguous or unfamiliar regional expressions: ask for clarification or infer cautiously rather than stereotyping.
- Consistent grammar, readability, factual precision, and tone adaptation without caricaturing a dialect.

Default output should be clear international English. Spelling and formatting may adapt to an explicitly stated user preference or the established context. The models must not treat one regional variety as inherently more correct or intelligent than another.

Global English is not an English-only constraint. Multilingual comprehension, translation, and code-switching should be measured according to each foundation's actual supported language coverage and the product's release scope.

## 4. Candidate evaluation process

Maintain independent candidate records for Prime and Prima. Each record must pin:
- Exact repository, checkpoint name, immutable revision/commit, and model-card snapshot date.
- License text and commercial-use obligations for that exact checkpoint.
- Architecture, parameter count, tokenizer, context limits, supported modalities, and weight format.
- Native chat template, reasoning controls, tool-call format, and structured-output support.
- Supported inference engines and known adapter/quantization constraints.
- Hardware requirements, measured peak VRAM/RAM, tokens per second, time-to-first-token, and concurrency.
- Training compatibility: model class, attention/MLP target modules, quantization support, and adapter compatibility.
- Evaluation dataset versions, prompts, decoding settings, raw results, and evaluator versions.

### Weighted scorecards

Use separate scorecards; do not transfer one role's weights to the other. Score every dimension from 0 to 5, attach evidence, and report confidence. A missing result is **unknown**, not zero and not a pass.

| Dimension | Core Prime | Core Prima |
|---|---:|---:|
| General reasoning and knowledge | 20% | 8% |
| Global English quality and instruction following | 25% | 10% |
| Multilingual comprehension | 15% | 5% |
| Writing, synthesis, and long-context use | 15% | 5% |
| Software engineering and debugging | 5% | 25% |
| Tool calling and structured output | 5% | 20% |
| Agentic execution and recovery | 5% | 17% |
| Deployment efficiency and latency | 5% | 5% |
| Training compatibility and adaptability | 3% | 3% |
| License and operational constraints | 2% | 2% |

These weights are a prioritization instrument, not a substitute for minimum gates. A high aggregate score cannot compensate for a license failure, unacceptable safety behaviour, unreliable tool execution, or inability to deploy within the approved budget.

### Free-compute and cost gate

Because the project has no approved training or inference budget, record the actual no-cost compute options available at evaluation time for every candidate. For each provider or community environment, record accelerator type/count, VRAM, session and quota limits, queue/wait availability, permitted model sizes, storage and egress limits, expiry, regional/account eligibility, and whether a payment method or billing-enabled account is required. Verify availability from the provider's current terms and account-level quota rather than assuming a free tier exists.

Separate genuinely no-cost capacity from trials, promotional credits, limited-time grants, and services that require billing activation. Do not start paid API calls, paid compute, or a training run without explicit approval. If no suitable free capacity is currently available, mark the candidate **not currently testable at zero cost** rather than silently relaxing the evaluation or claiming it passed. Record measured inference cost and resource use where a provider or environment supplies them; parameter count alone is not a cost estimate.

### Minimum evaluation gates

1. **Identity and provenance:** exact revision is immutable and its source and license are verified.
2. **Capability:** role-specific benchmark suite is run with pinned prompts and settings.
3. **Global English:** dialect/register robustness, clarity, instruction fidelity, and multilingual coverage are measured.
4. **Reliability:** repeated trials measure variance, invalid outputs, hallucination, refusal errors, and calibration.
5. **Runtime:** candidate is loaded and exercised on the intended serving stack; tool-call parsing and cancellation/timeouts are tested.
6. **Resource fit:** measured memory, throughput, latency, and cost fit an explicitly approved deployment envelope.
7. **Training fit:** a small, bounded compatibility experiment verifies tokenizer, model class, target-module discovery, and adapter save/reload before any substantial run.
8. **Decision review:** retain raw evidence and explain why the selected candidate is better suited than the alternatives.

## 5. Training must be role-specific

### Prime training objectives
Prioritize general instruction following, broad reasoning, factual calibration, synthesis, planning, global-English communication, multilingual robustness, safe assistance, and reliable conversational continuity.

### Prima training objectives
Prioritize repository-level software engineering, test-driven implementation, debugging, code comprehension, architecture decisions, secure coding, tool selection, command/terminal use, structured task execution, recovery, and evidence-based completion reporting.

Prima's evaluation must include real executable tasks in isolated environments. Text-only coding questions are insufficient to establish engineering or autonomous-execution competence.

### Shared family conformance
Both models must pass the same vectolith identity, instruction hierarchy, safety, honesty, privacy, and user-permission conformance suite. They must interoperate through versioned task, delegation, status, result, and evidence contracts. Shared identity does not require shared weights or identical training data.

Training datasets must have documented provenance, licensing/usage review, deduplication, contamination checks, quality filters, and train/validation/test separation. Keep held-out evaluations private to the extent practical. Do not use benchmark answers as training examples.

## 6. Inference and optional consumer-interface gate

Do not bind the family to a single inference engine before candidate selection. After each foundation is selected:
- Choose a serving engine based on that checkpoint's architecture and measured deployment needs.
- Implement and test a concrete adapter for the selected engine/API.
- Publish a versioned model interface only if there is a justified consumer need; it is not a requirement for another Vectolith product.
- Any consuming application owns its own authentication, authorization, policy, permissions, tool execution, tenant isolation, approvals and audit enforcement. Model-generated text is never an authorization authority.
- Keep model identity, lifecycle, capability and serving requirements explicit; never assume Prime and Prima share a backend.
- Test model loading, inference correctness, invalid outputs, timeout, cancellation, backend failure, partial output and evidence handling within this repository's own release scope.

## 7. Initial research shortlist (not a selection)

The following are candidates for evidence collection only. Their inclusion does not imply approval or a final ranking.

| Candidate | Potential evaluation relevance | Evidence to verify before selection |
|---|---|---|
| IBM Granite 4.2 8B | Dense reasoning model with documented tool calling and agentic workflow focus; potentially relevant to Prima and as a Prime comparator | Exact checkpoint revision/license; global-English and multilingual results; independent code/agent benchmark runs; memory and latency on target hardware |
| Qwen3.5-9B | Candidate with documented OpenAI-compatible serving and tool-call parser guidance; potentially relevant to both roles | Exact revision/license; role-specific quality; tokenizer/training compatibility; actual serving-engine stability and resource profile |
| Additional candidates | Keep the candidate pool open; add models based on role fit, license, architecture, and feasible deployment | Require the same evidence record and gates; do not lower the bar for a preferred vendor |

Reference material:
- IBM Granite 4.2 overview: https://github.com/ibm-granite/granite-4.2-language-models
- Granite 4.2 8B model card: https://huggingface.co/ibm-granite/granite-4.2-8b
- Granite 4.2 technical report: https://huggingface.co/blog/ibm-granite/granite-4-2
- Qwen3.5-9B model card and serving guidance: https://huggingface.co/Qwen/Qwen3.5-9B

## 8. Current decision

- Core Prime foundation: **NOT SELECTED**.
- Core Prima foundation: **NOT SELECTED**.
- Expensive training: **NOT AUTHORIZED / NOT STARTED**.
- Concrete foundation-specific inference adapters: **PENDING FOUNDATION SELECTION**.
- Global-English target: **REQUIRED FOR BOTH**.
- Next gate: complete independent candidate scorecards and runtime compatibility evidence for each role, then record an explicit selection decision before training or provider-specific implementation.
