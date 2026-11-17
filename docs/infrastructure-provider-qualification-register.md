# Infrastructure provider qualification register

**Assessment date:** 2026-11-17  
**Scope:** GPU compute and execution infrastructure for Models by vectolith  
**Decision:** No remote compute provider is approved yet. Public documentation review is not proof of account eligibility, capacity, payment acceptance, or a Vectolith service entitlement.

## Candidate summary

| Candidate | Current state | What public evidence establishes | Blocking evidence |
|---|---|---|---|
| RunPod Secure Cloud Pods | discovered; preferred candidate for account/access verification | On-demand GPU Pods, 30+ regions across the US, Europe, Asia and Australia, per-second billing, and published GPU prices | Nigerian account/payment eligibility, actual region inventory, Secure Cloud entitlement, final price/quota, data-processing terms and support/SLA are unverified |
| Lambda Cloud | blocked for Nigeria-based billing | Public GPU instances and published hourly prices | Lambda's billing documentation currently excludes Nigeria from supported purchase regions; it also says prepaid/debit cards are not accepted |
| NVIDIA DGX Cloud Lepton | discovered; access unverified | NeMo-Run has a Lepton executor and documents its setup requirements | Authenticated Lepton workspace, node-group entitlement, GPU capacity, remote storage and pricing/contract are not available as evidence |

No provider API has been called, no account has been connected, and no instance has been provisioned.

## Candidate evidence

### 1. RunPod Secure Cloud

Official evidence:
- [GPU pricing](https://www.runpod.io/pricing) — updated 2026-11-12. Secure Cloud list prices include L40S at $1.09/GPU-hour and H100 PCIe at $2.89/GPU-hour. Actual quote depends on SKU, region, inventory and storage; re-check in the console immediately before deployment.
- [Cloud GPU overview](https://www.runpod.io/product/cloud-gpus) — describes 31 global regions across the US, Europe, Asia and Australia and per-second billing.
- [Billing overview](https://github.com/runpod/docs/blob/main/accounts-billing/billing.mdx) — says RunPod accepts Visa, Mastercard, American Express and other Stripe-supported cards; prepaid cards require at least $100 per transaction; cryptocurrency is accepted through integrated processors subject to any required KYC; business invoicing is available for transactions above $5,000. It documents a default $80/hour account spend limit.
- [REST API v2 overview](https://www.runpod.io/blog/runpods-rest-api-v2-is-here-one-api-for-your-entire-gpu-stack) — API v2 is the current integration target and was described as public beta on 2026-08-25. It covers Pods, templates, volumes, GPU/data-center catalog and billing.
- [REST API v1 deprecation notice](https://github.com/runpod/docs/blob/main/api-reference/overview.mdx) — v1 was scheduled for retirement on 2026-11-15, which has passed as of this register's assessment date. Do not build new integrations on v1.
- [RunPod API MCP setup](https://github.com/runpod/docs/blob/main/get-started/mcp-servers.mdx) — official hosted MCP at https://mcp.runpod.io/ supports Sign in with RunPod OAuth, or API-key authentication. OAuth approval must be initiated by the account holder.
- [Terms of Service](https://www.runpod.io/legal/terms-of-service) — customer remains responsible for securing data, workloads and guest environments.

Assessment:
- Keep Secure Cloud as the candidate tier. Do not use Community Cloud for Vectolith training data until the third-party host, isolation, support and data-handling implications have been separately reviewed.
- The public region list does not establish a Nigeria-based region or prove that a Nigerian customer can pass account/payment checks. The country-code option is a placement control, not evidence of Nigerian billing eligibility.
- Published prices are indicative only. The final hourly rate, storage charges, taxes, network costs, GPU availability and payment acceptance must be checked in the authenticated account.
- New automation must target REST API v2, not v1. v2 was still described as public beta in RunPod's August 2026 announcement; pin and validate against the live OpenAPI specification before production use.
- RunPod documents a hosted MCP with OAuth. That is the intended account-connection path if available in this ChatGPT environment; the account holder must still approve OAuth. An API key must never be pasted into chat or committed to GitHub.
- No customer-data approval is granted by this assessment. Start only with synthetic/non-sensitive test data after the legal, security and data-handling review.

**Qualification state: discovered, not approved.** Next evidence required: successful account onboarding and billing from the actual account holder's country, an available Secure Cloud datacenter and exact GPU SKU, current quote/quota, data-processing/retention terms, support path, and a controlled test instance with a verified cleanup and cost report. The official hosted MCP OAuth path is documented, but no RunPod connector is currently exposed in this ChatGPT session.

### 2. Lambda Cloud

Official evidence:
- [GPU pricing](https://lambda.com/pricing) — lists public-cloud instance options and prices, including V100, A100, H100 and B200 configurations.
- [Managing billing](https://docs.lambda.com/public-cloud/manage-billing/) — says Lambda currently supports purchases only from a specified list of regions, which does not include Nigeria. It also states that Lambda accepts major credit cards, not prepaid or debit cards, and performs a $10 pre-authorization.

Assessment:

**Qualification state: blocked for Nigeria-based billing at the time of this review.** Reassess only if Lambda changes its supported-country policy or Vectolith has a separately eligible billing entity and account that complies with its terms. Do not attempt to bypass the country or payment restrictions.

### 3. NVIDIA DGX Cloud Lepton

Official evidence:
- [NeMo-Run Lepton executor](https://docs.nvidia.com/nemo/run/nightly/guides/executors/lepton.html) — requires the Lepton CLI to be installed and authenticated, a node group with sufficient GPU capacity, and remote storage accessible to job pods.
- [Nemotron environment profiles and executors](https://docs.nvidia.com/nemotron/latest/train-models/how-to/env-and-executors.html) — describes NeMo-Run execution profiles and local, Slurm, Lepton and other configured backends.

Assessment:

**Qualification state: discovered, access unverified.** The integration is technically relevant to Nemotron, but public documentation is not a capacity grant. Require a real workspace, node-group availability, quota, pricing/contract, region, data-handling terms and an approved Vectolith adapter before qualification.

## Qualification gates before any paid workload

1. **Identity and eligibility:** confirm the legal account holder, country, account verification and payment method are accepted without geographic workarounds.
2. **Capacity:** verify exact GPU model/VRAM, region, availability, quota, maximum runtime and storage.
3. **Economics:** record the exact hourly rate, billing granularity, storage, egress, tax, minimum charge and an explicit run budget.
4. **Security and data governance:** review data location, retention/deletion, encryption, isolation, access control, network exposure, support and incident terms. Use synthetic data until approval.
5. **Execution compatibility:** pin the container image, CUDA/driver, framework, Nemotron revision, foundation model revision and tokenizer revision; run preflight and a no-training environment smoke test first.
6. **Artifact portability:** export logs, checkpoints and run metadata to Vectolith-controlled storage with content hashes and restore verification.
7. **Cost controls:** require a host-verified budget reference, operator approval, automatic stop/termination, and a tested cleanup path.

## Current operating decision

- Local CPU remains the development and contract-test environment.
- RunPod Secure Cloud is the first candidate to verify for a small, bounded GPU smoke test, but it is not approved or connected.
- Lambda is excluded for the current Nigeria-based billing context.
- DGX Cloud Lepton remains an unverified enterprise/contracted option.
- Do not run model training until the foundation model, dataset, evaluation gates, compute budget and provider qualification are all approved.
