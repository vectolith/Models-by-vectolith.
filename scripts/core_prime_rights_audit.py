#!/usr/bin/env python3
"""Fail-closed audit of model-teacher rights evidence; never grants rights."""
import argparse,hashlib,json,sys
from pathlib import Path

REQUIRED_FLAGS=("training_use","output_use","retention_use")
def sha(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def validate(p):
 p=Path(p).resolve(); errors=[]
 try:d=json.loads(p.read_text(encoding="utf-8"))
 except Exception as e:return ["unreadable JSON: "+str(e)]
 if not isinstance(d,dict):return ["root must be object"]
 if d.get("schema_version")!="teacher-rights-evidence/1.0":errors.append("schema_version mismatch")
 sources=d.get("sources")
 if not isinstance(sources,list) or not sources:return errors+["sources must be nonempty list"]
 root=p.parent.resolve()
 seen=set()
 for i,s in enumerate(sources):
  prefix=f"source[{i}]"
  if not isinstance(s,dict):errors.append(prefix+" malformed");continue
  sid=s.get("source_id")
  if not isinstance(sid,str) or not sid.strip():errors.append(prefix+" source_id required")
  elif sid in seen:errors.append(prefix+" duplicate source_id")
  else:seen.add(sid)
  for field in ("provider","model_name","revision","license_id","scope_description","reviewer","reviewed_at"):
   v=s.get(field)
   if not isinstance(v,str) or not v.strip():errors.append(prefix+" "+field+" required")
  if s.get("reviewer") and s.get("rights_holder") and s["reviewer"]==s["rights_holder"]:
   errors.append(prefix+" reviewer cannot be rights-holder")
  for flag in REQUIRED_FLAGS:
   if s.get("permissions",{}).get(flag) is not True:errors.append(prefix+" permission not explicitly verified: "+flag)
  evidence=s.get("evidence")
  if not isinstance(evidence,dict) or not evidence.get("path") or not evidence.get("sha256"):
   errors.append(prefix+" evidence path and SHA-256 required");continue
  rel,expected=evidence["path"],evidence["sha256"]
  if not isinstance(rel,str) or Path(rel).is_absolute() or not isinstance(expected,str) or len(expected)!=64 or any(c not in "0123456789abcdefABCDEF" for c in expected):
   errors.append(prefix+" evidence must use relative path and 64 hex SHA-256");continue
  path=(root/rel).resolve()
  if not path.is_relative_to(root):errors.append(prefix+" evidence path escapes ledger directory");continue
  if not path.is_file():errors.append(prefix+" evidence file missing");continue
  if sha(path)!=expected.lower():errors.append(prefix+" evidence digest mismatch")
 return errors
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument("ledger");args=a.parse_args()
 e=validate(args.ledger)
 if e:print("BLOCKED\n"+"\n".join("- "+x for x in e));return 1
 print("STRUCTURAL PASS only: evidence files and declared scope/permission flags match ledger. Legal interpretation and authority are not independently established.");return 0
if __name__=="__main__":sys.exit(main())
