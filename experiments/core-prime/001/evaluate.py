#!/usr/bin/env python3
"""Reproducible baseline evaluator; outputs raw per-task records and integrity summary."""
from __future__ import annotations
import argparse, hashlib, json, math, platform, random, sys, time, uuid, importlib.metadata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def sha256_text(s: str) -> str: return hashlib.sha256(s.encode("utf-8")).hexdigest()
def sha256_serialized(value: Any) -> str:
    text=value if isinstance(value,str) else json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return sha256_text(text)
def seed_python(seed: int) -> None: random.seed(seed)
def write_jsonl(path: Path, records: list[dict[str,Any]]) -> None:
    with path.open("w",encoding="utf-8") as f:
        for record in records: f.write(json.dumps(record,ensure_ascii=False)+"\n")
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
def load_jsonl(path: Path) -> list[dict[str,Any]]:
    rows=[]
    with path.open(encoding="utf-8") as f:
        for n,line in enumerate(f,1):
            if not line.strip(): continue
            try: row=json.loads(line)
            except json.JSONDecodeError as e: raise ValueError(f"{path}:{n}: invalid JSON: {e}") from e
            if not isinstance(row,dict): raise ValueError(f"{path}:{n}: expected object")
            for k in ("task_id","prompt","category"):
                if not isinstance(row.get(k),str) or not row[k].strip(): raise ValueError(f"{path}:{n}: invalid {k}")
            if row.get("split") not in ("train","development","holdout"): raise ValueError(f"{path}:{n}: invalid split")
            rows.append(row)
    ids=[r["task_id"] for r in rows]
    if len(ids)!=len(set(ids)): raise ValueError("task_id values must be unique")
    return rows

def verify_frozen_config(manifest_path: Path, model: str, revision: str, tasks_path: Path, seed: int, max_new_tokens: int, temperature: float, trust_remote_code: bool, qwen3_thinking: bool, limit: int, selected_task_ids: list[str]) -> str:
    try: manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e: raise ValueError(f"freeze manifest invalid: {e}") from e
    expected={"model":model,"revision":revision,"tasks_sha256":sha256_file(tasks_path),"seed":seed,"max_new_tokens":max_new_tokens,"temperature":temperature,"trust_remote_code":trust_remote_code,"qwen3_thinking":qwen3_thinking,"limit":limit,"selected_task_count":len(selected_task_ids),"selected_task_ids_sha256":sha256_serialized(selected_task_ids)}
    for key,value in expected.items():
        if manifest.get(key)!=value: raise ValueError(f"freeze manifest mismatch: {key}")
    return sha256_file(manifest_path)

def initialization_failure_records(run_id: str, tasks: list[dict[str,Any]], error: Exception, status: str="initialization_failed") -> list[dict[str,Any]]:
    return [{"run_id":run_id,"task_id":task["task_id"],"category":task["category"],"split":task["split"],
        "prompt_sha256":sha256_text(task["prompt"]),"status":status,"error":repr(error)}
        for task in tasks]

def new_run_id() -> str:
    return "cp001-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]

def tally_records(records: list[dict[str,Any]], task_count: int) -> tuple[int,int,str]:
    by_id={}
    for record in records:
        by_id.setdefault(record.get("task_id"),[]).append(record)
    ambiguous=sum(len(group)!=1 or not group[0].get("task_id") for group in by_id.values())
    completed_ids=sum(len(group)==1 and group[0].get("status")=="completed" for group in by_id.values())
    completed=min(completed_ids,task_count)
    accounted=len(by_id)
    missing=max(0,task_count-accounted)
    excess=max(0,accounted-task_count)
    failed=max(task_count-completed,ambiguous,missing,excess)
    clean=completed==task_count and failed==0 and len(records)==task_count and accounted==task_count
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
    p.add_argument("--qwen3-thinking",action="store_true",help="Enable Qwen3 thinking mode; default disabled when template supports it")
    a=p.parse_args()
    if a.max_new_tokens<=0:p.error("--max-new-tokens must be positive")
    if not math.isfinite(a.temperature):p.error("--temperature must be finite")
    if a.temperature<0:p.error("--temperature cannot be negative")
    if a.seed<0:p.error("--seed must be non-negative")
    if a.limit<0:p.error("--limit must be non-negative")
    tasks=load_jsonl(a.tasks)
    if any(t["split"]=="holdout" for t in tasks):p.error("holdout inference blocked; this evaluator has no reviewed holdout authorization mechanism")
    if a.limit>0:tasks=tasks[:a.limit]
    if not tasks:p.error("no tasks")
    selected_task_ids=[t["task_id"] for t in tasks]
    selected_task_ids_sha256=sha256_serialized(selected_task_ids)
    try: freeze_sha=verify_frozen_config(a.freeze_manifest,a.model,a.revision,a.tasks,a.seed,a.max_new_tokens,a.temperature,a.trust_remote_code,bool(a.qwen3_thinking),a.limit,selected_task_ids)
    except Exception as e:p.error(f"evaluation configuration not frozen: {e}")
    a.output.mkdir(parents=True,exist_ok=True);task_hash=sha256_file(a.tasks)
    run_id=new_run_id()
    raw=a.output/f"{run_id}-raw.jsonl";summary_file=a.output/f"{run_id}-summary.json"
    started=time.time()
    try:
        import torch
        import transformers
        from transformers import AutoModelForCausalLM,AutoTokenizer
    except Exception as e:
        records=initialization_failure_records(run_id,tasks,e,status="dependency_blocked")
        write_jsonl(raw,records)
        inventory,inventory_sha256=package_inventory_snapshot()
        summary={"run_id":run_id,"status":"blocked","error":repr(e),"task_file_sha256":task_hash,
            "task_count":len(tasks),"completed_count":0,"failed_count":len(tasks),"raw_file":str(raw),
            "raw_file_sha256":sha256_file(raw),"model":a.model,"revision":a.revision,"seed":a.seed,
            "effective_limit":a.limit,"selected_task_count":len(selected_task_ids),"selected_task_ids_sha256":selected_task_ids_sha256,
            "freeze_manifest":str(a.freeze_manifest.resolve()),"freeze_manifest_sha256":freeze_sha,
            "package_inventory":inventory,"package_inventory_sha256":inventory_sha256}
        summary_file.write_text(json.dumps(summary,indent=2),encoding="utf-8");print(json.dumps(summary,indent=2));return 2
    seed_python(a.seed)
    torch.manual_seed(a.seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(a.seed)
    records=[];errors=0;device="cpu";hardware=platform.processor() or platform.machine();model=None;tokenizer=None
    try:
        device="cuda" if torch.cuda.is_available() else "cpu"
        hardware=torch.cuda.get_device_name(0) if device=="cuda" else (platform.processor() or platform.machine())
        tokenizer=AutoTokenizer.from_pretrained(a.model,revision=a.revision,trust_remote_code=a.trust_remote_code)
        model=AutoModelForCausalLM.from_pretrained(a.model,revision=a.revision,trust_remote_code=a.trust_remote_code,
            torch_dtype="auto",device_map="auto" if device=="cuda" else None)
        if device=="cpu":model.to(device)
        model.eval()
        if device=="cuda":torch.cuda.reset_peak_memory_stats()
    except Exception as e:
        errors=len(tasks)
        records=initialization_failure_records(run_id,tasks,e)
    if model is not None and tokenizer is not None:
        for task in tasks:
            prompt=task["prompt"];t0=time.perf_counter()
            try:
                if getattr(tokenizer,"chat_template",None):
                    messages=[{"role":"user","content":prompt}]
                    template_kwargs={"tokenize":False,"add_generation_prompt":True}
                    if "qwen3" in str(getattr(model.config,"model_type","")).lower():
                        template_kwargs["enable_thinking"]=bool(a.qwen3_thinking)
                    encoded=tokenizer.apply_chat_template(messages,**template_kwargs)
                    inputs=tokenizer(encoded,return_tensors="pt")
                else:inputs=tokenizer(prompt,return_tensors="pt")
                model_device=model.get_input_embeddings().weight.device
                inputs={k:v.to(model_device) for k,v in inputs.items()}
                input_tokens=int(inputs["input_ids"].shape[-1])
                if device=="cuda":torch.cuda.synchronize()
                generation={"max_new_tokens":a.max_new_tokens,"do_sample":a.temperature>0}
                if a.temperature>0:generation["temperature"]=a.temperature
                with torch.inference_mode():out=model.generate(**inputs,**generation)
                if device=="cuda":torch.cuda.synchronize()
                elapsed=time.perf_counter()-t0;new=out[0][input_tokens:];response=tokenizer.decode(new,skip_special_tokens=True)
                records.append({"run_id":run_id,"task_id":task["task_id"],"category":task["category"],"split":task["split"],
                    "prompt_sha256":sha256_text(prompt),"prompt":prompt,"response":response,"response_sha256":sha256_text(response),
                    "input_tokens":input_tokens,"output_tokens":int(new.shape[-1]),"generation_seconds":elapsed,
                    "tokens_per_second":int(new.shape[-1])/elapsed if elapsed else None,"status":"completed"})
            except Exception as e:
                errors+=1
                records.append({"run_id":run_id,"task_id":task["task_id"],"category":task["category"],"split":task["split"],
                    "prompt_sha256":sha256_text(prompt),"status":"failed","error":repr(e),"generation_seconds":time.perf_counter()-t0})
    write_jsonl(raw,records)
    completed,failed,status=tally_records(records,len(tasks))
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
        "package_inventory":package_inventory_snapshot()[0],"package_inventory_sha256":package_inventory_snapshot()[1],
        "model_config_sha256":config_hash,"chat_template_sha256":template_hash,"capture_warnings":capture_warnings,
        "started_at_epoch":started,"duration_seconds":time.time()-started,"max_new_tokens":a.max_new_tokens,
        "temperature":a.temperature,"qwen3_thinking":bool(a.qwen3_thinking),"trust_remote_code":a.trust_remote_code,
        "freeze_manifest":str(a.freeze_manifest.resolve()),"freeze_manifest_sha256":freeze_sha,"raw_file":str(raw),"raw_file_sha256":sha256_file(raw)}
    summary_file.write_text(json.dumps(summary,indent=2),encoding="utf-8");print(json.dumps(summary,indent=2))
    return 0 if status=="completed" else 1
if __name__=="__main__":raise SystemExit(main())
