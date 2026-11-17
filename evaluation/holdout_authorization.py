"""Custodian-signed, single-use authorization for protected holdout execution."""
from __future__ import annotations
import base64, hashlib, hmac, json, os, stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def _outside_repo(path: Path) -> Path:
    from evaluation.run_private_holdout import REPO_ROOT
    resolved=path.expanduser().resolve()
    if resolved==REPO_ROOT or REPO_ROOT in resolved.parents:
        raise ValueError("authorization and audit files must be outside the repository")
    return resolved

def _private(path: Path, directory: bool=False) -> None:
    if os.name=="posix":
        mode=stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            raise ValueError("authorization/audit permissions must be owner-only (0700 directory, 0600 file)")

def verify_authorization(token_path: Path, secret: str, *, expected: dict[str,str], now: datetime|None=None) -> dict[str,Any]:
    token_file=_outside_repo(token_path)
    if not token_file.is_file(): raise ValueError("authorization token must be a regular file")
    _private(token_file)
    parts=token_file.read_text(encoding="utf-8").strip().split(".")
    if len(parts)!=2: raise ValueError("authorization token format is invalid")
    payload_bytes=_b64decode(parts[0])
    supplied=_b64decode(parts[1])
    expected_sig=hmac.new(secret.encode(),payload_bytes,hashlib.sha256).digest()
    if not hmac.compare_digest(supplied,expected_sig): raise ValueError("authorization signature is invalid")
    payload=json.loads(payload_bytes)
    if not isinstance(payload,dict): raise ValueError("authorization payload must be an object")
    for key,value in expected.items():
        if payload.get(key)!=value: raise ValueError(f"authorization {key} does not match requested run")
    for key in ("principal_id","run_id","issued_at","expires_at"):
        if not isinstance(payload.get(key),str) or not payload[key].strip():
            raise ValueError(f"authorization {key} is required")
    current=now or datetime.now(timezone.utc)
    issued=datetime.fromisoformat(payload["issued_at"].replace("Z","+00:00"))
    expires=datetime.fromisoformat(payload["expires_at"].replace("Z","+00:00"))
    if issued.tzinfo is None or expires.tzinfo is None: raise ValueError("authorization timestamps must be timezone-aware")
    if issued>current or expires<=current: raise ValueError("authorization is not currently valid")
    if (expires-issued).total_seconds()>3600: raise ValueError("authorization lifetime cannot exceed one hour")
    payload["token_sha256"]=hashlib.sha256(token_file.read_bytes()).hexdigest()
    return payload

def claim_and_audit_run(audit_dir: Path, authorization: dict[str,Any], *, candidate_id: str, revision: str, dataset_version: str, dataset_sha256: str) -> Path:
    directory=_outside_repo(audit_dir)
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    if os.name=="posix":
        os.chmod(directory,0o700)
    _private(directory,True)
    run_id=authorization["run_id"]
    if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in run_id):
        raise ValueError("authorization run_id contains unsafe characters")
    marker=directory/(run_id+".claimed")
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    try: fd=os.open(marker,flags,0o600)
    except FileExistsError as exc: raise ValueError("authorization run_id has already been used") from exc
    event={"event":"holdout_run_authorized","run_id":run_id,"principal_id":authorization["principal_id"],
        "candidate_id":candidate_id,"model_revision":revision,"dataset_version":dataset_version,
        "dataset_sha256":dataset_sha256,"token_sha256":authorization["token_sha256"],
        "authorized_at":datetime.now(timezone.utc).isoformat()}
    with os.fdopen(fd,"w",encoding="utf-8") as handle:
        json.dump(event,handle,sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
    return marker
