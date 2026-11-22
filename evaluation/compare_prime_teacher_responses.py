#!/usr/bin/env python3
"""Integrity-check and compare real ASH PRIME teacher JSON/JSONL artifacts.

Reports coverage, completion and pairwise response disagreement. It does not
score, rank, select, grade, or discard any teacher or response.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_RECORD_FIELDS = ("candidate_id", "repo_id", "immutable_revision", "run_id")

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def normalized_completion_status(row: dict) -> str:
    """Fail closed when completion fields contradict one another."""
    if row.get("error"):
        return "error"

    explicit = row.get("completion_status")
    cap_flag = row.get("generation_cap_reached")
    generation_status = row.get("generation_status")
    cap_status = generation_status == "token_limit_reached"
    explicit_cap = explicit == "token_cap_truncated"
    cap_signal = cap_flag is True or cap_status or explicit_cap

    # Contradictory metadata must never be summarized as a completed response.
    if cap_flag is False and (cap_status or explicit_cap):
        return "metadata_conflict"
    if explicit_cap and generation_status not in (None, "token_limit_reached"):
        return "metadata_conflict"
    if cap_signal and explicit in {
        "eos_completed", "stopped_without_eos", "completed_without_token_cap"
    }:
        return "metadata_conflict"
    if cap_signal:
        return "token_cap_truncated"

    response = row.get("response_text")
    if not isinstance(response, str) or not response.strip():
        return "empty_output"
    if isinstance(explicit, str) and explicit:
        return explicit
    if generation_status == "eos_or_early_stop":
        return "completed_without_token_cap"
    return "unclassified"

def load_artifact(path: Path) -> tuple[dict,dict]:
    record=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record,dict): raise ValueError(f"{path}: JSON root must be an object")
    for field in REQUIRED_RECORD_FIELDS:
        if not isinstance(record.get(field),str) or not record[field].strip():
            raise ValueError(f"{path}: missing or invalid {field}")
    revision=record["immutable_revision"]
    if not re.fullmatch(r"[0-9a-f]{40}",revision):
        raise ValueError(f"{path}: immutable_revision must be a full lowercase commit SHA")
    rows_path=path.with_suffix(".jsonl")
    if not rows_path.is_file(): raise ValueError(f"missing paired JSONL: {rows_path}")
    rows=[]
    for line_number,line in enumerate(rows_path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try: row=json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{rows_path}:{line_number}: invalid JSONL: {exc}") from exc
        if not isinstance(row,dict): raise ValueError(f"{rows_path}:{line_number}: row must be an object")
        rows.append(row)
    if not isinstance(record.get("case_count"),int) or len(rows)!=record["case_count"]:
        raise ValueError(f"{path}: JSON/JSONL case count mismatch")
    case_ids=[r.get("case_id") for r in rows]
    if any(not isinstance(case_id,str) or not case_id for case_id in case_ids):
        raise ValueError(f"{path}: every row requires a non-empty case_id")
    if len(set(case_ids))!=len(rows): raise ValueError(f"{path}: duplicate case IDs")
    for row in rows:
        if row.get("candidate_id")!=record["candidate_id"]:
            raise ValueError(f"{path}: candidate provenance mismatch")
        if row.get("model_revision")!=revision:
            raise ValueError(f"{path}: revision provenance mismatch")
        if row.get("run_id")!=record["run_id"]:
            raise ValueError(f"{path}: run provenance mismatch")
        prompt_hash=row.get("prompt_sha256")
        if not isinstance(prompt_hash,str) or not SHA256_RE.fullmatch(prompt_hash):
            raise ValueError(f"{path}: invalid or missing prompt_sha256 for {row['case_id']}")
        if row.get("response_text") is not None and not isinstance(row.get("response_text"),str):
            raise ValueError(f"{path}: response_text must be a string or null")
    # The full evaluation JSON embeds its results as well as writing JSONL.
    # Loader-smoke and older summary artifacts may omit embedded results.
    embedded=record.get("results")
    if embedded is not None:
        if not isinstance(embedded,list) or len(embedded)!=len(rows):
            raise ValueError(f"{path}: embedded results count does not match JSONL")
        by_id={row["case_id"]:row for row in rows}
        for item in embedded:
            if not isinstance(item,dict) or item.get("case_id") not in by_id:
                raise ValueError(f"{path}: embedded result has unknown or invalid case_id")
            raw=by_id[item["case_id"]]
            for field in ("candidate_id","model_revision","run_id","prompt_sha256","completion_status","response_text"):
                if item.get(field)!=raw.get(field):
                    raise ValueError(f"{path}: embedded JSON/JSONL mismatch for {item['case_id']} field {field}")
        if len({item.get("case_id") for item in embedded})!=len(rows):
            raise ValueError(f"{path}: duplicate embedded result case IDs")
    return record,{r["case_id"]:r for r in rows}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact",type=Path,action="append",required=True,help="one real inference JSON record; paired JSONL must sit beside it")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    loaded=[]
    seen_runs=set()
    for path in a.artifact:
        record,rows=load_artifact(path)
        identity=(record["candidate_id"],record["run_id"])
        if identity in seen_runs: raise ValueError(f"duplicate candidate/run artifact: {identity}")
        seen_runs.add(identity)
        loaded.append({"path":str(path),"sha256_json":digest(path),"sha256_jsonl":digest(path.with_suffix(".jsonl")),"record":record,"rows":rows})
    contributors=[]
    for item in loaded:
        r=item["record"]; rows=list(item["rows"].values())
        contributors.append({
          "candidate_id":r["candidate_id"],"repo_id":r["repo_id"],"revision":r["immutable_revision"],
          "run_id":r["run_id"],"schema_version":r.get("schema_version"),
          "case_count":len(rows),"case_ids":sorted(item["rows"]),
          "artifact_json":item["path"],"artifact_json_sha256":item["sha256_json"],
          "artifact_jsonl_sha256":item["sha256_jsonl"],
          "completion_counts":dict(sorted(Counter(normalized_completion_status(x) for x in rows).items())),
          "error_count":sum(normalized_completion_status(x)=="error" for x in rows),
          "empty_output_count":sum(normalized_completion_status(x)=="empty_output" for x in rows),
          "token_cap_truncated_count":sum(normalized_completion_status(x)=="token_cap_truncated" for x in rows),
          "prompt_hash_count":len({x["prompt_sha256"] for x in rows})
        })
    pairwise=[]
    for i,left in enumerate(loaded):
      for right in loaded[i+1:]:
        common=sorted(set(left["rows"]) & set(right["rows"]))
        exact=0; similarities=[]; prompt_mismatches=0
        for case_id in common:
          left_row=left["rows"][case_id]; right_row=right["rows"][case_id]
          if left_row["prompt_sha256"] != right_row["prompt_sha256"]:
            prompt_mismatches += 1
            continue
          x=left_row.get("response_text") or ""
          y=right_row.get("response_text") or ""
          exact += x==y
          similarities.append(SequenceMatcher(None,x,y).ratio())
        pairwise.append({
          "left_candidate":left["record"]["candidate_id"],"left_run_id":left["record"]["run_id"],
          "right_candidate":right["record"]["candidate_id"],"right_run_id":right["record"]["run_id"],
          "common_case_count":len(common),"comparable_case_count":len(similarities),
          "prompt_hash_mismatch_count":prompt_mismatches,
          "left_only_case_count":len(set(left["rows"])-set(right["rows"])),
          "right_only_case_count":len(set(right["rows"])-set(left["rows"])),
          "exact_response_matches":exact,
          "exact_response_match_ratio":round(exact/len(similarities),6) if similarities else None,
          "mean_character_similarity":round(sum(similarities)/len(similarities),6) if similarities else None,
          "interpretation":"descriptive_disagreement_only_not_a_quality_score"
        })
    report={"schema_version":"vectolith-prime-teacher-disagreement/1.1",
      "integrity_validation":"passed","contributors":contributors,
      "pairwise_disagreement":pairwise,"ranking":"not_performed",
      "winner_selection":"not_performed","human_grading":"required_and_not_inferred",
      "responses_discarded":False,"training_started":False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"artifact_count":len(loaded),"pair_count":len(pairwise),
      "output":str(a.output),"integrity_validation":"passed"},sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
