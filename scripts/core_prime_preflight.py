#!/usr/bin/env python3
"""Fail-closed Core Prime experiment evidence preflight. This does not launch training."""
import argparse, hashlib, json, sys
from pathlib import Path

REQUIRED = ("rights", "grading", "dataset", "holdout", "student", "compute", "experiment", "authorization")

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()

def validate(manifest_path):
    manifest_path=Path(manifest_path).resolve()
    errors=[]
    try: data=json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e: return [f"manifest unreadable/invalid JSON: {e}"]
    if not isinstance(data,dict): return ["manifest root must be an object"]\n    if data.get("schema_version")!="core-prime-training-readiness/1.0":
        errors.append("schema_version must be core-prime-training-readiness/1.0")
    gates=data.get("gates")
    if not isinstance(gates,dict): return errors+["gates must be an object"]
    for gate in REQUIRED:
        record=gates.get(gate)
        if not isinstance(record,dict): errors.append(f"{gate}: missing gate record"); continue
        if record.get("status")!="verified": errors.append(f"{gate}: status is not verified")
        if not isinstance(record.get("reviewer"),str) or not record.get("reviewer").strip() or not isinstance(record.get("verified_at"),str) or not record.get("verified_at").strip(): errors.append(f"{gate}: reviewer and verified_at required")
        artifacts=record.get("artifacts")
        if not isinstance(artifacts,list) or not artifacts: errors.append(f"{gate}: at least one artifact reference required"); continue
        for i,a in enumerate(artifacts):
            if not isinstance(a,dict): errors.append(f"{gate}: artifact {i} malformed");continue
            rel=a.get("path"); expected=a.get("sha256")
            if not isinstance(rel,str) or not isinstance(expected,str) or len(expected)!=64:
                errors.append(f"{gate}: artifact {i} needs path and 64-char sha256");continue
            p=(manifest_path.parent/rel).resolve()
            if not p.is_relative_to(manifest_path.parent.resolve()):
                errors.append(f"{gate}: artifact path escapes manifest directory");continue
            if not p.is_file(): errors.append(f"{gate}: artifact missing: {rel}");continue
            if digest(p)!=expected.lower(): errors.append(f"{gate}: digest mismatch: {rel}")
    if data.get("training_authorized") is not True: errors.append("training_authorized must be explicitly true")
    if not data.get("authorization_id"): errors.append("authorization_id required")
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest",type=Path)
    args=p.parse_args()
    errors=validate(args.manifest)
    if errors:
        print("BLOCKED")
        for e in errors: print("- "+e)
        return 1
    print("PREFLIGHT PASS: evidence manifest and referenced artifact digests validated.")
    print("This validator does not independently authenticate reviewers, legal conclusions, provider quotas, holdout security, or authorization.")
    print("It does not start training.")
    return 0
if __name__=="__main__": sys.exit(main())
