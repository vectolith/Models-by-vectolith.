#!/usr/bin/env python3
"""Reproducible, non-destructive screening of preserved Core Prime teacher outputs.

This tool does not assign quality scores or qualify teachers. Heuristic flags are
review leads requiring substantive adjudication; they are not proof of a defect.
"""
from __future__ import annotations
import argparse, collections, csv, glob, hashlib, json, os, re, statistics, zipfile

META_RE = re.compile(r"</?think>|\b(let me think|the user wants me|I should respond|as an AI language model)\b", re.I)
ACTION_RE = re.compile(r"\b(I have|I already|I just|successfully)\b.{0,70}\b(deleted|sent|emailed|created|updated|searched|called|executed|ran|booked|transferred)\b", re.I)

def load_rows(paths):
    rows=[]
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith(".jsonl"):
                    for line in archive.read(name).decode("utf-8").splitlines():
                        item=json.loads(line); item["_artifact"]=os.path.basename(path); rows.append(item)
    return rows

def screen(rows):
    findings=[]
    for item in rows:
        answer=item.get("response_text") or ""
        flags=[]
        if item.get("generation_cap_reached") or item.get("generation_status")=="token_limit_reached": flags.append("truncated_at_generation_cap")
        if META_RE.search(answer): flags.append("possible_internal_reasoning_or_meta_text")
        if ACTION_RE.search(answer): flags.append("possible_unverified_action_claim")
        if len(answer.strip())<35: flags.append("very_short_response")
        if re.search(r"\b(TODO|INSERT HERE|lorem ipsum|PLACEHOLDER)\b",answer,re.I): flags.append("placeholder_text")
        if item.get("error") is not None: flags.append("generation_error")
        if not answer.strip(): flags.append("empty_response")
        if item.get("generated_tokens",0)>item.get("max_new_tokens",10): flags.append("token_count_exceeds_cap")
        findings.append({
            "candidate_id":item.get("candidate_id"),"model_revision":item.get("model_revision"),
            "run_id":item.get("run_id"),"case_id":item.get("case_id"),"category":item.get("category"),
            "generation_status":item.get("generation_status"),"generated_tokens":item.get("generated_tokens"),
            "max_new_tokens":item.get("max_new_tokens"),"latency_seconds":item.get("latency_seconds"),
            "response_sha256":hashlib.sha256(answer.encode()).hexdigest(),"response_chars":len(answer),
            "response_words":len(answer.split()),"flags":flags,"artifact":item.get("_artifact")
        })
    return findings

def summarize(rows, findings):
    result={"schema_version":"1.0","review_type":"automated_evidence_screening_not_human_grading",
            "response_count":len(rows),"candidate_summaries":{},"category_summaries":{},
            "duplicate_candidate_run_case_keys":0,"all_errors_null":all(x.get("error") is None for x in rows)}
    keys=collections.Counter((x.get("candidate_id"),x.get("run_id"),x.get("case_id")) for x in rows)
    result["duplicate_candidate_run_case_keys"]=sum(n>1 for n in keys.values())
    for candidate in sorted({x["candidate_id"] for x in rows}):
        rr=[x for x in rows if x["candidate_id"]==candidate]
        ff=[x for x in findings if x["candidate_id"]==candidate]
        lat=[x["latency_seconds"] for x in rr]
        def n(flag): return sum(flag in y["flags"] for y in ff)
        caps=sum(bool(x.get("generation_cap_reached")) for x in rr)
        result["candidate_summaries"][candidate]={
            "responses":len(rr),"unique_cases":len({x["case_id"] for x in rr}),
            "unique_runs":len({x["run_id"] for x in rr}),"token_cap_hits":caps,
            "token_cap_rate":round(caps/len(rr),4),"mean_latency_seconds":round(statistics.mean(lat),3),
            "median_latency_seconds":round(statistics.median(lat),3),
            "mean_response_words":round(statistics.mean(len(x["response_text"].split()) for x in rr),2),
            "possible_reasoning_meta_leak":n("possible_internal_reasoning_or_meta_text"),
            "possible_unverified_action_claim":n("possible_unverified_action_claim"),
            "very_short_response":n("very_short_response"),"placeholder_text":n("placeholder_text"),
            "generation_errors":n("generation_error")}
    for category in sorted({x["category"] for x in rows}):
        rr=[x for x in rows if x["category"]==category]
        ff=[x for x in findings if x["category"]==category]
        caps=sum(bool(x.get("generation_cap_reached")) for x in rr)
        result["category_summaries"][category]={
            "responses":len(rr),"token_cap_hits":caps,"token_cap_rate":round(caps/len(rr),4),
            "possible_reasoning_meta_leak":sum("possible_internal_reasoning_or_meta_text" in x["flags"] for x in ff),
            "possible_unverified_action_claim":sum("possible_unverified_action_claim" in x["flags"] for x in ff)}
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact-dir",required=True)
    parser.add_argument("--json-output",required=True)
    parser.add_argument("--csv-output",required=True)
    args=parser.parse_args()
    paths=sorted(glob.glob(os.path.join(args.artifact_dir,"core-prime-*.zip")))
    if not paths: raise SystemExit("No core-prime-*.zip artifacts found")
    rows=load_rows(paths)
    if len(rows)!=2700: raise SystemExit(f"Expected 2700 rows from pinned historical corpus, found {len(rows)}")
    findings=screen(rows); summary=summarize(rows,findings)
    summary["source_artifacts"]=[os.path.basename(x) for x in paths]
    with open(args.json_output,"w",encoding="utf-8") as f: json.dump(summary,f,indent=2)
    with open(args.csv_output,"w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(findings[0])); writer.writeheader()
        for row in findings:
            row=dict(row); row["flags"]=";".join(row["flags"]); writer.writerow(row)
    print(json.dumps({"responses":len(rows),"candidates":len(summary["candidate_summaries"]),
                      "categories":len(summary["category_summaries"]),
                      "token_cap_hits":sum(x["token_cap_hits"] for x in summary["candidate_summaries"].values()),
                      "duplicate_keys":summary["duplicate_candidate_run_case_keys"],
                      "all_errors_null":summary["all_errors_null"]},indent=2))
if __name__=="__main__": main()
