#!/usr/bin/env python3
"""Capture a real local snapshot inventory; does not load or run model weights."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import evaluation_gate
def capture(candidate_record_path):
 try:record=json.loads(candidate_record_path.read_text(encoding="utf-8"))
 except Exception as exc:raise ValueError(f"candidate record parse failed: {exc}") from exc
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
 return {"candidate_record_sha256":evaluation_gate.sha256_file(candidate_record_path),"model_snapshot_path":rel,"inventory":inventory,"inventory_sha256":evaluation_gate.sha256_serialized(inventory),"scope":"file inventory and SHA-256 only; no license or permission approval, model loading, inference or training"}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--candidate-record",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 try:result=capture(a.candidate_record)
 except Exception as exc:p.error(str(exc))
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
