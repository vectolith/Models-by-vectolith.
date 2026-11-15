"""Versioned, model-neutral contracts for delegated task execution."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


CONTRACT_VERSION = "1.0"


class ModelRole(StrEnum):
    CORE_PRIME = "core_prime"
    CORE_PRIMA = "core_prima"


class TaskStatus(StrEnum):
    RECEIVED = "received"
    UNDERSTOOD = "understood"
    PLANNED = "planned"
    DELEGATED = "delegated"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.PARTIALLY_COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
}


@dataclass(frozen=True, slots=True)
class TaskRequest:
    task_id: str
    requester_model: ModelRole
    assigned_model: ModelRole
    user_request: str
    objective: str
    requirements: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    allowed_tools: frozenset[str] = frozenset()
    approval_required_tools: frozenset[str] = frozenset()
    context: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be empty")
        if not self.user_request.strip() or not self.objective.strip():
            raise ValueError("user_request and objective must not be empty")
        if not self.approval_required_tools.issubset(self.allowed_tools):
            raise ValueError("approval-required tools must also be allowed")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["requester_model"] = self.requester_model.value
        data["assigned_model"] = self.assigned_model.value
        data["allowed_tools"] = sorted(self.allowed_tools)
        data["approval_required_tools"] = sorted(self.approval_required_tools)
        data["contract_version"] = self.contract_version
        return data


@dataclass(frozen=True, slots=True)
class TaskResult:
    task_id: str
    status: TaskStatus
    summary: str
    deliverables: tuple[str, ...] = ()
    tests: tuple[dict[str, Any], ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved_issues: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status == TaskStatus.COMPLETED and self.unresolved_issues:
            raise ValueError("completed result cannot contain unresolved issues")
        if self.status == TaskStatus.COMPLETED and not self.evidence:
            raise ValueError("completed result requires verification evidence")
