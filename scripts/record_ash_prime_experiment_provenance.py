#!/usr/bin/env python3
"""Write reproducibility provenance for a ASH PRIME paired-output experiment.

Run after generation. Records hashes, timestamp, model label and run configuration;
does not download models or perform inference.
"""
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def count_cases(path):
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True,help="Model ID, local path, or revision label used")
    p.add_argument("--cases",type=Path,default=Path("evaluation/personality/ash-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--character-prompt",type=Path,default=Path("evaluation/personality/ash-prime-character-system-prompt-v1.txt"))
    p.add_argument("--outputs",type=Path,required=True)
    p.add_argument("--max-new-tokens",type=int,default=256)
    p.add_argument("--seed",type=int,default=0,help="Seed value used, if configured by the generation process; record only")
    p.add_argument("--manifest",type=Path,required=True)
    args=p.parse_args()
    for path in (args.cases,args.character_prompt,args.outputs):
        if not path.is_file(): p.error(f"Required file not found: {path}")
    data=json.loads(args.outputs.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or not data: p.error("Outputs must be a nonempty JSON object keyed by case ID")
    manifest={
      "schema":"ash-prime-experiment-provenance-v1",
      "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
      "model_label":args.model,
      "case_count_in_dataset":count_cases(args.cases),
      "case_count_in_outputs":len(data),
      "max_new_tokens":args.max_new_tokens,
      "seed_recorded":args.seed,
      "python_version":platform.python_version(),
      "platform":platform.platform(),
      "files":{
        "cases":{"path":str(args.cases),"sha256":sha256(args.cases)},
        "character_prompt":{"path":str(args.character_prompt),"sha256":sha256(args.character_prompt)},
        "outputs":{"path":str(args.outputs),"sha256":sha256(args.outputs)}
      },
      "limitations":["This manifest records provenance only; it does not independently verify model identity, generation settings, or output quality."]
    }
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__": main()
