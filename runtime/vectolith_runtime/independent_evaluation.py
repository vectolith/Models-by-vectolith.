"""Evidence-backed student evaluation. Keyword overlap is never a quality score."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, os
from pathlib import Path
from typing import Any, Callable
from .distillation import IndependenceEvidence, TeacherContribution

@dataclass(frozen=True, slots=True)
class EvaluationCase:
    case_id: str
    competency: str
    prompt: str
    # Legacy field retained for input compatibility; deliberately never scored.
    expected_keywords: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class VerificationResult:
    status: str
    method: str
    evidence: tuple[dict[str, Any], ...]
    confidence: float | None = None
    limitations: tuple[str, ...] = ()

    def validate(self) -> list[str]:
        errors=[]
        if self.status not in {"verified_pass","verified_fail","inconclusive"}: errors.append("invalid verifier status")
        if not self.method.strip(): errors.append("verifier method/version is required")
        if not self.evidence: errors.append("verifier evidence is required")
        for i,item in enumerate(self.evidence):
            if not isinstance(item,dict) or not item.get("type") or not item.get("reference"):
                errors.append(f"evidence[{i}] requires type and reference")
        if self.confidence is not None and (isinstance(self.confidence,bool) or not isinstance(self.confidence,(int,float)) or not 0<=self.confidence<=1):
            errors.append("confidence must be between 0 and 1")
        return errors

Verifier = Callable[[EvaluationCase,str], VerificationResult | dict[str,Any]]

def load_student_generator(checkpoint_dir: str, *, max_new_tokens: int = 1024) -> Callable[[str], str]:
    """Load only the student checkpoint; no teacher client or endpoint is used."""
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("install vectolith-runtime[training] to load a local student") from exc
    tokenizer=AutoTokenizer.from_pretrained(checkpoint_dir,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(checkpoint_dir,device_map="auto",local_files_only=True)
    model.eval()
    def generate(prompt: str) -> str:
        messages=[{"role":"user","content":prompt}]
        rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True) if getattr(tokenizer,"chat_template",None) else prompt
        inputs=tokenizer(rendered,return_tensors="pt")
        inputs={key:value.to(model.device) for key,value in inputs.items()}
        with torch.inference_mode(): output=model.generate(**inputs,max_new_tokens=max_new_tokens)
        return tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:],skip_special_tokens=True)
    return generate

def _verification(value: VerificationResult | dict[str,Any]) -> VerificationResult:
    if isinstance(value,dict):
        value=VerificationResult(value.get("status",""),value.get("method",""),tuple(value.get("evidence",())),value.get("confidence"),tuple(value.get("limitations",())))
    if not isinstance(value,VerificationResult): raise TypeError("verifier must return VerificationResult or mapping")
    errors=value.validate()
    if errors: raise ValueError("invalid verifier evidence: "+"; ".join(errors))
    return value

def run_capability_suite(generate: Callable[[str],str], cases: list[EvaluationCase], verifier: Verifier | None=None) -> dict[str,Any]:
    """Without a verifier, preserve output hashes and explicitly require human grading."""
    if not cases: raise ValueError("evaluation suite must not be empty")
    ids=[case.case_id for case in cases]
    if len(ids)!=len(set(ids)): raise ValueError("evaluation case IDs must be unique")
    rows=[]
    for case in cases:
        output=generate(case.prompt)
        if not isinstance(output,str): raise TypeError(f"generator returned non-text output for {case.case_id}")
        result=_verification(verifier(case,output)) if verifier else None
        rows.append({"case_id":case.case_id,"competency":case.competency,
            "status":result.status if result else "requires_human_review",
            "scoring_method":result.method if result else None,
            "confidence":result.confidence if result else None,
            "evidence":list(result.evidence) if result else [],
            "limitations":list(result.limitations) if result else ["No criterion-specific verifier supplied; independent human grading is required."],
            "output_sha256":hashlib.sha256(output.encode()).hexdigest()})
    verified=[r for r in rows if r["status"] in {"verified_pass","verified_fail"}]
    report={"schema_version":"vectolith-capability-evidence/2.0","cases":rows,"total":len(rows),
        "verified_case_count":len(verified),"unscored_case_count":len(rows)-len(verified),
        "passed":sum(r["status"]=="verified_pass" for r in verified),
        "failed":sum(r["status"]=="verified_fail" for r in verified),
        "evaluation_disposition":"complete_with_verifier_evidence" if len(verified)==len(rows) else "incomplete_requires_human_review",
        "quality_decision":"not_made"}
    if len(verified)==len(rows): report["pass_rate"]=report["passed"]/len(rows)
    return report

def run_teacher_disabled_check(*, checkpoint_dir: str, endpoint_env_names: tuple[str,...], credential_env_names: tuple[str,...], inference_dependencies: tuple[str,...], capability_passed: bool, teacher_calls_observed: int) -> IndependenceEvidence:
    for name in endpoint_env_names+credential_env_names: os.environ.pop(name,None)
    digest=hashlib.sha256(); root=Path(checkpoint_dir)
    if not root.is_dir(): raise FileNotFoundError(root)
    files=sorted(p for p in root.rglob("*") if p.is_file())
    if not files: raise ValueError("student checkpoint directory is empty")
    for path in files:
        digest.update(str(path.relative_to(root)).encode()); digest.update(path.read_bytes())
    evidence=IndependenceEvidence(student_checkpoint_sha256=digest.hexdigest(),
        teacher_endpoints_disabled=all(not os.environ.get(n) for n in endpoint_env_names),
        teacher_credentials_absent=all(not os.environ.get(n) for n in credential_env_names),
        teacher_calls_observed=teacher_calls_observed,required_capability_checks_passed=capability_passed,
        inference_dependencies=inference_dependencies)
    evidence.require_valid(); return evidence

def leave_one_teacher_out(train_and_evaluate: Callable[[str|None],float], teacher_ids: tuple[str,...]) -> dict[str,Any]:
    if len(set(teacher_ids))<4: raise ValueError("ablation requires at least four distinct teacher identities")
    full=train_and_evaluate(None); deltas={t:full-train_and_evaluate(t) for t in teacher_ids}
    return {"full_score":full,"leave_one_teacher_out_deltas":deltas,
        "every_teacher_contributed":all(d>0 for d in deltas.values()),"release_eligible":all(d>0 for d in deltas.values())}

def write_release_report(path: str|Path, report: dict[str,Any]) -> None:
    Path(path).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")

def evaluate_release(*, capability_report: dict[str,Any], minimum_capability_pass_rate: float, ablation_report: dict[str,Any], independence_evidence: IndependenceEvidence, teacher_contributions: tuple[TeacherContribution,...]) -> dict[str,Any]:
    raw=capability_report.get("pass_rate")
    rate=float(raw) if isinstance(raw,(int,float)) and not isinstance(raw,bool) else None
    deltas=ablation_report.get("leave_one_teacher_out_deltas",{}); errors=[]
    for contribution in teacher_contributions: errors.extend(contribution.validate())
    reasons=[]
    if rate is None: reasons.append("capability evaluation is unscored or incomplete; criterion-specific evidence and human review are required")
    elif rate<minimum_capability_pass_rate: reasons.append("capability pass rate is below the release threshold")
    if len(teacher_contributions)<4: reasons.append("fewer than four teacher contributions are recorded")
    if len({x.teacher_id for x in teacher_contributions})<4: reasons.append("teacher contributions do not come from four distinct identities")
    if set(deltas)!={x.teacher_id for x in teacher_contributions}: reasons.append("ablation evidence does not cover exactly the contributing teachers")
    if not ablation_report.get("release_eligible",False): reasons.append("one or more teacher ablations failed")
    if any(not isinstance(d,(int,float)) or isinstance(d,bool) or d<=0 for d in deltas.values()): reasons.append("each teacher must have a positive measured leave-one-out delta")
    for c in teacher_contributions:
        d=deltas.get(c.teacher_id)
        if d is None or abs(float(d)-c.ablation_quality_delta)>1e-9: reasons.append(f"{c.teacher_id}: recorded ablation delta does not match evaluation evidence")
    reasons.extend(errors); reasons.extend(independence_evidence.validate())
    return {"release_approved":not reasons,"capability_pass_rate":rate,"minimum_capability_pass_rate":minimum_capability_pass_rate,
        "teacher_count":len({x.teacher_id for x in teacher_contributions}),"ablation_deltas":deltas,
        "independence_checkpoint_sha256":independence_evidence.student_checkpoint_sha256,"blocking_reasons":reasons}
