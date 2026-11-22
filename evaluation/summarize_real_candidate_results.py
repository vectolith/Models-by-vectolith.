#!/usr/bin/env python3
"""Summarize real checkpoint execution artifacts without inventing quality scores."""
from __future__ import annotations
import argparse, json, statistics
from pathlib import Path

GIB=1024**3

def summarize(record: dict) -> dict:
    results=record.get("results")
    if not isinstance(results,list) or not results: raise ValueError("candidate result must contain non-empty results")
    latencies=[float(x["latency_seconds"]) for x in results]
    generated=sum(int(x["generated_tokens"]) for x in results)
    generation=float(record["generation_seconds"])
    return {
      "family":record["family"],"repo_id":record["repo_id"],"revision":record["immutable_revision"],
      "cpu_capability":record.get("cpu_capability"),"cpu_count_visible":record.get("cpu_count_visible"),
      "dtype":record["dtype"],"case_count":len(results),"checkpoint_gib":round(record["snapshot_size_bytes"]/GIB,3),
      "peak_rss_gib":round(record["max_rss_kib"]*1024/GIB,3),
      "download_seconds":record["download_seconds"],"model_load_seconds":record["model_load_seconds"],
      "generation_seconds":generation,"total_seconds":record["total_seconds"],
      "generated_tokens":generated,"tokens_per_second":round(generated/generation,3) if generation>0 else None,
      "mean_case_latency_seconds":round(statistics.mean(latencies),3),
      "median_case_latency_seconds":round(statistics.median(latencies),3),
      "role_case_counts":{
        role:sum(1 for item in results if item.get("role")==role)
        for role in ("ash_prime","fyr_prima")
      },
      "grading":"human_review_required","teacher_qualification":"not_qualified",
      "license_review":record.get("license_review","pending_human_legal_review"),
      "training_output_permission":record.get("training_output_permission","not_verified")
    }

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-record",type=Path,required=True)
    p.add_argument("--results-dir",type=Path,required=True)
    p.add_argument("--output-json",type=Path,required=True)
    p.add_argument("--output-markdown",type=Path,required=True)
    a=p.parse_args()
    run=json.loads(a.run_record.read_text(encoding="utf-8"))
    metrics=[]; failures=[]; skipped=[]
    for outcome in run["outcomes"]:
        if outcome["status"]=="skipped_gated":
            skipped.append(outcome); continue
        if outcome["status"]!="passed":
            failures.append(outcome); continue
        path=Path(outcome["result_file"])
        if not path.is_absolute(): path=Path.cwd()/path
        record=json.loads(path.read_text(encoding="utf-8"))
        if record["immutable_revision"]!=outcome["revision"]:
            raise ValueError(f"{outcome['candidate_id']}: loaded revision does not match manifest")
        if record["repo_id"]!=outcome["repo_id"]:
            raise ValueError(f"{outcome['candidate_id']}: loaded repository does not match manifest")
        metrics.append({"candidate_id":outcome["candidate_id"],**summarize(record)})
    cpu_caps=sorted({x["cpu_capability"] for x in metrics if x["cpu_capability"]})
    cpu_counts=sorted({x["cpu_count_visible"] for x in metrics if x["cpu_count_visible"] is not None})
    same_cpu=(len(cpu_caps)<=1 and len(cpu_counts)<=1 and run.get("runner_mode")=="sequential_single_runner")
    report={
      "schema_version":"vectolith-candidate-comparison-report/1.0",
      "runner_mode":run.get("runner_mode"),"dtype":run.get("dtype"),
      "cpu_capabilities_observed":cpu_caps,"cpu_counts_observed":cpu_counts,
      "same_runner_control":same_cpu,"metrics":metrics,"failed_candidates":failures,
      "skipped_gated_candidates":skipped,
      "quality_ranking":"not_performed",
      "reason":"Public smoke cases are small and require independent rubric grading; execution metrics are not capability scores.",
      "foundation_selection":"not_performed","teacher_qualification":"not_performed",
      "training_started":False
    }
    a.output_json.parent.mkdir(parents=True,exist_ok=True)
    a.output_json.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    headers=["Candidate","Family","CPU","Checkpoint GiB","Peak RAM GiB","Download s","Load s","Generation s","Tokens/s","Mean case s"]
    rows=[]
    for x in metrics:
        rows.append([x["candidate_id"],x["family"],x["cpu_capability"] or "unknown",x["checkpoint_gib"],
          x["peak_rss_gib"],x["download_seconds"],x["model_load_seconds"],x["generation_seconds"],
          x["tokens_per_second"],x["mean_case_latency_seconds"]])
    lines=["# Real checkpoint execution comparison","",
      f"- Execution mode: {run.get('runner_mode')}",
      f"- Same visible CPU capability/count across candidates: **{same_cpu}**",
      f"- Dtype: {run.get('dtype')}",
      "- All candidate outputs are from real pinned checkpoints; raw per-case outputs are retained separately.",
      "- This report measures execution and resource footprint only. It does not rank model quality.",
      "- Public smoke cases are not a hidden holdout. Independent rubric grading is still required.",
      "- License review, training-output permission and teacher qualification remain unverified.",
      "- No training was performed.",""]
    if rows:
        lines.append("| "+" | ".join(headers)+" |")
        lines.append("| "+" | ".join(["---"]*len(headers))+" |")
        for row in rows: lines.append("| "+" | ".join(str(x) for x in row)+" |")
    if skipped:
        lines.extend(["","## Gated candidates not run",""])
        for x in skipped: lines.append(f"- {x['candidate_id']} ({x['repo_id']}): {x['reason']}")
    if failures:
        lines.extend(["","## Failed candidate runs",""])
        for x in failures: lines.append(f"- {x['candidate_id']} ({x['repo_id']}): exit code {x.get('return_code')}")
    a.output_markdown.parent.mkdir(parents=True,exist_ok=True)
    a.output_markdown.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(a.output_markdown.read_text(encoding="utf-8"))
    return 1 if failures else 0

if __name__=="__main__": raise SystemExit(main())
