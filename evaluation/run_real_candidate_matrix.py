#!/usr/bin/env python3
"""Execute the pinned candidate set sequentially on one runner/CPU."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

SHA=re.compile(r"^[0-9a-f]{40}$")

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--suite",action="append",required=True,type=Path)
    p.add_argument("--dtype",choices=("bfloat16","float32"),default="bfloat16")
    p.add_argument("--max-new-tokens",type=int,default=64)
    p.add_argument("--cache-dir",type=Path,default=Path(".hf-cache"))
    p.add_argument("--output-dir",type=Path,default=Path("artifacts/evaluations/candidates"))
    p.add_argument("--run-record",type=Path,default=Path("artifacts/evaluations/candidate-run.json"))
    a=p.parse_args()
    manifest=json.loads(a.manifest.read_text(encoding="utf-8"))
    candidates=manifest.get("candidates")
    if not isinstance(candidates,list) or not candidates: raise ValueError("manifest must contain a non-empty candidates array")
    ids=[x.get("id") for x in candidates]
    if any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)): raise ValueError("candidate IDs must be unique non-empty strings")
    a.output_dir.mkdir(parents=True,exist_ok=True)
    outcomes=[]
    failed=False
    for candidate in candidates:
        cid=candidate["id"]; revision=candidate.get("revision","")
        if not SHA.fullmatch(revision): raise ValueError(f"{cid}: revision must be a full immutable 40-character SHA")
        if candidate.get("gated") is True:
            outcomes.append({"candidate_id":cid,"family":candidate.get("family"),"repo_id":candidate.get("repo_id"),
              "revision":revision,"status":"skipped_gated","reason":"Manual model access/acceptance is required; no credentials or access controls are bypassed."})
            print(f"[{cid}] SKIPPED: gated checkpoint requires authorized manual access",flush=True)
            continue
        output=a.output_dir/f"{cid}.json"; log=a.output_dir/f"{cid}.log"
        cmd=[sys.executable,"evaluation/run_real_candidate_eval.py","--repo",candidate["repo_id"],
          "--revision",revision,"--family",candidate["family"],"--dtype",a.dtype,
          "--max-new-tokens",str(a.max_new_tokens),"--cache-dir",str(a.cache_dir),"--output",str(output)]
        for suite in a.suite: cmd.extend(["--suite",str(suite)])
        print(f"[{cid}] START {candidate['repo_id']}@{revision}",flush=True)
        with log.open("w",encoding="utf-8") as stream:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            assert proc.stdout is not None
            for line in proc.stdout:
                stream.write(line); stream.flush()
                print(f"[{cid}] {line}",end="",flush=True)
            code=proc.wait()
        status="passed" if code==0 and output.exists() else "failed"
        failed=failed or status=="failed"
        outcomes.append({"candidate_id":cid,"family":candidate["family"],"repo_id":candidate["repo_id"],
          "revision":revision,"status":status,"return_code":code,"result_file":str(output) if output.exists() else None,
          "log_file":str(log)})
        print(f"[{cid}] {status.upper()}",flush=True)
    record={"schema_version":"vectolith-sequential-candidate-run/1.0",
      "completed_at":datetime.now(timezone.utc).isoformat(),"manifest":str(a.manifest),
      "runner_mode":"sequential_single_runner","dtype":a.dtype,"max_new_tokens":a.max_new_tokens,
      "suite_files":[str(x) for x in a.suite],"outcomes":outcomes,
      "all_ungated_candidates_passed":not failed}
    a.run_record.parent.mkdir(parents=True,exist_ok=True)
    a.run_record.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    return 1 if failed else 0

if __name__=="__main__": raise SystemExit(main())
