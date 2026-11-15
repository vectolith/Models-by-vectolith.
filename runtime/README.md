# Vectolith Runtime — reference implementation

This package is the first executable foundation for the reusable vectolith orchestration layer. It is model- and provider-neutral: application integrations register model executors and a review function rather than depending on a particular model architecture or vendor SDK.

## Current capabilities

- Versioned task request/result contracts.
- Distinct Core Prime and Core Prima model roles.
- Async model-executor routing.
- In-memory task lifecycle and event history.
- Tool registry with per-task allowlists and explicit approval gates.
- Completion evidence requirement.
- Independent review hook before a completed result is accepted.
- Honest handling of executor exceptions, cancellation, missing evidence, and rejected review.

## Quick start

Python 3.11+ is required.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Integrations provide provider-specific model adapters implementing the async executor contract and a Core Prime review adapter. The runtime itself does not contain model weights, credentials, provider API clients, or a production database.

## Important limitations

This is an initial reference implementation, not a production-ready autonomous agent platform. Task state is in-memory and is lost on process restart. Durable persistence, distributed workers, authentication/tenant isolation, secret management, policy-engine integration, approval UI, sandboxed tool execution, observability exporters, retries/deadlines, and production adapter implementations remain future work. Never expose unrestricted credentials to model executors.

See the canonical [runtime architecture](../docs/runtime-architecture.md) and [delegated execution contract](../docs/delegated-execution-contract.md).
