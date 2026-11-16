"""Provider-neutral infrastructure contribution registry and adapter contracts.

This module is metadata-only. It performs no network, provider, download, billing,
or compute operations at import time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from threading import RLock
from typing import Protocol, runtime_checkable


INFRASTRUCTURE_CONTRACT_VERSION = "1.0"


class ContributionClass(StrEnum):
    COMPUTE = "compute"
    TRAINING_FRAMEWORK = "training_framework"
    ORCHESTRATION = "orchestration"
    DATA = "data"
    EVALUATION = "evaluation"
    SERVING = "serving"
    OBSERVABILITY = "observability"
    ENGINEERING_REFERENCE = "engineering_reference"


class AccessMode(StrEnum):
    PUBLIC_REFERENCE = "public_reference"
    LOCALLY_INSTALLED = "locally_installed"
    SELF_HOSTED = "self_hosted"
    PROVIDER_HOSTED = "provider_hosted"
    PROVISIONED_CAPACITY = "provisioned_capacity"


class ProviderState(StrEnum):
    DISCOVERED = "discovered"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class QualificationState(StrEnum):
    DISCOVERED = "discovered"
    DOCUMENTED = "documented"
    LEGAL_REVIEW = "legal_review"
    SECURITY_REVIEW = "security_review"
    COMPATIBILITY_TEST = "compatibility_test"
    COST_REVIEW = "cost_review"
    APPROVED = "approved"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class InfrastructureProvider:
    provider_id: str
    display_name: str
    provider_category: str
    relationship_state: ProviderState = ProviderState.DISCOVERED
    official_domains: tuple[str, ...] = ()
    legal_review_ref: str | None = None
    security_review_ref: str | None = None
    operational_contact_ref: str | None = None

    def __post_init__(self) -> None:
        _required(self.provider_id, self.display_name, self.provider_category)
        if len(set(self.official_domains)) != len(self.official_domains):
            raise ValueError("official_domains must be unique")


@dataclass(frozen=True, slots=True)
class InfrastructureContribution:
    contribution_id: str
    provider_id: str
    contribution_class: ContributionClass
    name: str
    source_revision: str
    license_id: str
    access_mode: AccessMode
    capabilities: frozenset[str]
    qualification_status: QualificationState = QualificationState.DISCOVERED
    source_url: str | None = None
    permitted_use: frozenset[str] = frozenset()
    hardware_requirements: tuple[str, ...] = ()
    region: str | None = None
    price_or_quota_ref: str | None = None
    data_handling_ref: str | None = None
    adapter_id: str | None = None
    adapter_version: str | None = None
    evidence_refs: tuple[str, ...] = ()
    artifact_sha256: str | None = None

    def __post_init__(self) -> None:
        _required(self.contribution_id, self.provider_id, self.name, self.source_revision, self.license_id)
        if not self.capabilities or any(not item.strip() for item in self.capabilities):
            raise ValueError("at least one non-empty capability is required")
        if self.artifact_sha256 is not None and (
            len(self.artifact_sha256) != 64
            or any(ch not in "0123456789abcdef" for ch in self.artifact_sha256)
        ):
            raise ValueError("artifact_sha256 must be a lowercase SHA-256 digest")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("evidence_refs must be unique")


def _required(*values: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("required identifiers and names must be non-empty strings")


def qualification_blockers(
    provider: InfrastructureProvider,
    contribution: InfrastructureContribution,
) -> tuple[str, ...]:
    """Return every unmet approval gate; never infer approval from discovery."""
    blockers: list[str] = []
    if provider.provider_id != contribution.provider_id:
        blockers.append("provider identity does not match contribution")
    if provider.relationship_state != ProviderState.APPROVED:
        blockers.append("provider relationship is not approved")
    if not provider.legal_review_ref:
        blockers.append("provider legal review evidence is missing")
    if not provider.security_review_ref:
        blockers.append("provider security review evidence is missing")
    if contribution.qualification_status != QualificationState.APPROVED:
        blockers.append("contribution qualification status is not approved")
    if not contribution.permitted_use:
        blockers.append("permitted use is not declared")
    if not contribution.evidence_refs:
        blockers.append("qualification evidence is missing")
    if contribution.access_mode in {AccessMode.PROVIDER_HOSTED, AccessMode.PROVISIONED_CAPACITY}:
        if not contribution.price_or_quota_ref:
            blockers.append("verified price or quota evidence is missing")
        if not contribution.data_handling_ref:
            blockers.append("data-handling review evidence is missing")
    return tuple(blockers)


class InfrastructureRegistry:
    """Thread-safe metadata registry; credentials and secret values are not accepted."""

    def __init__(self) -> None:
        self._providers: dict[str, InfrastructureProvider] = {}
        self._contributions: dict[str, InfrastructureContribution] = {}
        self._lock = RLock()

    def register_provider(self, provider: InfrastructureProvider, *, replace: bool = False) -> None:
        with self._lock:
            if provider.provider_id in self._providers and not replace:
                raise ValueError(f"provider already registered: {provider.provider_id}")
            self._providers[provider.provider_id] = provider

    def register_contribution(
        self, contribution: InfrastructureContribution, *, replace: bool = False
    ) -> None:
        with self._lock:
            if contribution.provider_id not in self._providers:
                raise KeyError(f"unknown provider: {contribution.provider_id}")
            if contribution.contribution_id in self._contributions and not replace:
                raise ValueError(f"contribution already registered: {contribution.contribution_id}")
            self._contributions[contribution.contribution_id] = contribution

    def get_provider(self, provider_id: str) -> InfrastructureProvider:
        with self._lock:
            return self._providers[provider_id]

    def get_contribution(self, contribution_id: str) -> InfrastructureContribution:
        with self._lock:
            return self._contributions[contribution_id]

    def list_contributions(
        self, *, contribution_class: ContributionClass | None = None,
        approved_only: bool = False,
    ) -> tuple[InfrastructureContribution, ...]:
        with self._lock:
            items = tuple(self._contributions.values())
        if contribution_class is not None:
            items = tuple(x for x in items if x.contribution_class == contribution_class)
        if approved_only:
            items = tuple(
                x for x in items
                if x.qualification_status == QualificationState.APPROVED
                and self._provider_approved(x.provider_id)
            )
        return tuple(sorted(items, key=lambda x: x.contribution_id))

    def _provider_approved(self, provider_id: str) -> bool:
        provider = self._providers.get(provider_id)
        return bool(provider and provider.relationship_state == ProviderState.APPROVED)


@dataclass(frozen=True, slots=True)
class ComputeRequest:
    job_id: str
    contribution_id: str
    cpu_cores: int = 1
    memory_gb: int = 1
    gpu_count: int = 0
    max_runtime_seconds: int = 60

    def __post_init__(self) -> None:
        _required(self.job_id, self.contribution_id)
        if min(self.cpu_cores, self.memory_gb, self.max_runtime_seconds) < 1 or self.gpu_count < 0:
            raise ValueError("resource requests must be positive (gpu_count may be zero)")


@dataclass(frozen=True, slots=True)
class ComputeJob:
    job_id: str
    contribution_id: str
    state: str
    backend: str
    resources: tuple[tuple[str, int], ...]
    detail: str = ""


@runtime_checkable
class ComputeAdapter(Protocol):
    adapter_id: str

    def preflight(
        self, request: ComputeRequest, contribution: InfrastructureContribution,
        provider: InfrastructureProvider,
    ) -> tuple[str, ...]: ...

    def submit(self, request: ComputeRequest) -> ComputeJob: ...
    def status(self, job_id: str) -> ComputeJob: ...
    def cancel(self, job_id: str) -> ComputeJob: ...


class MockComputeAdapter:
    """Deterministic, in-memory adapter for tests; it never allocates real resources."""

    adapter_id = "vectolith.mock-compute"
    _supported = frozenset({"cpu", "memory", "gpu.mock"})

    def __init__(self) -> None:
        self._jobs: dict[str, ComputeJob] = {}
        self._lock = RLock()

    def preflight(
        self, request: ComputeRequest, contribution: InfrastructureContribution,
        provider: InfrastructureProvider,
    ) -> tuple[str, ...]:
        blockers = list(qualification_blockers(provider, contribution))
        if contribution.contribution_class != ContributionClass.COMPUTE:
            blockers.append("contribution is not compute infrastructure")
        if not {"cpu", "memory"}.issubset(contribution.capabilities):
            blockers.append("mock adapter requires cpu and memory capabilities")
        if contribution.adapter_id != self.adapter_id:
            blockers.append("contribution is not bound to this adapter")
        if request.gpu_count and "gpu.mock" not in contribution.capabilities:
            blockers.append("requested GPU capability is unavailable")
        return tuple(blockers)

    def submit(self, request: ComputeRequest) -> ComputeJob:
        with self._lock:
            if request.job_id in self._jobs:
                raise ValueError(f"job already exists: {request.job_id}")
            job = ComputeJob(
                request.job_id, request.contribution_id, "queued", self.adapter_id,
                (("cpu_cores", request.cpu_cores), ("memory_gb", request.memory_gb),
                 ("gpu_count", request.gpu_count)),
                "mock only; no resources were provisioned",
            )
            self._jobs[request.job_id] = job
            return job

    def status(self, job_id: str) -> ComputeJob:
        with self._lock:
            return self._jobs[job_id]

    def cancel(self, job_id: str) -> ComputeJob:
        with self._lock:
            job = self._jobs[job_id]
            if job.state in {"cancelled", "completed", "failed"}:
                return job
            cancelled = ComputeJob(
                job.job_id, job.contribution_id, "cancelled", job.backend,
                job.resources, "mock cancellation; no resources existed",
            )
            self._jobs[job_id] = cancelled
            return cancelled
