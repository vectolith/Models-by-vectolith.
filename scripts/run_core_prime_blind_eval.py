#!/usr/bin/env python3
"""Create blinded evaluation score sheets and summarize scored records; no model inference."""
import argparse, json, random, csv
from pathlib import Path

DIMENSIONS = ["judgment","naturalness","situational_fit","independence","humor_timing","useful_originality","restraint","grounding_calibration","task_craft","relational_intelligence","long_context_consistency","repair"]
def read_jsonl(p):
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
def write_jsonl(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")
def make_sheet(cases, outputs, seed):
    rng=random.Random(seed); sheet=[]
    for case in cases:
        candidates=list(outputs.get(case["id"],{}).items())
        rng.shuffle(candidates)
        sheet.append({"case_id":case["id"],"prompt":case["prompt"],"context":case.get("context",""),
          "test":case["test"],"dimension":case["dimension"],
          "responses":[{"blind_label":f"candidate_{i+1}","response":text} for i,(condition,text) in enumerate(candidates)],
          "mapping":{f"candidate_{i+1}":condition for i,(condition,text) in enumerate(candidates)}})
    return sheet
def summarize(scores):
    accum={d:[] for d in DIMENSIONS}
    flags=[]
    for row in scores:
        d=row.get("dimension")
        score=row.get("score")
        if d not in accum: raise ValueError(f"Unknown dimension: {d}")
        if score is not None and (not isinstance(score,int) or not 1<=score<=5): raise ValueError("Scores must be integer 1-5 or null")
        if score is not None: accum[d].append(score)
        flags.extend(row.get("gate_flags",[]))
    return {"dimension_means":{d:(round(sum(v)/len(v),3) if v else None) for d,v in accum.items()},
            "dimension_counts":{d:len(v) for d,v in accum.items()},"gate_flags":sorted(set(flags)),
            "scored_records":len(scores),"note":"Descriptive summary only; does not establish statistical significance or model quality."}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cases",type=Path,default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    p.add_argument("--outputs",type=Path,help="JSON mapping case ID to condition name and response text")
    p.add_argument("--scores",type=Path,help="JSONL with case_id, dimension, integer score 1-5 or null, gate_flags")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--seed",type=int,default=20261121)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    cases=read_jsonl(args.cases)
    if args.outputs:
        sheet=make_sheet(cases,json.loads(args.outputs.read_text(encoding="utf-8")),args.seed)
        write_jsonl(args.output/"blind-score-sheet.jsonl",sheet)
        (args.output/"blind-label-map.json").write_text(json.dumps({r["case_id"]:r["mapping"] for r in sheet},indent=2)+"\n",encoding="utf-8")
    if args.scores:
        result=summarize(read_jsonl(args.scores))
        (args.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(result,indent=2))
if __name__=="__main__": main()
