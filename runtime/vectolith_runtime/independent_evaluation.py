"""Teacher-disabled capability and per-teacher ablation evaluation."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from .distillation import IndependenceEvidence, TeacherContribution


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    competency: str
    prompt: str
    expected_keywords: tuple[str, ...] = ()


def load_student_generator(checkpoint_dir: str, *, max_new_tokens: int = 1024) -> Callable[[str], str]:
    """Load only the student checkpoint; no teacher client or endpoint is used."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("install vectolith-runtime[training] to load a local student") from exc
    tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        checkpoint_dir, device_map="auto", local_files_only=True
    )
    model.eval()

    def generate(prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        if getattr(tokenizer, "chat_template", None):
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            rendered = prompt
        inputs = tokenizer(rendered, return_tensors="pt")
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
        with torch.inference_mode():
            output = model.generate(**inputs, max_new_tokens=max_new_tokens)
        generated = output[0][inputs["input_ids"].shape[-1]:]
        return tokenizer.decode(generated, skip_special_tokens=True)

    return generate


def run_capability_suite(
    generate: Callable[[str], str],
    cases: list[EvaluationCase],
) -> dict[str, Any]:
    if not cases:
        raise ValueError("evaluation suite must not be empty")
    results = []
    for case in cases:
        output = generate(case.prompt)
        hits = sum(keyword.casefold() in output.casefold() for keyword in case.expected_keywords)
        passed = hits == len(case.expected_keywords) and bool(output.strip())
        results.append({
            "case_id": case.case_id, "competency": case.competency,
            "passed": passed, "keyword_hits": hits,
            "keyword_total": len(case.expected_keywords),
            "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        })
    total = len(results)
    return {
        "cases": results,
        "passed": sum(item["passed"] for item in results),
        "total": total,
        "pass_rate": sum(item["passed"] for item in results) / total,
    }


def run_teacher_disabled_check(
    *,
    checkpoint_dir: str,
    endpoint_env_names: tuple[str, ...],
    credential_env_names: tuple[str, ...],
    inference_dependencies: tuple[str, ...],
    capability_passed: bool,
    teacher_calls_observed: int,
) -> IndependenceEvidence:
    """Require explicit isolation evidence from the evaluation harness."""
    for name in endpoint_env_names + credential_env_names:
        os.environ.pop(name, None)
    digest = hashlib.sha256()
    root = Path(checkpoint_dir)
    if not root.is_dir():
        raise FileNotFoundError(root)
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise ValueError("student checkpoint directory is empty")
    for path in files:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    evidence = IndependenceEvidence(
        student_checkpoint_sha256=digest.hexdigest(),
        teacher_endpoints_disabled=all(not os.environ.get(name) for name in endpoint_env_names),
        teacher_credentials_absent=all(not os.environ.get(name) for name in credential_env_names),
        teacher_calls_observed=teacher_calls_observed,
        required_capability_checks_passed=capability_passed,
        inference_dependencies=inference_dependencies,
    )
    evidence.require_valid()
    return evidence


def leave_one_teacher_out(
    train_and_evaluate: Callable[[str | None], float],
    teacher_ids: tuple[str, ...],
) -> dict[str, Any]:
    """Caller supplies isolated retraining/evaluation for full and ablated corpora."""
    if len(set(teacher_ids)) < 4:
        raise ValueError("ablation requires at least four distinct teacher identities")
    full_score = train_and_evaluate(None)
    deltas = {}
    for teacher_id in teacher_ids:
        ablated_score = train_and_evaluate(teacher_id)
        deltas[teacher_id] = full_score - ablated_score
    return {
        "full_score": full_score,
        "leave_one_teacher_out_deltas": deltas,
        "every_teacher_contributed": all(delta > 0 for delta in deltas.values()),
        "release_eligible": all(delta > 0 for delta in deltas.values()),
    }


def write_release_report(path: str | Path, report: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")



def evaluate_release(
    *,
    capability_report: dict[str, Any],
    minimum_capability_pass_rate: float,
    ablation_report: dict[str, Any],
    independence_evidence: IndependenceEvidence,
    teacher_contributions: tuple[TeacherContribution, ...],
) -> dict[str, Any]:
    """Fail-closed release decision combining all required student gates."""
    capability_rate = float(capability_report.get("pass_rate", 0.0))
    ablation_deltas = ablation_report.get("leave_one_teacher_out_deltas", {})
    contribution_errors = []
    for contribution in teacher_contributions:
        contribution_errors.extend(contribution.validate())
    reasons = []
    if capability_rate < minimum_capability_pass_rate:
        reasons.append("capability pass rate is below the release threshold")
    if len(teacher_contributions) < 4:
        reasons.append("fewer than four teacher contributions are recorded")
    if len({item.teacher_id for item in teacher_contributions}) < 4:
        reasons.append("teacher contributions do not come from four distinct identities")
    if set(ablation_deltas) != {item.teacher_id for item in teacher_contributions}:
        reasons.append("ablation evidence does not cover exactly the contributing teachers")
    if not ablation_report.get("release_eligible", False):
        reasons.append("one or more teacher ablations failed")
    if any(not isinstance(delta, (int, float)) or delta <= 0 for delta in ablation_deltas.values()):
        reasons.append("each teacher must have a positive measured leave-one-out delta")
    for contribution in teacher_contributions:
        measured = ablation_deltas.get(contribution.teacher_id)
        if measured is None or abs(float(measured) - contribution.ablation_quality_delta) > 1e-9:
            reasons.append(f"{contribution.teacher_id}: recorded ablation delta does not match evaluation evidence")
    if contribution_errors:
        reasons.extend(contribution_errors)
    reasons.extend(independence_evidence.validate())
    return {
        "release_approved": not reasons,
        "capability_pass_rate": capability_rate,
        "minimum_capability_pass_rate": minimum_capability_pass_rate,
        "teacher_count": len({item.teacher_id for item in teacher_contributions}),
        "ablation_deltas": ablation_deltas,
        "independence_checkpoint_sha256": independence_evidence.student_checkpoint_sha256,
        "blocking_reasons": reasons,
    }
