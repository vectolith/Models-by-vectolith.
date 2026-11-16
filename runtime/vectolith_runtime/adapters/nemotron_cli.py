"""Explicit, provider-isolated bridge to NVIDIA Nemotron Steps CLI.

This adapter does not import NeMo/Nemotron Python packages, install dependencies,
contact a provider, provision resources, or start work at import time. A caller
must explicitly approve every training invocation.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence

_STEP_IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./-]*$")
_NAME_IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")


def _valid_step_id(value: str) -> bool:
    return bool(_STEP_IDENTIFIER.fullmatch(value)) and all(
        segment not in {"", ".", ".."} for segment in value.split("/")
    )


@dataclass(frozen=True, slots=True)
class NemotronStepRequest:
    step_id: str
    config: str = "tiny"
    execution_profile: str | None = None
    environment_file: str | None = None
    resource_budget_ref: str | None = None
    timeout_seconds: int = 3600

    def __post_init__(self) -> None:
        if not _valid_step_id(self.step_id):
            raise ValueError(f"invalid Nemotron step_id: {self.step_id!r}")
        if not _NAME_IDENTIFIER.fullmatch(self.config):
            raise ValueError(f"invalid Nemotron config: {self.config!r}")
        if self.execution_profile is not None and not _NAME_IDENTIFIER.fullmatch(self.execution_profile):
            raise ValueError("invalid Nemotron execution profile")
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")
        if self.environment_file is not None and not self.environment_file.strip():
            raise ValueError("environment_file must be a non-empty path")
        if self.execution_profile is not None and not (
            self.resource_budget_ref and self.resource_budget_ref.strip()
        ):
            raise ValueError("profile-based execution requires a verified resource_budget_ref")


@dataclass(frozen=True, slots=True)
class NemotronStepResult:
    command: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    execution_profile: str | None
    approval_ref: str


class CommandRunner(Protocol):
    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: str,
        env: dict[str, str],
        timeout: int,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]: ...


class NemotronCLIAdapter:
    """Run documented Nemotron Steps commands through a bounded subprocess.

    Local runs omit an execution profile. Attached profile runs use the -r flag
    so the process remains observable until completion. Detached -b submission
    is intentionally unsupported until remote job polling and artifact lineage
    are implemented in Vectolith.
    """

    adapter_id = "vectolith.nemotron-steps-cli"

    def __init__(
        self,
        *,
        executable: str = "nemotron",
        working_directory: str | Path,
        runner: CommandRunner = subprocess.run,
        command_exists: Callable[[str], bool] | None = None,
        budget_ref_validator: Callable[[str], bool] | None = None,
    ) -> None:
        if not executable or not executable.strip():
            raise ValueError("executable must be a non-empty command")
        self.executable = executable
        self.working_directory = Path(working_directory).expanduser().resolve()
        self._runner = runner
        self._command_exists = command_exists or (
            lambda command: Path(command).is_file() or shutil.which(command) is not None
        )
        self._budget_ref_validator = budget_ref_validator

    def preflight(self, request: NemotronStepRequest) -> tuple[str, ...]:
        blockers: list[str] = []
        if not self._command_exists(self.executable):
            blockers.append(f"Nemotron CLI executable not found: {self.executable}")
        if not self.working_directory.is_dir():
            blockers.append("Nemotron working directory does not exist")
        if request.execution_profile is not None and (
            self._budget_ref_validator is None
            or not self._budget_ref_validator(request.resource_budget_ref or "")
        ):
            blockers.append("resource budget reference is not verified by the host")
        if request.environment_file is not None:
            env_file = Path(request.environment_file).expanduser()
            if not env_file.is_absolute():
                env_file = self.working_directory / env_file
            if not env_file.is_file():
                blockers.append("configured NEMOTRON_ENV_FILE does not exist")
        return tuple(blockers)

    def run_step(
        self,
        request: NemotronStepRequest,
        *,
        approved: bool = False,
        approval_ref: str | None = None,
    ) -> NemotronStepResult:
        """Execute one attached/local step after explicit operator approval."""
        if not approved or not approval_ref or not approval_ref.strip():
            raise PermissionError(
                "Nemotron execution requires explicit approval and an approval reference"
            )
        blockers = self.preflight(request)
        if blockers:
            raise RuntimeError("Nemotron preflight blocked: " + "; ".join(blockers))

        environment = dict(os.environ)
        if request.environment_file is not None:
            env_file = Path(request.environment_file).expanduser()
            if not env_file.is_absolute():
                env_file = self.working_directory / env_file
            environment["NEMOTRON_ENV_FILE"] = str(env_file)

        show_command = [self.executable, "steps", "show", request.step_id]
        self._invoke(show_command, environment, request.timeout_seconds)

        command = [
            self.executable, "steps", "run", request.step_id, "-c", request.config
        ]
        if request.execution_profile is not None:
            command.extend(["-r", request.execution_profile])
        completed = self._invoke(command, environment, request.timeout_seconds)
        return NemotronStepResult(
            tuple(command),
            completed.returncode,
            completed.stdout or "",
            completed.stderr or "",
            request.execution_profile,
            approval_ref,
        )

    def _invoke(
        self, command: list[str], environment: dict[str, str], timeout_seconds: int
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = self._runner(
                command,
                cwd=str(self.working_directory),
                env=environment,
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"Nemotron command exceeded {timeout_seconds}s: {' '.join(command[1:4])}"
            ) from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "no command output").strip()
            raise RuntimeError(f"Nemotron command failed ({result.returncode}): {detail}")
        return result
