"""Validated capability registry and deterministic delegation routing (stdlib only)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable

class RegistryError(ValueError): pass

def load_registry(path: str | Path) -> dict:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    validate_registry(data)
    return data

def validate_registry(data: dict) -> None:
    if not isinstance(data,dict) or data.get("registry_version") != "1.0.0" or data.get("identity") != "vectolith":
        raise RegistryError("invalid registry header")
    models=data.get("models")
    if not isinstance(models,list) or not models: raise RegistryError("models must be a non-empty list")
    ids=set()
    required={"id","display_name","role","status","capabilities","delegates_to","limits"}
    for m in models:
        if not isinstance(m,dict) or not required.issubset(m): raise RegistryError("model record missing required fields")
        if not all(isinstance(m[k],str) and m[k] for k in ("id","display_name","role","status")): raise RegistryError("invalid identity fields")
        if m["id"] in ids: raise RegistryError(f"duplicate model id: {m['id']}")
        ids.add(m["id"])
        for k in ("capabilities","delegates_to","limits"):
            if not isinstance(m[k],list) or not all(isinstance(v,str) and v for v in m[k]): raise RegistryError(f"{m['id']}: {k} must be string lists")
        if len(set(m["capabilities"]))!=len(m["capabilities"]): raise RegistryError(f"{m['id']}: duplicate capabilities")
    for m in models:
        missing=set(m["delegates_to"])-ids
        if missing: raise RegistryError(f"{m['id']}: unknown delegates {sorted(missing)}")

def route(registry: dict, required_capabilities: Iterable[str], *, available_ids: Iterable[str] | None=None) -> list[dict]:
    """Return capability-complete specialists sorted by ID; availability is explicit."""
    validate_registry(registry)
    required=set(required_capabilities)
    if not required: return []
    available=set(available_ids) if available_ids is not None else {m["id"] for m in registry["models"] if m.get("status")=="ready"}
    selected=[]
    for m in registry["models"]:
        if m["id"] in available and required.issubset(set(m["capabilities"])):
            selected.append({"id":m["id"],"role":m["role"],"capabilities":sorted(m["capabilities"])})
    return sorted(selected,key=lambda x:x["id"])

def delegation_targets(registry: dict, model_id: str, *, available_ids: Iterable[str]) -> list[str]:
    validate_registry(registry)
    models={m["id"]:m for m in registry["models"]}
    if model_id not in models: raise RegistryError(f"unknown model: {model_id}")
    available=set(available_ids)
    return sorted(t for t in models[model_id]["delegates_to"] if t in available)
