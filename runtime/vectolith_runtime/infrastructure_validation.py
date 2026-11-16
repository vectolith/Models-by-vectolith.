"""Versioned JSON Schema validation for infrastructure metadata."""
from __future__ import annotations
import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator, FormatChecker

_SCHEMA_NAMES = {"provider": "infrastructure-provider-v1.schema.json", "contribution": "infrastructure-contribution-v1.schema.json"}

@lru_cache(maxsize=4)
def _load_validator(kind: str, schema_dir: str | None = None) -> Draft202012Validator:
    if kind not in _SCHEMA_NAMES:
        raise ValueError(f"unknown infrastructure schema kind: {kind}")
    path = Path(schema_dir) / _SCHEMA_NAMES[kind] if schema_dir else Path(str(files("vectolith_runtime").joinpath("schemas", _SCHEMA_NAMES[kind])))
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot load infrastructure schema {path}: {exc}") from exc
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())

def validate_infrastructure_record(kind: str, record: dict[str, Any], *, schema_dir: str | None = None) -> None:
    """Raise ValueError with deterministic paths for every schema violation."""
    errors = sorted(_load_validator(kind, schema_dir).iter_errors(record), key=lambda e: (tuple(str(p) for p in e.absolute_path), e.message))
    if errors:
        details = "; ".join(f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errors)
        raise ValueError(f"invalid infrastructure {kind} record: {details}")
