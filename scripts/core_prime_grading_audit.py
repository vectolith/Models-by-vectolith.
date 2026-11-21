#!/usr/bin/env python3
"""Audit blinded human grading coverage and agreement; does not grade responses."""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path

def audit(payload, cohort_ids=None, min_cases=1):
    errors=[]
    if not isinstance(payload,dict) or not isinstance(payload.get("ratings"),list):
        return {"errors":["input must be an object with ratings list"],"summary":{}}
    ratings=payload["ratings"]
    grouped=defaultdict(dict)
    reviewer_ids=set()
    for i,r in enumerate(ratings):
        if not isinstance(r,dict): errors.append(f"rating {i}: malformed"); continue
        case,reviewer,score=r.get("blind_case_id"),r.get("reviewer_id"),r.get("score")
        if not isinstance(case,str) or not case.strip() or not isinstance(reviewer,str) or not reviewer.strip():
            errors.append(f"rating {i}: blind_case_id and reviewer_id required"); continue
        if isinstance(score,bool) or not isinstance(score,(int,float)) or not 0<=score<=5:
            errors.append(f"rating {i}: score must be numeric in 0..5"); continue
        if reviewer in grouped[case]: errors.append(f"{case}: duplicate reviewer rating {reviewer}"); continue
        if cohort_ids and reviewer in cohort_ids: errors.append(f"{case}: reviewer overlaps teacher cohort: {reviewer}")
        grouped[case][reviewer]=score; reviewer_ids.add(reviewer)
    eligible={c:r for c,r in grouped.items() if len(r)>=2}
    under_review={c:len(r) for c,r in grouped.items() if len(r)<2}
    if len(eligible)<min_cases: errors.append(f"only {len(eligible)} cases have 2+ ratings; minimum is {min_cases}")
    pairs=[]
    for c,rs in eligible.items():
        ordered=sorted(rs)
        pairs.append((rs[ordered[0]],rs[ordered[1]]))
    exact=sum(a==b for a,b in pairs)/len(pairs) if pairs else None
    kappa=None
    if pairs:
        labels=sorted({v for pair in pairs for v in pair})
        n=len(pairs); p0=sum(a==b for a,b in pairs)/n
        p1=sum(a==b for a,b in pairs)/n
        marg_a={v:sum(a==v for a,b in pairs)/n for v in labels}
        marg_b={v:sum(b==v for a,b in pairs)/n for v in labels}
        pe=sum(marg_a[v]*marg_b[v] for v in labels)
        kappa=(p0-pe)/(1-pe) if pe<1 else (1.0 if p0==1 else 0.0)
    return {"errors":errors,"summary":{"rating_rows":len(ratings),"unique_cases":len(grouped),
      "reviewers":len(reviewer_ids),"cases_with_two_or_more_reviewers":len(eligible),
      "cases_under_review":under_review,"exact_agreement_first_two_reviewers_per_case":exact,
      "cohen_kappa_first_two_sorted_reviewers":kappa,
      "note":"Agreement statistics are descriptive, not teacher qualification or permission evidence."}}

def main():
    p=argparse.ArgumentParser(); p.add_argument("ratings_json",type=Path); p.add_argument("--cohort",type=Path); p.add_argument("--minimum-cases",type=int,default=1); p.add_argument("--output",type=Path)
    a=p.parse_args()
    try: data=json.loads(a.ratings_json.read_text(encoding="utf-8")); cohort=json.loads(a.cohort.read_text(encoding="utf-8")) if a.cohort else []
    except Exception as e: print(f"input error: {e}",file=sys.stderr); return 2
    if not isinstance(cohort,list) or any(not isinstance(x,str) for x in cohort): print("cohort must be a JSON list of reviewer-conflicting IDs",file=sys.stderr); return 2
    result=audit(data,set(cohort),a.minimum_cases)
    rendered=json.dumps(result,indent=2,sort_keys=True)
    if a.output: a.output.write_text(rendered+"\n",encoding="utf-8")
    print(rendered); return 1 if result["errors"] else 0
if __name__=="__main__": sys.exit(main())
