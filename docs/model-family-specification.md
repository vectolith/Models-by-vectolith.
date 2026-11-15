# Extensible vectolith model-family specification

## Scope

Models by vectolith is an extensible family of independently trained and versioned models. Core Prime and Core Prima are the initial members, not an exhaustive list or a permanent limit. New models may be introduced for any validated specialization or modality.

Every model has its own model ID, display name, version, specialization, foundation/architecture declaration, capability set, training objectives, datasets and lineage, evaluation suite, lifecycle state, and release record. A specialization is a declared focus, not an artificial restriction on useful general capabilities.

## Family membership

A model is a vectolith family member when it:
1. Implements the applicable shared identity and behavioural contract.
2. Publishes a versioned manifest and machine-readable capabilities.
3. Uses compatible task, message, result, and delegation contracts.
4. Passes family-wide safety, instruction-following, interoperability, and disclosure evaluations.
5. Has its own evidence-backed release decision and model card.

The family does not require identical foundations, architectures, tokenizers, processors, context lengths, or modalities. Compatibility must be declared and tested rather than assumed.

## Initial members

- **Core Prime:** general-purpose reasoning, conversation, instruction following, planning, synthesis, and user-facing coordination.
- **Core Prima:** coding, software engineering, architecture, debugging, technical design, testing, and technical execution.

These are the initial specialization baselines. Future models may focus on research, mathematics, vision, audio, translation, data analysis, security research, or other areas. Examples are illustrative, not a closed roadmap.

## Independent model lifecycle

Each model progresses independently through experimental, development, evaluation, released, deprecated, and retired states. Promotion requires model-specific evaluations plus family-wide gates. A model must not inherit another model's release status, benchmark claims, or training evidence.

Training objectives, data curation, optimization, and specialist evaluations should be designed for the intended ability. More training data or a larger checkpoint alone does not establish a new specialization or a superior model.

## Runtime integration

The runtime discovers models through manifests and a central registry. It must not hardcode a two-model roster or use model names as the only routing signal. Routing should consider requested capabilities, modality compatibility, lifecycle/release policy, runtime constraints, permissions, and evaluation-backed suitability.

Registry storage and model serving are separate concerns. A registered manifest does not imply weights are available, loaded, released, or executable. The serving adapter and runtime must verify those states independently.
