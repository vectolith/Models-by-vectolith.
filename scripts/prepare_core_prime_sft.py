#!/usr/bin/env python3
"""Prepare train-only Core Prime personality data in chat SFT and DPO formats.

Uses no external dependencies. Excludes holdout rows and keeps source IDs for traceability.
"""
from pathlib import Path
import argparse, json

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "trajectories": ROOT / "data/personality/core-prime-multiturn-trajectories-v1.jsonl",
    "preferences": ROOT / "data/personality/core-prime-contrastive-preferences-v1.jsonl",
    "micro": ROOT / "data/personality/core-prime-behavioral-micro-scenarios-v1.jsonl",
}

def read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")

def prepare(root=ROOT, output=None):
    output = Path(output or root / "data/personality/prepared")
    trajectory_rows = read_jsonl(root / "data/personality/core-prime-multiturn-trajectories-v1.jsonl")
    micro_rows = read_jsonl(root / "data/personality/core-prime-behavioral-micro-scenarios-v1.jsonl")
    preference_rows = read_jsonl(root / "data/personality/core-prime-contrastive-preferences-v1.jsonl")
    sft = []
    for row in trajectory_rows:
        if row.get("split") != "train": continue
        turns = row.get("turns", [])
        # Each assistant turn becomes an example with preceding context, preserving dialogue.
        for i in range(1, len(turns), 2):
            sft.append({"source_id": row["id"], "messages": [{"role": m["role"], "content": m["text"]} for m in turns[:i+1]]})
    for row in micro_rows:
        if row.get("split") != "train": continue
        sft.append({"source_id": row["id"], "messages": [
            {"role":"user","content":row["prompt"]},
            {"role":"assistant","content":row["desired_observable_behavior"]},
        ]})
    dpo=[]
    for row in preference_rows:
        if row.get("split") != "train": continue
        dpo.append({"source_id":row["id"],"prompt":[{"role":"user","content":row["prompt"]}],
                    "chosen":[{"role":"assistant","content":row["preferred"]["text"]}],
                    "rejected":[{"role":"assistant","content":row["rejected"]["text"]}]})
    write_jsonl(output / "sft-train.jsonl", sft)
    write_jsonl(output / "dpo-train.jsonl", dpo)
    manifest={"sft_records":len(sft),"dpo_records":len(dpo),
              "holdout_excluded":{"trajectories":sum(r.get("split")=="holdout" for r in trajectory_rows),
                                   "micro":sum(r.get("split")=="holdout" for r in micro_rows),
                                   "preferences":sum(r.get("split")=="holdout" for r in preference_rows)},
              "source":"synthetic draft","outputs":["sft-train.jsonl","dpo-train.jsonl"]}
    (output/"prepared-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return manifest

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=ROOT/"data/personality/prepared")
    args=p.parse_args()
    print(json.dumps(prepare(output=args.output),indent=2))
if __name__=="__main__": main()
