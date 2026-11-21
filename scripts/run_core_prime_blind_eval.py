#!/usr/bin/env python3
"""Create blinded evaluation score sheets and summarize scored records; no model inference."""
import argparse
import json
import random
from pathlib import Path

DIMENSIONS = ["judgment","naturalness","situational_fit","independence","humor_timing","useful_originality","restraint","grounding_calibration","task_craft","relational_intelligence","long_context_consistency","repair"]
CONDITIONS = {"base", "character_prompt"}

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False)+"\n" for row in rows), encoding="utf-8")

def make_sheet(cases, outputs, seed):
    rng = random.Random(seed)
    sheet, label_map = [], {}
    expected_ids = {case.get("id") for case in cases}
    if set(outputs) != expected_ids:
        raise ValueError(f"Output IDs mismatch: missing={sorted(expected_ids-set(outputs))}, extra={sorted(set(outputs)-expected_ids)}")
    case_ids=set()
    for case in cases:
        case_id=case.get("id")
        if not case_id or case_id in case_ids: raise ValueError("Case IDs must be present and unique")
        case_ids.add(case_id)
        candidates=list(outputs.get(case_id, {}).items())
        if set(condition for condition,_ in candidates)!=CONDITIONS or len(candidates)!=2:
            raise ValueError(f"{case_id}: expected exactly base and character_prompt conditions")
        if any(not isinstance(response,str) or not response.strip() for _,response in candidates):
            raise ValueError(f"{case_id}: responses must be non-empty strings")
        rng.shuffle(candidates)
        sheet.append({"case_id":case_id, "prompt":case["prompt"], "context":case.get("context",""),
          "test":case["test"], "dimension":case["dimension"],
          "responses":[{"blind_label":f"candidate_{i+1}", "response":response} for i,(_,response) in enumerate(candidates)]})
        label_map[case_id]={f"candidate_{i+1}":condition for i,(condition,_) in enumerate(candidates)}
    missing=set(outputs)-case_ids
    if missing: raise ValueError(f"Outputs contain unknown case IDs: {sorted(missing)}")
    return sheet, label_map

def summarize(scores):
    accum={dimension:[] for dimension in DIMENSIONS}
    flags=[]
    for row in scores:
        dimension=row.get("dimension")
        score=row.get("score")
        if dimension not in accum: raise ValueError(f"Unknown dimension: {dimension}")
        if score is not None and (not isinstance(score,int) or isinstance(score,bool) or not 1<=score<=5): raise ValueError("Scores must be integer 1-5 or null")
        if score is not None: accum[dimension].append(score)
        flags.extend(row.get("gate_flags",[]))
    return {"dimension_means":{d:(round(sum(v)/len(v),3) if v else None) for d,v in accum.items()},
            "dimension_counts":{d:len(v) for d,v in accum.items()},"gate_flags":sorted(set(flags)),
            "scored_records":len(scores),"note":"Descriptive summary only; does not establish statistical significance or model quality."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--cases",type=Path,default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
    parser.add_argument("--outputs",type=Path,help="JSON mapping case ID to condition name and response text")
    parser.add_argument("--scores",type=Path,help="JSONL with case_id, dimension, score, and gate_flags")
    parser.add_argument("--output",type=Path,required=True,help="Evaluator-facing score-sheet directory")
    parser.add_argument("--map-output",type=Path,help="Restricted mapping directory; defaults to a sibling directory")
    parser.add_argument("--seed",type=int,default=20261121)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    cases=read_jsonl(args.cases)
    if args.outputs:
        sheet,label_map=make_sheet(cases,json.loads(args.outputs.read_text(encoding="utf-8")),args.seed)
        write_jsonl(args.output/"blind-score-sheet.jsonl",sheet)
        map_dir=args.map_output or args.output.parent/(args.output.name+"-restricted")
        map_dir.mkdir(parents=True,exist_ok=True)
        (map_dir/"blind-label-map.json").write_text(json.dumps(label_map,indent=2)+"\n",encoding="utf-8")
    if args.scores:
        result=summarize(read_jsonl(args.scores))
        (args.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
