#!/usr/bin/env python3
"""Capture package/Git environment evidence without importing ML runtimes or running inference."""
from __future__ import annotations
import argparse,importlib.metadata,json,platform,sys
from datetime import datetime,timezone
from pathlib import Path
import evaluation_gate
def capture():
 packages=sorted([{"name":d.metadata.get("Name") or d.name or "unknown","version":d.version} for d in importlib.metadata.distributions()],key=lambda x:(x["name"].lower(),x["version"]))
 return {"captured_at_utc":datetime.now(timezone.utc).isoformat(),"git_head":evaluation_gate.git_head(),"python":sys.version,"platform":platform.platform(),"package_inventory":packages,"package_inventory_sha256":evaluation_gate.sha256_serialized(packages),"scope":"package metadata and Git checkout only; no ML runtime imports, hardware/free-budget validation, inference or training"}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
 result=capture();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2),encoding="utf-8");print(json.dumps(result,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
