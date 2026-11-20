#!/usr/bin/env python3
"""Compare baseline and adapter evaluation records using independently supplied grades.

Grade JSONL rows: task_id, candidate_id, scores (criterion->number), optional notes.
This script computes paired score deltas; it does not grade responses or invent scores.
"""
import argparse, json, math, hashlib, os, tempfile
from pathlib import Path


def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def atomic_write_json(path,record):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            f.write(json.dumps(record,indent=2,ensure_ascii=False)+"\n");f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    except BaseException:
        try:os.unlink(temp)
        except FileNotFoundError:pass
        raise
    return sha256_file(path)

def load_snapshot(path):
    raw=Path(path).read_bytes()
    try:text=raw.decode("utf-8")
    except UnicodeDecodeError as exc:raise ValueError(f"{path}: invalid UTF-8: {exc}") from exc
    rows={}
    for n,line in enumerate(text.splitlines(),1):
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
            if not isinstance(k,str) or not k.strip() or not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v):
                raise ValueError(f"{path}:{n}: scores must be finite numeric values")
        notes=r.get("notes")
        if notes is not None and not isinstance(notes,str):raise ValueError(f"{path}:{n}: notes must be text when present")
        rows[r["task_id"]]=r
    if not rows:raise ValueError(f"{path}: no grades")
    candidate_ids={r["candidate_id"] for r in rows.values()}
    if len(candidate_ids)!=1:raise ValueError(f"{path}: candidate_id must be consistent across all grade records")
    return rows,hashlib.sha256(raw).hexdigest()

def load(path):return load_snapshot(path)[0]

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
        if criteria and set(a)!=criteria:raise ValueError(f"{tid}: criterion set differs across tasks; consistent rubric criteria required")
        if not criteria:criteria=set(a)
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
    try:
        baseline,baseline_sha=load_snapshot(a.baseline_grades)
        adapter,adapter_sha=load_snapshot(a.adapter_grades)
        result=compare(baseline,adapter)
    except ValueError as e:p.error(str(e))
    result["input_grade_file_sha256"]={"baseline":baseline_sha,"adapter":adapter_sha}
    result["comparison_schema_version"]=1
    output_sha256=atomic_write_json(a.output,result)
    print(json.dumps({"task_count":result["task_count"],"criteria":result["criteria"],"input_grade_file_sha256":result["input_grade_file_sha256"],"output_sha256":output_sha256,"output":str(a.output)},indent=2))
if __name__=="__main__":main()
