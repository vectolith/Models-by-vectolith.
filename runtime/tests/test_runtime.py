import unittest

from vectolith_runtime import (
    ApprovalRequired,
    ModelRole,
    PermissionDenied,
    TaskRequest,
    TaskResult,
    TaskStatus,
    ToolRegistry,
    VectolithRuntime,
)


def request(task_id="task-1", *, allowed=frozenset(), approval=frozenset()):
    return TaskRequest(
        task_id=task_id,
        requester_model=ModelRole.CORE_PRIME,
        assigned_model=ModelRole.CORE_PRIMA,
        user_request="Build a small application",
        objective="Implement the requested application",
        requirements=("Preserve the user requirements",),
        acceptance_criteria=("Tests pass",),
        allowed_tools=allowed,
        approval_required_tools=approval,
    )


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_requires_evidence_and_prime_review(self):
        async def prima(task):
            return TaskResult(task.task_id, TaskStatus.COMPLETED, "implemented", ("app/",), evidence=("tests passed",))

        async def prime_review(task, result):
            return True

        runtime = VectolithRuntime({ModelRole.CORE_PRIMA: prima}, prime_review)
        result = await runtime.delegate(request())
        self.assertEqual(result.status, TaskStatus.COMPLETED)
        record = await runtime.store.get("task-1")
        self.assertEqual(record.events[-2]["status"], "verifying")
        self.assertEqual(record.status, TaskStatus.COMPLETED)

    async def test_no_evidence_cannot_be_completed(self):
        async def prima(task):
            return TaskResult(task.task_id, TaskStatus.COMPLETED, "done")

        async def review(task, result):
            return True

        runtime = VectolithRuntime({ModelRole.CORE_PRIMA: prima}, review)
        result = await runtime.delegate(request())
        self.assertEqual(result.status, TaskStatus.PARTIALLY_COMPLETED)
        self.assertIn("verification evidence missing", result.unresolved_issues)

    async def test_prime_review_can_reject_completion(self):
        async def prima(task):
            return TaskResult(task.task_id, TaskStatus.COMPLETED, "done", evidence=("build log",))

        async def review(task, result):
            return False

        runtime = VectolithRuntime({ModelRole.CORE_PRIMA: prima}, review)
        result = await runtime.delegate(request())
        self.assertEqual(result.status, TaskStatus.PARTIALLY_COMPLETED)

    async def test_executor_failure_is_reported(self):
        async def prima(task):
            raise RuntimeError("compiler failed")

        async def review(task, result):
            return True

        runtime = VectolithRuntime({ModelRole.CORE_PRIMA: prima}, review)
        result = await runtime.delegate(request())
        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertIn("compiler failed", result.unresolved_issues[0])

    async def test_tool_permissions_and_approval_are_enforced(self):
        registry = ToolRegistry()

        async def deploy(**kwargs):
            return "deployed"

        registry.register("deploy", deploy)
        with self.assertRaises(PermissionDenied):
            await registry.invoke(request(), "deploy")
        restricted = request(allowed=frozenset({"deploy"}), approval=frozenset({"deploy"}))
        with self.assertRaises(ApprovalRequired):
            await registry.invoke(restricted, "deploy")
        self.assertEqual(await registry.invoke(restricted, "deploy", approved=True), "deployed")

    async def test_duplicate_task_ids_are_rejected(self):
        async def prima(task):
            return TaskResult(task.task_id, TaskStatus.FAILED, "not run")

        async def review(task, result):
            return False

        runtime = VectolithRuntime({ModelRole.CORE_PRIMA: prima}, review)
        await runtime.store.create(request())
        with self.assertRaises(ValueError):
            await runtime.delegate(request())


if __name__ == "__main__":
    unittest.main()
