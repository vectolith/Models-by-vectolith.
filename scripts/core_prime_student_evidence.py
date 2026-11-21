#!/usr/bin/env python3
"""Validate student benchmark evidence records and strict zero-cost constraint."""
import argparse,json,math,sys
from pathlib import Path
FIELDS=("model_id","revision","license_id","license_evidence_sha256","tokenizer_revision","benchmark_dataset_sha256","hardware","runtime","peak_memory_mb","tokens_per_second","quality_score","quality_method","reviewer","timestamp","artifact_sha256","cost_usd")
DIGESTS=("license_evidence_sha256","benchmark_dataset_sha256","artifact_sha256")
TEXT_FIELDS=("model_id","revision","license_id","tokenizer_revision","hardware","runtime","quality_method","reviewer","timestamp")
def validate(data):
 e=[]
 if not isinstance(data,dict) or not isinstance(data.get("candidates"),list) or not data["candidates"]:return ["root must contain nonempty candidates list"]
 ids=set()
 for i,c in enumerate(data["candidates"]):
  p=f"candidate[{i}]"
  if not isinstance(c,dict):e.append(p+" malformed");continue
  for f in FIELDS:
   if f not in c:e.append(p+" missing "+f)
  for f in TEXT_FIELDS:
   v=c.get(f)
   if not isinstance(v,str) or not v.strip():e.append(p+" nonempty string required for "+f)
  mid=c.get("model_id")
  if isinstance(mid,str):
   if mid in ids:e.append(p+" duplicate model_id")
   ids.add(mid)
  for f in DIGESTS:
   v=c.get(f)
   if not isinstance(v,str) or len(v)!=64 or any(ch not in "0123456789abcdefABCDEF" for ch in v):e.append(p+" invalid "+f)
  for f in ("peak_memory_mb","tokens_per_second","quality_score","cost_usd"):
   v=c.get(f)
   if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):e.append(p+" finite numeric "+f+" required")
  v=c.get("cost_usd")
  if isinstance(v,(int,float)) and (isinstance(v,bool) or not math.isfinite(v) or v!=0):e.append(p+" violates zero-budget: cost_usd must be exactly 0")
  v=c.get("peak_memory_mb")
  if isinstance(v,(int,float)) and (isinstance(v,bool) or not math.isfinite(v) or v<=0):e.append(p+" peak_memory_mb must be finite and positive")
  v=c.get("tokens_per_second")
  if isinstance(v,(int,float)) and (isinstance(v,bool) or not math.isfinite(v) or v<=0):e.append(p+" tokens_per_second must be finite and positive")
 return e
def main():
 a=argparse.ArgumentParser();a.add_argument("file");args=a.parse_args()
 try:d=json.loads(Path(args.file).read_text(encoding="utf-8"))
 except Exception as x:print("invalid input: "+str(x));return 2
 e=validate(d)
 if e:print("BLOCKED\\n"+"\\n".join("- "+x for x in e));return 1
 print("STRUCTURAL PASS only. No benchmark authenticity, license interpretation, model quality or free quota is independently verified.");return 0
if __name__=="__main__":sys.exit(main())
