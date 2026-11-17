"""Evidence gates for Core Prime training preflight; no training dependencies imported."""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime
from pathlib import Path
from typing import Any
from .protected_holdout import validate_deployment_file, validate_candidate_result

TEACHER_SCHEMA="vectolith-teacher-qualification-candidate/1.0"
FOUNDATION_SCHEMA="vectolith-foundation-selection/1.0"

def _sha(value: Any) -> bool:
    return isinstance(value,str) and re.fullmatch(r"[0-9a-f]{64}",value.lower()) is not None

def _time(value: Any) -> bool:
    if not isinstance(value,str) or not value.strip(): return False
    try: datetime.fromisoformat(value.replace("Z","+00:00")); return True
    except ValueError: return False

def validate_teacher_manifest(manifest: dict[str,Any], teacher_id: str, revision: str, *, holdout_deployment_sha256: str | None = None, holdout_evaluation_sha256: str | None = None, holdout_case_count: int | None = None, holdout_audit_sha256: str | None = None) -> list[str]:
    errors=[]
    if manifest.get("schema_version")!=TEACHER_SCHEMA: errors.append("unsupported teacher manifest schema")
    if manifest.get("candidate_id")!=teacher_id: errors.append("teacher identity mismatch")
    if manifest.get("immutable_revision")!=revision or not isinstance(revision,str) or not re.fullmatch(r"[0-9a-f]{40}",revision): errors.append("teacher immutable revision mismatch")
    gates=manifest.get("gates")
    if not isinstance(gates,dict): return errors+["qualification gates object missing"]
    def gate(name): 
        value=gates.get(name)
        if not isinstance(value,dict): errors.append(f"{name}: gate object missing"); return {}
        return value
    s=gate("snapshot")
    if s.get("status")!="verified" or s.get("immutable_revision")!=revision or not _sha(s.get("manifest_sha256")): errors.append("snapshot gate failed")
    l=gate("license_review")
    if l.get("status")!="approved" or not _sha(l.get("license_text_sha256")) or not l.get("legal_reviewer_id") or not _time(l.get("reviewed_at")) or not l.get("evidence_uri"): errors.append("license review gate failed")
    loader=gate("loader_compatibility"); remote=loader.get("remote_code")
    if loader.get("status")!="passed" or loader.get("tested_revision")!=revision or not loader.get("model_class") or not loader.get("runtime_versions") or not isinstance(remote,dict) or remote.get("status") not in {"disabled","audited"}: errors.append("loader compatibility gate failed")
    if isinstance(remote,dict) and remote.get("status")=="audited" and not _sha(remote.get("audit_sha256")): errors.append("remote-code audit digest missing")
    inf=gate("real_inference")
    if (inf.get("status")!="completed" or inf.get("tested_revision")!=revision or not inf.get("workflow_run_id") or not inf.get("internal_run_id") or not isinstance(inf.get("expected_response_count"),int) or isinstance(inf.get("expected_response_count"),bool) or inf.get("expected_response_count",0)<=0 or inf.get("response_count")!=inf.get("expected_response_count") or inf.get("error_count")!=0 or not _sha(inf.get("artifact_sha256"))): errors.append("real inference gate failed")
    res=gate("resource_measurement")
    if (res.get("status")!="recorded" or not res.get("runner_type") or not res.get("device") or not isinstance(res.get("peak_rss_bytes"),int) or isinstance(res.get("peak_rss_bytes"),bool) or res.get("peak_rss_bytes",0)<=0 or not isinstance(res.get("mean_latency_seconds"),(int,float)) or isinstance(res.get("mean_latency_seconds"),bool) or res.get("mean_latency_seconds",0)<=0 or not _sha(res.get("compute_record_sha256"))): errors.append("resource measurement gate failed")
    h=gate("human_review"); reviewers=h.get("independent_reviewer_ids")
    if (h.get("status")!="passed" or not isinstance(reviewers,list) or len(set(x for x in reviewers if isinstance(x,str) and x.strip()))<2 or h.get("independence_attested") is not True or h.get("adjudication_complete") is not True or not isinstance(h.get("expected_response_count"),int) or h.get("expected_response_count",0)<=0 or h.get("graded_response_count")!=h.get("expected_response_count") or not _sha(h.get("grade_report_sha256")) or not _sha(h.get("adjudication_sha256"))): errors.append("independent human review/adjudication gate failed")
    agreement=h.get("agreement")
    if not isinstance(agreement,dict) or agreement.get("status")!="accepted" or agreement.get("metric") not in {"quadratic_weighted_cohen_kappa","krippendorff_alpha"}: errors.append("human-review agreement record missing or invalid")
    else:
        value,threshold=agreement.get("value"),agreement.get("minimum_required")
        if not isinstance(value,(int,float)) or isinstance(value,bool) or not -1<=value<=1 or not isinstance(threshold,(int,float)) or isinstance(threshold,bool) or not 0<=threshold<=1 or value<threshold: errors.append("human-review agreement below policy threshold or invalid")
        if not _sha(agreement.get("report_sha256")) or not _sha(agreement.get("policy_sha256")) or not _sha(agreement.get("reviewer_independence_sha256")): errors.append("human-review agreement/independence digest missing")
    safety=gate("safety_review")
    if safety.get("status")!="passed" or not safety.get("reviewer_id") or not _sha(safety.get("report_sha256")): errors.append("safety review gate failed")
    holdout=gate("holdout")
    if (holdout.get("status")!="passed" or not isinstance(holdout.get("case_count"),int) or holdout.get("case_count",0)<=0 or holdout.get("leakage_audit_passed") is not True or not _sha(holdout.get("audit_sha256")) or not _sha(holdout.get("deployment_manifest_sha256")) or not _sha(holdout.get("evaluation_report_sha256"))): errors.append("protected holdout gate failed")
    if holdout_deployment_sha256 is not None and holdout.get("deployment_manifest_sha256") != holdout_deployment_sha256: errors.append("teacher holdout deployment digest mismatch")
    if holdout_evaluation_sha256 is not None and holdout.get("evaluation_report_sha256") != holdout_evaluation_sha256: errors.append("teacher holdout evaluation report digest mismatch")
    if holdout_case_count is not None and holdout.get("case_count") != holdout_case_count: errors.append("teacher holdout case count mismatch")
    if holdout_audit_sha256 is not None and holdout.get("audit_sha256") != holdout_audit_sha256: errors.append("teacher holdout audit digest mismatch")
    corpus=gate("corpus_integrity")
    if corpus.get("status")!="passed" or not _sha(corpus.get("corpus_sha256")) or corpus.get("duplicate_count")!=0 or corpus.get("provenance_verified") is not True: errors.append("corpus integrity gate failed")
    perm=gate("training_output_permission")
    if perm.get("status")!="granted" or not _sha(perm.get("document_sha256")) or not perm.get("authorized_by") or not _time(perm.get("authorized_at")): errors.append("training output permission gate failed")
    return errors

def validate_foundation_selection(manifest: dict[str,Any], model_id: str, revision: str) -> list[str]:
    errors=[]
    if manifest.get("schema_version")!=FOUNDATION_SCHEMA: errors.append("unsupported foundation selection schema")
    if manifest.get("decision_status")!="approved": errors.append("foundation selection is not approved")
    if manifest.get("selected_model_id")!=model_id: errors.append("selected foundation model ID mismatch")
    if manifest.get("immutable_revision")!=revision or not isinstance(revision,str) or not re.fullmatch(r"[0-9a-f]{40}",revision): errors.append("selected foundation revision mismatch")
    if not _sha(manifest.get("comparison_report_sha256")): errors.append("foundation comparison report digest missing")
    if not manifest.get("approved_by") or not _time(manifest.get("approved_at")): errors.append("foundation approval provenance missing")
    evidence=manifest.get("evaluation_evidence")
    required_kinds = {"candidate_metadata", "license_review", "training_output_permission",
        "loader_compatibility", "resource_measurement", "capability_evaluation",
        "protected_holdout", "baseline_comparison"}
    if not isinstance(evidence,list) or not evidence or any(
        not isinstance(x,dict) or not _sha(x.get("sha256")) or not x.get("kind")
        or x.get("model_id") != model_id or x.get("immutable_revision") != revision
        for x in evidence
    ):
        errors.append("foundation evaluation evidence is incomplete or not bound to the exact candidate revision")
    elif not required_kinds.issubset({item["kind"] for item in evidence}):
        errors.append("foundation evaluation evidence is missing required categories: " +
            ", ".join(sorted(required_kinds - {item["kind"] for item in evidence})))
    return errors

def validate_training_preflight(*, dataset_path: str|Path, foundation_model: str, foundation_revision: str, foundation_selection_path: str|Path, teacher_manifest_dir: str|Path, holdout_deployment_manifest_path: str|Path, holdout_evaluation_results_dir: str|Path) -> tuple[list[dict[str,Any]],dict[str,Any]]:
    dataset=Path(dataset_path); selection_path=Path(foundation_selection_path); manifest_dir=Path(teacher_manifest_dir)
    if not dataset.is_file(): raise FileNotFoundError(dataset)
    if not selection_path.is_file(): raise FileNotFoundError(selection_path)
    if not manifest_dir.is_dir(): raise FileNotFoundError(manifest_dir)
    holdout_deployment, holdout_deployment_sha256 = validate_deployment_file(holdout_deployment_manifest_path)
    holdout_results_dir = Path(holdout_evaluation_results_dir)
    if not holdout_results_dir.is_dir(): raise FileNotFoundError(holdout_results_dir)
    selection=json.loads(selection_path.read_text(encoding="utf-8"))
    selection_errors=validate_foundation_selection(selection,foundation_model,foundation_revision)
    if selection_errors: raise ValueError("foundation selection preflight failed: "+"; ".join(selection_errors))
    manifests={}
    manifest_hashes={}
    for path in sorted(manifest_dir.glob("*.json")):
        value=json.loads(path.read_text(encoding="utf-8"))
        teacher_id=value.get("candidate_id") if isinstance(value,dict) else None
        revision=value.get("immutable_revision") if isinstance(value,dict) else None
        if not isinstance(teacher_id,str) or not teacher_id.strip(): raise ValueError(f"{path}: candidate_id missing")
        if teacher_id in manifests: raise ValueError(f"duplicate qualification manifest for {teacher_id}")
        result_path = holdout_results_dir / f"{teacher_id}.json"
        _, holdout_result_sha256 = validate_candidate_result(
            result_path, holdout_deployment, holdout_deployment_sha256, teacher_id, revision
        )
        errors=validate_teacher_manifest(
            value,teacher_id,revision,
            holdout_deployment_sha256=holdout_deployment_sha256,
            holdout_evaluation_sha256=holdout_result_sha256,
            holdout_case_count=holdout_deployment["case_count"],
            holdout_audit_sha256=holdout_deployment["audit"]["leakage_audit_sha256"],
        )
        if errors: raise ValueError(f"{teacher_id}: qualification preflight failed: "+"; ".join(errors))
        manifests[teacher_id]=revision
        manifest_hashes[teacher_id]=hashlib.sha256(path.read_bytes()).hexdigest()
    rows=[]
    for number,line in enumerate(dataset.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        row=json.loads(line)
        if not isinstance(row,dict) or row.get("accepted") is not True: raise ValueError(f"dataset line {number}: row is not accepted")
        for field in ("teacher_id","teacher_revision","prompt","response","content_sha256"):
            if not isinstance(row.get(field),str) or not row[field]: raise ValueError(f"dataset line {number}: {field} missing")
        if row["teacher_id"] not in manifests: raise ValueError(f"dataset line {number}: teacher has no approved qualification manifest")
        if row["teacher_revision"]!=manifests[row["teacher_id"]]: raise ValueError(f"dataset line {number}: teacher revision does not match qualification manifest")
        expected=hashlib.sha256((row["prompt"]+"\0"+row["response"]).encode("utf-8")).hexdigest()
        if row["content_sha256"]!=expected: raise ValueError(f"dataset line {number}: content digest mismatch")
        rows.append(row)
    if not rows: raise ValueError("training dataset is empty")
    teacher_ids={row["teacher_id"] for row in rows}
    if len(teacher_ids)<4: raise ValueError("student training requires at least four distinct qualified teachers")
    return rows,{"schema_version":"vectolith-training-preflight/1.0","status":"passed","foundation_model":foundation_model,"foundation_revision":foundation_revision,"foundation_selection_sha256":hashlib.sha256(selection_path.read_bytes()).hexdigest(),"protected_holdout_deployment_sha256":holdout_deployment_sha256,"dataset_sha256":hashlib.sha256(dataset.read_bytes()).hexdigest(),"training_rows":len(rows),"qualified_teacher_ids":sorted(teacher_ids),"teacher_manifest_sha256":{key:manifest_hashes[key] for key in sorted(teacher_ids)}}


EXECUTION_SCHEMA = "vectolith-training-execution-approval/1.0"

def validate_training_execution_manifest(
    manifest: dict[str,Any], *, foundation_model: str, foundation_revision: str,
    dataset_sha256: str, training_code_revision: str, training_config: dict[str,Any],
) -> list[str]:
    """Validate run-specific compute, budget, and configuration approval."""
    errors=[]
    if not isinstance(manifest,dict) or manifest.get("schema_version")!=EXECUTION_SCHEMA:
        return ["unsupported_or_missing_training_execution_schema"]
    if manifest.get("status")!="approved": errors.append("training execution is not approved")
    bindings={
        "student_model_id":"core-prime",
        "foundation_model":foundation_model,
        "foundation_revision":foundation_revision,
        "dataset_sha256":dataset_sha256,
        "training_code_revision":training_code_revision,
    }
    for field,expected in bindings.items():
        if manifest.get(field)!=expected: errors.append(f"training execution {field} mismatch")
    if not manifest.get("run_id"): errors.append("training execution run_id missing")
    if not manifest.get("approved_by") or not manifest.get("approval_reference") or not _time(manifest.get("approved_at")):
        errors.append("training execution approval provenance missing")
    if not _sha(manifest.get("approval_document_sha256")): errors.append("training execution approval document digest missing")
    if manifest.get("approved_configuration")!=training_config:
        errors.append("training configuration differs from approved configuration")
    budget=manifest.get("budget")
    if not isinstance(budget,dict): budget={}
    cost=budget.get("maximum_cost_usd")
    runtime=budget.get("maximum_runtime_seconds")
    if (isinstance(cost,bool) or not isinstance(cost,(int,float)) or cost<0 or
        isinstance(runtime,bool) or not isinstance(runtime,int) or runtime<=0):
        errors.append("training budget cap is missing or invalid")
    if budget.get("currency")!="USD" or not _sha(budget.get("pricing_evidence_sha256")) or not budget.get("budget_reference"):
        errors.append("training budget evidence is incomplete")
    compute=manifest.get("compute")
    if not isinstance(compute,dict): compute={}
    for field in ("provider","account_or_project","region","runner_type","accelerator_type","runtime_image"):
        if not isinstance(compute.get(field),str) or not compute[field].strip():
            errors.append(f"training compute field missing:{field}")
    devices=compute.get("accelerator_count")
    if isinstance(devices,bool) or not isinstance(devices,int) or devices<1:
        errors.append("training accelerator count invalid")
    versions=compute.get("software_versions")
    required_versions={"python","torch","transformers","datasets","peft","accelerate"}
    if not isinstance(versions,dict) or not required_versions.issubset(versions) or any(not versions.get(k) for k in required_versions):
        errors.append("training software versions incomplete")
    if not _sha(compute.get("runtime_image_sha256")): errors.append("training runtime image digest missing")
    capacity=manifest.get("capacity")
    if not isinstance(capacity,dict): capacity={}
    resource_fields=("available_vram_bytes","available_ram_bytes","available_storage_bytes",
                     "estimated_peak_vram_bytes","estimated_peak_ram_bytes","estimated_storage_bytes")
    values={field:capacity.get(field) for field in resource_fields}
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in values.values()):
        errors.append("training capacity measurements are invalid")
    elif (values["available_ram_bytes"]<=0 or values["available_storage_bytes"]<=0 or
          values["estimated_peak_vram_bytes"]>values["available_vram_bytes"] or
          values["estimated_peak_ram_bytes"]>values["available_ram_bytes"] or
          values["estimated_storage_bytes"]>values["available_storage_bytes"]):
        errors.append("training resource estimate exceeds measured capacity")
    if not _sha(capacity.get("resource_probe_sha256")): errors.append("training resource probe digest missing")
    return errors
