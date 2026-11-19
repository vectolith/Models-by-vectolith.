#!/usr/bin/env python3
"""Validate JSONL task structure, uniqueness, and split integrity."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("files", nargs="+", type=Path)
    args=p.parse_args()
    seen={}
    errors=[]
    for file in args.files:
        for n,line in enumerate(file.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip(): continue
            try: row=json.loads(line)
            except Exception as e:
                errors.append(f"{file}:{n}: JSON parse error: {e}"); continue
            if not isinstance(row,dict):
                errors.append(f"{file}:{n}: record must be an object"); continue
            for key in ("task_id","category","prompt","split","rubric_id","provenance"):
                if not isinstance(row.get(key),str) or not row[key].strip():
                    errors.append(f"{file}:{n}: {key} must be non-empty string")
            if row.get("split") not in ("train","development","holdout"):
                errors.append(f"{file}:{n}: invalid split")
            tid=row.get("task_id")
            if tid in seen: errors.append(f"{file}:{n}: duplicate task_id {tid!r} (also {seen[tid]})")
            elif isinstance(tid,str): seen[tid]=f"{file}:{n}"
    if errors:
        print("\n".join(errors)); return 1
    print(f"Validated {len(seen)} task records across {len(args.files)} file(s).")
    return 0
if __name__=="__main__": raise SystemExit(main())
