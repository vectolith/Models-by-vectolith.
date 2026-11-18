# Model-side runtime and optional integration architecture

## Purpose

This document describes the boundary between model specifications in this repository and the application runtimes operated by products that may choose to use a model from this family.

This repository does not own or require a shared Vectolith application runtime. Each Vectolith product is independently responsible for its own runtime, user identity, authentication, authorization, orchestration, tool execution, state, storage, observability, deployment, and release process. A product must remain buildable, deployable, and useful for its core purpose without this repository or any model published here.

## Model boundary

A model interprets input and produces outputs or structured proposals according to its published interface. The consuming application remains authoritative for:

- user authentication and authorization;
- tenant isolation and data access;
- tool registration, credential scope, and tool execution;
- approval requirements for consequential actions;
- task state, retries, cancellation, deadlines, and resource limits;
- validation of model output and all external side effects;
- evidence collection, audit logging, and completion status.

A model response is untrusted input to the consuming application. The application must validate schemas, enforce permissions independently, and never treat model-generated text as proof that an action occurred.

## Optional integration contract

A product may optionally connect to a released model through a documented API, SDK, or adapter. Any such integration must:

1. Be explicitly enabled and configured by that product.
2. Be replaceable with another provider or disabled without preventing the product from starting or performing its non-model core functions.
3. Use versioned request and response schemas with validation at the application boundary.
4. Apply product-owned authentication, authorization, rate limits, privacy controls, and data-retention rules.
5. Avoid sharing credentials, databases, user sessions, or private state with another Vectolith product.
6. Fail closed for consequential actions when model output is invalid, unavailable, or unverifiable.
7. Be tested by the consuming product independently of this repository's training and evaluation pipelines.

No downstream consumer is presumed. No other Vectolith product is required to adopt this model family or any runtime described here.

## Model family operations

Model training, evaluation, artifact storage, model registry publication, and model release are owned and operated within this repository's own lifecycle. Teacher models may be used during training and evaluation under documented provenance and licensing constraints. Released student models must serve inference without requiring teacher inference.

## Security boundaries

- Do not embed application credentials or unrestricted tool credentials in model weights or prompts.
- Do not let model output expand application permissions.
- Keep user data and model-training data separated according to the applicable privacy and consent requirements.
- Minimize sensitive context sent to external inference providers.
- Record enough provenance to identify the model revision and interface version used for an inference.
- Treat model outputs, tool arguments, retrieved content, and external responses as untrusted until validated.

## Completion semantics

A model cannot establish that a user task is complete merely by generating a plausible response. The consuming application must verify its own acceptance criteria and side effects. If verification is unavailable or fails, the consuming application must report a non-complete state.

## Integration readiness

This repository's optional model interface is ready for adoption only when published schemas, compatibility guarantees, model revision identifiers, licence terms, and reproducible conformance tests are available. Each consumer must independently test its adapter, failure handling, privacy boundary, and operational behaviour before enabling the integration.
