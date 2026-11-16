# Teacher infrastructure contribution system

**Status:** normative architecture and qualification specification  
**Version:** 1.0  
**Applies to:** Models by vectolith; active student track: Core Prime

## 1. Purpose

Teacher providers may contribute useful infrastructure as well as model outputs and training knowledge. Vectolith must be able to discover, evaluate, integrate and replace these contributions without transferring ownership of its control plane to any teacher or provider.

This specification establishes an infrastructure-contribution track alongside (not inside) model-teacher qualification. A provider may be useful as an infrastructure source even when its model is not an appointed teacher. Conversely, a qualified teaching model does not automatically grant access to its provider's compute, software, hosted services or support.

**No provider contribution is presumed.** Public code, documentation and published recipes are reusable references subject to their licenses. Compute, hosted endpoints, credits, private support and service access require separately verified availability, account entitlement, terms and explicit authorization.

## 2. Contribution classes

Each contribution is registered independently and may have one or more classes:

| Class | Examples | Evidence required |
|---|---|---|
| Compute capacity | GPU/CPU instances, clusters, storage, network | Actual entitlement, region/availability, quota, hardware, price/credits, duration and operator authorization |
| Training framework | PyTorch, NeMo, trainer libraries, distributed runtimes | Exact package/revision, license, supported model/method matrix, compatibility tests |
| Orchestration | Local, Docker, Slurm, Kubernetes, cloud job schedulers | Executor capabilities, lifecycle semantics, cancellation, logs and resource accounting |
| Data infrastructure | Curation, storage, tokenization, deduplication, dataset versioning | Data handling, access controls, provenance, retention and reproducibility |
| Evaluation infrastructure | Benchmark harnesses, graders, sandbox runners | Suite/version, isolation, reproducibility, validity and holdout protections |
| Model serving | Inference engines, batching, quantization, routing | Supported architectures, tokenizer compatibility, latency/memory measurements and security |
| Observability/artifacts | Metrics, logs, checkpoint stores, experiment tracking | Exportability, immutable identifiers, retention, access controls and cost |
| Engineering reference | Open-source implementations, technical docs, recipes | Source URL/revision, license/terms, provenance and a documented adaptation rationale |

Do not treat a provider's marketing statement or model card as proof that a resource is available to Vectolith.

## 3. Provider and contribution records

Keep provider identity separate from individual contributions. One provider may offer several independently versioned contributions; the same contribution type may have several competing providers.

A provider record should contain:
- stable provider ID, display name, official domains and provider category;
- relationship state: discovered, reviewed, approved, suspended or retired;
- legal/terms review reference and responsible reviewer;
- security/contact and incident process where applicable;
- no credentials, access tokens or private account identifiers.

A contribution record should contain:
- unique contribution ID and provider ID;
- class, purpose, description and exact product/package/service;
- immutable source revision, package version or service/API version where applicable;
- source URL and license/terms identifier, plus permitted use and redistribution notes;
- access mode: public-reference, locally-installed, self-hosted, provider-hosted or provisioned-capacity;
- capability declaration and supported/unsupported matrix;
- required hardware, software, network, region and dependencies;
- price, quota, credits and billing assumptions, marked unknown when not verified;
- data categories sent to or retained by the provider, retention/deletion terms and privacy review;
- qualification status, evidence artifact hashes, evaluator and timestamp;
- adapter ID/version, contract version, operational owner and deprecation/replacement status.

Credentials and secret material belong only in an approved secret manager. Manifests contain secret references, never secret values.

## 4. Qualification is contribution-specific

A contribution moves through:

`discovered → documented → legal_review → security_review → compatibility_test → cost_review → approved`

It may instead become `blocked`, `rejected`, `suspended` or `retired`. Missing evidence is a block, not an implicit pass. Approval is scoped to the exact revision, service, use case, data class and environment reviewed. Material changes require requalification.

Minimum checks:
1. **Provenance:** exact source, publisher, revision and artifact digest are recorded.
2. **Rights:** license and terms permit the intended use, modification, deployment and redistribution (where relevant).
3. **Security:** dependencies, permissions, network egress, secret handling, isolation and data exposure are reviewed.
4. **Compatibility:** deterministic contract tests verify declared capabilities and failure behavior.
5. **Operations:** health, observability, cancellation, retry, recovery, export and rollback behavior are understood.
6. **Economics:** real price, quota, credits, usage limits and expected cost are recorded; unknown values remain unknown.
7. **Data governance:** payloads, retention, region, training use, deletion and access controls are explicitly assessed.
8. **Portability:** artifacts and records can be exported in Vectolith-owned formats, or the lock-in is explicitly documented and accepted.

A provider can pass one class and fail another. For example, its open-source framework may be approved while its hosted API or compute offer remains unapproved.

## 5. Vectolith-owned adapter boundary

All external infrastructure is accessed through Vectolith-owned interfaces. Provider SDKs, APIs and configuration formats remain inside adapters.

A compute/execution adapter should expose:
- capability discovery and preflight validation;
- resource estimate and explicit cost/quota disclosure;
- submit, status, logs, cancel and cleanup operations;
- artifact/checkpoint export with content hashes;
- hardware/runtime inventory and job provenance;
- bounded retries, timeout behavior and normalized failure states.

A training-framework adapter should expose:
- supported architectures, tokenizers, methods and precision modes;
- immutable trainer/package revision and configuration snapshot;
- input validation, bounded execution and checkpoint export;
- normalized metrics, logs and reproducibility metadata.

A serving adapter should expose:
- model/runtime compatibility, tokenizer and modality requirements;
- health/readiness, inference, timeout and cancellation behavior;
- resource/latency telemetry and normalized errors;
- explicit isolation of serving credentials from training and student inference.

Adapters must not change Vectolith's model identity, task/message contracts, teacher qualification decisions, safety policy, dataset ownership, evaluation gates or release lifecycle. Provider-specific fields are namespaced and cannot silently redefine canonical fields.

## 6. Reference architecture

```text
                 MODELS BY VECTOLITH
                          |
                VECTOLITH CONTROL PLANE
                          |
       +------------------+------------------+
       |                  |                  |
  Model Registry     Data & Lineage      Evaluation
       |                  |                  |
       +------------------+------------------+
                          |
               Infrastructure Broker
                          |
             Capability + Policy Routing
                          |
       +------------------+------------------+
       |                  |                  |
    Compute           Training            Serving
    Adapters          Adapters            Adapters
       |                  |                  |
   Local/Docker     NeMo/PyTorch        vLLM/other
   Cloud/Slurm      other frameworks    engines
       |                  |                  |
       +------------------+------------------+
                          |
             Provider contribution registry
                          |
       NVIDIA | cloud vendors | open source | others
```

The broker selects only approved contributions that satisfy the job's architecture, method, hardware, region, security, data and budget constraints. Selection is evidence-based and policy-controlled, not based on teacher ranking or provider popularity.

## 7. Relationship to teacher qualification

Maintain two independent records and decisions:

- **Teacher qualification:** Is this exact model revision permitted and demonstrably useful for generating training targets in specified competencies?
- **Infrastructure qualification:** Is this exact software, service or resource approved to perform a specified infrastructure function?

Do not let either decision imply the other. A teacher model can be disqualified while its open-source training framework remains approved. A cloud provider can supply GPU capacity without being a teacher. Infrastructure access does not count toward the minimum number of distinct qualified teachers, and teacher count does not satisfy compute requirements.

Teacher outputs, datasets and infrastructure artifacts retain separate provenance. A training run records both the teacher-panel revision IDs and the infrastructure contribution IDs/revisions actually used.

## 8. Dependency and portability policy

- Prefer stable, open interfaces and replaceable adapters over importing an entire provider stack into the core runtime.
- Keep provider SDKs optional extras or isolated worker images; pin exact versions and hashes.
- Do not make a provider-specific control plane the source of truth for model manifests, run state, datasets or evaluation.
- Export run manifests, logs, metrics, checkpoints and evaluation reports into Vectolith-defined formats.
- Keep a local/mock adapter for deterministic tests and development without network access or paid compute.
- Maintain at least one viable fallback path for critical capabilities where practical; document cases where no fallback exists.
- No adapter import may trigger network access, downloads, account discovery, job submission or billing.
- A real job requires explicit operator approval after preflight, budget check and access verification.

NeMo/Nemotron is a candidate reference and optional training/execution adapter, not a required dependency. Its specific capabilities must be pinned and verified against the selected release. Other providers and open-source projects are evaluated under the same contribution contract.

## 9. Initial implementation sequence

**Initial reference milestone status:** versioned provider and contribution JSON Schemas, in-memory metadata registry, fail-closed qualification blocker checks, adapter protocol, and deterministic mock compute lifecycle are implemented in `runtime/vectolith_runtime/infrastructure.py`. CPU-only unit tests cover registry, qualification and mock submit/status/cancel. These components do not provision resources or contact providers. SQLite persistence, schema-validator integration, production adapters and remote execution remain future work.



1. Add versioned provider and contribution schemas with valid/invalid fixtures.
2. Add a registry interface and SQLite persistence that stores metadata only, never secrets.
3. Implement qualification state transitions and fail-closed validators.
4. Define provider-neutral compute, training and serving adapter protocols.
5. Add deterministic local/mock adapters and contract tests for success, timeout, cancellation, partial failure and artifact export.
6. Add a NeMo adapter spike behind an optional extra only after the contract tests exist; compare it with at least one non-NeMo path before adopting it.
7. Add cost/quota preflight and explicit approval before any remote execution.
8. Add provenance links from every training run to the exact approved contributions it used.

The first milestone must be CPU-only and network-free. It must not download model weights, provision cloud resources, invoke teacher APIs or start training.

## 10. Acceptance criteria

The contribution system is ready for its first implementation milestone when:
- schemas reject unknown required versions, missing provenance and invalid lifecycle transitions;
- teacher qualification and infrastructure qualification can be independently approved or blocked;
- mock adapters pass deterministic contract tests without external services;
- a run manifest records exact contribution IDs/revisions and resource observations;
- secrets never appear in records, logs, fixtures or repository files;
- no import-time network, provider, download, compute or billing side effects exist;
- a provider can be replaced without changing the canonical model registry, task contracts, dataset format or evaluation report;
- tests prove that unapproved, expired, incompatible or over-budget contributions cannot be scheduled.

No actual provider capacity, credits, hosted service access or infrastructure donation is claimed by this specification.
