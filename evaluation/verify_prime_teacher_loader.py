#!/usr/bin/env python3
"""Candidate-specific real loader and one-case generation smoke for Core Prime."""
from __future__ import annotations
import argparse, json, resource, time, uuid
from datetime import datetime, timezone
from pathlib import Path
import torch, transformers
from transformers import AutoTokenizer, AutoProcessor, AutoModelForCausalLM
from run_real_checkpoint_suite import prompt_hash
from completion import classify_completion

REGISTRY=Path(__file__).with_name("prime_teacher_candidate_registry.json")
MESSAGES=[
 {"role":"system","content":"You are evaluated as Core Prime. Be accurate, respect constraints and never claim unperformed actions."},
 {"role":"user","content":"Explain the difference between a process and a thread in an operating system in three concise points."}
]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate-id",required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    reg=json.loads(REGISTRY.read_text(encoding="utf-8"))
    spec=next((x for x in reg["contributors"] if x["candidate_id"]==a.candidate_id),None)
    if spec is None: raise SystemExit("candidate not in registry")
    if spec.get("license_review")!="approved_for_local_inference" or spec.get("local_inference_authorized") is not True:
        raise SystemExit("local inference authorization is not approved")
    conflict=spec.get("license_evidence_conflict")
    if conflict and conflict.get("status")!="resolved":
        raise SystemExit("candidate license evidence conflict is unresolved")
    manifest=json.loads(a.manifest.read_text(encoding="utf-8"))
    if manifest["candidate_id"]!=a.candidate_id: raise RuntimeError("manifest candidate mismatch")
    if manifest["repo_id"]!=spec["repo_id"]: raise RuntimeError("manifest repository mismatch")
    snapshot=Path(manifest["snapshot_path"])
    if snapshot.name!=manifest["immutable_revision"]: raise RuntimeError("snapshot path is not immutable revision")
    config=json.loads((snapshot/"config.json").read_text(encoding="utf-8"))
    if config.get("model_type")!=spec["expected_model_type"]: raise RuntimeError("model_type mismatch")
    if spec["expected_architecture"] not in config.get("architectures",[]): raise RuntimeError("architecture mismatch")
    torch.set_num_threads(max(1,min(torch.get_num_threads(),2)))
    dtype=torch.bfloat16
    start=time.perf_counter()
    if spec["loader"]=="causal":
        tok=AutoTokenizer.from_pretrained(snapshot,local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(snapshot,local_files_only=True,torch_dtype=dtype,low_cpu_mem_usage=True,trust_remote_code=False)
        encoded=tok.apply_chat_template(MESSAGES,tokenize=True,add_generation_prompt=True,return_tensors="pt",return_dict=True)
        decode=lambda ids: tok.decode(ids,skip_special_tokens=True)
    else:
        tok=AutoProcessor.from_pretrained(snapshot,local_files_only=True)
        if spec["loader"]=="image_text":
            from transformers import AutoModelForImageTextToText
            cls=AutoModelForImageTextToText
        elif spec["loader"]=="multimodal":
            from transformers import AutoModelForMultimodalLM
            cls=AutoModelForMultimodalLM
        else: raise RuntimeError(f"unsupported loader {spec['loader']!r}")
        model=cls.from_pretrained(snapshot,local_files_only=True,torch_dtype=dtype,low_cpu_mem_usage=True,trust_remote_code=False)
        encoded=tok.apply_chat_template(MESSAGES,tokenize=True,add_generation_prompt=True,return_tensors="pt",return_dict=True)
        encoded.pop("token_type_ids",None)
        decode=lambda ids: tok.tokenizer.decode(ids,skip_special_tokens=True)
    model.eval()
    load_seconds=time.perf_counter()-start
    gen=time.perf_counter()
    tokenizer_for_eos=tok if spec["loader"]=="causal" else tok.tokenizer
    eos_id=tokenizer_for_eos.eos_token_id
    pad_id=tokenizer_for_eos.pad_token_id
    if pad_id is None: pad_id=eos_id[0] if isinstance(eos_id,(list,tuple)) else eos_id
    with torch.inference_mode():
        output=model.generate(**encoded,max_new_tokens=96,do_sample=False,use_cache=True,pad_token_id=pad_id)
    n=int(encoded["input_ids"].shape[1]); new=output[0,n:]
    response=decode(new)
    if not response.strip(): raise RuntimeError("loader smoke produced an empty response")
    run_id=uuid.uuid4().hex
    completion_status=classify_completion(new.tolist(),96,eos_id,response)
    result={
      "schema_version":"vectolith-prime-loader-smoke/1.0","candidate_id":a.candidate_id,
      "repo_id":spec["repo_id"],"immutable_revision":manifest["immutable_revision"],
      "run_id":run_id,"case_count":1,
      "loader":spec["loader"],"model_class":model.__class__.__name__,
      "processor_or_tokenizer_class":tok.__class__.__name__,
      "transformers_version":transformers.__version__,"torch_version":torch.__version__,
      "dtype":"bfloat16","device":"cpu","load_seconds":round(load_seconds,3),
      "generation_seconds":round(time.perf_counter()-gen,3),
      "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      "prompt_case":"prime-loader-smoke-process-vs-thread","prompt_sha256":prompt_hash(MESSAGES),
      "case_id":"prime-loader-smoke-process-vs-thread","completion_status":completion_status,
      "input_tokens":n,"generated_tokens":int(new.numel()),"response_text":response,
      "loader_verified":True,"license_review":"approved_for_local_inference",
      "training_output_permission":spec.get("training_output_permission","not_verified"),
      "teacher_qualification":"not_qualified","training_started":False,
      "completed_at":datetime.now(timezone.utc).isoformat()
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    row={"case_id":result["case_id"],"candidate_id":a.candidate_id,"model_revision":manifest["immutable_revision"],
      "run_id":run_id,"prompt_sha256":result["prompt_sha256"],"completion_status":completion_status,
      "response_text":response,"generated_tokens":int(new.numel())}
    a.output.with_suffix(".jsonl").write_text(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"candidate_id":a.candidate_id,"loader_verified":True,"model_class":result["model_class"]},sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
