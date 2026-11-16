import subprocess
import tempfile
import unittest
from pathlib import Path

from vectolith_runtime.adapters.nemotron_cli import NemotronCLIAdapter, NemotronStepRequest


class FakeRunner:
    def __init__(self, results=None):
        self.calls = []
        self.results = list(results or [])

    def __call__(self, args, **kwargs):
        self.calls.append((list(args), kwargs))
        if self.results:
            return self.results.pop(0)
        return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")


class NemotronCLIAdapterTests(unittest.TestCase):
    def test_preflight_is_local_and_does_not_execute_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeRunner()
            adapter = NemotronCLIAdapter(
                working_directory=directory, runner=runner, command_exists=lambda _: True
            )
            self.assertEqual(adapter.preflight(NemotronStepRequest("sft/automodel")), ())
            self.assertEqual(runner.calls, [])

    def test_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = NemotronCLIAdapter(
                working_directory=directory, runner=FakeRunner(), command_exists=lambda _: True
            )
            with self.assertRaises(PermissionError):
                adapter.run_step(NemotronStepRequest("sft/automodel"))

    def test_runs_show_then_attached_step_without_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeRunner()
            adapter = NemotronCLIAdapter(
                working_directory=directory, runner=runner, command_exists=lambda _: True
            )
            result = adapter.run_step(
                NemotronStepRequest("sft/automodel", "tiny", "local_cpu", resource_budget_ref="budget:local-cpu"),
                approved=True,
                approval_ref="change-control:42",
            )
            self.assertEqual(
                runner.calls[0][0], ["nemotron", "steps", "show", "sft/automodel"]
            )
            self.assertEqual(
                runner.calls[1][0],
                ["nemotron", "steps", "run", "sft/automodel", "-c", "tiny", "-r", "local_cpu"],
            )
            self.assertFalse(runner.calls[1][1].get("shell", False))
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.execution_profile, "local_cpu")
            self.assertEqual(result.approval_ref, "change-control:42")

    def test_environment_profile_is_passed_by_environment_variable(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / "env.toml"
            env_file.write_text("[local]\nexecutor='local'\n", encoding="utf-8")
            runner = FakeRunner()
            adapter = NemotronCLIAdapter(
                working_directory=directory, runner=runner, command_exists=lambda _: True
            )
            adapter.run_step(
                NemotronStepRequest("sft/automodel", environment_file="env.toml"),
                approved=True,
                approval_ref="change-control:43",
            )
            self.assertEqual(
                runner.calls[1][1]["env"]["NEMOTRON_ENV_FILE"], str(env_file)
            )

    def test_profile_requires_budget_evidence(self):
        with self.assertRaisesRegex(ValueError, "resource_budget_ref"):
            NemotronStepRequest("sft/automodel", execution_profile="remote_gpu")

    def test_rejects_invalid_step_and_missing_environment_file(self):
        with self.assertRaises(ValueError):
            NemotronStepRequest("sft/../../unsafe")
        with tempfile.TemporaryDirectory() as directory:
            adapter = NemotronCLIAdapter(
                working_directory=directory, runner=FakeRunner(), command_exists=lambda _: True
            )
            blockers = adapter.preflight(
                NemotronStepRequest("sft/automodel", environment_file="missing.toml")
            )
            self.assertIn("configured NEMOTRON_ENV_FILE does not exist", blockers)

    def test_nonzero_show_command_prevents_training(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeRunner([
                subprocess.CompletedProcess([], 2, stdout="", stderr="unknown step")
            ])
            adapter = NemotronCLIAdapter(
                working_directory=directory, runner=runner, command_exists=lambda _: True
            )
            with self.assertRaisesRegex(RuntimeError, "unknown step"):
                adapter.run_step(
                    NemotronStepRequest("sft/automodel"),
                    approved=True,
                    approval_ref="change-control:44",
                )
            self.assertEqual(len(runner.calls), 1)


if __name__ == "__main__":
    unittest.main()
