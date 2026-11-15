"""Minimal safe orchestration core; integrations supply model and tool adapters."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Protocol

from .contracts import ModelRole, TaskRequest, TaskResult, TaskStatus, TERMINAL_STATUSES


class PermissionDenied(PermissionError):
    pass


class ApprovalRequired(PermissionError):
    pass


class ModelExecutor(Protocol):
    async def __call__(self, task: TaskRequest) -> TaskResult: ...


class Reviewer(Protocol):
    async def __call__(self, task: TaskRequest, result: TaskResult) -> bool: ...


@dataclass(slots=True)
class TaskRecord:
    request: TaskRequest
    status: TaskStatus = TaskStatus.RECEIVED
    events: list[dict[str, str]] = field(default_factory=list)
    result: TaskResult | None = None


class TaskStore:
    """In-memory reference store. Production adapters should use durable storage."""

    def __init__(self) -> None:
        self._records: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()

    async def create(self, request: TaskRequest) -> TaskRecord:
        async with self._lock:
            if request.task_id in self._records:
                raise ValueError(f"duplicate task_id: {request.task_id}")
            record = TaskRecord(request=request)
            self._records[request.task_id] = record
            self._event(record, TaskStatus.RECEIVED, "task accepted")
            return record

    async def get(self, task_id: str) -> TaskRecord:
        async with self._lock:
            return self._records[task_id]

    async def transition(self, task_id: str, status: TaskStatus, detail: str) -> TaskRecord:
        async with self._lock:
            record = self._records[task_id]
            if record.status in TERMINAL_STATUSES:
                raise ValueError("terminal task cannot transition")
            record.status = status
            self._event(record, status, detail)
            return record

    async def set_result(self, task_id: str, result: TaskResult) -> TaskRecord:
        async with self._lock:
            record = self._records[task_id]
            if result.task_id != task_id:
                raise ValueError("result task_id does not match request")
            record.result = result
            record.status = result.status
            self._event(record, result.status, result.summary)
            return record

    @staticmethod
    def _event(record: TaskRecord, status: TaskStatus, detail: str) -> None:
        record.events.append({"status": status.value, "detail": detail})


class ToolRegistry:
    """Executes registered tools only within the task's declared permission scope."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Awaitable[object]]] = {}

    def register(self, name: str, handler: Callable[..., Awaitable[object]]) -> None:
        if not name or name in self._tools:
            raise ValueError("tool name must be unique and non-empty")
        self._tools[name] = handler

    async def invoke(
        self,
        task: TaskRequest,
        name: str,
        *,
        approved: bool = False,
        **arguments: object,
    ) -> object:
        if name not in task.allowed_tools:
            raise PermissionDenied(f"tool not permitted for task: {name}")
        if name in task.approval_required_tools and not approved:
            raise ApprovalRequired(f"explicit approval required for tool: {name}")
        if name not in self._tools:
            raise LookupError(f"tool is not registered: {name}")
        return await self._tools[name](**arguments)


class VectolithRuntime:
    """Routes tasks to model executors and requires evidence plus Prime review."""

    def __init__(
        self,
        executors: dict[ModelRole, ModelExecutor],
        reviewer: Reviewer,
        store: TaskStore | None = None,
    ) -> None:
        self.executors = executors
        self.reviewer = reviewer
        self.store = store or TaskStore()

    async def delegate(self, request: TaskRequest) -> TaskResult:
        if request.assigned_model not in self.executors:
            raise LookupError(f"no executor registered for {request.assigned_model.value}")
        await self.store.create(request)
        await self.store.transition(request.task_id, TaskStatus.DELEGATED, "assigned to model executor")
        await self.store.transition(request.task_id, TaskStatus.RUNNING, "execution started")
        try:
            result = await self.executors[request.assigned_model](request)
        except asyncio.CancelledError:
            await self.store.set_result(
                request.task_id,
                TaskResult(request.task_id, TaskStatus.CANCELLED, "execution cancelled"),
            )
            raise
        except Exception as exc:
            failed = TaskResult(
                request.task_id,
                TaskStatus.FAILED,
                "executor raised an exception",
                unresolved_issues=(f"{type(exc).__name__}: {exc}",),
            )
            await self.store.set_result(request.task_id, failed)
            return failed

        if result.task_id != request.task_id:
            failed = TaskResult(
                request.task_id, TaskStatus.FAILED,
                "executor returned a mismatched task identifier",
                unresolved_issues=("task_id mismatch",),
            )
            await self.store.set_result(request.task_id, failed)
            return failed

        if result.status != TaskStatus.COMPLETED:
            if result.status not in {
                TaskStatus.PARTIALLY_COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:
                invalid = TaskResult(
                    request.task_id, TaskStatus.FAILED,
                    "executor returned an invalid terminal status",
                    unresolved_issues=(f"invalid status: {result.status.value}",),
                )
                await self.store.set_result(request.task_id, invalid)
                return invalid
            await self.store.set_result(request.task_id, result)
            return result

        await self.store.transition(request.task_id, TaskStatus.VERIFYING, "checking evidence and acceptance")
        if not result.evidence:
            failed = TaskResult(
                request.task_id, TaskStatus.PARTIALLY_COMPLETED,
                "executor claimed completion without verification evidence",
                deliverables=result.deliverables,
                tests=result.tests,
                unresolved_issues=("verification evidence missing",),
                assumptions=result.assumptions,
            )
            await self.store.set_result(request.task_id, failed)
            return failed

        try:
            reviewed = await self.reviewer(request, result)
        except Exception as exc:
            reviewed = False
            review_issue = f"reviewer raised {type(exc).__name__}: {exc}"
        else:
            review_issue = "Core Prime review did not approve completion"
        if not reviewed:
            rejected = TaskResult(
                request.task_id, TaskStatus.PARTIALLY_COMPLETED,
                "independent review did not approve completion",
                deliverables=result.deliverables,
                tests=result.tests,
                evidence=result.evidence,
                unresolved_issues=(review_issue,),
                assumptions=result.assumptions,
            )
            await self.store.set_result(request.task_id, rejected)
            return rejected

        await self.store.set_result(request.task_id, result)
        return result
