#!/usr/bin/env python3
"""Verify a release evidence bundle's manifest, hashes, and required qualification gates.

This verifier only checks evidence integrity/completeness; it does not attest truth,
legal permission, reviewer independence, or model quality.
"""
import argparse, hashlib, json, re, os, stat
from pathlib import Path
SHA=re.compile(r"^[a-f0-9]{64}$")
REQUIRED_GATES=("legal_review","data_provenance","baseline_evaluation","post_training_evaluation","independent_human_grading","safety_review","reproducibility_review","release_approval")
def sha256(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def verify(root,manifest):
 errors=[]
 if not isinstance(manifest,dict):return ["manifest must be a JSON object"]
 if not isinstance(manifest.get("release_version"),str) or not manifest["release_version"].strip():errors.append("release_version required")
 if manifest.get("model_name")!="Core Prime":errors.append("model_name must be Core Prime")
 gates=manifest.get("gates")
 if not isinstance(gates,dict):errors.append("gates object required")
 else:
  seen_gate_paths=set()
  for name in REQUIRED_GATES:
   item=gates.get(name)
   if not isinstance(item,dict) or item.get("status")!="approved" or not isinstance(item.get("evidence_path"),str) or not isinstance(item.get("sha256"),str) or not SHA.fullmatch(item["sha256"]):
    errors.append(f"gate {name} lacks approved status and evidence hash/path")
   else:
    if "holdout" in item["evidence_path"].lower():
     errors.append(f"gate {name}: holdout evidence forbidden: {item['evidence_path']}")
     continue
    try:
     target=verify_file(root,item["evidence_path"],item["sha256"])
     canonical=str(target)
     if canonical in seen_gate_paths:errors.append(f"duplicate gate evidence file: {item['evidence_path']}")
     seen_gate_paths.add(canonical)
    except ValueError as e:errors.append(f"gate {name}: {e}")
 artifacts=manifest.get("artifacts")
 if not isinstance(artifacts,list) or not artifacts:errors.append("non-empty artifacts array required")
 else:
  seen=set()
  for i,item in enumerate(artifacts):
   if not isinstance(item,dict) or not isinstance(item.get("path"),str) or not isinstance(item.get("sha256"),str) or not SHA.fullmatch(item["sha256"]):
    errors.append(f"artifact {i} malformed");continue
   if "holdout" in item["path"].lower():errors.append(f"holdout artifact forbidden in release bundle: {item['path']}")
   try:
    target=verify_file(root,item["path"],item["sha256"])
    canonical=str(target)
    if canonical in seen:errors.append(f"duplicate artifact file: {item['path']}")
    seen.add(canonical)
   except ValueError as e:errors.append(f"artifact {item['path']}: {e}")
 if manifest.get("holdout_included") is not False:errors.append("holdout_included must be explicitly false")
 if manifest.get("release_status")!="qualified":errors.append("release_status must be qualified")
 return errors
def verify_file(root,relative,digest):
 base=Path(root).resolve();rel=Path(relative)
 if rel.is_absolute() or ".." in rel.parts or not rel.parts:raise ValueError("path must be relative and confined")
 # Verify and hash the same bytes through no-follow descriptors. A path check
 # followed by a separate open/hash would leave a symlink replacement race.
 nofollow=getattr(os,"O_NOFOLLOW",0);directory=getattr(os,"O_DIRECTORY",0);flags=os.O_RDONLY
 descriptors=[];chunks=[]
 try:
  current=os.open(base,flags|directory);descriptors.append(current)
  for part in rel.parts[:-1]:
   current=os.open(part,flags|directory|nofollow,dir_fd=current);descriptors.append(current)
  file_fd=os.open(rel.parts[-1],flags|nofollow,dir_fd=current);descriptors.append(file_fd)
  if not stat.S_ISREG(os.fstat(file_fd).st_mode):raise ValueError("evidence file is not regular")
  while True:
   chunk=os.read(file_fd,1024*1024)
   if not chunk:break
   chunks.append(chunk)
 except FileNotFoundError as exc:
  raise ValueError(f"evidence file missing: {exc}") from exc
 except OSError as exc:
  raise ValueError(f"evidence path contains symlink components or is unreadable: {exc}") from exc
 finally:
  for fd in reversed(descriptors):
   try:os.close(fd)
   except OSError:pass
 raw=b"".join(chunks)
 if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("SHA-256 mismatch")
 p=base/rel
 try:p.resolve().relative_to(base)
 except ValueError:raise ValueError("path escapes evidence root")
 return p.resolve()
def main():
 p=argparse.ArgumentParser();p.add_argument("manifest",type=Path);a=p.parse_args()
 try:m=json.loads(a.manifest.read_text(encoding="utf-8"))
 except Exception as e:p.error(f"manifest read/parse failed: {e}")
 errors=verify(a.manifest.parent,m)
 if errors:print("\n".join(errors));return 1
 print("Release bundle evidence integrity/completeness passed. Independent substantive qualification remains outside this verifier.")
 return 0
if __name__=="__main__":raise SystemExit(main())
