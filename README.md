# Models by vectolith

Canonical upstream for the vectolith model family. This repository owns model definitions, foundation selection, data and distillation pipelines, training, evaluation, runtime contracts, artifacts, and releases.

Downstream products—including VELNOR and future vectolith products or third-party integrations—consume approved model releases and stable runtime interfaces. VELNOR is one downstream consumer, not the owner of the model family.

## Model family

| Model | Primary responsibility |
|---|---|
| **Core Prime** | General-purpose intelligence: understanding user intent, reasoning, conversation, everyday assistance, instruction following, writing, learning, planning, and communicating outcomes. |
| **Core Prima** | Technical intelligence and execution: coding, software engineering, architecture, product/UI design, debugging, testing, technical investigation, tool use, and autonomous task completion. |

The models have distinct delegated duties, but both remain independently useful. Core Prime may perform useful work directly; Core Prima may reason, clarify, and communicate technical findings directly. Neither model is required to invoke the other for ordinary tasks.

## Shared vectolith family contract

Both models must maintain:

- One vectolith identity.
- One behavioural and safety contract.
- Compatible conversation and task-state formats.
- Interoperable, bidirectional delegation protocols.
- Consistent user experience across VELNOR and future integrations.

The models may use different foundation architectures and tokenizers. Interoperability is established through stable external contracts, not by forcing identical internal architectures.

## Delegated execution

The canonical example is a software-build request:

1. Core Prime understands the user's request, clarifies requirements where necessary, and defines the desired outcome and acceptance criteria.
2. Core Prime delegates implementation to Core Prima with the original intent, requirements, constraints, relevant context, permissions, and acceptance criteria intact.
3. Core Prima designs, implements, tests, debugs, and verifies the work.
4. Core Prima returns deliverables, execution status, test results, verification evidence, and known limitations to Core Prime.
5. Core Prime reviews the evidence and communicates an accurate result to the user.

Delegation is bidirectional. Either model may request clarification, return work for revision, or delegate a bounded responsibility to the other. The runtime must preserve task ownership, context, permissions, and audit history throughout.

See [the runtime architecture](docs/runtime-architecture.md) and [the delegated execution contract](docs/delegated-execution-contract.md).

## Foundation selection and training

Do not assume a particular foundation model. Compare candidates using reproducible evidence for reasoning, coding, tool use, multilingual performance, latency, memory/VRAM, serving cost, licensing, deployability, and trainer compatibility. Prime and Prima may select different foundations.

The initial teacher candidate pool covers IBM Granite, Google Gemma, Mistral Ministral, and Alibaba Qwen families. Teachers contribute independently generated responses, critiques, disagreement signals, and curated examples. Do not merge weights across different architectures. Use logit-level distillation only when tokenizer and output compatibility are demonstrated.

Teachers are training-time dependencies only. Released students must run independently without teacher inference.

## Current status

This is the project scaffold and specification. **No foundation has been selected, no expensive training has started, and no trained student weights are claimed to exist.** Candidate selection and runtime compatibility work must precede expensive training.

- [Model-family architecture](docs/architecture.md)
- [Reusable runtime architecture](docs/runtime-architecture.md)
- [Delegated execution contract](docs/delegated-execution-contract.md)
- [Foundation selection](docs/foundation-selection.md)
- [Collective distillation](docs/collective-distillation.md)
- [Training and promotion](docs/training-and-promotion.md)
- [Release policy](docs/release-policy.md)

## Principles

1. Evidence before foundation selection; selection before expensive training.
2. Immutable model revisions and verified licenses.
3. Distinct objectives, datasets, evaluations, and promotion criteria for each model.
4. Shared family identity, safety baseline, and interoperability.
5. Runtime-level task execution, permission enforcement, and verifiable outcomes.
6. Reproducible runs, auditable data lineage, and honest model cards.
7. Never commit credentials, private datasets, or large model weights to Git.

## Licensing

The source-code license does not automatically apply to foundation models, teacher outputs, datasets, or model weights. Record each component's actual license and obligations separately.
