"""Training-time multi-teacher data generation for vectolith students.

Uses OpenAI-compatible endpoints (local or explicitly configured hosted
services). No endpoint is contacted until run_generation() is invoked.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import json
import os
import re
from pathlib import Path
import time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .distillation import TeacherContribution, TeacherPanel


class TeacherClient(Protocol):
    def generate(self, messages: list[dict[str, str]], *, max_tokens: int) -> str: ...


@dataclass(frozen=True, slots=True)
class TeacherEndpoint:
    teacher_id: str
    model: str
    base_url: str
    api_key_env: str
    immutable_revision: str
    timeout_seconds: int = 120


class OpenAICompatibleTeacher:
    """Minimal chat-completions client; secrets are read only at call time."""

    MAX_RESPONSE_BYTES = 8 * 1024 * 1024

    def __init__(self, endpoint: TeacherEndpoint):
        self.endpoint = endpoint

    def generate(self, messages: list[dict[str, str]], *, max_tokens: int) -> str:
        key = os.environ.get(self.endpoint.api_key_env, "")
        if not key:
            raise RuntimeError(f"missing credential environment variable: {self.endpoint.api_key_env}")
        url = self.endpoint.base_url.rstrip("/") + "/chat/completions"
        payload = json.dumps({
            "model": self.endpoint.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }).encode()
        request = Request(url, data=payload, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        })
        try:
            with urlopen(request, timeout=self.endpoint.timeout_seconds) as response:
                raw = response.read(self.MAX_RESPONSE_BYTES + 1)
                if len(raw) > self.MAX_RESPONSE_BYTES:
                    raise RuntimeError("teacher response exceeds configured byte limit")
                body = json.loads(raw)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"teacher request failed for {self.endpoint.teacher_id}: {type(exc).__name__}") from exc
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"invalid chat-completions response from {self.endpoint.teacher_id}") from exc


@dataclass(frozen=True, slots=True)
class TeachingTask:
    task_id: str
    competency: str
    prompt: str
    rubric: str


@dataclass(frozen=True, slots=True)
class TeacherAssignmentPanel:
    student_model_id: str
    foundation_revision: str
    run_id: str
    teachers: tuple["QualifiedTeacher", ...]

    def validate(self) -> None:
        if len(self.teachers) < 4:
            raise ValueError("each student requires at least four teachers")
        ids = [item.endpoint.teacher_id for item in self.teachers]
        if len(ids) != len(set(ids)):
            raise ValueError("teacher identities must be distinct")
        if not re.fullmatch(r"[0-9a-f]{40}", self.foundation_revision):
            raise ValueError("student foundation revision must be an immutable 40-character commit SHA")
        if not self.student_model_id.strip() or not self.run_id.strip():
            raise ValueError("student model and run identifiers are required")
        for teacher in self.teachers:
            q = teacher.qualification
            if not q.qualification_passed or not q.training_output_permission_verified:
                raise ValueError(f"{q.teacher_id}: teacher is not qualified or lacks training-output permission")
            if q.teacher_id != teacher.endpoint.teacher_id or q.immutable_revision != teacher.endpoint.immutable_revision:
                raise ValueError(f"{q.teacher_id}: endpoint identity or immutable revision mismatch")
            if not re.fullmatch(r"[0-9a-f]{40}", q.immutable_revision):
                raise ValueError(f"{q.teacher_id}: teacher revision must be an immutable commit SHA")
            if q.qualification_passed and (q.quality_score is None or not 0 < q.quality_score <= 1):
                raise ValueError(f"{q.teacher_id}: a qualified teacher requires an independently established quality score")
            if q.quality_score is not None and not 0 < q.quality_score <= 1:
                raise ValueError(f"{q.teacher_id}: invalid quality score")
            if q.p50_latency_ms <= 0 or q.cost_per_million_tokens_usd < 0:
                raise ValueError(f"{q.teacher_id}: invalid efficiency metrics")
            if not q.license_id.strip() or not q.output_training_permission_evidence.strip():
                raise ValueError(f"{q.teacher_id}: license and training-output permission evidence are required")


@dataclass(frozen=True, slots=True)
class TeacherQualification:
    teacher_id: str
    provider: str
    immutable_revision: str
    license_id: str
    training_output_permission_verified: bool
    output_training_permission_evidence: str
    assigned_competencies: tuple[str, ...]
    quality_score: float | None
    p50_latency_ms: float
    cost_per_million_tokens_usd: float
    qualification_suite: str
    qualification_passed: bool


@dataclass(frozen=True, slots=True)
class QualifiedTeacher:
    qualification: TeacherQualification
    endpoint: TeacherEndpoint
    # Raw, case-bound outputs are retained for blinded human/executable review.
    response_evidence: tuple[dict[str, Any], ...] = ()


def qualify_teacher(
    endpoint: TeacherEndpoint,
    *,
    provider: str,
    license_id: str,
    training_output_permission_verified: bool,
    output_training_permission_evidence: str,
    competencies: tuple[str, ...],
    benchmark_tasks: list[TeachingTask],
    minimum_quality: float = 0.75,
    cost_per_million_tokens_usd: float = 0.0,
    qualification_suite: str = "vectolith-teacher-qualification-v1",
) -> QualifiedTeacher:
    """Collect immutable-revision inference evidence; never self-qualify a teacher.

    The legacy minimum_quality argument is retained for API compatibility but
    is intentionally unused. Keyword/rubric-term matching is not a correctness
    measure. The returned candidate remains unqualified until independent,
    criterion-specific human/executable review and all qualification gates pass.
    """
    if not benchmark_tasks:
        raise ValueError("teacher evidence collection requires benchmark tasks")
    if cost_per_million_tokens_usd < 0:
        raise ValueError("teacher token cost must be non-negative")
    if not re.fullmatch(r"[0-9a-f]{40}", endpoint.immutable_revision):
        raise ValueError("teacher revision must be an immutable 40-character commit SHA")
    if not license_id.strip() or not output_training_permission_evidence.strip():
        raise ValueError("license and training-output permission evidence are required")
    client = OpenAICompatibleTeacher(endpoint)
    latencies: list[float] = []
    response_evidence: list[dict[str, Any]] = []
    for task in benchmark_tasks:
        started = time.monotonic()
        answer = client.generate([
            {"role": "system", "content": "Answer the benchmark task accurately. Do not fabricate sources or claim unperformed actions."},
            {"role": "user", "content": f"Competency: {task.competency}\nRubric: {task.rubric}\nTask: {task.prompt}"},
        ], max_tokens=2048)
        latency_ms = (time.monotonic() - started) * 1000
        latencies.append(latency_ms)
        response_evidence.append({
            "task_id": task.task_id,
            "competency": task.competency,
            "prompt": task.prompt,
            "rubric": task.rubric,
            "teacher_id": endpoint.teacher_id,
            "teacher_revision": endpoint.immutable_revision,
            "response": answer,
            "response_sha256": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
            "latency_ms": round(latency_ms, 2),
        })
    ordered = sorted(latencies)
    p50 = ordered[len(ordered) // 2]
    qualification = TeacherQualification(
        teacher_id=endpoint.teacher_id,
        provider=provider,
        immutable_revision=endpoint.immutable_revision,
        license_id=license_id,
        training_output_permission_verified=training_output_permission_verified,
        output_training_permission_evidence=output_training_permission_evidence,
        assigned_competencies=competencies,
        quality_score=None,
        p50_latency_ms=p50,
        cost_per_million_tokens_usd=cost_per_million_tokens_usd,
        qualification_suite=qualification_suite,
        qualification_passed=False,
    )
    return QualifiedTeacher(qualification, endpoint, tuple(response_evidence))


def select_teacher_panel(
    student_model_id: str,
    foundation_revision: str,
    run_id: str,
    candidates: list[QualifiedTeacher],
    *,
    required_competencies: set[str],
    minimum_quality: float = 0.75,
) -> TeacherAssignmentPanel:
    """Select four or more qualified teachers with complementary coverage."""
    eligible = [
        item for item in candidates
        if item.qualification.qualification_passed
        and item.qualification.output_training_permission_evidence.strip()
        and item.qualification.training_output_permission_verified
        and item.qualification.quality_score is not None
        and item.qualification.quality_score >= minimum_quality
        and item.endpoint.immutable_revision == item.qualification.immutable_revision
        and item.endpoint.teacher_id == item.qualification.teacher_id
        and bool(item.qualification.assigned_competencies)
    ]
    selected: list[QualifiedTeacher] = []
    covered: set[str] = set()
    remaining = list(eligible)
    while remaining and (len(selected) < 4 or not required_competencies.issubset(covered)):
        remaining.sort(
            key=lambda item: (
                len(set(item.qualification.assigned_competencies) & (required_competencies - covered)),
                item.qualification.quality_score,
                -item.qualification.p50_latency_ms,
            ),
            reverse=True,
        )
        best = remaining.pop(0)
        selected.append(best)
        covered.update(best.qualification.assigned_competencies)
    if len(selected) < 4:
        raise ValueError(f"only {len(selected)} qualified teachers; at least four are required")
    if not required_competencies.issubset(covered):
        raise ValueError(f"teacher panel does not cover: {sorted(required_competencies - covered)}")
    panel = TeacherAssignmentPanel(
        student_model_id=student_model_id,
        foundation_revision=foundation_revision,
        teachers=tuple(selected),
        run_id=run_id,
    )
    panel.validate()
    return panel


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def generate_teaching_corpus(
    panel: TeacherAssignmentPanel,
    endpoints: dict[str, TeacherEndpoint],
    tasks: list[TeachingTask],
    output_path: str | Path,
    *,
    max_tokens: int = 2048,
    concurrency: int = 4,
) -> dict[str, Any]:
    """All panel teachers generate; peers cross-review; accepted records are JSONL.

    The peer review is a quality-control signal, not ground truth. It is retained
    as provenance and must be followed by executable/reference validation where
    the competency permits it.
    """
    panel.validate()
    if max_tokens <= 0 or concurrency <= 0:
        raise ValueError("max_tokens and concurrency must be positive")
    if set(endpoints) != {teacher.endpoint.teacher_id for teacher in panel.teachers}:
        raise ValueError("endpoint set must exactly match the validated teacher panel")
    if not tasks:
        raise ValueError("at least one teaching task is required")
    expected_endpoints = {teacher.endpoint.teacher_id: teacher.endpoint for teacher in panel.teachers}
    if endpoints != expected_endpoints:
        raise ValueError("endpoint configurations must exactly match the qualified panel")
    clients = {teacher_id: OpenAICompatibleTeacher(endpoint) for teacher_id, endpoint in endpoints.items()}
    sem = asyncio.Semaphore(concurrency)

    async def call(teacher_id: str, messages: list[dict[str, str]]) -> tuple[str, str, float]:
        async with sem:
            started = time.monotonic()
            result = await asyncio.to_thread(clients[teacher_id].generate, messages, max_tokens=max_tokens)
            return teacher_id, result, (time.monotonic() - started) * 1000

    records: list[dict[str, Any]] = []
    counts = {teacher_id: 0 for teacher_id in endpoints}
    for task in tasks:
        generated = await asyncio.gather(*[
            call(teacher_id, [
                {"role": "system", "content": "You are a teacher contributing a high-quality, self-contained training example. Follow the task rubric. Do not claim tool execution that did not occur."},
                {"role": "user", "content": f"Competency: {task.competency}\nRubric: {task.rubric}\nTask: {task.prompt}"},
            ]) for teacher_id in endpoints
        ])
        teacher_ids = list(endpoints)
        for teacher_index, (teacher_id, answer, latency) in enumerate(generated):
            reviewer_id = teacher_ids[(teacher_index + 1) % len(teacher_ids)]
            _, review, review_latency = await call(reviewer_id, [
                {"role": "system", "content": "Review the proposed teaching example against the task rubric. Return JSON with keys: score (0 to 1), issues (array), verdict (accept or reject). Be critical; do not assume correctness."},
                {"role": "user", "content": f"Competency: {task.competency}\nRubric: {task.rubric}\nTask: {task.prompt}\nProposed answer:\n{answer}"},
            ])
            try:
                review_data = json.loads(review)
                score = float(review_data["score"])
                verdict = review_data["verdict"] == "accept"
                issues = review_data.get("issues", [])
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                score, verdict, issues = 0.0, False, ["review response was not valid rubric JSON"]
            accepted = verdict and 0 <= score <= 1 and score >= 0.75 and bool(answer.strip())
            record = {
                "schema_version": "1.0",
                "student_model_id": panel.student_model_id,
                "run_id": panel.run_id,
                "task_id": task.task_id,
                "competency": task.competency,
                "prompt": task.prompt,
                "response": answer,
                "teacher_id": teacher_id,
                "teacher_revision": endpoints[teacher_id].immutable_revision,
                "reviewer_id": reviewer_id,
                "review": {"score": score, "verdict": "accept" if accepted else "reject", "issues": issues},
                "teacher_latency_ms": round(latency, 2),
                "review_latency_ms": round(review_latency, 2),
                "content_sha256": _digest(task.prompt + "\0" + answer),
                "accepted": accepted,
            }
            records.append(record)
            if accepted:
                counts[teacher_id] += 1

    # Do not produce a purported four-teacher corpus if any teacher contributed nothing.
    empty = [teacher_id for teacher_id, count in counts.items() if count == 0]
    if empty:
        raise RuntimeError(f"teachers produced no accepted examples: {empty}")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            if record["accepted"]:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {
        "run_id": panel.run_id,
        "student_model_id": panel.student_model_id,
        "records_generated": len(records),
        "records_accepted": sum(counts.values()),
        "accepted_by_teacher": counts,
        "dataset_path": str(path),
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def finalize_teacher_panel(
    assignment: TeacherAssignmentPanel,
    *,
    accepted_examples_by_teacher: dict[str, int],
    accepted_tokens_by_teacher: dict[str, int],
    dataset_shard_id: str,
    ablation_report: dict[str, Any],
) -> TeacherPanel:
    """Create the auditable post-training panel from actual corpus and ablation evidence."""
    assignment.validate()
    teacher_ids = {teacher.endpoint.teacher_id for teacher in assignment.teachers}
    if set(accepted_examples_by_teacher) != teacher_ids or set(accepted_tokens_by_teacher) != teacher_ids:
        raise ValueError("corpus contribution counts must cover exactly the selected teacher panel")
    deltas = ablation_report.get("leave_one_teacher_out_deltas", {})
    if set(deltas) != teacher_ids or not ablation_report.get("release_eligible", False):
        raise ValueError("positive leave-one-teacher-out evidence is required for every selected teacher")
    contributions = []
    for teacher in assignment.teachers:
        q = teacher.qualification
        teacher_id = q.teacher_id
        contributions.append(TeacherContribution(
            teacher_id=teacher_id,
            provider=q.provider,
            immutable_revision=q.immutable_revision,
            license_id=q.license_id,
            training_output_permission_verified=q.training_output_permission_verified,
            assigned_competencies=q.assigned_competencies,
            dataset_shard_id=dataset_shard_id,
            accepted_examples=accepted_examples_by_teacher[teacher_id],
            accepted_tokens=accepted_tokens_by_teacher[teacher_id],
            ablation_quality_delta=float(deltas[teacher_id]),
            quality_score=q.quality_score,
            p50_latency_ms=q.p50_latency_ms,
            cost_per_million_tokens_usd=q.cost_per_million_tokens_usd,
        ))
    panel = TeacherPanel(
        student_model_id=assignment.student_model_id,
        student_foundation_revision=assignment.foundation_revision,
        teachers=tuple(contributions),
        run_id=assignment.run_id,
    )
    panel.require_valid()
    return panel
