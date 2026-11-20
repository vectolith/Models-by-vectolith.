#!/usr/bin/env python3
"""Reproducible baseline evaluator; outputs raw per-task records and integrity summary."""
from __future__ import annotations
import argparse, hashlib, json, math, platform, random, sys, time, uuid, importlib.metadata, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import evaluation_gate

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def sha256_text(s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()
def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def sha256_serialized(value: Any) -> str:
    text=value if isinstance(value,str) else json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return sha256_text(text)
def seed_python(seed: int) -> None: random.seed(seed)
def append_jsonl(path: Path, record: dict[str,Any]) -> None:
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(record,ensure_ascii=False)+"\n")
        f.flush();os.fsync(f.fileno())
def write_jsonl(path: Path, records: list[dict[str,Any]]) -> None:
    temp=path.with_suffix(path.suffix+".tmp")
    with temp.open("w",encoding="utf-8") as f:
        for record in records: f.write(json.dumps(record,ensure_ascii=False)+"\n")
        f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
def write_json(path: Path, record: dict[str,Any]) -> None:
    temp=path.with_suffix(path.suffix+".tmp")
    with temp.open("w",encoding="utf-8") as f:
        f.write(json.dumps(record,indent=2,ensure_ascii=False));f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
def package_version(name: str) -> str | None:
    try: return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: return None
def package_inventory() -> list[dict[str,str]]:
    items=[]
    for dist in importlib.metadata.distributions():
        name=dist.metadata.get("Name") or dist.name or "unknown"
        items.append({"name":name,"version":dist.version})
    return sorted(items,key=lambda item:(item["name"].lower(),item["version"]))
def package_inventory_snapshot() -> tuple[list[dict[str,str]],str]:
    inventory=package_inventory()
    return inventory,sha256_serialized(inventory)
def load_jsonl_snapshot(path: Path) -> tuple[list[dict[str,Any]],str]:
    raw=path.read_bytes()
    try:text=raw.decode("utf-8")
    except UnicodeDecodeError as e:raise ValueError(f"{path}: invalid UTF-8: {e}") from e
    rows=[]
    allowed_fields={"task_id","category","prompt","split","rubric_id","reference_answer","expected_constraints","provenance","content_sha256"}
    for n,line in enumerate(text.splitlines(),1):
        if not line.strip(): continue
        try: row=json.loads(line)
        except json.JSONDecodeError as e: raise ValueError(f"{path}:{n}: invalid JSON: {e}") from e
        if not isinstance(row,dict): raise ValueError(f"{path}:{n}: expected object")
        unknown=set(row)-allowed_fields
        if unknown: raise ValueError(f"{path}:{n}: unexpected task fields: {sorted(unknown)}")
        for k in ("task_id","prompt","category","rubric_id","provenance"):
            if not isinstance(row.get(k),str) or not row[k].strip(): raise ValueError(f"{path}:{n}: invalid {k}")
        if row.get("split") not in ("train","development","holdout"): raise ValueError(f"{path}:{n}: invalid split")
        if "reference_answer" in row and row["reference_answer"] is not None and not isinstance(row["reference_answer"],str): raise ValueError(f"{path}:{n}: reference_answer must be text or null")
        if "expected_constraints" in row and (not isinstance(row["expected_constraints"],list) or any(not isinstance(item,str) for item in row["expected_constraints"])): raise ValueError(f"{path}:{n}: expected_constraints must be a string array")
        if "content_sha256" in row and row["content_sha256"] is not None:
            digest=row["content_sha256"]
            if not isinstance(digest,str) or not evaluation_gate.SHA64.fullmatch(digest): raise ValueError(f"{path}:{n}: content_sha256 must be a lowercase SHA-256 or null")
            if digest!=sha256_text(row["prompt"]): raise ValueError(f"{path}:{n}: content_sha256 mismatch")
        rows.append(row)
    ids=[r["task_id"] for r in rows]
    if len(ids)!=len(set(ids)): raise ValueError("task_id values must be unique")
    return rows,sha256_bytes(raw)
def load_jsonl(path: Path) -> list[dict[str,Any]]:
    return load_jsonl_snapshot(path)[0]

def verify_frozen_config(manifest_path: Path, model: str, revision: str, tasks_sha256: str, seed: int, max_new_tokens: int, temperature: float, trust_remote_code: bool, qwen3_thinking: bool, limit: int, selected_task_ids: list[str], candidate_sha: str, code_commit: str, package_hash: str, max_wall_seconds: int, manifest_snapshot=None, manifest_sha256=None) -> str:
    return evaluation_gate.verify_frozen_config(manifest_path,model,revision,tasks_sha256,seed,max_new_tokens,temperature,trust_remote_code,qwen3_thinking,limit,selected_task_ids,candidate_sha,code_commit,package_hash,max_wall_seconds,manifest_snapshot,manifest_sha256)


def validate_qwen3_thinking_mode(snapshot: Path, enabled: bool) -> None:
    """Reject a frozen thinking-mode setting that the snapshot cannot support."""
    if not enabled:
        return
    config_path=snapshot/"config.json"
    if not config_path.is_file():
        raise ValueError("Qwen3 thinking mode requires config.json in the verified local snapshot")
    try:
        config=json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"verified model config is invalid: {exc}") from exc
    model_type=config.get("model_type") if isinstance(config,dict) else None
    if not isinstance(model_type,str) or not model_type.lower().startswith("qwen3"):
        raise ValueError("--qwen3-thinking is only supported for a verified Qwen3-family config")

def initialization_failure_records(run_id: str, tasks: list[dict[str,Any]], error: Exception, status: str="initialization_failed") -> list[dict[str,Any]]:
    return [{"run_id":run_id,"task_id":task["task_id"],"category":task["category"],"split":task["split"],
        "prompt_sha256":sha256_text(task["prompt"]),"status":status,"error":repr(error)}
        for task in tasks]

def new_run_id() -> str:
    return "cp001-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]

def tally_records(records: list[dict[str,Any]], task_count: int, expected_task_ids: list[str] | None = None) -> tuple[int,int,str]:
    by_id={}
    for record in records:
        by_id.setdefault(record.get("task_id"),[]).append(record)
    expected=set(expected_task_ids) if expected_task_ids is not None else None
    ambiguous=sum(len(group)!=1 or not group[0].get("task_id") for group in by_id.values())
    completed_ids=sum(len(group)==1 and group[0].get("status")=="completed" and (expected is None or task_id in expected) for task_id,group in by_id.items())
    completed=min(completed_ids,task_count)
    accounted=len(by_id)
    missing=max(0,task_count-accounted)
    excess=max(0,accounted-task_count)
    missing_expected=len(expected-set(by_id)) if expected is not None else 0
    extra_unexpected=len(set(by_id)-expected) if expected is not None else 0
    failed=max(task_count-completed,ambiguous,missing,excess,missing_expected,extra_unexpected)
    clean=completed==task_count and failed==0 and len(records)==task_count and accounted==task_count and (expected is None or set(by_id)==expected)
    status="completed" if clean else ("failed" if completed==0 else "partial")
    return completed,failed,status

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",required=True);p.add_argument("--revision",required=True)
    p.add_argument("--tasks",required=True,type=Path);p.add_argument("--output",required=True,type=Path)
    p.add_argument("--max-new-tokens",type=int,default=256);p.add_argument("--temperature",type=float,default=0.0)
    p.add_argument("--limit",type=int,default=0);p.add_argument("--trust-remote-code",action="store_true")
    p.add_argument("--seed",type=int,default=42,help="Seed for Python and PyTorch RNGs (default: 42)")
    p.add_argument("--allow-holdout",action="store_true",help="deprecated; holdout access is disabled until a separately reviewed authorization mechanism exists")
    p.add_argument("--freeze-manifest",required=True,type=Path,help="immutable configuration manifest matching this evaluation run")
    p.add_argument("--candidate-record",required=True,type=Path)
    p.add_argument("--authorization",required=True,type=Path)
    p.add_argument("--code-commit",required=True)
    p.add_argument("--qwen3-thinking",action="store_true",help="Enable Qwen3 thinking mode; default disabled when template supports it")
    a=p.parse_args()
    if a.max_new_tokens<=0:p.error("--max-new-tokens must be positive")
    if not math.isfinite(a.temperature):p.error("--temperature must be finite")
    if a.temperature<0:p.error("--temperature cannot be negative")
    if a.seed<0:p.error("--seed must be non-negative")
    if a.limit<0:p.error("--limit must be non-negative")
    if a.trust_remote_code:p.error("--trust-remote-code is forbidden; verified local snapshots are loaded with remote code disabled")
    if not evaluation_gate.SHA40.fullmatch(a.code_commit):p.error("--code-commit must be a 40-character lowercase SHA")
    try:actual_code_commit=evaluation_gate.git_head()
    except Exception as e:p.error(f"Git commit capture failed: {e}")
    if actual_code_commit!=a.code_commit:p.error("--code-commit does not match evaluator checkout HEAD")
    tasks,task_hash=load_jsonl_snapshot(a.tasks)
    if any(t["split"]=="holdout" for t in tasks):p.error("holdout inference blocked; this evaluator has no reviewed holdout authorization mechanism")
    if any(t["split"]!="development" for t in tasks):p.error("baseline inference requires development-only task records")
    if a.limit>0:tasks=tasks[:a.limit]
    if not tasks:p.error("no tasks")
    selected_task_ids=[t["task_id"] for t in tasks]
    selected_task_ids_sha256=sha256_serialized(selected_task_ids)
    try:
        freeze_manifest_snapshot,freeze_manifest_sha256=evaluation_gate.load_json_snapshot(a.freeze_manifest,"freeze manifest")
        candidate,candidate_sha,snapshot=evaluation_gate.verify_candidate_record(a.candidate_record,a.model,a.revision)
        validate_qwen3_thinking_mode(snapshot,bool(a.qwen3_thinking))
        inventory,inventory_sha256=package_inventory_snapshot()
        authorization,authorization_sha256=evaluation_gate.verify_evaluation_authorization(a.authorization,candidate_sha,task_hash,a.freeze_manifest,a.code_commit,inventory_sha256,len(tasks),a.max_new_tokens,freeze_manifest_sha256)
        max_wall_seconds=authorization["budget"]["max_wall_seconds"]
        if authorization.get("candidate_revision")!=a.revision:raise ValueError("authorization candidate revision mismatch")
        freeze_sha=verify_frozen_config(a.freeze_manifest,a.model,a.revision,task_hash,a.seed,a.max_new_tokens,a.temperature,a.trust_remote_code,bool(a.qwen3_thinking),a.limit,selected_task_ids,candidate_sha,a.code_commit,inventory_sha256,max_wall_seconds,freeze_manifest_snapshot,freeze_manifest_sha256)
    except Exception as e:p.error(f"evaluation permission/reproducibility gate blocked: {e}")
    a.output.mkdir(parents=True,exist_ok=True)
    run_id=new_run_id()
    raw=a.output/f"{run_id}-raw.jsonl";summary_file=a.output/f"{run_id}-summary.json"
    started=time.time();run_started_monotonic=time.monotonic()
    try:
        import torch
        import transformers
        from transformers import AutoModelForCausalLM,AutoTokenizer,StoppingCriteria
    except Exception as e:
        records=initialization_failure_records(run_id,tasks,e,status="dependency_blocked")
        write_jsonl(raw,records)
        summary={"run_id":run_id,"status":"blocked","error":repr(e),"task_file_sha256":task_hash,
            "task_count":len(tasks),"completed_count":0,"failed_count":len(tasks),"raw_file":str(raw),
            "raw_file_sha256":sha256_file(raw),"model":a.model,"revision":a.revision,"seed":a.seed,
            "effective_limit":a.limit,"selected_task_count":len(selected_task_ids),"selected_task_ids_sha256":selected_task_ids_sha256,
            "freeze_manifest":str(a.freeze_manifest.resolve()),"freeze_manifest_sha256":freeze_sha,
            "candidate_record_sha256":candidate_sha,"authorization_sha256":authorization_sha256,"code_commit":a.code_commit,"max_wall_seconds":max_wall_seconds,
            "package_inventory":inventory,"package_inventory_sha256":inventory_sha256}
        write_json(summary_file,summary);print(json.dumps(summary,indent=2));return 2
    seed_python(a.seed)
    torch.manual_seed(a.seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(a.seed)
    records=[];errors=0;device="cpu";hardware=platform.processor() or platform.machine();model=None;tokenizer=None
    try:
        device="cuda" if torch.cuda.is_available() else "cpu"
        hardware=torch.cuda.get_device_name(0) if device=="cuda" else (platform.processor() or platform.machine())
        tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False)
        model=AutoModelForCausalLM.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False,
            torch_dtype="auto",device_map="auto" if device=="cuda" else None)
        if device=="cpu":model.to(device)
        model.eval()
        if device=="cuda":torch.cuda.reset_peak_memory_stats()
    except Exception as e:
        errors=len(tasks)
        records=initialization_failure_records(run_id,tasks,e)
    if model is not None and tokenizer is not None:
        class WallBudgetStoppingCriteria(StoppingCriteria):
            def __call__(self,input_ids,scores,**kwargs):return time.monotonic()-run_started_monotonic>=max_wall_seconds
        for task_index,task in enumerate(tasks):
            if time.monotonic()-run_started_monotonic>=max_wall_seconds:
                exhausted=[{"run_id":run_id,"task_id":remaining["task_id"],"category":remaining["category"],"split":remaining["split"],"prompt_sha256":sha256_text(remaining["prompt"]),"status":"budget_exhausted"} for remaining in tasks[task_index:]]
                records.extend(exhausted)
                for item in exhausted:append_jsonl(raw,item)
                break
            prompt=task["prompt"];t0=time.perf_counter()
            try:
                if getattr(tokenizer,"chat_template",None):
                    messages=[{"role":"user","content":prompt}]
                    template_kwargs={"tokenize":False,"add_generation_prompt":True}
                    if "qwen3" in str(getattr(model.config,"model_type","")).lower():
                        template_kwargs["enable_thinking"]=bool(a.qwen3_thinking)
                    encoded=tokenizer.apply_chat_template(messages,**template_kwargs)
                    inputs=tokenizer(encoded,return_tensors="pt",add_special_tokens=False)
                else:
                    encoded=f"User:\n{prompt}\nAssistant:\n"
                    inputs=tokenizer(encoded,return_tensors="pt",add_special_tokens=False)
                model_device=model.get_input_embeddings().weight.device
                inputs={k:v.to(model_device) for k,v in inputs.items()}
                input_tokens=int(inputs["input_ids"].shape[-1])
                if device=="cuda":torch.cuda.synchronize()
                generation={"max_new_tokens":a.max_new_tokens,"do_sample":a.temperature>0,"stopping_criteria":[WallBudgetStoppingCriteria()]}
                if a.temperature>0:generation["temperature"]=a.temperature
                with torch.inference_mode():out=model.generate(**inputs,**generation)
                if device=="cuda":torch.cuda.synchronize()
                elapsed=time.perf_counter()-t0;new=out[0][input_tokens:];response=tokenizer.decode(new,skip_special_tokens=True)
                record={"run_id":run_id,"task_id":task["task_id"],"category":task["category"],"split":task["split"],
                    "prompt_sha256":sha256_text(prompt),"prompt":prompt,"response":response,"response_sha256":sha256_text(response),
                    "input_tokens":input_tokens,"output_tokens":int(new.shape[-1]),"generation_seconds":elapsed,
                    "tokens_per_second":int(new.shape[-1])/elapsed if elapsed else None,"status":"completed"}
                if time.monotonic()-run_started_monotonic>=max_wall_seconds:record["status"]="budget_exhausted"
                records.append(record);append_jsonl(raw,record)
            except Exception as e:
                errors+=1
                record={"run_id":run_id,"task_id":task["task_id"],"category":task["category"],"split":task["split"],
                    "prompt_sha256":sha256_text(prompt),"status":"failed","error":repr(e),"generation_seconds":time.perf_counter()-t0}
                records.append(record);append_jsonl(raw,record)
    write_jsonl(raw,records)
    completed,failed,status=tally_records(records,len(tasks),selected_task_ids)
    capture_warnings=[];peak_memory=None;config_hash=None;template_hash=None
    if device=="cuda":
        try:peak_memory=torch.cuda.max_memory_allocated()
        except Exception as e:capture_warnings.append("CUDA peak memory capture failed: "+repr(e))
    if model is not None:
        try:
            config_text=model.config.to_json_string() if hasattr(model.config,"to_json_string") else json.dumps(model.config.to_dict(),sort_keys=True)
            config_hash=sha256_text(config_text)
        except Exception as e:capture_warnings.append("Model config hash capture failed: "+repr(e))
    if tokenizer is not None:
        try:
            template_text=getattr(tokenizer,"chat_template",None)
            template_hash=sha256_serialized(template_text) if template_text else None
        except Exception as e:capture_warnings.append("Chat-template hash capture failed: "+repr(e))
    summary={"run_id":run_id,"status":status,"model":a.model,"revision":a.revision,"task_file":str(a.tasks),
        "task_file_sha256":task_hash,"task_count":len(tasks),"completed_count":completed,"failed_count":failed,
        "device":device,"hardware":hardware,"peak_cuda_memory_allocated_bytes":peak_memory,
        "python":sys.version,"platform":platform.platform(),"torch_version":torch.__version__,"transformers_version":transformers.__version__,
        "accelerate_version":package_version("accelerate"),"safetensors_version":package_version("safetensors"),
        "seed":a.seed,"seed_scope":"Python and PyTorch CPU/CUDA RNGs; deterministic kernels are not guaranteed",
        "effective_limit":a.limit,"selected_task_count":len(selected_task_ids),"selected_task_ids_sha256":selected_task_ids_sha256,
        "package_inventory":inventory,"package_inventory_sha256":inventory_sha256,
        "model_config_sha256":config_hash,"chat_template_sha256":template_hash,"capture_warnings":capture_warnings,
        "started_at_epoch":started,"duration_seconds":time.time()-started,"max_new_tokens":a.max_new_tokens,
        "temperature":a.temperature,"qwen3_thinking":bool(a.qwen3_thinking),"trust_remote_code":a.trust_remote_code,
        "freeze_manifest":str(a.freeze_manifest.resolve()),"freeze_manifest_sha256":freeze_sha,"candidate_record_sha256":candidate_sha,"authorization_sha256":authorization_sha256,"code_commit":a.code_commit,"max_wall_seconds":max_wall_seconds,"raw_file":str(raw),"raw_file_sha256":sha256_file(raw)}
    write_json(summary_file,summary);print(json.dumps(summary,indent=2))
    return 0 if status=="completed" else 1
if __name__=="__main__":raise SystemExit(main())
