#!/usr/bin/env python3
"""Local dataset integrity audit and deterministic protected split. Never uploads data."""
import argparse,hashlib,hmac,json,os,sys
from pathlib import Path

def audit(path):
 errors=[]; rows=[]; ids=set(); hashes=set()
 try:
  with Path(path).open(encoding="utf-8") as f:
   for n,line in enumerate(f,1):
    try:r=json.loads(line)
    except Exception as e:errors.append(f"line {n}: invalid JSON: {e}");continue
    if not isinstance(r,dict):errors.append(f"line {n}: row must be object");continue
    rid=r.get("id")
    if not isinstance(rid,str) or not rid.strip():errors.append(f"line {n}: id required")
    elif rid in ids:errors.append(f"line {n}: duplicate id {rid}")
    else:ids.add(rid)
    digest=hashlib.sha256(line.encode()).hexdigest()
    if digest in hashes:errors.append(f"line {n}: duplicate row content")
    hashes.add(digest);rows.append(r)
 except Exception as e:return {"errors":["read error: "+str(e)],"count":0}
 return {"errors":errors,"count":len(rows),"rows":rows}
def digest_file(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def split(rows,key,holdout_pct,dev_pct):
 buckets={"train":[],"dev":[],"holdout":[]}
 for row in rows:
  rid=row["id"].encode()
  score=int.from_bytes(hmac.new(key,rid,hashlib.sha256).digest()[:8],"big")/2**64
  if score<holdout_pct:buckets["holdout"].append(row)
  elif score<holdout_pct+dev_pct:buckets["dev"].append(row)
  else:buckets["train"].append(row)
 return buckets
def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
 a=sub.add_parser("audit");a.add_argument("jsonl")
 s=sub.add_parser("split");s.add_argument("jsonl");s.add_argument("--out-dir",required=True);s.add_argument("--key-file",required=True);s.add_argument("--holdout",type=float,default=.15);s.add_argument("--dev",type=float,default=.10)
 args=p.parse_args()
 if args.cmd=="audit":
  result=audit(args.jsonl);print(json.dumps({"errors":result["errors"],"count":result["count"]},indent=2));return 1 if result["errors"] else 0
 result=audit(args.jsonl)
 if result["errors"]:print(json.dumps(result["errors"],indent=2));return 1
 if not 0<args.holdout<1 or not 0<=args.dev<1 or args.holdout+args.dev>=1:print("invalid proportions",file=sys.stderr);return 2
 keypath=Path(args.key_file)
 if not keypath.is_file():print("key file must already exist; generate a high-entropy secret locally and keep it outside the repository",file=sys.stderr);return 2
 key=keypath.read_bytes()
 if len(key)<32:print("split key must be at least 32 bytes",file=sys.stderr);return 2
 out=Path(args.out_dir).resolve()
 if out.exists() and any(out.iterdir()):print("output directory must be new or empty",file=sys.stderr);return 2
 out.mkdir(parents=True,exist_ok=True)
 try:os.chmod(out,0o700)
 except OSError:pass
 parts=split(result["rows"],key,args.holdout,args.dev)
 manifest={"schema":"core-prime-local-split/1.0","input_sha256":digest_file(Path(args.jsonl)),"rows":result["count"],"split_counts":{k:len(v) for k,v in parts.items()},"holdout_pct_requested":args.holdout,"dev_pct_requested":args.dev,"holdout_key_sha256":hashlib.sha256(key).hexdigest(),"files":{},"warning":"Local split outputs are sensitive. Do not commit holdout contents, key, or manifest with IDs into a public repository. This utility does not attest source rights, data quality, leakage, or holdout secrecy."}
 for name,rows in parts.items():
  path=out/(name+".jsonl")
  with path.open("x",encoding="utf-8") as f:
   for row in rows:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
  try:os.chmod(path,0o600)
  except OSError:pass
  manifest["files"][name]={"sha256":digest_file(path),"count":len(rows)}
 m=out/"manifest.json"
 with m.open("x",encoding="utf-8") as f:json.dump(manifest,f,indent=2)
 try:os.chmod(m,0o600)
 except OSError:pass
 print(json.dumps(manifest,indent=2));return 0
if __name__=="__main__":sys.exit(main())
