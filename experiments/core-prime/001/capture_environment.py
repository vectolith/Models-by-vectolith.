#!/usr/bin/env python3
"""Capture package/Git environment evidence without importing ML runtimes or running inference."""
from __future__ import annotations
import argparse,importlib.metadata,json,platform,sys,os,tempfile
from datetime import datetime,timezone
from pathlib import Path
import evaluation_gate
def capture():
 packages=sorted([{"name":d.metadata.get("Name") or d.name or "unknown","version":d.version} for d in importlib.metadata.distributions()],key=lambda x:(x["name"].lower(),x["version"]))
 return {"captured_at_utc":datetime.now(timezone.utc).isoformat(),"git_head":evaluation_gate.git_head(),"python":sys.version,"platform":platform.platform(),"package_inventory":packages,"package_inventory_sha256":evaluation_gate.sha256_serialized(packages),"scope":"package metadata and Git checkout only; no ML runtime imports, hardware/free-budget validation, inference or training"}
def atomic_write_json(path,record):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=path.parent)
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:
   f.write(json.dumps(record,indent=2)+"\n");f.flush();os.fsync(f.fileno())
  os.replace(temp,path)
  evaluation_gate.fsync_directory(path.parent)
 except BaseException:
  try:os.unlink(temp)
  except FileNotFoundError:pass
  raise
 return path
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 result=capture();atomic_write_json(a.output,result);print(json.dumps(result,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
