#!/usr/bin/env python3
"""Run real CPU inference on one immutable foundation candidate checkpoint."""
from __future__ import annotations
import argparse, gc, json, os, resource, shutil, time, uuid
from datetime import datetime, timezone
from pathlib import Path
import torch, transformers
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from generation import render_prompt
from run_real_checkpoint_suite import prompt_hash
from run_eval import load_cases
from completion import classify_completion, summarize_completion

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",required=True); p.add_argument("--revision",required=True)
    p.add_argument("--family",required=True); p.add_argument("--candidate-id"); p.add_argument("--suite",action="append",required=True,type=Path)
    p.add_argument("--dtype",choices=("bfloat16","float32"),default="bfloat16")
    p.add_argument("--max-new-tokens",type=int,default=64)
    p.add_argument("--cache-dir",type=Path,default=Path(".hf-cache"))
    p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    rev=a.revision.lower()
    if len(rev)!=40 or any(ch not in "0123456789abcdef" for ch in rev): p.error("--revision must be a full immutable 40-character commit SHA")
    if not 1<=a.max_new_tokens<=1024: p.error("--max-new-tokens must be between 1 and 1024")
    requested_threads = max(1, int(os.environ.get("VELNOR_INFERENCE_THREADS", "2")))
    torch.set_num_threads(min(torch.get_num_threads(), requested_threads))
    if a.dtype=="bfloat16":
        try:
            probe=torch.ones((16,16),dtype=torch.bfloat16); _=probe@probe; del probe
        except Exception as exc: raise RuntimeError(f"CPU bfloat16 matrix multiplication is unavailable: {exc}") from exc
    cases=[]
    for suite in a.suite: cases.extend((suite,c) for c in load_cases(suite))
    if not cases: raise ValueError("no benchmark cases loaded")
    ids=[c["id"] for _,c in cases]
    if len(ids)!=len(set(ids)): raise ValueError("benchmark case IDs must be unique across suites")
    candidate_id=a.candidate_id or a.repo
    run_id=uuid.uuid4().hex
    run_started_at=datetime.now(timezone.utc).isoformat()
    total=time.perf_counter(); dl=time.perf_counter()
    snapshot=Path(snapshot_download(repo_id=a.repo,revision=rev,cache_dir=str(a.cache_dir)))
    download_s=round(time.perf_counter()-dl,3)
    if snapshot.name!=rev: raise RuntimeError(f"Hub snapshot revision {snapshot.name!r} does not match {rev!r}")
    snapshot_bytes=sum(x.stat().st_size for x in snapshot.rglob("*") if x.is_file())
    load=time.perf_counter()
    tok=AutoTokenizer.from_pretrained(snapshot,local_files_only=True)
    dtype=torch.bfloat16 if a.dtype=="bfloat16" else torch.float32
    model=AutoModelForCausalLM.from_pretrained(snapshot,local_files_only=True,torch_dtype=dtype,low_cpu_mem_usage=True)
    model.eval(); load_s=round(time.perf_counter()-load,3)
    gen=time.perf_counter(); results=[]
    raw_output=a.output.with_suffix('.jsonl')
    raw_output.parent.mkdir(parents=True,exist_ok=True)
    failures=0
    with raw_output.open('w',encoding='utf-8') as raw_handle:
        for suite,case in cases:
            case_started_at=datetime.now(timezone.utc).isoformat()
            base={"suite":str(suite),"role":"core_prime","case_id":case["id"],"benchmark_case_id":case["id"],
              "candidate_id":candidate_id,"model_revision":rev,"run_id":run_id,"started_at":case_started_at,
              "recorded_at":datetime.now(timezone.utc).isoformat(),"category":case.get("category","uncategorized"),
              "prompt_sha256":prompt_hash(case["messages"]),"rubric":case.get("rubric"),
              "max_new_tokens":a.max_new_tokens,"generation_cap_reached":False,
              "generation_status":"error","completion_status":"error","latency_seconds":None,"input_tokens":None,
              "generated_tokens":0,"response_text":None,"error":None}
            start=time.perf_counter()
            try:
                encoded=render_prompt(tok,case["messages"])
                with torch.inference_mode():
                    output=model.generate(**encoded,max_new_tokens=a.max_new_tokens,do_sample=False,use_cache=True,pad_token_id=tok.eos_token_id)
                latency=round(time.perf_counter()-start,3); n=int(encoded["input_ids"].shape[1]); new=output[0,n:]
                response=tok.decode(new,skip_special_tokens=True)
                if new.numel()<1 or not response.strip():
                    base["completion_status"] = "empty_output"
                    raise RuntimeError("no visible generated output")
                completion_status = classify_completion(
                    new.tolist(), a.max_new_tokens, tok.eos_token_id, response
                )
                hit_token_cap = completion_status == "token_cap_truncated"
                base.update({"input_tokens":n,"generated_tokens":int(new.numel()),
                  "generation_cap_reached":hit_token_cap,
                  "generation_status":"token_limit_reached" if hit_token_cap else "eos_or_early_stop",
                  "completion_status":completion_status,
                  "latency_seconds":latency,"response_text":response,"error":None})
                print(f"{case['id']}: {len(new)} tokens in {latency}s",flush=True)
            except Exception as exc:
                failures+=1
                base.update({"latency_seconds":round(time.perf_counter()-start,3),
                  "error":f"{type(exc).__name__}: {exc}",
                  "completion_status":"empty_output" if base.get("completion_status")=="empty_output" else "error"})
                print(f"{case['id']}: ERROR {base['error']}",flush=True)
            results.append(base)
            raw_handle.write(json.dumps(base,ensure_ascii=False,sort_keys=True)+"\n")
            raw_handle.flush()

    generation_s=round(time.perf_counter()-gen,3)
    vocab=int(model.get_input_embeddings().weight.shape[0])
    if len(tok)>vocab: raise RuntimeError("tokenizer vocabulary exceeds model embedding vocabulary")
    record={"schema_version":"vectolith-real-candidate-evaluation/1.2","completed_at":datetime.now(timezone.utc).isoformat(),
      "workflow_run_id":os.environ.get("GITHUB_RUN_ID"),
      "workflow_run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),
      "workflow_job":os.environ.get("GITHUB_JOB"),
      "family":a.family,"candidate_id":candidate_id,"run_id":run_id,"started_at":run_started_at,"repo_id":a.repo,"immutable_revision":rev,"loaded_snapshot_path_revision":snapshot.name,
      "architectures":getattr(model.config,"architectures",None),"model_class":model.__class__.__name__,
      "tokenizer_class":tok.__class__.__name__,"tokenizer_vocab_size":len(tok),"model_vocab_size":vocab,
      "embedding_vocab_padding":vocab-len(tok),"device":"cpu","dtype":a.dtype,
      "cpu_capability":torch.backends.cpu.get_cpu_capability(),"cpu_count_visible":os.cpu_count(),
      "snapshot_size_bytes":snapshot_bytes,"download_seconds":download_s,"model_load_seconds":load_s,
      "generation_seconds":generation_s,"total_seconds":round(time.perf_counter()-total,3),
      "torch_version":torch.__version__,"transformers_version":transformers.__version__,
      "decoding":{"do_sample":False,"max_new_tokens":a.max_new_tokens,"chat_template":True,"enable_thinking":False},
      "case_count":len(results),"error_count":failures,"successful_case_count":len(results)-failures,
      "completion_status_counts":summarize_completion(results),"token_cap_truncated_count":sum(1 for row in results if row.get("completion_status")=="token_cap_truncated"),"raw_results_file":str(raw_output),"max_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      "license_review":"pending_human_legal_review","training_output_permission":"not_verified",
      "teacher_qualification":"not_qualified","training_started":False,"grading":"human_review_required","results":results}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Captured {len(results)} real outputs for {a.repo}@{rev}",flush=True)
    del model,tok; gc.collect()
    shutil.rmtree(a.cache_dir/f"models--{a.repo.replace('/','--')}",ignore_errors=True)
    return 1 if failures else 0
if __name__=="__main__": raise SystemExit(main())
