#!/usr/bin/env python3
"""Guarded LoRA training runner; authorization/evidence checks precede ML imports."""
import argparse,hashlib,json,platform,sys,time,uuid,math
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
def validate_checkpoint(path):
 state=path/"trainer_state.json"
 if not path.is_dir() or not state.is_file():raise ValueError("checkpoint missing trainer_state.json")
 try:record=json.loads(state.read_text(encoding="utf-8"))
 except Exception as e:raise ValueError(f"checkpoint trainer state invalid: {e}")
 try:step=int(path.name.removeprefix("checkpoint-"))
 except Exception:raise ValueError("checkpoint directory name invalid")
 if record.get("global_step")!=step:raise ValueError("checkpoint step mismatch")
 if not (path/"adapter_model.safetensors").exists() and not (path/"adapter_model.bin").exists() and not (path/"model.safetensors").exists() and not (path/"pytorch_model.bin").exists():raise ValueError("checkpoint weights missing")\n for required in ("optimizer.pt","scheduler.pt"):\n  if not (path/required).is_file():raise ValueError(f"checkpoint missing {required}")\n if not any(path.glob("rng_state*.pth")):raise ValueError("checkpoint RNG state missing")
 return step
def make_labels(input_ids, attention_mask):
 labels=input_ids.clone()
 labels[attention_mask==0]=-100
 return labels
def gates(c,a,rows,x):
 for k,v in (("status","verified"),("output_training_permission","verified"),("human_legal_review","approved"),("compatibility_status","compatible")):
  if c.get(k)!=v:raise ValueError(f"candidate gate {k} not {v}")
 if a.get("approval")!="approved":raise ValueError("training approval not approved")
 if a.get("candidate_revision")!=c.get("revision"):raise ValueError("candidate revision mismatch")
 if a.get("dataset_sha256")!=sha256_file(x.dataset):raise ValueError("dataset hash mismatch")
 if a.get("code_commit")!=x.code_commit:raise ValueError("code commit mismatch")
 h=a.get("hardware",{})
 if h.get("verified_free_budget") is not True or not h.get("provider") or not h.get("session_id"):raise ValueError("verified free compute/session evidence missing")
 b=a.get("budget",{})
 for k,v in (("max_steps",x.max_steps),("max_wall_seconds",x.max_wall_seconds)):
  if not isinstance(b.get(k),int) or b[k]<=0 or v>b[k]:raise ValueError(f"{k} exceeds or lacks approved budget")
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
   by_session={}
   for rec in records: by_session[rec.get("session_id","unknown")]=max(by_session.get(rec.get("session_id","unknown"),0.0),float(rec.get("session_elapsed_seconds",rec.get("elapsed_seconds",0.0))))
   prior_elapsed=sum(by_session.values())
  except Exception as e:p.error(f"telemetry history invalid; recovery blocked: {e}")
 if prior_elapsed>=x.max_wall_seconds:p.error("cumulative wall-time budget already exhausted")
 tok=AutoTokenizer.from_pretrained(c["repository_id"],revision=c["revision"]);model=AutoModelForCausalLM.from_pretrained(c["repository_id"],revision=c["revision"],torch_dtype=torch.float16,device_map="auto")
 model=get_peft_model(model,LoraConfig(r=x.rank,lora_alpha=x.alpha,target_modules=[s.strip() for s in x.target_modules.split(",") if s.strip()],lora_dropout=0,bias="none",task_type="CAUSAL_LM"))
 if tok.pad_token is None:tok.pad_token=tok.eos_token
 class DS(torch.utils.data.Dataset):
  def __init__(self):
   self.items=[]
   for r in rows:
    ids=tok(f"User:\n{r['prompt']}\nAssistant:\n{r['response']}"+tok.eos_token,truncation=True,max_length=2048)["input_ids"];self.items.append(ids)
  def __len__(self):return len(self.items)
  def __getitem__(self,i):return self.items[i]
 def collate(batch):
  tensors=[torch.tensor(i) for i in batch];lengths=torch.tensor([len(i) for i in tensors]);z=torch.nn.utils.rnn.pad_sequence(tensors,batch_first=True,padding_value=tok.pad_token_id);mask=(torch.arange(z.shape[1])[None,:]<lengths[:,None]).long()
  return {"input_ids":z,"attention_mask":mask,"labels":make_labels(z,mask)}
 class TelemetryAndBudget(TrainerCallback):
  def __init__(self):self.started=time.monotonic();self.telemetry=telemetry_path
  def on_log(self,args,state,control,logs=None,**kwargs):
   record={"timestamp":time.time(),"step":state.global_step,"session_id":session_id,"run_id":run_id,"session_elapsed_seconds":time.monotonic()-self.started,"cumulative_elapsed_seconds":prior_elapsed+time.monotonic()-self.started,"logs":logs or {}}
   with self.telemetry.open("a",encoding="utf-8") as f:f.write(json.dumps(record,default=str)+"\n")
   return control
  def on_step_end(self,args,state,control,**kwargs):
   if prior_elapsed+time.monotonic()-self.started>=x.max_wall_seconds:control.should_training_stop=True
   return control
 args=TrainingArguments(output_dir=str(x.output/"checkpoints"),max_steps=x.max_steps,per_device_train_batch_size=1,gradient_accumulation_steps=4,learning_rate=2e-4,logging_steps=1,save_steps=max(1,min(25,x.max_steps)),save_total_limit=2,fp16=True,report_to=[],seed=42,data_seed=42)
 trainer=Trainer(model=model,args=args,train_dataset=DS(),data_collator=collate,callbacks=[TelemetryAndBudget()])
 checkpoints=sorted((x.output/"checkpoints").glob("checkpoint-*"),key=lambda q:int(q.name.split("-")[-1])) if x.resume else []
 resume=checkpoints[-1] if checkpoints else None
 if x.resume and resume is None:p.error("--resume requested but no checkpoint exists")
 trainer.train(resume_from_checkpoint=str(resume) if resume else None)
 model.save_pretrained(x.output/"adapter");tok.save_pretrained(x.output/"adapter")
 manifest={"candidate_id":c["candidate_id"],"candidate_revision":c["revision"],"dataset_sha256":sha256_file(x.dataset),"code_commit":x.code_commit,"steps_limit":x.max_steps,"wall_limit_seconds":x.max_wall_seconds,"duration_seconds":time.time()-started,"prior_session_elapsed_seconds":prior_elapsed,"cumulative_wall_seconds":prior_elapsed+time.time()-started,"gpu":torch.cuda.get_device_name(0),"python":sys.version,"platform":platform.platform(),"torch":torch.__version__,"adapter_sha256_inventory":[{"path":str(f.relative_to(x.output)),"sha256":sha256_file(f)} for f in sorted((x.output/"adapter").rglob("*")) if f.is_file()],"status":"trained_pending_evaluation","holdout_evaluated":False}
 (x.output/"training-manifest.json").write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
if __name__=="__main__":main()
