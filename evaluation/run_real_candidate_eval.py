#!/usr/bin/env python3
"""Run real CPU inference on one immutable foundation candidate checkpoint."""
from __future__ import annotations
import argparse, gc, json, os, resource, shutil, time
from datetime import datetime, timezone
from pathlib import Path
import torch, transformers
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from run_real_checkpoint_suite import prompt_hash, render_prompt
from run_eval import load_cases

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",required=True); p.add_argument("--revision",required=True)
    p.add_argument("--family",required=True); p.add_argument("--suite",action="append",required=True,type=Path)
    p.add_argument("--dtype",choices=("bfloat16","float32"),default="bfloat16")
    p.add_argument("--max-new-tokens",type=int,default=64)
    p.add_argument("--cache-dir",type=Path,default=Path(".hf-cache"))
    p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    rev=a.revision.lower()
    if len(rev)!=40 or any(ch not in "0123456789abcdef" for ch in rev): p.error("--revision must be a full immutable 40-character commit SHA")
    if not 1<=a.max_new_tokens<=256: p.error("--max-new-tokens must be between 1 and 256")
    torch.set_num_threads(min(torch.get_num_threads(),4))
    if a.dtype=="bfloat16":
        try:
            probe=torch.ones((16,16),dtype=torch.bfloat16); _=probe@probe; del probe
        except Exception as exc: raise RuntimeError(f"CPU bfloat16 matrix multiplication is unavailable: {exc}") from exc
    cases=[]
    for suite in a.suite: cases.extend((suite,c) for c in load_cases(suite))
    if not cases: raise ValueError("no benchmark cases loaded")
    ids=[c["id"] for _,c in cases]
    if len(ids)!=len(set(ids)): raise ValueError("benchmark case IDs must be unique across suites")
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
    raw_handle=raw_output.open('w',encoding='utf-8')
    for suite,case in cases:
        encoded=render_prompt(tok,case["messages"]); start=time.perf_counter()
        with torch.inference_mode():
            output=model.generate(**encoded,max_new_tokens=a.max_new_tokens,do_sample=False,use_cache=True,pad_token_id=tok.eos_token_id)
        latency=round(time.perf_counter()-start,3); n=int(encoded["input_ids"].shape[1]); new=output[0,n:]
        response=tok.decode(new,skip_special_tokens=True)
        if new.numel()<1 or not response.strip(): raise RuntimeError(f"{case['id']}: no visible generated output")
        hit_token_cap = int(new.numel()) >= a.max_new_tokens and (
            tok.eos_token_id is None or tok.eos_token_id not in new.tolist()
        )
        results.append({"suite":str(suite),"role":"core_prima" if suite.name.startswith("prima") else "core_prime",
          "case_id":case["id"],"category":case.get("category","uncategorized"),"prompt_sha256":prompt_hash(case["messages"]),
          "rubric":case.get("rubric"),"input_tokens":n,"generated_tokens":int(new.numel()),
          "max_new_tokens":a.max_new_tokens,"generation_cap_reached":hit_token_cap,
          "generation_status":"token_limit_reached" if hit_token_cap else "eos_or_early_stop",
          "latency_seconds":latency,"response_text":response,"error":None})
        raw_handle.write(json.dumps(results[-1],ensure_ascii=False,sort_keys=True)+"\n")
        raw_handle.flush()
        print(f"{case['id']}: {len(new)} tokens in {latency}s",flush=True)
    raw_handle.close()
    generation_s=round(time.perf_counter()-gen,3)
    vocab=int(model.get_input_embeddings().weight.shape[0])
    if len(tok)>vocab: raise RuntimeError("tokenizer vocabulary exceeds model embedding vocabulary")
    record={"schema_version":"vectolith-real-candidate-evaluation/1.1","completed_at":datetime.now(timezone.utc).isoformat(),
      "family":a.family,"repo_id":a.repo,"immutable_revision":rev,"loaded_snapshot_path_revision":snapshot.name,
      "architectures":getattr(model.config,"architectures",None),"model_class":model.__class__.__name__,
      "tokenizer_class":tok.__class__.__name__,"tokenizer_vocab_size":len(tok),"model_vocab_size":vocab,
      "embedding_vocab_padding":vocab-len(tok),"device":"cpu","dtype":a.dtype,
      "cpu_capability":torch.backends.cpu.get_cpu_capability(),"cpu_count_visible":os.cpu_count(),
      "snapshot_size_bytes":snapshot_bytes,"download_seconds":download_s,"model_load_seconds":load_s,
      "generation_seconds":generation_s,"total_seconds":round(time.perf_counter()-total,3),
      "torch_version":torch.__version__,"transformers_version":transformers.__version__,
      "decoding":{"do_sample":False,"max_new_tokens":a.max_new_tokens,"chat_template":True,"enable_thinking":False},
      "case_count":len(results),"raw_results_file":str(raw_output),"max_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      "license_review":"pending_human_legal_review","training_output_permission":"not_verified",
      "teacher_qualification":"not_qualified","training_started":False,"grading":"human_review_required","results":results}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"Captured {len(results)} real outputs for {a.repo}@{rev}",flush=True)
    del model,tok; gc.collect()
    shutil.rmtree(a.cache_dir/f"models--{a.repo.replace('/','--')}",ignore_errors=True)
    return 0
if __name__=="__main__": raise SystemExit(main())
