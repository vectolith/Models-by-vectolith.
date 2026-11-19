#!/usr/bin/env python3
"""Guarded LoRA training runner; authorization/evidence checks precede ML imports."""
import argparse,hashlib,json,platform,sys,time,uuid,math,os,importlib.metadata
from pathlib import Path
def sha256_file(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
def load_rows(p):
 rows=[];ids=set()
 for n,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
  if not line.strip():continue
  r=json.loads(line)
  if not isinstance(r,dict):raise ValueError(f"line {n}: record must be object")
  for k in ("task_id","prompt","response","provenance"):
   if not isinstance(r.get(k),str) or not r[k].strip():raise ValueError(f"line {n}: {k} required")
  if r.get("split")!="train":raise ValueError(f"line {n}: split must be train; development/holdout forbidden")
  if r["task_id"] in ids:raise ValueError(f"line {n}: duplicate task_id")
  ids.add(r["task_id"]);rows.append(r)
 if not rows:raise ValueError("empty dataset")
 return rows
def telemetry_elapsed(records):
 by_run={}
 legacy={}
 for n,r in enumerate(records,1):
  if not isinstance(r,dict):raise ValueError(f"telemetry record {n} must be an object")
  elapsed=r.get("session_elapsed_seconds",r.get("elapsed_seconds"))
  if not isinstance(elapsed,(int,float)) or isinstance(elapsed,bool) or not math.isfinite(elapsed) or elapsed<0:raise ValueError(f"telemetry record {n} has invalid elapsed time")
  run_id=r.get("run_id")
  session=r.get("session_id","unknown")
  if run_id:
   if not isinstance(run_id,str) or not run_id:raise ValueError(f"telemetry record {n} has invalid run_id")
   by_run[run_id]=max(by_run.get(run_id,0.0),float(elapsed))
  else:
   legacy[session]=max(legacy.get(session,0.0),float(elapsed))
 return sum(by_run.values())+sum(legacy.values())
def checkpoint_step(path):
 state=path/"trainer_state.json"
 if not path.is_dir() or not state.is_file():raise ValueError("checkpoint missing trainer_state.json")
 try:record=json.loads(state.read_text(encoding="utf-8"))
 except Exception as e:raise ValueError(f"checkpoint trainer state invalid: {e}")
 try:step=int(path.name.removeprefix("checkpoint-"))
 except Exception:raise ValueError("checkpoint directory name invalid")
 if isinstance(record.get("global_step"),bool) or record.get("global_step")!=step:raise ValueError("checkpoint step mismatch")
 return step
def checkpoint_inventory(path):
 return [{"path":str(f.relative_to(path)),"sha256":sha256_file(f)} for f in sorted(path.rglob("*")) if f.is_file() and f.name not in ("checkpoint-integrity.json","checkpoint-integrity.json.tmp")]
def seal_checkpoint(path):
 step=checkpoint_step(path)
 weights=("adapter_model.safetensors","adapter_model.bin","model.safetensors","pytorch_model.bin")
 if not any((path/name).is_file() and (path/name).stat().st_size>0 for name in weights):raise ValueError("checkpoint weights missing or empty")
 for required in ("optimizer.pt","scheduler.pt"):
  if not (path/required).is_file() or (path/required).stat().st_size==0:raise ValueError(f"checkpoint missing or empty {required}")
 if not any(f.is_file() and f.stat().st_size>0 for f in path.glob("rng_state*.pth")):raise ValueError("checkpoint RNG state missing or empty")
 inventory=checkpoint_inventory(path)
 record={"schema_version":1,"step":step,"files":inventory}
 temp=path/"checkpoint-integrity.json.tmp"
 temp.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 os.replace(temp,path/"checkpoint-integrity.json")
 return record
def validate_checkpoint(path):
 step=checkpoint_step(path)
 weights=("adapter_model.safetensors","adapter_model.bin","model.safetensors","pytorch_model.bin")
 if not any((path/name).is_file() and (path/name).stat().st_size>0 for name in weights):raise ValueError("checkpoint weights missing or empty")
 for required in ("optimizer.pt","scheduler.pt"):
  if not (path/required).is_file() or (path/required).stat().st_size==0:raise ValueError(f"checkpoint missing or empty {required}")
 if not any(f.is_file() and f.stat().st_size>0 for f in path.glob("rng_state*.pth")):raise ValueError("checkpoint RNG state missing or empty")
 manifest_path=path/"checkpoint-integrity.json"
 if not manifest_path.is_file():raise ValueError("checkpoint integrity manifest missing")
 try:manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
 except Exception as e:raise ValueError(f"checkpoint integrity manifest invalid: {e}")
 if manifest.get("schema_version")!=1 or manifest.get("step")!=step:raise ValueError("checkpoint integrity manifest step/schema mismatch")
 actual=checkpoint_inventory(path);expected=manifest.get("files")
 if not isinstance(expected,list) or {i.get("path") for i in expected if isinstance(i,dict)}!={i["path"] for i in actual}:raise ValueError("checkpoint integrity file inventory mismatch")
 by_path={i["path"]:i["sha256"] for i in expected if isinstance(i,dict)}
 for item in actual:
  if by_path.get(item["path"])!=item["sha256"]:raise ValueError(f"checkpoint integrity hash mismatch: {item['path']}")
 return step
def select_recovery_checkpoint(directory):
 candidates=sorted(directory.glob("checkpoint-*"),key=lambda q:int(q.name.split("-")[-1]),reverse=True)
 failures=[]
 for candidate in candidates:
  try:validate_checkpoint(candidate);return candidate
  except Exception as e:failures.append(f"{candidate.name}: {e}")
 if candidates:raise ValueError("no valid recovery checkpoint; "+ "; ".join(failures))
 return None
def build_sequence(tok,prompt,response,max_length=2048):
 prefix=f"User:\n{prompt}\nAssistant:\n"
 prefix_ids=tok(prefix)["input_ids"]
 response_ids=tok(response+tok.eos_token,add_special_tokens=False)["input_ids"]
 if not response_ids:raise ValueError("empty tokenized response")
 prefix_len=len(prefix_ids)
 ids=(prefix_ids+response_ids)[:max_length]
 prefix_len=min(prefix_len,len(ids))
 if prefix_len>=len(ids):raise ValueError("truncation left no response tokens")
 return ids,prefix_len
def make_labels(input_ids, attention_mask, prompt_lengths):
 labels=input_ids.clone()
 labels[attention_mask==0]=-100
 for i,prefix_len in enumerate(prompt_lengths):
  labels[i,:int(prefix_len)]=-100
 return labels
def verify_evidence_file(base,relative_path,digest,label):
 if not isinstance(relative_path,str) or not relative_path.strip():raise ValueError(f"{label} evidence path missing")
 if not isinstance(digest,str) or len(digest)!=64 or any(ch not in "0123456789abcdef" for ch in digest):raise ValueError(f"{label} evidence SHA-256 invalid")
 root=Path(base).resolve();target=(root/relative_path).resolve()
 try:target.relative_to(root)
 except ValueError:raise ValueError(f"{label} evidence path escapes evidence root")
 if not target.is_file():raise ValueError(f"{label} evidence file missing")
 if sha256_file(target)!=digest:raise ValueError(f"{label} evidence hash mismatch")
def gates(c,a,rows,x):
 for k,v in (("status","verified"),("output_training_permission","verified"),("human_legal_review","approved"),("compatibility_status","compatible")):
  if c.get(k)!=v:raise ValueError(f"candidate gate {k} not {v}")
 if not c.get("license_identifier") or c.get("tokenizer_revision")!=c.get("revision"):raise ValueError("candidate license/tokenizer evidence missing or revision mismatch")
 for path_key,hash_key,label in (("license_evidence_path","license_evidence_sha256","license"),("output_training_permission_evidence_path","output_training_permission_evidence_sha256","output training permission"),("human_legal_review_evidence_path","human_legal_review_evidence_sha256","legal review"),("model_config_evidence_path","model_config_sha256","model config"),("chat_template_evidence_path","chat_template_sha256","chat template")):
  verify_evidence_file(x.candidate.parent,c.get(path_key),c.get(hash_key),label)
 inv=c.get("weight_inventory")
 if not isinstance(inv,list) or not inv:raise ValueError("candidate weight inventory missing")
 for item in inv:
  if not isinstance(item,dict) or not isinstance(item.get("path"),str) or not item.get("path") or not isinstance(item.get("sha256"),str) or len(item["sha256"])!=64 or any(ch not in "0123456789abcdef" for ch in item["sha256"]):raise ValueError("candidate weight inventory malformed")
 if a.get("approval")!="approved":raise ValueError("training approval not approved")
 if a.get("candidate_revision")!=c.get("revision"):raise ValueError("candidate revision mismatch")
 if a.get("dataset_sha256")!=sha256_file(x.dataset):raise ValueError("dataset hash mismatch")
 if a.get("code_commit")!=x.code_commit:raise ValueError("code commit mismatch")
 provenance=a.get("dataset_provenance",{})
 if provenance.get("status")!="reviewed":raise ValueError("dataset provenance review missing")
 verify_evidence_file(x.authorization.parent,provenance.get("evidence_path"),provenance.get("evidence_sha256"),"dataset provenance")
 h=a.get("hardware",{})
 if h.get("verified_free_budget") is not True or not h.get("provider") or not h.get("session_id"):raise ValueError("verified free compute/session evidence missing")
 verify_evidence_file(x.authorization.parent,h.get("evidence_path"),h.get("evidence_sha256"),"free compute")
 b=a.get("budget",{})
 for k,v in (("max_steps",x.max_steps),("max_wall_seconds",x.max_wall_seconds)):
  if isinstance(b.get(k),bool) or not isinstance(b.get(k),int) or b[k]<=0 or v>b[k]:raise ValueError(f"{k} exceeds or lacks approved budget")
 if a.get("holdout_access") not in ("sealed","denied"):raise ValueError("holdout must remain sealed")
def main():
 p=argparse.ArgumentParser();p.add_argument("--candidate",type=Path,required=True);p.add_argument("--authorization",type=Path,required=True);p.add_argument("--dataset",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--max-steps",type=int,required=True);p.add_argument("--max-wall-seconds",type=int,required=True);p.add_argument("--code-commit",required=True);p.add_argument("--authorize-training",action="store_true");p.add_argument("--resume",action="store_true",help="resume from latest Trainer checkpoint");p.add_argument("--rank",type=int,default=8);p.add_argument("--alpha",type=int,default=16);p.add_argument("--target-modules",default="q_proj,k_proj,v_proj,o_proj");x=p.parse_args()
 if not x.authorize_training:p.error("explicit acknowledgement required after gates cleared")
 if min(x.max_steps,x.max_wall_seconds,x.rank,x.alpha)<=0:p.error("steps, time budget, rank and alpha must be positive")
 try:c=json.loads(x.candidate.read_text());a=json.loads(x.authorization.read_text());rows=load_rows(x.dataset);gates(c,a,rows,x)
 except Exception as e:p.error(f"preflight blocked: {e}")
 try:import torch
 except Exception as e:p.error(f"torch unavailable: {e}")
 try:from transformers import AutoModelForCausalLM,AutoTokenizer,Trainer,TrainingArguments,TrainerCallback
 except Exception as e:p.error(f"transformers unavailable: {e}")
 try:from peft import LoraConfig,get_peft_model
 except Exception as e:p.error(f"peft unavailable: {e}")
 if not torch.cuda.is_available():p.error("free-GPU requirement not met; CPU training blocked")
 started=time.time();x.output.mkdir(parents=True,exist_ok=True);telemetry_path=x.output/"telemetry.jsonl";session_id=str(a.get("hardware",{}).get("session_id"));run_id=str(uuid.uuid4());prior_elapsed=0.0
 if telemetry_path.exists():
  try:
   records=[json.loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines() if line.strip()]
   prior_elapsed=telemetry_elapsed(records)
  except Exception as e:p.error(f"telemetry history invalid; recovery blocked: {e}")
 if prior_elapsed>=x.max_wall_seconds:p.error("cumulative wall-time budget already exhausted")
 run_started_monotonic=time.monotonic()
 tok=AutoTokenizer.from_pretrained(c["repository_id"],revision=c["revision"]);model=AutoModelForCausalLM.from_pretrained(c["repository_id"],revision=c["revision"],torch_dtype=torch.float16,device_map="auto")
 model=get_peft_model(model,LoraConfig(r=x.rank,lora_alpha=x.alpha,target_modules=[s.strip() for s in x.target_modules.split(",") if s.strip()],lora_dropout=0,bias="none",task_type="CAUSAL_LM"))
 if tok.pad_token is None:tok.pad_token=tok.eos_token
 class DS(torch.utils.data.Dataset):
  def __init__(self):
   self.items=[]
   for r in rows:
    try:ids,prefix_len=build_sequence(tok,r["prompt"],r["response"])
    except ValueError as e:raise ValueError(f"task {r['task_id']}: {e}")
    self.items.append((ids,prefix_len))
  def __len__(self):return len(self.items)
  def __getitem__(self,i):return self.items[i]
 def collate(batch):
  items=[torch.tensor(i[0]) for i in batch];prefix_lengths=[i[1] for i in batch];lengths=torch.tensor([len(i) for i in items]);z=torch.nn.utils.rnn.pad_sequence(items,batch_first=True,padding_value=tok.pad_token_id);mask=(torch.arange(z.shape[1])[None,:]<lengths[:,None]).long()
  return {"input_ids":z,"attention_mask":mask,"labels":make_labels(z,mask,prefix_lengths)}
 class TelemetryAndBudget(TrainerCallback):
  def __init__(self):self.started=time.monotonic();self.telemetry=telemetry_path
  def on_log(self,args,state,control,logs=None,**kwargs):
   record={"timestamp":time.time(),"step":state.global_step,"session_id":session_id,"run_id":run_id,"session_elapsed_seconds":time.monotonic()-run_started_monotonic,"cumulative_elapsed_seconds":prior_elapsed+time.monotonic()-run_started_monotonic,"logs":logs or {}}
   with self.telemetry.open("a",encoding="utf-8") as f:f.write(json.dumps(record,default=str)+"\n")
   return control
  def on_step_end(self,args,state,control,**kwargs):
   if prior_elapsed+time.monotonic()-run_started_monotonic>=x.max_wall_seconds:
    control.should_training_stop=True
    control.should_save=True
   return control
  def on_save(self,args,state,control,**kwargs):
   checkpoint=Path(args.output_dir)/f"checkpoint-{state.global_step}"
   seal_checkpoint(checkpoint)
   if prior_elapsed+time.monotonic()-run_started_monotonic>=x.max_wall_seconds:
    control.should_training_stop=True
   return control
 args=TrainingArguments(output_dir=str(x.output/"checkpoints"),max_steps=x.max_steps,per_device_train_batch_size=1,gradient_accumulation_steps=4,learning_rate=2e-4,logging_steps=1,save_steps=max(1,min(25,x.max_steps)),save_total_limit=2,fp16=True,report_to=[],seed=42,data_seed=42)
 trainer=Trainer(model=model,args=args,train_dataset=DS(),data_collator=collate,callbacks=[TelemetryAndBudget()])
 if prior_elapsed+time.monotonic()-run_started_monotonic>=x.max_wall_seconds:p.error("wall-time budget exhausted before training started")
 resume=None
 if x.resume:
  try:resume=select_recovery_checkpoint(x.output/"checkpoints")
  except Exception as e:p.error(f"recovery selection blocked: {e}")
  if resume is None:p.error("--resume requested but no checkpoint exists")
 trainer.train(resume_from_checkpoint=str(resume) if resume else None)
 model.save_pretrained(x.output/"adapter");tok.save_pretrained(x.output/"adapter")
 packages=sorted([{"name":d.metadata.get("Name") or d.name or "unknown","version":d.version} for d in importlib.metadata.distributions()],key=lambda q:(q["name"].lower(),q["version"]))
manifest={"candidate_id":c["candidate_id"],"candidate_repository":c["repository_id"],"candidate_revision":c["revision"],"dataset_path":str(x.dataset.resolve()),"dataset_sha256":sha256_file(x.dataset),"code_commit":x.code_commit,"run_id":run_id,"provider_session_id":session_id,"steps_limit":x.max_steps,"wall_limit_seconds":x.max_wall_seconds,"rank":x.rank,"alpha":x.alpha,"target_modules":[s.strip() for s in x.target_modules.split(",") if s.strip()],"learning_rate":2e-4,"batch_size":1,"gradient_accumulation_steps":4,"seed":42,"data_seed":42,"max_sequence_length":2048,"duration_seconds":time.time()-started,"prior_session_elapsed_seconds":prior_elapsed,"cumulative_wall_seconds":prior_elapsed+time.time()-started,"gpu":torch.cuda.get_device_name(0),"gpu_memory_total_bytes":torch.cuda.get_device_properties(0).total_memory,"cuda_version":torch.version.cuda,"python":sys.version,"platform":platform.platform(),"torch":torch.__version__,"transformers_version":__import__("transformers").__version__,"peft_version":__import__("peft").__version__,"package_inventory":packages,"package_inventory_sha256":hashlib.sha256(json.dumps(packages,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest(),"adapter_sha256_inventory":[{"path":str(f.relative_to(x.output)),"sha256":sha256_file(f)} for f in sorted((x.output/"adapter").rglob("*")) if f.is_file()],"status":"trained_pending_evaluation","holdout_evaluated":False}
 (x.output/"training-manifest.json").write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
if __name__=="__main__":main()
