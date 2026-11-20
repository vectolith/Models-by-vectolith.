#!/usr/bin/env python3
"""Create a revision-pinned, hash-complete snapshot for an additive Prime teacher.

Full weight downloads are fail-closed until the registry records explicit local
inference legal review. This gate is not training-output permission.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = Path(__file__).with_name("prime_teacher_candidate_registry.json")

def model_card_license_tag(card: dict) -> str:
    """Prefer the named custom license tag over generic Hub metadata such as `other`."""
    return str(card.get("license_name") or card.get("license") or "").lower()

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate-id",required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--cache-dir",type=Path,required=True)
    a=p.parse_args()
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    candidates={x["candidate_id"]:x for x in registry["contributors"]}
    if a.candidate_id not in candidates: p.error("unknown candidate id")
    spec=candidates[a.candidate_id]
    if spec["license_review"]!="approved_for_local_inference" or spec["local_inference_authorized"] is not True:
        raise SystemExit(f"BLOCKED: {a.candidate_id} local inference gate is not approved; no weights downloaded")
    conflict=spec.get("license_evidence_conflict")
    if conflict and conflict.get("status")!="resolved":
        raise SystemExit(f"BLOCKED: {a.candidate_id} license evidence conflict is unresolved; no weights downloaded")
    from huggingface_hub import HfApi, snapshot_download
    api=HfApi()
    info=api.model_info(spec["repo_id"],revision=spec.get("revision") or "main",files_metadata=True)
    revision=(info.sha or "").lower()
    if len(revision)!=40 or any(c not in "0123456789abcdef" for c in revision):
        raise RuntimeError("Hub did not return a full immutable 40-character commit SHA")
    if spec.get("revision") and revision!=spec["revision"]:
        raise RuntimeError(f"pinned revision mismatch: registry={spec['revision']} Hub={revision}")
    if info.gated or info.private or info.disabled:
        raise RuntimeError(f"repository access is gated/private/disabled: gated={info.gated}, private={info.private}, disabled={info.disabled}")
    card=info.card_data.to_dict() if info.card_data else {}
    observed=model_card_license_tag(card)
    if observed!=spec["license_tag"]:
        raise RuntimeError(f"license tag mismatch: expected {spec['license_tag']!r}, got {observed!r}")
    snapshot=Path(snapshot_download(repo_id=spec["repo_id"],revision=revision,cache_dir=str(a.cache_dir)))
    if snapshot.name!=revision: raise RuntimeError("snapshot directory does not match immutable revision")
    config=json.loads((snapshot/"config.json").read_text(encoding="utf-8"))
    if config.get("model_type")!=spec["expected_model_type"]: raise RuntimeError(f"unexpected model_type {config.get('model_type')!r}")
    if spec["expected_architecture"] not in config.get("architectures",[]): raise RuntimeError("expected architecture absent from config")
    files=[]
    for f in sorted(x for x in snapshot.rglob("*") if x.is_file()):
        files.append({"path":f.relative_to(snapshot).as_posix(),"size_bytes":f.stat().st_size,"sha256":sha256(f)})
    license_files=[x for x in files if Path(x["path"]).name.upper().startswith(("LICENSE","NOTICE"))]
    card_license_evidence={k:card.get(k) for k in ("license","license_name","license_link","license_url") if card.get(k) not in (None,"")}
    nonempty_license_file=any(Path(x["path"]).name.upper().startswith("LICENSE") and x["size_bytes"]>0 for x in license_files)
    linked_license=bool(card_license_evidence.get("license_link") or card_license_evidence.get("license_url"))
    external_license_evidence=[]
    for index,url in enumerate(spec.get("license_evidence_urls",[])):
        from urllib.request import Request, urlopen
        request=Request(url,headers={"User-Agent":"vectolith-core-prime-evidence/1.0"})
        with urlopen(request,timeout=30) as response:
            content=response.read()
        if not content:
            raise RuntimeError(f"empty external license evidence from {url}")
        evidence_path=a.output.parent/f"{a.candidate_id}-license-evidence-{index+1}.txt"
        evidence_path.parent.mkdir(parents=True,exist_ok=True)
        evidence_path.write_bytes(content)
        external_license_evidence.append({"url":url,"path":str(evidence_path),"size_bytes":len(content),"sha256":sha256(evidence_path)})
    if not nonempty_license_file and not linked_license and not external_license_evidence:
        raise RuntimeError("no nonempty license text or explicit model-card/external license evidence; legal evidence gate blocked")
    manifest={
      "schema_version":"vectolith-prime-teacher-snapshot/1.0",
      "captured_at":datetime.now(timezone.utc).isoformat(),
      "candidate_id":a.candidate_id,"repo_id":spec["repo_id"],"immutable_revision":revision,
      "model_type":config["model_type"],"architectures":config["architectures"],
      "loader":spec["loader"],"snapshot_path":str(snapshot),"license_tag":observed,"model_card_license_evidence":card_license_evidence,"license_review":"approved_for_local_inference",
      "training_output_permission":spec["training_output_permission"],
      "teacher_qualification":"not_qualified","training_started":False,
      "snapshot_size_bytes":sum(x["size_bytes"] for x in files),"file_count":len(files),
      "files":files,"license_files":license_files,"external_license_evidence":external_license_evidence
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"candidate_id":a.candidate_id,"revision":revision,"files":len(files),"snapshot_bytes":manifest["snapshot_size_bytes"]},sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
