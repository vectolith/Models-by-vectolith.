"""SQLite-backed durable model registry."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any
from .registry import FamilyIdentity, ModelLifecycle, ModelManifest, ModelRegistry

def _encode(manifest: ModelManifest) -> str:
    payload = {
        "model_id": manifest.model_id, "display_name": manifest.display_name,
        "version": manifest.version, "specialization": manifest.specialization,
        "capabilities": sorted(manifest.capabilities),
        "identity": {
            "family": manifest.identity.family,
            "contract_version": manifest.identity.contract_version,
            "behavioural_principles": list(manifest.identity.behavioural_principles),
            "safety_baseline": manifest.identity.safety_baseline,
        },
        "modalities_in": sorted(manifest.modalities_in),
        "modalities_out": sorted(manifest.modalities_out),
        "lifecycle": manifest.lifecycle.value, "foundation": manifest.foundation,
        "adapter_id": manifest.adapter_id, "metadata": [list(x) for x in manifest.metadata],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))

def _decode(raw: str) -> ModelManifest:
    data: dict[str, Any] = json.loads(raw)
    identity_data = data["identity"]
    identity = FamilyIdentity(
        family=identity_data["family"], contract_version=identity_data["contract_version"],
        behavioural_principles=tuple(identity_data["behavioural_principles"]),
        safety_baseline=identity_data["safety_baseline"],
    )
    return ModelManifest(
        model_id=data["model_id"], display_name=data["display_name"],
        version=data["version"], specialization=data["specialization"],
        capabilities=frozenset(data["capabilities"]), identity=identity,
        modalities_in=frozenset(data["modalities_in"]),
        modalities_out=frozenset(data["modalities_out"]),
        lifecycle=ModelLifecycle(data["lifecycle"]), foundation=data.get("foundation"),
        adapter_id=data.get("adapter_id"),
        metadata=tuple((str(k), str(v)) for k, v in data.get("metadata", [])),
    )

class SQLiteModelRegistry(ModelRegistry):
    """SQLite-backed registry; filesystem databases survive process restarts."""
    def __init__(self, database: str | Path, identity: FamilyIdentity | None = None) -> None:
        super().__init__(identity)
        self.database = str(database)
        if self.database != ":memory:":
            Path(self.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database, timeout=10, check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS model_manifests (
                model_id TEXT PRIMARY KEY,
                manifest_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self._connection.commit()
        rows = self._connection.execute(
            "SELECT manifest_json FROM model_manifests ORDER BY model_id"
        ).fetchall()
        for (raw,) in rows:
            super().register(_decode(raw))

    def register(self, manifest: ModelManifest, *, replace: bool = False) -> None:
        if manifest.identity != self.identity:
            raise ValueError("model identity contract does not match this vectolith family")
        with self._lock:
            exists = manifest.model_id in self._models
            if exists and not replace:
                raise ValueError(f"model already registered: {manifest.model_id}")
            self._connection.execute(
                """INSERT INTO model_manifests(model_id, manifest_json, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(model_id) DO UPDATE SET
                     manifest_json=excluded.manifest_json, updated_at=CURRENT_TIMESTAMP""",
                (manifest.model_id, _encode(manifest)),
            )
            self._connection.commit()
            super().register(manifest, replace=replace)

    def unregister(self, model_id: str) -> ModelManifest:
        with self._lock:
            if model_id not in self._models:
                raise KeyError(f"unknown model: {model_id}")
            self._connection.execute("DELETE FROM model_manifests WHERE model_id = ?", (model_id,))
            self._connection.commit()
            return super().unregister(model_id)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "SQLiteModelRegistry":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
