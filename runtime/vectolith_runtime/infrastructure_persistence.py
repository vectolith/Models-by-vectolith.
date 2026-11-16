"""SQLite persistence for provider and infrastructure-contribution metadata."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any
from .infrastructure import AccessMode, ContributionClass, InfrastructureContribution, InfrastructureProvider, InfrastructureRegistry, ProviderState, QualificationState
from .infrastructure_validation import validate_infrastructure_record

def provider_to_record(item: InfrastructureProvider) -> dict[str, Any]:
    return {"schema_version":"1.0","provider_id":item.provider_id,"display_name":item.display_name,"provider_category":item.provider_category,"relationship_state":item.relationship_state.value,"official_domains":list(item.official_domains),"legal_review_ref":item.legal_review_ref,"security_review_ref":item.security_review_ref,"operational_contact_ref":item.operational_contact_ref}

def contribution_to_record(item: InfrastructureContribution) -> dict[str, Any]:
    return {"schema_version":"1.0","contribution_id":item.contribution_id,"provider_id":item.provider_id,"contribution_class":item.contribution_class.value,"name":item.name,"source_url":item.source_url,"source_revision":item.source_revision,"license_id":item.license_id,"permitted_use":sorted(item.permitted_use),"access_mode":item.access_mode.value,"capabilities":sorted(item.capabilities),"hardware_requirements":list(item.hardware_requirements),"region":item.region,"price_or_quota_ref":item.price_or_quota_ref,"data_handling_ref":item.data_handling_ref,"adapter_id":item.adapter_id,"adapter_version":item.adapter_version,"qualification_status":item.qualification_status.value,"evidence_refs":list(item.evidence_refs),"artifact_sha256":item.artifact_sha256}

def provider_from_record(d: dict[str, Any]) -> InfrastructureProvider:
    if d.get("schema_version") != "1.0": raise ValueError("unsupported infrastructure provider schema version")
    return InfrastructureProvider(d["provider_id"],d["display_name"],d["provider_category"],ProviderState(d["relationship_state"]),tuple(d.get("official_domains",())),d.get("legal_review_ref"),d.get("security_review_ref"),d.get("operational_contact_ref"))

def contribution_from_record(d: dict[str, Any]) -> InfrastructureContribution:
    if d.get("schema_version") != "1.0": raise ValueError("unsupported infrastructure contribution schema version")
    return InfrastructureContribution(d["contribution_id"],d["provider_id"],ContributionClass(d["contribution_class"]),d["name"],d["source_revision"],d["license_id"],AccessMode(d["access_mode"]),frozenset(d["capabilities"]),QualificationState(d["qualification_status"]),d.get("source_url"),frozenset(d.get("permitted_use",())),tuple(d.get("hardware_requirements",())),d.get("region"),d.get("price_or_quota_ref"),d.get("data_handling_ref"),d.get("adapter_id"),d.get("adapter_version"),tuple(d.get("evidence_refs",())),d.get("artifact_sha256"))

class SQLiteInfrastructureRegistry(InfrastructureRegistry):
    """Durable metadata registry. Credentials and secret values are never stored."""
    def __init__(self, database: str | Path, *, schema_dir: str | Path | None = None) -> None:
        super().__init__()
        self.database = str(database)
        self.schema_dir = str(schema_dir) if schema_dir is not None else None
        if self.database != ":memory:": Path(self.database).expanduser().resolve().parent.mkdir(parents=True,exist_ok=True)
        self._connection = sqlite3.connect(self.database,timeout=10,check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.executescript("""CREATE TABLE IF NOT EXISTS infrastructure_providers(provider_id TEXT PRIMARY KEY,record_json TEXT NOT NULL); CREATE TABLE IF NOT EXISTS infrastructure_contributions(contribution_id TEXT PRIMARY KEY,provider_id TEXT NOT NULL REFERENCES infrastructure_providers(provider_id),record_json TEXT NOT NULL);""")
        self._connection.commit()
        try:
            for (raw,) in self._connection.execute("SELECT record_json FROM infrastructure_providers ORDER BY provider_id").fetchall():
                record=json.loads(raw); validate_infrastructure_record("provider",record,schema_dir=self.schema_dir); super().register_provider(provider_from_record(record))
            for (raw,) in self._connection.execute("SELECT record_json FROM infrastructure_contributions ORDER BY contribution_id").fetchall():
                record=json.loads(raw); validate_infrastructure_record("contribution",record,schema_dir=self.schema_dir); super().register_contribution(contribution_from_record(record))
        except Exception:
            self._connection.close(); raise

    def register_provider(self, provider: InfrastructureProvider, *, replace: bool=False) -> None:
        record=provider_to_record(provider); validate_infrastructure_record("provider",record,schema_dir=self.schema_dir)
        raw=json.dumps(record,sort_keys=True,separators=(",",":"))
        with self._lock:
            exists=provider.provider_id in self._providers
            if exists and not replace: raise ValueError(f"provider already registered: {provider.provider_id}")
            previous=self._providers.get(provider.provider_id)
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute("INSERT INTO infrastructure_providers VALUES (?,?) ON CONFLICT(provider_id) DO UPDATE SET record_json=excluded.record_json",(provider.provider_id,raw))
                super().register_provider(provider,replace=replace); self._connection.commit()
            except Exception:
                self._connection.rollback()
                if previous is None: self._providers.pop(provider.provider_id,None)
                else: self._providers[provider.provider_id]=previous
                raise

    def register_contribution(self, contribution: InfrastructureContribution, *, replace: bool=False) -> None:
        record=contribution_to_record(contribution); validate_infrastructure_record("contribution",record,schema_dir=self.schema_dir)
        raw=json.dumps(record,sort_keys=True,separators=(",",":"))
        with self._lock:
            if contribution.provider_id not in self._providers:
                raise KeyError(f"unknown provider: {contribution.provider_id}")
            exists=contribution.contribution_id in self._contributions
            if exists and not replace: raise ValueError(f"contribution already registered: {contribution.contribution_id}")
            previous=self._contributions.get(contribution.contribution_id)
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                self._connection.execute("INSERT INTO infrastructure_contributions VALUES (?,?,?) ON CONFLICT(contribution_id) DO UPDATE SET provider_id=excluded.provider_id,record_json=excluded.record_json",(contribution.contribution_id,contribution.provider_id,raw))
                super().register_contribution(contribution,replace=replace); self._connection.commit()
            except Exception:
                self._connection.rollback()
                if previous is None: self._contributions.pop(contribution.contribution_id,None)
                else: self._contributions[contribution.contribution_id]=previous
                raise

    def close(self) -> None:
        with self._lock: self._connection.close()
    def __enter__(self) -> "SQLiteInfrastructureRegistry": return self
    def __exit__(self,*_: object) -> None: self.close()
