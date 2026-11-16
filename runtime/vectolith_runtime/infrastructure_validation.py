"""Versioned JSON Schema validation for infrastructure metadata."""
from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

_SCHEMA_NAMES = {
    "provider": "infrastructure-provider-v1.schema.json",
    "contribution": "infrastructure-contribution-v1.schema.json",
}


@lru_cache(maxsize=4)
def _load_validator(kind: str, schema_dir: str | None = None) -> Draft202012Validator:
    if kind not in _SCHEMA_NAMES:
        raise ValueError(f"unknown infrastructure schema kind: {kind}")

    try:
        if schema_dir is not None:
            schema_path = Path(schema_dir) / _SCHEMA_NAMES[kind]
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        else:
            # Read through Traversable so schemas also work from zipped wheels.
            schema_resource = files("vectolith_runtime").joinpath(
                "schemas", _SCHEMA_NAMES[kind]
            )
            schema = json.loads(schema_resource.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot load infrastructure {kind} schema: {exc}") from exc

    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_infrastructure_record(
    kind: str, record: dict[str, Any], *, schema_dir: str | None = None
) -> None:
    """Raise ValueError with deterministic paths for every schema violation."""
    errors = sorted(
        _load_validator(kind, schema_dir).iter_errors(record),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            error.message,
        ),
    )
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
            f"{error.message}"
            for error in errors
        )
        raise ValueError(f"invalid infrastructure {kind} record: {details}")
