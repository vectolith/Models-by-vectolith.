#!/usr/bin/env python3
"""Guarded LoRA training runner; authorization/evidence checks precede ML imports."""
import argparse,hashlib,json,platform,sys,time,uuid,math,os,importlib.metadata,tempfile
from pathlib import Path
import evaluation_gate
def atomic_write_text(path,text):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=path.parent)
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:
   f.write(text);f.flush();os.fsync(f.fileno())
  os.replace(temp,path)
  dir_fd=os.open(path.parent,os.O_RDONLY)
  try:os.fsync(dir_fd)
  finally:os.close(dir_fd)
 except BaseException:
  try:os.unlink(temp)
  except FileNotFoundError:pass
  raise
def sha256_file(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(1048576),b""):h.update(c)
 return h.hexdigest()
def package_inventory():
 return sorted([{"name":d.metadata.get("Name") or d.name or "unknown","version":d.version} for d in importlib.metadata.distributions()],key=lambda q:(q["name"].lower(),q["version"]))
def package_inventory_sha256():
 return evaluation_gate.sha256_serialized(package_inventory())
def package_inventory_snapshot():
 items=package_inventory()
 return items,evaluation_gate.sha256_serialized(items)
def load_rows_snapshot(p):
 raw=p.read_bytes()
 try:text=raw.decode("utf-8")
 except UnicodeDecodeError as exc:raise ValueError(f"dataset invalid UTF-8: {exc}") from exc
 rows=[];ids=set();allowed={"task_id","prompt","response","provenance","split"}
 for n,line in enumerate(text.splitlines(),1):
  if not line.strip():continue
  try:r=evaluation_gate.strict_json_loads(line)
  except ValueError as exc:raise ValueError(f"line {n}: invalid JSON: {exc}") from exc
  if not isinstance(r,dict):raise ValueError(f"line {n}: record must be object")
  unknown=set(r)-allowed
  if unknown:raise ValueError(f"line {n}: unexpected training dataset fields: {sorted(unknown)}")
  for k in allowed-{"split"}:
   if not isinstance(r.get(k),str) or not r[k].strip():raise ValueError(f"line {n}: {k} required as non-empty text")
  if r.get("split")!="train":raise ValueError(f"line {n}: split must be train; development/holdout forbidden")
  if r["task_id"] in ids:raise ValueError(f"line {n}: duplicate task_id")
  ids.add(r["task_id"]);rows.append(r)
 if not rows:raise ValueError("empty dataset")
 return rows,hashlib.sha256(raw).hexdigest()
def load_rows(p):return load_rows_snapshot(p)[0]
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
def telemetry_steps(records):
 by_run={}
 legacy={}
 for n,r in enumerate(records,1):
  if not isinstance(r,dict):raise ValueError(f"telemetry record {n} must be an object")
  step=r.get("step")
  start=r.get("start_global_step",0)
  if isinstance(step,bool) or not isinstance(step,int) or step<0:raise ValueError(f"telemetry record {n} has invalid step")
  if isinstance(start,bool) or not isinstance(start,int) or start<0 or start>step:raise ValueError(f"telemetry record {n} has invalid start_global_step")
  run_id=r.get("run_id")
  session=r.get("session_id","unknown")
  key=run_id if run_id else session
  bucket=by_run if run_id else legacy
  if run_id and (not isinstance(run_id,str) or not run_id):raise ValueError(f"telemetry record {n} has invalid run_id")
  prior=bucket.get(key)
  if prior and prior[0]!=start:raise ValueError(f"telemetry records for {key} disagree on start_global_step")
  bucket[key]=(start,max(prior[1] if prior else start,step))
 return sum(max_step-start for start,max_step in by_run.values())+sum(max_step-start for start,max_step in legacy.values())
def check_step_budget(prior_steps,target_step,start_step,approved_steps):
 if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in (prior_steps,target_step,start_step,approved_steps)):
  raise ValueError("step budget values must be non-negative integers")
 if target_step<=start_step:raise ValueError("target max_steps must exceed recovery checkpoint global_step")
 planned=target_step-start_step
 cumulative=prior_steps+planned
 if cumulative>approved_steps:raise ValueError(f"cumulative step budget exceeded: {prior_steps} prior steps + {planned} planned steps = {cumulative}, approved maximum {approved_steps}")
 return cumulative
def checkpoint_step(path):
 state=path/"trainer_state.json"
 if path.is_symlink():raise ValueError("checkpoint directory symlink is unsafe")
 if state.is_symlink():raise ValueError("checkpoint trainer state symlink is unsafe")
 if not path.is_dir() or not state.is_file():raise ValueError("checkpoint missing trainer_state.json")
 try:record=evaluation_gate.strict_json_loads(state.read_text(encoding="utf-8"))
 except Exception as e:raise ValueError(f"checkpoint trainer state invalid: {e}")
 try:step=int(path.name.removeprefix("checkpoint-"))
 except Exception:raise ValueError("checkpoint directory name invalid")
 if isinstance(record.get("global_step"),bool) or record.get("global_step")!=step:raise ValueError("checkpoint step mismatch")
 return step
def checkpoint_inventory(path):
 if path.is_symlink():raise ValueError("checkpoint directory symlink is unsafe")
 # Anchor reads to the checkpoint parent and open every path component with
 # no-follow descriptors. The path walk and hash must not be separate reads.
 anchor=path.parent.resolve()
 root_component=path.name
 items=[]
 for f in sorted(path.rglob("*")):
  if f.is_symlink():raise ValueError("checkpoint contains symlinks")
  if not f.is_file() or f.name in ("checkpoint-integrity.json","checkpoint-integrity.json.tmp","checkpoint-budget.json.tmp"):continue
  relative_inside=str(f.relative_to(path))
  confined_relative=str(Path(root_component)/relative_inside)
  _,raw=evaluation_gate.read_confined_bytes(anchor,confined_relative,"checkpoint")
  items.append({"path":relative_inside,"sha256":hashlib.sha256(raw).hexdigest()})
 return items
def write_checkpoint_budget_state(path,step,cumulative_elapsed_seconds):
 if isinstance(cumulative_elapsed_seconds,bool) or not isinstance(cumulative_elapsed_seconds,(int,float)) or not math.isfinite(cumulative_elapsed_seconds) or cumulative_elapsed_seconds<0:raise ValueError("checkpoint cumulative elapsed time must be finite and non-negative")
 record={"schema_version":1,"global_step":step,"cumulative_elapsed_seconds":float(cumulative_elapsed_seconds)}
 atomic_write_text(path/"checkpoint-budget.json",json.dumps(record,sort_keys=True,indent=2)+"\n")
 return record
def checkpoint_budget_state(path):
 target=path/"checkpoint-budget.json"
 if target.is_symlink():raise ValueError("checkpoint budget state symlink is unsafe")
 if not target.is_file():raise ValueError("checkpoint cumulative budget state missing")
 try:record=evaluation_gate.strict_json_loads(target.read_text(encoding="utf-8"))
 except Exception as e:raise ValueError(f"checkpoint budget state invalid: {e}")
 if not isinstance(record,dict) or record.get("schema_version")!=1 or record.get("global_step")!=checkpoint_step(path):raise ValueError("checkpoint budget state step/schema mismatch")
 elapsed=record.get("cumulative_elapsed_seconds")
 if isinstance(elapsed,bool) or not isinstance(elapsed,(int,float)) or not math.isfinite(elapsed) or elapsed<0:raise ValueError("checkpoint cumulative elapsed time invalid")
 return record
def recover_budget_from_checkpoint(prior_steps,prior_elapsed,path):
 step=validate_checkpoint(path)
 record=checkpoint_budget_state(path)
 return max(prior_steps,step),max(prior_elapsed,float(record["cumulative_elapsed_seconds"]))
def append_telemetry_record(path,record):
 with Path(path).open("a",encoding="utf-8") as f:
  f.write(json.dumps(record,default=str)+"\n")
  f.flush();os.fsync(f.fileno())
def seal_checkpoint(path,cumulative_elapsed_seconds=0.0):
 step=checkpoint_step(path)
 write_checkpoint_budget_state(path,step,cumulative_elapsed_seconds)
 weights=("adapter_model.safetensors","adapter_model.bin","model.safetensors","pytorch_model.bin")
 if not any((path/name).is_file() and (path/name).stat().st_size>0 for name in weights):raise ValueError("checkpoint weights missing or empty")
 for required in ("optimizer.pt","scheduler.pt"):
  if not (path/required).is_file() or (path/required).stat().st_size==0:raise ValueError(f"checkpoint missing or empty {required}")
 if not any(f.is_file() and f.stat().st_size>0 for f in path.glob("rng_state*.pth")):raise ValueError("checkpoint RNG state missing or empty")
 inventory=checkpoint_inventory(path)
 record={"schema_version":1,"step":step,"files":inventory}
 atomic_write_text(path/"checkpoint-integrity.json",json.dumps(record,sort_keys=True,indent=2)+"\n")
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
 try:manifest=evaluation_gate.strict_json_loads(manifest_path.read_text(encoding="utf-8"))
 except Exception as e:raise ValueError(f"checkpoint integrity manifest invalid: {e}")
 if manifest.get("schema_version")!=1 or manifest.get("step")!=step:raise ValueError("checkpoint integrity manifest step/schema mismatch")
 checkpoint_budget_state(path)
 actual=checkpoint_inventory(path);expected=manifest.get("files")
 if not isinstance(expected,list) or not all(isinstance(i,dict) and set(i)=={"path","sha256"} and isinstance(i["path"],str) and isinstance(i["sha256"],str) and len(i["sha256"])==64 and all(ch in "0123456789abcdef" for ch in i["sha256"]) for i in expected):raise ValueError("checkpoint integrity manifest file entries malformed")
 expected_paths=[i["path"] for i in expected]
 if len(expected_paths)!=len(set(expected_paths)):raise ValueError("checkpoint integrity manifest has duplicate paths")
 if set(expected_paths)!={i["path"] for i in actual}:raise ValueError("checkpoint integrity file inventory mismatch")
 by_path={i["path"]:i["sha256"] for i in expected}
 for item in actual:
  if by_path.get(item["path"])!=item["sha256"]:raise ValueError(f"checkpoint integrity hash mismatch: {item['path']}")
 return step
def select_recovery_checkpoint(directory):
 candidates=[]
 for path in directory.glob("checkpoint-*"):
  suffix=path.name.removeprefix("checkpoint-")
  if path.is_dir() and suffix.isdecimal():
   candidates.append((int(suffix),path))
 candidates.sort(key=lambda item:item[0],reverse=True)
 failures=[]
 for _,candidate in candidates:
  try:validate_checkpoint(candidate);return candidate
  except Exception as e:failures.append(f"{candidate.name}: {e}")
 if candidates:raise ValueError("no valid recovery checkpoint; "+ "; ".join(failures))
 return None
def validate_tokenizer_tokens(tok,require_padding_id=True):
 eos=getattr(tok,"eos_token",None)
 if not isinstance(eos,str) or not eos:raise ValueError("tokenizer EOS token required for supervised sequence construction")
 if getattr(tok,"pad_token",None) is None:tok.pad_token=eos
 if require_padding_id and getattr(tok,"pad_token_id",None) is None:raise ValueError("tokenizer padding token ID required for batch collation")
 return tok
def build_sequence(tok,prompt,response,max_length=2048):
 validate_tokenizer_tokens(tok,require_padding_id=False)
 if getattr(tok,"chat_template",None):
  messages=[{"role":"user","content":prompt}]
  try:
   prefix=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
  except TypeError:
   prefix=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
 else:
  prefix=f"User:\n{prompt}\nAssistant:\n"
 prefix_ids=tok(prefix,add_special_tokens=False)["input_ids"]
 response_ids=tok(response+tok.eos_token,add_special_tokens=False)["input_ids"]
 if not response_ids:raise ValueError("empty tokenized response")
 if max_length < 2:raise ValueError("max_length must allow at least one prompt and one response token")
 if len(response_ids)>=max_length:raise ValueError("response exceeds sequence limit; response truncation is forbidden")
 prefix_budget=max_length-len(response_ids)
 if len(prefix_ids)>prefix_budget:prefix_ids=prefix_ids[-prefix_budget:]
 prefix_len=len(prefix_ids)
 if prefix_len<=0:raise ValueError("truncation left no prompt tokens")
 return prefix_ids+response_ids,prefix_len
def make_labels(input_ids, attention_mask, prompt_lengths):
 labels=input_ids.clone()
 labels[attention_mask==0]=-100
 for i,prefix_len in enumerate(prompt_lengths):
  labels[i,:int(prefix_len)]=-100
 return labels
def training_config(x):
 target_modules=[s.strip() for s in x.target_modules.split(",") if s.strip()]
 if not target_modules:raise ValueError("training target_modules must be non-empty")
 if len(target_modules)!=len(set(target_modules)):raise ValueError("training target_modules must be unique")
 return {"max_steps":x.max_steps,"max_wall_seconds":x.max_wall_seconds,"rank":x.rank,"alpha":x.alpha,"target_modules":target_modules,"learning_rate":2e-4,"per_device_train_batch_size":1,"gradient_accumulation_steps":4,"fp16":True,"bf16":False,"gradient_checkpointing":False,"logging_steps":1,"save_steps":1,"save_total_limit":2,"seed":42,"data_seed":42,"max_sequence_length":2048,"optimizer":"adamw_torch","lr_scheduler_type":"linear","warmup_steps":0,"weight_decay":0.0,"max_grad_norm":1.0,"adam_beta1":0.9,"adam_beta2":0.999,"adam_epsilon":1e-8,"packing":False}
def training_config_sha256(x):
 return evaluation_gate.sha256_serialized(training_config(x))
def verify_evidence_file(base,relative_path,digest,label):
 # Use the shared descriptor-based verifier so training evidence hashes the exact
 # bytes read through no-follow directory/file descriptors. The former
 # path-check/resolve/hash sequence was vulnerable to path replacement races.
 return evaluation_gate.verify_evidence_file(base,relative_path,digest,label)
def gates(c,a,rows,x,package_hash=None,training_config_hash=None,dataset_sha256=None,candidate_record_sha256=None):
 candidate,candidate_sha,snapshot=evaluation_gate.verify_candidate_record(x.candidate,c.get("repository_id"),c.get("revision"))
 if candidate!=c:raise ValueError("candidate record content mismatch")
 if candidate_record_sha256 is not None and candidate_sha!=candidate_record_sha256:raise ValueError("candidate record snapshot hash mismatch")
 if not isinstance(x.code_commit,str) or not evaluation_gate.SHA40.fullmatch(x.code_commit):raise ValueError("code commit must be a 40-character lowercase SHA")
 if a.get("candidate_record_sha256")!=candidate_sha:raise ValueError("candidate record hash mismatch")
 if package_hash is None:package_hash=package_inventory_sha256()
 if a.get("environment_package_inventory_sha256")!=package_hash:raise ValueError("environment package inventory hash mismatch")
 if training_config_hash is None:training_config_hash=training_config_sha256(x)
 if a.get("training_config_sha256")!=training_config_hash:raise ValueError("training config hash mismatch")
 if a.get("approval")!="approved":raise ValueError("training approval not approved")
 if a.get("candidate_revision")!=c.get("revision"):raise ValueError("candidate revision mismatch")
 if dataset_sha256 is None:dataset_sha256=sha256_file(x.dataset)
 if a.get("dataset_sha256")!=dataset_sha256:raise ValueError("dataset hash mismatch")
 if a.get("code_commit")!=x.code_commit:raise ValueError("code commit mismatch")
 provenance=a.get("dataset_provenance",{})
 if provenance.get("status")!="reviewed":raise ValueError("dataset provenance review missing")
 evaluation_gate.verify_dataset_provenance_evidence(x.authorization.parent,provenance.get("evidence_path"),provenance.get("evidence_sha256"),dataset_sha256)
 h=a.get("hardware",{})
 if h.get("verified_free_budget") is not True or not h.get("provider") or not h.get("session_id"):raise ValueError("verified free compute/session evidence missing")
 verify_evidence_file(x.authorization.parent,h.get("evidence_path"),h.get("evidence_sha256"),"free compute")
 b=a.get("budget",{})
 for k,v in (("max_steps",x.max_steps),("max_wall_seconds",x.max_wall_seconds)):
  if isinstance(b.get(k),bool) or not isinstance(b.get(k),int) or b[k]<=0 or v>b[k]:raise ValueError(f"{k} exceeds or lacks approved budget")
 if a.get("holdout_access") not in ("sealed","denied"):raise ValueError("holdout must remain sealed")
 return snapshot
def main():
 p=argparse.ArgumentParser();p.add_argument("--candidate",type=Path,required=True);p.add_argument("--authorization",type=Path,required=True);p.add_argument("--dataset",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--max-steps",type=int,required=True);p.add_argument("--max-wall-seconds",type=int,required=True);p.add_argument("--code-commit",required=True);p.add_argument("--authorize-training",action="store_true");p.add_argument("--resume",action="store_true",help="resume from latest Trainer checkpoint");p.add_argument("--rank",type=int,default=8);p.add_argument("--alpha",type=int,default=16);p.add_argument("--target-modules",default="q_proj,k_proj,v_proj,o_proj");x=p.parse_args()
 if not x.authorize_training:p.error("explicit acknowledgement required after gates cleared")
 if min(x.max_steps,x.max_wall_seconds,x.rank,x.alpha)<=0:p.error("steps, time budget, rank and alpha must be positive")
 try:
  actual_code_commit=evaluation_gate.git_head()
  if actual_code_commit!=x.code_commit:p.error("--code-commit does not match training runner checkout HEAD")
  c,candidate_record_sha256=evaluation_gate.load_json_snapshot(x.candidate,"candidate record");a,authorization_sha256=evaluation_gate.load_json_snapshot(x.authorization,"training authorization");rows,dataset_sha256=load_rows_snapshot(x.dataset);packages,packages_hash=package_inventory_snapshot();training_config_hash=training_config_sha256(x);snapshot=gates(c,a,rows,x,packages_hash,training_config_hash,dataset_sha256,candidate_record_sha256)
 except Exception as e:p.error(f"preflight blocked: {e}")
 try:import torch
 except Exception as e:p.error(f"torch unavailable: {e}")
 try:from transformers import AutoModelForCausalLM,AutoTokenizer,Trainer,TrainingArguments,TrainerCallback
 except Exception as e:p.error(f"transformers unavailable: {e}")
 try:from peft import LoraConfig,get_peft_model
 except Exception as e:p.error(f"peft unavailable: {e}")
 if not torch.cuda.is_available():p.error("free-GPU requirement not met; CPU training blocked")
 started=time.time();x.output.mkdir(parents=True,exist_ok=True);telemetry_path=x.output/"telemetry.jsonl";session_id=str(a.get("hardware",{}).get("session_id"));run_id=str(uuid.uuid4());prior_elapsed=0.0;prior_steps=0
 records=[]
 if telemetry_path.exists():
  try:
   records=[evaluation_gate.strict_json_loads(line) for line in telemetry_path.read_text(encoding="utf-8").splitlines() if line.strip()]
   prior_elapsed=telemetry_elapsed(records);prior_steps=telemetry_steps(records)
  except Exception as e:p.error(f"telemetry history invalid; recovery blocked: {e}")
 resume=None
 checkpoint_dir=x.output/"checkpoints"
 if x.resume:
  try:resume=select_recovery_checkpoint(checkpoint_dir)
  except Exception as e:p.error(f"recovery selection blocked: {e}")
  if resume is None:p.error("--resume requested but no checkpoint exists")
 else:
  if checkpoint_dir.is_dir() and any(p.is_dir() and p.name.startswith("checkpoint-") for p in checkpoint_dir.iterdir()):
   p.error("existing checkpoints require --resume; refusing to restart and overwrite recovery state")
 start_step=checkpoint_step(resume) if resume else 0
 if resume:
  try:prior_steps,prior_elapsed=recover_budget_from_checkpoint(prior_steps,prior_elapsed,resume)
  except Exception as e:p.error(f"checkpoint budget recovery blocked: {e}")
 if prior_elapsed>=x.max_wall_seconds:p.error("cumulative wall-time budget already exhausted")
 try:planned_cumulative_steps=check_step_budget(prior_steps,x.max_steps,start_step,a.get("budget",{}).get("max_steps"))
 except Exception as e:p.error(f"cumulative step budget blocked: {e}")
 run_started_monotonic=time.monotonic()
 tok=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False)
 try:validate_tokenizer_tokens(tok)
 except ValueError as e:p.error(f"tokenizer validation blocked: {e}")
 model=AutoModelForCausalLM.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False,torch_dtype=torch.float16,device_map="auto")
 model=get_peft_model(model,LoraConfig(r=x.rank,lora_alpha=x.alpha,target_modules=[s.strip() for s in x.target_modules.split(",") if s.strip()],lora_dropout=0,bias="none",task_type="CAUSAL_LM"))
 class DS(torch.utils.data.Dataset):
  def __init__(self):
   self.items=[]
   for r in rows:
    try:ids,prefix_len=build_sequence(tok,r["prompt"],r["response"],max_length=training_config(x)["max_sequence_length"])
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
   record={"timestamp":time.time(),"step":state.global_step,"start_global_step":start_step,"session_id":session_id,"run_id":run_id,"session_elapsed_seconds":time.monotonic()-run_started_monotonic,"cumulative_elapsed_seconds":prior_elapsed+time.monotonic()-run_started_monotonic,"logs":logs or {}}
   append_telemetry_record(self.telemetry,record)
   return control
  def on_step_end(self,args,state,control,**kwargs):
   if prior_elapsed+time.monotonic()-run_started_monotonic>=x.max_wall_seconds:
    control.should_training_stop=True
    control.should_save=True
   return control
  def on_save(self,args,state,control,**kwargs):
   checkpoint=Path(args.output_dir)/f"checkpoint-{state.global_step}"
   seal_checkpoint(checkpoint,cumulative_elapsed_seconds=prior_elapsed+time.monotonic()-run_started_monotonic)
   if prior_elapsed+time.monotonic()-run_started_monotonic>=x.max_wall_seconds:
    control.should_training_stop=True
   return control
 cfg=training_config(x)
 args=TrainingArguments(output_dir=str(checkpoint_dir),max_steps=cfg["max_steps"],per_device_train_batch_size=cfg["per_device_train_batch_size"],gradient_accumulation_steps=cfg["gradient_accumulation_steps"],learning_rate=cfg["learning_rate"],logging_steps=cfg["logging_steps"],save_steps=cfg["save_steps"],save_total_limit=cfg["save_total_limit"],fp16=cfg["fp16"],bf16=cfg["bf16"],gradient_checkpointing=cfg["gradient_checkpointing"],report_to=[],seed=cfg["seed"],data_seed=cfg["data_seed"],optim=cfg["optimizer"],lr_scheduler_type=cfg["lr_scheduler_type"],warmup_steps=cfg["warmup_steps"],weight_decay=cfg["weight_decay"],max_grad_norm=cfg["max_grad_norm"],adam_beta1=cfg["adam_beta1"],adam_beta2=cfg["adam_beta2"],adam_epsilon=cfg["adam_epsilon"])
 trainer=Trainer(model=model,args=args,train_dataset=DS(),data_collator=collate,callbacks=[TelemetryAndBudget()])
 if prior_elapsed+time.monotonic()-run_started_monotonic>=x.max_wall_seconds:p.error("wall-time budget exhausted before training started")
 trainer.train(resume_from_checkpoint=str(resume) if resume else None)
 model.save_pretrained(x.output/"adapter");tok.save_pretrained(x.output/"adapter")
 manifest={"candidate_id":c["candidate_id"],"candidate_repository":c["repository_id"],"candidate_revision":c["revision"],"dataset_path":str(x.dataset.resolve()),"dataset_sha256":dataset_sha256,"code_commit":x.code_commit,"run_id":run_id,"provider_session_id":session_id,"steps_limit":x.max_steps,"start_global_step":start_step,"actual_steps_run":trainer.state.global_step-start_step,"prior_steps_consumed":prior_steps,"cumulative_steps_consumed":prior_steps+trainer.state.global_step-start_step,"planned_cumulative_steps":planned_cumulative_steps,"wall_limit_seconds":x.max_wall_seconds,"training_config":cfg,"training_config_sha256":training_config_hash,"rank":cfg["rank"],"alpha":cfg["alpha"],"target_modules":cfg["target_modules"],"learning_rate":cfg["learning_rate"],"batch_size":cfg["per_device_train_batch_size"],"gradient_accumulation_steps":cfg["gradient_accumulation_steps"],"seed":cfg["seed"],"data_seed":cfg["data_seed"],"max_sequence_length":cfg["max_sequence_length"],"duration_seconds":time.time()-started,"prior_session_elapsed_seconds":prior_elapsed,"cumulative_wall_seconds":prior_elapsed+time.time()-started,"gpu":torch.cuda.get_device_name(0),"gpu_memory_total_bytes":torch.cuda.get_device_properties(0).total_memory,"cuda_version":torch.version.cuda,"python":sys.version,"platform":platform.platform(),"torch":torch.__version__,"transformers_version":__import__("transformers").__version__,"peft_version":__import__("peft").__version__,"package_inventory":packages,"package_inventory_sha256":packages_hash,"environment_package_inventory_sha256":packages_hash,"candidate_record_sha256":candidate_record_sha256,"authorization_sha256":authorization_sha256,"model_snapshot_path":str(snapshot.resolve()),"model_snapshot_inventory_sha256":evaluation_gate.sha256_serialized(c["weight_inventory"]),"adapter_sha256_inventory":[{"path":str(f.relative_to(x.output)),"sha256":sha256_file(f)} for f in sorted((x.output/"adapter").rglob("*")) if f.is_file()],"status":"trained_pending_evaluation","holdout_evaluated":False}
 atomic_write_text(x.output/"training-manifest.json",json.dumps(manifest,indent=2)+"\n");print(json.dumps(manifest,indent=2))
if __name__=="__main__":main()
