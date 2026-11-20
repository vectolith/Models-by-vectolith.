#!/usr/bin/env python3
"""Strict standard-library validator for candidate records (not a legal review)."""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import evaluation_gate
SHA40=re.compile(r"^[a-f0-9]{40}$");SHA64=re.compile(r"^[a-f0-9]{64}$")
REQUIRED={"record_version","candidate_id","repository_id","revision","status","output_training_permission","human_legal_review","compatibility_status","model_snapshot_path"}
STATUSES={"pending","verified","blocked","measured","not_applicable"}
def validate(record):
 errors=[]
 if not isinstance(record,dict):return ["candidate record must be a JSON object"]
 for k in REQUIRED:
  if k not in record:errors.append(f"missing required field: {k}")
 revision=record.get("revision")
 if not isinstance(revision,str) or not SHA40.fullmatch(revision):errors.append("revision must be a non-null 40-character lowercase immutable commit SHA")
 for k in ("candidate_id","repository_id","record_version"):
  if k in record and(not isinstance(record[k],str)or not record[k].strip()):errors.append(f"{k} must be a non-empty string")
 if record.get("model_snapshot_path") is not None and (not isinstance(record["model_snapshot_path"],str) or not record["model_snapshot_path"].strip()):errors.append("model_snapshot_path must be null or a non-empty path string")
 if record.get("status") not in STATUSES:errors.append("invalid status")
 if record.get("output_training_permission") not in {"pending","verified","denied","unclear"}:errors.append("invalid output_training_permission")
 if record.get("human_legal_review") not in {"pending","approved","rejected"}:errors.append("invalid human_legal_review")
 if record.get("compatibility_status") not in {"pending","compatible","incompatible","blocked"}:errors.append("invalid compatibility_status")
 for k in ("license_evidence_sha256","model_config_sha256","chat_template_sha256","output_training_permission_evidence_sha256","human_legal_review_evidence_sha256"):
  v=record.get(k)
  if v is not None and not SHA64.fullmatch(str(v)):errors.append(f"{k} must be null or a 64-character lowercase SHA-256")
 for k in ("license_evidence_path","output_training_permission_evidence_path","human_legal_review_evidence_path","model_config_evidence_path","chat_template_evidence_path","model_snapshot_path"):
  v=record.get(k)
  if v is not None and (not isinstance(v,str) or not v.strip()):errors.append(f"{k} must be null or a non-empty path string")
 inv=record.get("weight_inventory",[])
 if not isinstance(inv,list):errors.append("weight_inventory must be an array")
 else:
  for i,item in enumerate(inv):
   if not isinstance(item,dict) or set(item)!={"path","sha256"}:errors.append(f"weight_inventory[{i}] must contain exactly path and sha256")
   elif not isinstance(item["path"],str)or not item["path"] or not SHA64.fullmatch(str(item["sha256"])):errors.append(f"weight_inventory[{i}] has invalid path or SHA-256")
 for k in ("parameter_count","context_length"):
  v=record.get(k)
  if v is not None and(not isinstance(v,int)or isinstance(v,bool)or v<=0):errors.append(f"{k} must be a positive integer or null")
 allowed={"record_version","candidate_id","repository_id","revision","status","license_identifier","license_evidence_path","license_evidence_sha256","output_training_permission","output_training_permission_evidence_path","output_training_permission_evidence_sha256","human_legal_review","human_legal_review_evidence_path","human_legal_review_evidence_sha256","model_config_evidence_path","model_config_sha256","tokenizer_revision","chat_template_evidence_path","chat_template_sha256","model_snapshot_path","weight_inventory","architecture","parameter_count","context_length","compatibility_status","compute_evidence","notes","publisher"}
 extra=set(record)-allowed
 if extra:errors.append("unexpected fields: "+", ".join(sorted(extra)))
 if record.get("status")=="verified":
  required_evidence=("license_identifier","license_evidence_path","license_evidence_sha256","output_training_permission_evidence_path","output_training_permission_evidence_sha256","human_legal_review_evidence_path","human_legal_review_evidence_sha256","model_config_evidence_path","model_config_sha256","tokenizer_revision","chat_template_evidence_path","chat_template_sha256","model_snapshot_path")
  missing=[k for k in required_evidence if not record.get(k)]
  if record.get("output_training_permission")!="verified"or record.get("human_legal_review")!="approved"or record.get("compatibility_status")!="compatible"or record.get("tokenizer_revision")!=revision or not inv or missing:
   errors.append("verified status requires complete license, output permission, legal review, model config, tokenizer/template and weight inventory evidence; verified output permission, approved human legal review and compatible status")
 return errors
def main():
 p=argparse.ArgumentParser();p.add_argument("file",type=Path);a=p.parse_args()
 try:r=evaluation_gate.strict_json_loads(a.file.read_text(encoding="utf-8"))
 except Exception as e:print(f"input error: {e}");return 2
 err=validate(r)
 if err:print("\n".join(err));return 1
 print("Candidate record structurally valid. This does not establish authenticity, legal rights, or model compatibility.");return 0
if __name__=="__main__":raise SystemExit(main())
