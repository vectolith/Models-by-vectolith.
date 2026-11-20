#!/usr/bin/env python3
"""Validate JSONL task records, duplicate IDs, exact prompt leakage, and hashes."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

SPLITS = {"train", "development", "holdout"}
REQUIRED = ("task_id", "category", "prompt", "split", "rubric_id", "provenance")
ALLOWED = set(REQUIRED) | {"reference_answer", "expected_constraints", "content_sha256"}
SHA64 = re.compile(r"^[a-f0-9]{64}$")
def normalized_prompt(prompt: str) -> str: return " ".join(prompt.split()).casefold()
def sha256(text: str) -> str: return hashlib.sha256(text.encode("utf-8")).hexdigest()
def validate(files):
    errors, seen_ids, prompts, count = [], {}, {}, 0
    for file in files:
        try: lines = file.read_text(encoding="utf-8").splitlines()
        except OSError as exc: errors.append(f"{file}: read error: {exc}"); continue
        for n,line in enumerate(lines,1):
            if not line.strip(): continue
            count += 1
            try: row=json.loads(line)
            except json.JSONDecodeError as exc: errors.append(f"{file}:{n}: JSON parse error: {exc}"); continue
            if not isinstance(row,dict): errors.append(f"{file}:{n}: record must be an object"); continue
            unknown=set(row)-ALLOWED
            if unknown: errors.append(f"{file}:{n}: unexpected fields: {sorted(unknown)}")
            for key in REQUIRED:
                if not isinstance(row.get(key),str) or not row[key].strip(): errors.append(f"{file}:{n}: {key} must be a non-empty string")
            split=row.get("split")
            if split not in SPLITS: errors.append(f"{file}:{n}: invalid split")
            if "reference_answer" in row and row["reference_answer"] is not None and not isinstance(row["reference_answer"],str): errors.append(f"{file}:{n}: reference_answer must be text or null")
            if "expected_constraints" in row and (not isinstance(row["expected_constraints"],list) or any(not isinstance(item,str) for item in row["expected_constraints"])): errors.append(f"{file}:{n}: expected_constraints must be a string array")
            tid=row.get("task_id")
            if isinstance(tid,str):
                if tid in seen_ids: errors.append(f"{file}:{n}: duplicate task_id {tid!r} (also {seen_ids[tid]})")
                else: seen_ids[tid]=f"{file}:{n}"
            prompt=row.get("prompt")
            if isinstance(prompt,str) and prompt.strip() and split in SPLITS:
                key=sha256(normalized_prompt(prompt))
                if key in prompts:
                    prior_split,prior_location=prompts[key]
                    kind="exact normalized prompt leakage" if prior_split!=split else "duplicate normalized prompt"
                    errors.append(f"{file}:{n}: {kind} (also {prior_location})")
                else: prompts[key]=(split,f"{file}:{n}")
                supplied=row.get("content_sha256")
                if supplied is not None:
                    if not isinstance(supplied,str) or not SHA64.fullmatch(supplied): errors.append(f"{file}:{n}: content_sha256 must be a lowercase SHA-256 or null")
                    elif supplied != sha256(prompt): errors.append(f"{file}:{n}: content_sha256 mismatch (expected SHA-256 of exact prompt UTF-8)")
    return count, errors
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("files",nargs="+",type=Path);args=p.parse_args()
    count,errors=validate(args.files)
    if errors: print("\n".join(errors));return 1
    print(f"Validated {count} task records across {len(args.files)} file(s); no exact duplicates/leakage detected.")
    print("Note: semantic leakage and answer-level leakage are not tested.");return 0
if __name__=="__main__": raise SystemExit(main())
