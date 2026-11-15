"""Validation primitives for multi-teacher distillation runs.

This module validates evidence and manifests; it does not call teacher APIs or
start training. Teacher credentials and generation adapters belong in a
separate, protected training service.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import re
from typing import Iterable


_SHA40 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class TeacherContribution:
    teacher_id: str
    provider: str
    immutable_revision: str
    license_id: str
    training_output_permission_verified: bool
    assigned_competencies: tuple[str, ...]
    dataset_shard_id: str
    accepted_examples: int
    accepted_tokens: int
    ablation_quality_delta: float
    quality_score: float
    p50_latency_ms: float
    cost_per_million_tokens_usd: float

    def validate(self) -> list[str]:
        errors: list[str] = []
        required = {
            "teacher_id": self.teacher_id,
            "provider": self.provider,
            "license_id": self.license_id,
            "dataset_shard_id": self.dataset_shard_id,
        }
        errors.extend(f"{name} must not be empty" for name, value in required.items() if not value.strip())
        if not _SHA40.fullmatch(self.immutable_revision):
            errors.append(f"{self.teacher_id}: immutable_revision must be a 40-character commit SHA")
        if not self.training_output_permission_verified:
            errors.append(f"{self.teacher_id}: training-output permission is not verified")
        if not self.assigned_competencies:
            errors.append(f"{self.teacher_id}: at least one competency must be assigned")
        if self.accepted_examples <= 0 or self.accepted_tokens <= 0:
            errors.append(f"{self.teacher_id}: accepted examples and tokens must both be positive")
        if not isfinite(self.ablation_quality_delta) or self.ablation_quality_delta <= 0:
            errors.append(f"{self.teacher_id}: ablation must show a positive, finite contribution")
        if not isfinite(self.quality_score) or not 0 < self.quality_score <= 1:
            errors.append(f"{self.teacher_id}: quality_score must be in the interval (0, 1]")
        if not isfinite(self.p50_latency_ms) or self.p50_latency_ms <= 0:
            errors.append(f"{self.teacher_id}: p50_latency_ms must be positive and finite")
        if not isfinite(self.cost_per_million_tokens_usd) or self.cost_per_million_tokens_usd < 0:
            errors.append(f"{self.teacher_id}: cost per million tokens must be finite and non-negative")
        return errors


@dataclass(frozen=True, slots=True)
class TeacherPanel:
    student_model_id: str
    student_foundation_revision: str
    teachers: tuple[TeacherContribution, ...]
    run_id: str

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.student_model_id.strip():
            errors.append("student_model_id must not be empty")
        if not self.run_id.strip():
            errors.append("run_id must not be empty")
        if not _SHA40.fullmatch(self.student_foundation_revision):
            errors.append("student_foundation_revision must be a 40-character commit SHA")
        if len(self.teachers) < 4:
            errors.append("each student requires at least four teacher models")
        ids = [teacher.teacher_id for teacher in self.teachers]
        if len(ids) != len(set(ids)):
            errors.append("teacher identities must be distinct")
        for teacher in self.teachers:
            errors.extend(teacher.validate())
        return errors

    def require_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise ValueError("invalid teacher panel: " + "; ".join(errors))


@dataclass(frozen=True, slots=True)
class IndependenceEvidence:
    student_checkpoint_sha256: str
    teacher_endpoints_disabled: bool
    teacher_credentials_absent: bool
    teacher_calls_observed: int
    required_capability_checks_passed: bool
    inference_dependencies: tuple[str, ...] = ()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not re.fullmatch(r"[0-9a-f]{64}", self.student_checkpoint_sha256):
            errors.append("student checkpoint must have a SHA-256 digest")
        if not self.teacher_endpoints_disabled:
            errors.append("teacher endpoints must be disabled during independence evaluation")
        if not self.teacher_credentials_absent:
            errors.append("teacher credentials must be absent during independence evaluation")
        if self.teacher_calls_observed != 0:
            errors.append("student made teacher calls during independence evaluation")
        if not self.required_capability_checks_passed:
            errors.append("required standalone capability checks did not pass")
        if self.inference_dependencies:
            errors.append("inference dependencies must not include teacher services or artifacts")
        return errors

    def require_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise ValueError("student independence gate failed: " + "; ".join(errors))


def validate_panels(panels: Iterable[TeacherPanel]) -> None:
    """Validate a collection of panels, one per student training run."""
    seen_runs: set[str] = set()
    for panel in panels:
        panel.require_valid()
        if panel.run_id in seen_runs:
            raise ValueError(f"duplicate training run id: {panel.run_id}")
        seen_runs.add(panel.run_id)
