#!/usr/bin/env python3
"""Export train-only personality JSONL files; never exports holdout records."""
from pathlib import Path
import json
import argparse

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
 "trajectories": ROOT / "data/personality/ash-prime-multiturn-trajectories-v1.jsonl",
 "preferences": ROOT / "data/personality/ash-prime-contrastive-preferences-v1.jsonl",
 "micro": ROOT / "data/personality/ash-prime-behavioral-micro-scenarios-v1.jsonl",
}
def read(path):
 return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--output",required=True,type=Path)
 args=parser.parse_args()
 args.output.mkdir(parents=True,exist_ok=True)
 manifest={}
 for name,path in SOURCES.items():
  rows=read(path); train=[r for r in rows if r.get("split")=="train"]
  if any(r.get("split") not in {"train","holdout"} for r in rows):
   raise ValueError(f"Invalid split label in {name}")
  dest=args.output/f"{name}-train.jsonl"
  dest.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in train),encoding="utf-8")
  manifest[name]={"source":str(path.relative_to(ROOT)),"output":dest.name,"records":len(train),"holdout_excluded":sum(r["split"]=="holdout" for r in rows)}
 (args.output/"train-export-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(manifest,indent=2))
if __name__=="__main__": main()
