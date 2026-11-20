#!/usr/bin/env python3
"""Capture a real local snapshot inventory; does not load or run model weights."""
from __future__ import annotations
import argparse,json,os,tempfile,hashlib
from pathlib import Path
import evaluation_gate
def capture(candidate_record_path):
 try:
  candidate_record_bytes=candidate_record_path.read_bytes()
  record=json.loads(candidate_record_bytes.decode("utf-8"))
 except Exception as exc:raise ValueError(f"candidate record parse failed: {exc}") from exc
 # Bind the inventory to the exact candidate bytes that were parsed, not a later file read.
 candidate_record_sha256=hashlib.sha256(candidate_record_bytes).hexdigest()
 if not isinstance(record,dict):raise ValueError("candidate record must be an object")
 rel=record.get("model_snapshot_path")
 if not isinstance(rel,str) or not rel.strip():raise ValueError("candidate model_snapshot_path is unset")
 relative=Path(rel)
 if relative.is_absolute() or ".." in relative.parts:raise ValueError("model snapshot path must be relative and confined")
 root=candidate_record_path.parent.resolve();raw_snapshot=root/relative
 cursor=root
 for part in relative.parts:
  cursor=cursor/part
  if cursor.is_symlink():raise ValueError("model snapshot path contains symlink components")
 snapshot=raw_snapshot.resolve()
 try:snapshot.relative_to(root)
 except ValueError:raise ValueError("model snapshot path escapes candidate root")
 if not snapshot.is_dir():raise ValueError("snapshot directory missing")
 inventory=[]
 for path in sorted(snapshot.rglob("*")):
  if path.is_symlink():raise ValueError("snapshot contains symlinks")
  if path.is_file():inventory.append({"path":str(path.relative_to(root)),"sha256":evaluation_gate.sha256_file(path)})
 if not inventory:raise ValueError("snapshot is empty")
 return {"candidate_record_sha256":candidate_record_sha256,"model_snapshot_path":rel,"inventory":inventory,"inventory_sha256":evaluation_gate.sha256_serialized(inventory),"scope":"file inventory and SHA-256 only; no license or permission approval, model loading, inference or training"}
def atomic_write_json(path,record):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=path.parent)
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:
   f.write(json.dumps(record,indent=2)+"\n");f.flush();os.fsync(f.fileno())
  os.replace(temp,path)
 except BaseException:
  try:os.unlink(temp)
  except FileNotFoundError:pass
  raise
 return path
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--candidate-record",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 try:result=capture(a.candidate_record)
 except Exception as exc:p.error(str(exc))
 atomic_write_json(a.output,result);print(json.dumps(result,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
