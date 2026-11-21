#!/usr/bin/env python3
"""Validate student benchmark evidence records and strict zero-cost constraint."""
import argparse,json,sys
from pathlib import Path
FIELDS=("model_id","revision","license_id","license_evidence_sha256","tokenizer_revision","benchmark_dataset_sha256","hardware","runtime","peak_memory_mb","tokens_per_second","quality_score","quality_method","reviewer","timestamp","artifact_sha256","cost_usd")
def validate(data):
 e=[]
 if not isinstance(data,dict) or not isinstance(data.get("candidates"),list) or not data["candidates"]:return ["root must contain nonempty candidates list"]
 ids=set()
 for i,c in enumerate(data["candidates"]):
  p=f"candidate[{i}]"
  if not isinstance(c,dict):e.append(p+" malformed");continue
  for f in FIELDS:
   if f not in c:e.append(p+" missing "+f)
  mid=c.get("model_id")
  if isinstance(mid,str):
   if mid in ids:e.append(p+" duplicate model_id")
   ids.add(mid)
  for f in ("license_evidence_sha256","benchmark_dataset_sha256","artifact_sha256"):
   v=c.get(f)
   if not isinstance(v,str) or len(v)!=64 or any(ch not in "0123456789abcdefABCDEF" for ch in v):e.append(p+" invalid "+f)
  for f in ("peak_memory_mb","tokens_per_second","quality_score","cost_usd"):
   v=c.get(f)
   if isinstance(v,bool) or not isinstance(v,(int,float)):e.append(p+" numeric "+f+" required")
  if isinstance(c.get("cost_usd"),(int,float)) and c["cost_usd"]!=0:e.append(p+" violates zero-budget: cost_usd must be 0")
  if isinstance(c.get("peak_memory_mb"),(int,float)) and c["peak_memory_mb"]<=0:e.append(p+" peak_memory_mb must be positive")
  if isinstance(c.get("tokens_per_second"),(int,float)) and c["tokens_per_second"]<=0:e.append(p+" tokens_per_second must be positive")
 return e
def main():
 a=argparse.ArgumentParser();a.add_argument("file");args=a.parse_args()
 try:d=json.loads(Path(args.file).read_text())
 except Exception as x:print("invalid input: "+str(x));return 2
 e=validate(d)
 if e:print("BLOCKED\n"+"\n".join("- "+x for x in e));return 1
 print("STRUCTURAL PASS only. No benchmark authenticity, license interpretation, model quality or free quota is independently verified.");return 0
if __name__=="__main__":sys.exit(main())
