#!/usr/bin/env python3
"""Compare baseline and adapter evaluation records using independently supplied grades.

Grade JSONL rows: task_id, candidate_id, scores (criterion->number), optional notes.
This script computes paired score deltas; it does not grade responses or invent scores.
"""
import argparse, json, math
from pathlib import Path

def load(path):
    rows={}
    for n,line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try:r=json.loads(line)
        except Exception as e:raise ValueError(f"{path}:{n}: invalid JSON: {e}")
        if not isinstance(r,dict) or not isinstance(r.get("task_id"),str) or not r["task_id"].strip():
            raise ValueError(f"{path}:{n}: task_id required")
        candidate_id=r.get("candidate_id")
        if not isinstance(candidate_id,str) or not candidate_id.strip():
            raise ValueError(f"{path}:{n}: candidate_id required")
        if r["task_id"] in rows:raise ValueError(f"{path}:{n}: duplicate task_id")
        scores=r.get("scores")
        if not isinstance(scores,dict) or not scores:raise ValueError(f"{path}:{n}: nonempty scores object required")
        for k,v in scores.items():
            if not isinstance(k,str) or not k or not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v):
                raise ValueError(f"{path}:{n}: scores must be finite numeric values")
        rows[r["task_id"]]=r
    if not rows:raise ValueError(f"{path}: no grades")
    candidate_ids={r["candidate_id"] for r in rows.values()}
    if len(candidate_ids)!=1:raise ValueError(f"{path}: candidate_id must be consistent across all grade records")
    return rows

def compare(base,trained):
    for label,records in (("baseline",base),("adapter",trained)):
        ids={r.get("candidate_id") for r in records.values()}
        if not ids or len(ids)!=1 or not isinstance(next(iter(ids)),str) or not next(iter(ids)).strip():
            raise ValueError(f"{label} grades require one consistent non-empty candidate_id")
    baseline_candidate_id=next(iter({r["candidate_id"] for r in base.values()}))
    adapter_candidate_id=next(iter({r["candidate_id"] for r in trained.values()}))
    if set(base)!=set(trained):
        missing=sorted(set(base)-set(trained));extra=sorted(set(trained)-set(base))
        raise ValueError(f"task set mismatch; missing adapter={missing}, extra adapter={extra}")
    out=[];criteria=set()
    for tid in sorted(base):
        a,b=base[tid]["scores"],trained[tid]["scores"]
        if set(a)!=set(b):raise ValueError(f"{tid}: criterion set mismatch")
        criteria.update(a)
        out.append({"task_id":tid,"baseline_scores":a,"adapter_scores":b,
                    "deltas":{k:b[k]-a[k] for k in a}})
    aggregate={}
    for c in sorted(criteria):
        values=[r["deltas"][c] for r in out]
        aggregate[c]={"paired_count":len(values),"baseline_mean":sum(base[t]["scores"][c] for t in base)/len(base),
                      "adapter_mean":sum(trained[t]["scores"][c] for t in trained)/len(trained),
                      "mean_delta":sum(values)/len(values),"improved":sum(v>0 for v in values),
                      "regressed":sum(v<0 for v in values),"unchanged":sum(v==0 for v in values)}
    return {"task_count":len(out),"baseline_candidate_id":baseline_candidate_id,"adapter_candidate_id":adapter_candidate_id,"criteria":aggregate,"paired_records":out,
            "interpretation":"descriptive paired comparison; no statistical significance or release qualification implied"}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--baseline-grades",required=True,type=Path);p.add_argument("--adapter-grades",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    try:result=compare(load(a.baseline_grades),load(a.adapter_grades))
    except ValueError as e:p.error(str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8");print(json.dumps({"task_count":result["task_count"],"criteria":result["criteria"],"output":str(a.output)},indent=2))
if __name__=="__main__":main()
