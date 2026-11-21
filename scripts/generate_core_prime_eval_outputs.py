#!/usr/bin/env python3
"""Generate outputs for Core Prime eval cases using an optional local HF Transformers model.
No hosted inference or paid API. Model files must be available locally unless HF cache/network is explicitly enabled.
"""
import argparse,json
from pathlib import Path
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--model",required=True,help="HF model ID or local directory")
 p.add_argument("--cases",type=Path,default=Path("evaluation/personality/core-prime-evaluation-cases-v1.jsonl"))
 p.add_argument("--output",type=Path,required=True)
 p.add_argument("--offline",action="store_true",help="Load only from local model cache/directory")
 p.add_argument("--max-new-tokens",type=int,default=256)
 args=p.parse_args()
 try:
  from transformers import AutoTokenizer,AutoModelForCausalLM
  import torch
 except ImportError as exc:
  raise SystemExit("Install optional dependencies (transformers and torch) in your free local/Kaggle environment; no inference was run.") from exc
 tok=AutoTokenizer.from_pretrained(args.model,local_files_only=args.offline)
 model=AutoModelForCausalLM.from_pretrained(args.model,local_files_only=args.offline,torch_dtype="auto",device_map="auto")
 rows=[json.loads(x) for x in args.cases.read_text(encoding="utf-8").splitlines() if x.strip()]
 outputs={}
 for row in rows:
  prompt=(row.get("context","")+"\n"+row["prompt"]).strip()
  messages=[{"role":"user","content":prompt}]
  if hasattr(tok,"apply_chat_template"):
   encoded=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,return_tensors="pt")
  else:
   encoded=tok(prompt,return_tensors="pt").input_ids
  encoded=encoded.to(model.device)
  with torch.no_grad(): generated=model.generate(encoded,max_new_tokens=args.max_new_tokens,do_sample=False)
  text=tok.decode(generated[0][encoded.shape[-1]:],skip_special_tokens=True).strip()
  outputs[row["id"]]={args.model:text}
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(outputs,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(f"Generated {len(outputs)} cases for {args.model}")
if __name__=="__main__": main()
