#!/usr/bin/env python3
"""Guarded LoRA training runner; authorization/evidence checks precede ML imports."""
import argparse,hashlib,json,platform,sys,time
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
 p=argparse.ArgumentParser();p.add_argument("--candidate",type=Path,required=True);p.add_argument("--authorization",type=Path,required=True);p.add_argument("--dataset",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--max-steps",type=int,required=True);p.add_argument("--max-wall-seconds",type=int,required=True);p.add_argument("--code-commit",required=True);p.add_argument("--authorize-training",action="store_true");p.add_argument("--rank",type=int,default=8);p.add_argument("--alpha",type=int,default=16);p.add_argument("--target-modules",default="q_proj,k_proj,v_proj,o_proj");x=p.parse_args()
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
 started=time.time();x.output.mkdir(parents=True,exist_ok=True);tok=AutoTokenizer.from_pretrained(c["repository_id"],revision=c["revision"]);model=AutoModelForCausalLM.from_pretrained(c["repository_id"],revision=c["revision"],torch_dtype=torch.float16,device_map="auto")
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
  z=torch.nn.utils.rnn.pad_sequence([torch.tensor(i) for i in batch],batch_first=True,padding_value=tok.pad_token_id);labels=z.clone();labels[z==tok.pad_token_id]=-100
  return {"input_ids":z,"attention_mask":(z!=tok.pad_token_id).long(),"labels":labels}
 class WallBudget(TrainerCallback):\n  def __init__(self):self.started=time.monotonic()\n  def on_step_end(self,args,state,control,**kwargs):\n   if time.monotonic()-self.started>=x.max_wall_seconds:control.should_training_stop=True\n   return control\n args=TrainingArguments(output_dir=str(x.output/"checkpoints"),max_steps=x.max_steps,per_device_train_batch_size=1,gradient_accumulation_steps=4,learning_rate=2e-4,logging_steps=1,save_steps=max(1,min(25,x.max_steps)),save_total_limit=2,fp16=True,report_to=[],seed=42,data_seed=42)
 Trainer(model=model,args=args,train_dataset=DS(),data_collator=collate,callbacks=[WallBudget()]).train();model.save_pretrained(x.output/"adapter");tok.save_pretrained(x.output/"adapter")
 manifest={"candidate_id":c["candidate_id"],"candidate_revision":c["revision"],"dataset_sha256":sha256_file(x.dataset),"code_commit":x.code_commit,"steps_limit":x.max_steps,"wall_limit_seconds":x.max_wall_seconds,"duration_seconds":time.time()-started,"gpu":torch.cuda.get_device_name(0),"python":sys.version,"platform":platform.platform(),"torch":torch.__version__,"adapter_sha256_inventory":[{"path":str(f.relative_to(x.output)),"sha256":sha256_file(f)} for f in sorted((x.output/"adapter").rglob("*")) if f.is_file()],"status":"trained_pending_evaluation","holdout_evaluated":False}
 (x.output/"training-manifest.json").write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
if __name__=="__main__":main()
