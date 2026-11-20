#!/usr/bin/env python3
"""Integrity gates for baseline inference; this module does not decide legal rights."""
from __future__ import annotations
import hashlib,json,re,subprocess
from pathlib import Path
SHA40=re.compile(r"^[a-f0-9]{40}$")
SHA64=re.compile(r"^[a-f0-9]{64}$")
def sha256_file(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def sha256_serialized(value):
 text=value if isinstance(value,str) else json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"))
 return hashlib.sha256(text.encode("utf-8")).hexdigest()
def load_json_snapshot(path,label):
 raw=Path(path).read_bytes()
 try:text=raw.decode("utf-8")
 except UnicodeDecodeError as exc:raise ValueError(f"{label} invalid UTF-8: {exc}") from exc
 try:record=json.loads(text)
 except Exception as exc:raise ValueError(f"{label} invalid JSON: {exc}") from exc
 if not isinstance(record,dict):raise ValueError(f"{label} must be a JSON object")
 return record,hashlib.sha256(raw).hexdigest()
def git_head():
 root=Path(__file__).resolve().parents[3]
 result=subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True,check=True)
 return result.stdout.strip()
def verify_evidence_file(base,relative,digest,label):
 if not isinstance(relative,str) or not relative.strip():raise ValueError(f"{label} evidence path missing")
 rel=Path(relative)
 if rel.is_absolute() or ".." in rel.parts:raise ValueError(f"{label} evidence path must be relative and confined")
 if not isinstance(digest,str) or not SHA64.fullmatch(digest):raise ValueError(f"{label} evidence SHA-256 invalid")
 root=Path(base).resolve();cursor=root
 for part in rel.parts:
  cursor=cursor/part
  if cursor.is_symlink():raise ValueError(f"{label} evidence path contains symlink components")
 target=(root/rel).resolve()
 try:target.relative_to(root)
 except ValueError:raise ValueError(f"{label} evidence path escapes evidence root")
 if not target.is_file():raise ValueError(f"{label} evidence file missing")
 if sha256_file(target)!=digest:raise ValueError(f"{label} evidence hash mismatch")
 return target
def verify_model_snapshot(record,record_path):
 root=record_path.parent.resolve()
 rel=record.get("model_snapshot_path")
 if not isinstance(rel,str) or not rel.strip():raise ValueError("candidate model_snapshot_path missing")
 relpath=Path(rel)
 if relpath.is_absolute() or ".." in relpath.parts:raise ValueError("model snapshot path must be relative and confined")
 raw_snapshot=root/relpath
 cursor=root
 for part in relpath.parts:
  cursor=cursor/part
  if cursor.is_symlink():raise ValueError("model snapshot path contains symlink components")
 snapshot=raw_snapshot.resolve()
 try:snapshot.relative_to(root)
 except ValueError:raise ValueError("model snapshot path escapes candidate root")
 if not snapshot.is_dir() or snapshot.is_symlink():raise ValueError("local model snapshot directory missing or unsafe")
 inventory=record.get("weight_inventory")
 if not isinstance(inventory,list) or not inventory:raise ValueError("candidate snapshot inventory missing")
 expected={}
 for item in inventory:
  if not isinstance(item,dict) or set(item)!={"path","sha256"}:raise ValueError("candidate snapshot inventory malformed")
  relfile=Path(item["path"])
  if relfile.is_absolute() or ".." in relfile.parts:raise ValueError("snapshot inventory path must be relative and confined")
  if item["path"] in expected:raise ValueError("snapshot inventory contains duplicate path")
  target=verify_evidence_file(root,item["path"],item["sha256"],"candidate snapshot")
  try:target.relative_to(snapshot)
  except ValueError:raise ValueError("snapshot inventory path is outside model snapshot")
  expected[item["path"]]=item["sha256"]
 actual={}
 for path in sorted(snapshot.rglob("*")):
  if path.is_symlink():raise ValueError("model snapshot contains symlinks")
  if path.is_file():actual[str(path.relative_to(root))]=sha256_file(path)
 if set(expected)!=set(actual):raise ValueError("model snapshot inventory incomplete or contains unlisted files")
 for path,digest in expected.items():
  if actual[path]!=digest:raise ValueError(f"model snapshot hash mismatch: {path}")
 return snapshot
def verify_candidate_record(path,model,revision):
 record,candidate_sha=load_json_snapshot(path,"candidate record")
 if record.get("status")!="verified":raise ValueError("candidate status is not verified")
 if record.get("output_training_permission")!="verified":raise ValueError("output-training permission gate not verified")
 if record.get("human_legal_review")!="approved":raise ValueError("independent human legal review not approved")
 if record.get("compatibility_status")!="compatible":raise ValueError("candidate compatibility gate not compatible")
 if record.get("repository_id")!=model or record.get("revision")!=revision:raise ValueError("candidate repository/revision mismatch")
 if not isinstance(revision,str) or not SHA40.fullmatch(revision):raise ValueError("model revision must be an immutable 40-character SHA")
 if record.get("tokenizer_revision")!=revision or not record.get("license_identifier"):raise ValueError("candidate license/tokenizer evidence incomplete")
 config_targets=[]
 for path_key,hash_key,label in (("license_evidence_path","license_evidence_sha256","license"),("output_training_permission_evidence_path","output_training_permission_evidence_sha256","output-training permission"),("human_legal_review_evidence_path","human_legal_review_evidence_sha256","legal review"),("model_config_evidence_path","model_config_sha256","model config"),("chat_template_evidence_path","chat_template_sha256","chat template")):
  target=verify_evidence_file(path.parent,record.get(path_key),record.get(hash_key),label)
  if label in ("model config","chat template"):config_targets.append(target)
 snapshot=verify_model_snapshot(record,path)
 for target in config_targets:
  try:target.relative_to(snapshot)
  except ValueError:raise ValueError("model config/chat template evidence must be inside verified snapshot")
 return record,candidate_sha,snapshot
def verify_evaluation_authorization(path,candidate_sha,tasks_sha256,freeze_path,code_commit,package_hash,task_count,max_new_tokens,freeze_manifest_sha256=None):
 authorization,authorization_sha=load_json_snapshot(path,"evaluation authorization")
 if authorization.get("approval")!="approved":raise ValueError("evaluation authorization not approved")
 if not isinstance(tasks_sha256,str) or not SHA64.fullmatch(tasks_sha256):raise ValueError("exact loaded task snapshot SHA-256 invalid")
 expected={"candidate_record_sha256":candidate_sha,"tasks_sha256":tasks_sha256,"freeze_manifest_sha256":freeze_manifest_sha256 if freeze_manifest_sha256 is not None else sha256_file(freeze_path),"code_commit":code_commit,"package_inventory_sha256":package_hash}
 for key,value in expected.items():
  if authorization.get(key)!=value:raise ValueError(f"evaluation authorization mismatch: {key}")
 if not isinstance(authorization.get("candidate_revision"),str):raise ValueError("candidate revision missing in authorization")
 if authorization.get("holdout_access") not in ("sealed","denied"):raise ValueError("holdout access must remain sealed")
 provenance=authorization.get("dataset_provenance",{})
 if not isinstance(provenance,dict) or provenance.get("status")!="reviewed":raise ValueError("dataset provenance must be independently reviewed")
 verify_evidence_file(path.parent,provenance.get("evidence_path"),provenance.get("evidence_sha256"),"dataset provenance")
 hardware=authorization.get("hardware",{})
 if hardware.get("verified_free_budget") is not True or not hardware.get("provider") or not hardware.get("session_id"):raise ValueError("verified free compute/session evidence missing")
 verify_evidence_file(path.parent,hardware.get("evidence_path"),hardware.get("evidence_sha256"),"free compute")
 budget=authorization.get("budget",{})
 for key in ("max_task_count","max_new_tokens","max_wall_seconds"):
  value=budget.get(key)
  if isinstance(value,bool) or not isinstance(value,int) or value<=0:raise ValueError(f"evaluation budget {key} must be a positive integer")
 if task_count>budget["max_task_count"]:raise ValueError("selected tasks exceed authorized task budget")
 if max_new_tokens>budget["max_new_tokens"]:raise ValueError("max-new-tokens exceeds authorized budget")
 return authorization,authorization_sha
def verify_frozen_config(manifest_path,model,revision,tasks_sha256,seed,max_new_tokens,temperature,trust_remote_code,qwen3_thinking,limit,selected_task_ids,candidate_sha,code_commit,package_hash,max_wall_seconds,manifest_snapshot=None,manifest_sha256=None):
 if manifest_snapshot is None:manifest_snapshot,manifest_sha256=load_json_snapshot(manifest_path,"freeze manifest")
 manifest=manifest_snapshot
 if not isinstance(manifest,dict):raise ValueError("freeze manifest must be a JSON object")
 if not isinstance(tasks_sha256,str) or not SHA64.fullmatch(tasks_sha256):raise ValueError("exact loaded task snapshot SHA-256 invalid")
 expected={"model":model,"revision":revision,"tasks_sha256":tasks_sha256,"seed":seed,"max_new_tokens":max_new_tokens,"temperature":temperature,"trust_remote_code":trust_remote_code,"qwen3_thinking":qwen3_thinking,"limit":limit,"selected_task_count":len(selected_task_ids),"selected_task_ids_sha256":sha256_serialized(selected_task_ids),"candidate_record_sha256":candidate_sha,"code_commit":code_commit,"package_inventory_sha256":package_hash,"max_wall_seconds":max_wall_seconds}
 for key,value in expected.items():
  if manifest.get(key)!=value:raise ValueError(f"freeze manifest mismatch: {key}")
 return manifest_sha256
