#!/usr/bin/env python3
"""Integrity gates for baseline inference; this module does not decide legal rights."""
from __future__ import annotations
import hashlib,json,re,subprocess,os,stat
from datetime import datetime
from pathlib import Path
SHA40=re.compile(r"^[a-f0-9]{40}$")
SHA64=re.compile(r"^[a-f0-9]{64}$")
MAX_CONFined_EVIDENCE_BYTES=64*1024*1024
def strict_json_loads(text):
 """Parse JSON while rejecting duplicate object keys at every nesting level."""
 def unique_pairs(pairs):
  result={}
  for key,value in pairs:
   if key in result:raise ValueError(f"duplicate JSON object key: {key}")
   result[key]=value
  return result
 def reject_constant(value):
  raise ValueError(f"non-standard JSON numeric constant: {value}")
 return json.loads(text,object_pairs_hook=unique_pairs,parse_constant=reject_constant)
def sha256_file(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def fsync_directory(path):
 """Persist directory-entry changes after atomic replacement on POSIX."""
 directory=Path(path)
 if directory.is_file():directory=directory.parent
 fd=os.open(directory,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def sha256_serialized(value):
 text=value if isinstance(value,str) else json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"))
 return hashlib.sha256(text.encode("utf-8")).hexdigest()
def load_json_snapshot(path,label):
 raw=Path(path).read_bytes()
 try:text=raw.decode("utf-8")
 except UnicodeDecodeError as exc:raise ValueError(f"{label} invalid UTF-8: {exc}") from exc
 try:record=strict_json_loads(text)
 except Exception as exc:raise ValueError(f"{label} invalid JSON: {exc}") from exc
 if not isinstance(record,dict):raise ValueError(f"{label} must be a JSON object")
 return record,hashlib.sha256(raw).hexdigest()
def git_head():
 root=Path(__file__).resolve().parents[3]
 result=subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True,check=True)
 return result.stdout.strip()
def require_confined_open_support(label="evidence"):
 required=("O_NOFOLLOW","O_NONBLOCK","O_DIRECTORY")
 missing=[name for name in required if not getattr(os,name,0)]
 if missing or os.open not in getattr(os,"supports_dir_fd",set()):
  raise ValueError(f"{label} access requires descriptor-relative opens and O_NOFOLLOW/O_NONBLOCK/O_DIRECTORY; unsupported platform")
def read_confined_bytes(base,relative,label):
 require_confined_open_support(label)
 """Read a confined regular file using no-follow directory/file descriptors."""
 if not isinstance(relative,str) or not relative.strip():raise ValueError(f"{label} evidence path missing")
 rel=Path(relative)
 if rel.is_absolute() or ".." in rel.parts or not rel.parts:raise ValueError(f"{label} evidence path must be relative and confined")
 root=Path(base).resolve();nofollow=getattr(os,"O_NOFOLLOW",0);directory=getattr(os,"O_DIRECTORY",0);flags=os.O_RDONLY
 descriptors=[];chunks=[]
 try:
  current=os.open(root,flags|directory);descriptors.append(current)
  for part in rel.parts[:-1]:
   current=os.open(part,flags|directory|nofollow,dir_fd=current);descriptors.append(current)
  file_fd=os.open(rel.parts[-1],flags|nofollow|getattr(os,"O_NONBLOCK",0),dir_fd=current);descriptors.append(file_fd)
  if not stat.S_ISREG(os.fstat(file_fd).st_mode):raise ValueError(f"{label} evidence file is not regular")
  while True:
   chunk=os.read(file_fd,1024*1024)
   if not chunk:break
   if sum(map(len,chunks))+len(chunk)>MAX_CONFined_EVIDENCE_BYTES:raise ValueError(f"{label} evidence exceeds {MAX_CONFined_EVIDENCE_BYTES} byte limit")
   chunks.append(chunk)
 except FileNotFoundError as exc:
  raise ValueError(f"{label} evidence file missing: {exc}") from exc
 except OSError as exc:
  raise ValueError(f"{label} evidence path contains symlink components or is unreadable: {exc}") from exc
 finally:
  for fd in reversed(descriptors):
   try:os.close(fd)
   except OSError:pass
 return (root/rel),b"".join(chunks)
def hash_confined_file(base,relative,label,chunk_size=1024*1024):
 require_confined_open_support(label)
 """Hash a confined regular file incrementally without buffering its contents."""
 if isinstance(chunk_size,bool) or not isinstance(chunk_size,int) or chunk_size<=0:
  raise ValueError("hash chunk size must be a positive integer")
 if not isinstance(relative,str) or not relative.strip():raise ValueError(f"{label} evidence path missing")
 rel=Path(relative)
 if rel.is_absolute() or ".." in rel.parts or not rel.parts:raise ValueError(f"{label} evidence path must be relative and confined")
 root=Path(base).resolve();nofollow=getattr(os,"O_NOFOLLOW",0);directory=getattr(os,"O_DIRECTORY",0);flags=os.O_RDONLY
 descriptors=[];digest=hashlib.sha256();size=0
 try:
  current=os.open(root,flags|directory);descriptors.append(current)
  for part in rel.parts[:-1]:
   current=os.open(part,flags|directory|nofollow,dir_fd=current);descriptors.append(current)
  file_fd=os.open(rel.parts[-1],flags|nofollow|getattr(os,"O_NONBLOCK",0),dir_fd=current);descriptors.append(file_fd)
  if not stat.S_ISREG(os.fstat(file_fd).st_mode):raise ValueError(f"{label} evidence file is not regular")
  while True:
   chunk=os.read(file_fd,chunk_size)
   if not chunk:break
   digest.update(chunk);size+=len(chunk)
 except FileNotFoundError as exc:
  raise ValueError(f"{label} evidence file missing: {exc}") from exc
 except OSError as exc:
  raise ValueError(f"{label} evidence path contains symlink components or is unreadable: {exc}") from exc
 finally:
  for fd in reversed(descriptors):
   try:os.close(fd)
   except OSError:pass
 return (root/rel),digest.hexdigest(),size
def read_verified_evidence_bytes(base,relative,digest,label):
 """Read and hash the same confined bytes, avoiding path-check/open races."""
 if not isinstance(digest,str) or not SHA64.fullmatch(digest):raise ValueError(f"{label} evidence SHA-256 invalid")
 target,raw=read_confined_bytes(base,relative,label)
 if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError(f"{label} evidence hash mismatch")
 return target,raw
def verify_evidence_file(base,relative,digest,label):
 target,raw=read_verified_evidence_bytes(base,relative,digest,label)
 return target
def verify_dataset_provenance_evidence(base,relative,digest,dataset_sha256):
 target,raw=read_verified_evidence_bytes(base,relative,digest,"dataset provenance")
 try:record=strict_json_loads(raw.decode("utf-8"))
 except Exception as exc:raise ValueError(f"dataset provenance evidence must be valid JSON: {exc}") from exc
 if not isinstance(record,dict):raise ValueError("dataset provenance evidence must be a JSON object")
 if record.get("dataset_sha256")!=dataset_sha256:raise ValueError("dataset provenance evidence dataset SHA-256 mismatch")
 if record.get("review_status")!="reviewed":raise ValueError("dataset provenance evidence review_status must be reviewed")
 for key in ("reviewer","review_scope","reviewed_at_utc"):
  value=record.get(key)
  if not isinstance(value,str) or not value.strip():raise ValueError(f"dataset provenance evidence {key} required")
 try:
  reviewed=datetime.fromisoformat(record["reviewed_at_utc"].replace("Z","+00:00"))
 except ValueError as exc:raise ValueError("dataset provenance evidence reviewed_at_utc must be ISO-8601") from exc
 if reviewed.tzinfo is None:raise ValueError("dataset provenance evidence reviewed_at_utc must include timezone")
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
  if path.is_file():
   relative=str(path.relative_to(root));_,raw=read_confined_bytes(root,relative,"candidate snapshot")
   actual[relative]=hashlib.sha256(raw).hexdigest()
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
 verify_dataset_provenance_evidence(path.parent,provenance.get("evidence_path"),provenance.get("evidence_sha256"),tasks_sha256)
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
