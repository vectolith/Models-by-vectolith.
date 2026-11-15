"""Extensible model-family identity, registry, and capability discovery."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from threading import RLock

IDENTITY_CONTRACT_VERSION = "1.0"

@dataclass(frozen=True, slots=True)
class FamilyIdentity:
    family: str = "vectolith"
    contract_version: str = IDENTITY_CONTRACT_VERSION
    behavioural_principles: tuple[str, ...] = (
        "honest capability and uncertainty disclosure",
        "respect for user intent and instruction hierarchy",
        "safety and permission boundaries",
        "evidence-based claims and verifiable completion",
    )
    safety_baseline: str = "vectolith-safety-baseline"

    def __post_init__(self) -> None:
        if not self.family.strip() or not self.contract_version.strip():
            raise ValueError("family and identity contract version are required")
        if not self.behavioural_principles or any(not item.strip() for item in self.behavioural_principles):
            raise ValueError("behavioural principles must be non-empty")

class ModelLifecycle(StrEnum):
    EXPERIMENTAL = "experimental"
    DEVELOPMENT = "development"
    EVALUATION = "evaluation"
    RELEASED = "released"
    DEPRECATED = "deprecated"
    RETIRED = "retired"

@dataclass(frozen=True, slots=True)
class ModelManifest:
    model_id: str
    display_name: str
    version: str
    specialization: str
    capabilities: frozenset[str]
    identity: FamilyIdentity = field(default_factory=FamilyIdentity)
    modalities_in: frozenset[str] = frozenset({"text"})
    modalities_out: frozenset[str] = frozenset({"text"})
    lifecycle: ModelLifecycle = ModelLifecycle.EXPERIMENTAL
    foundation: str | None = None
    adapter_id: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        required = (self.model_id, self.display_name, self.version, self.specialization)
        if any(not value.strip() for value in required):
            raise ValueError("model_id, display_name, version, and specialization are required")
        if not self.capabilities or any(not value.strip() for value in self.capabilities):
            raise ValueError("at least one non-empty capability is required")
        if not self.modalities_in or not self.modalities_out:
            raise ValueError("input and output modalities must be declared")

class ModelRegistry:
    """Thread-safe in-memory registry; persistence is supplied by a future adapter."""

    def __init__(self, identity: FamilyIdentity | None = None) -> None:
        self.identity = identity or FamilyIdentity()
        self._models: dict[str, ModelManifest] = {}
        self._lock = RLock()

    def register(self, manifest: ModelManifest, *, replace: bool = False) -> None:
        if manifest.identity != self.identity:
            raise ValueError("model identity contract does not match this vectolith family")
        with self._lock:
            if manifest.model_id in self._models and not replace:
                raise ValueError(f"model already registered: {manifest.model_id}")
            self._models[manifest.model_id] = manifest

    def unregister(self, model_id: str) -> ModelManifest:
        with self._lock:
            try:
                return self._models.pop(model_id)
            except KeyError as exc:
                raise KeyError(f"unknown model: {model_id}") from exc

    def get(self, model_id: str) -> ModelManifest:
        with self._lock:
            try:
                return self._models[model_id]
            except KeyError as exc:
                raise KeyError(f"unknown model: {model_id}") from exc

    def list_models(self, *, lifecycle: ModelLifecycle | None = None) -> tuple[ModelManifest, ...]:
        with self._lock:
            models = tuple(self._models.values())
        if lifecycle is not None:
            models = tuple(model for model in models if model.lifecycle == lifecycle)
        return tuple(sorted(models, key=lambda model: model.model_id))

    def discover(
        self,
        required_capabilities: frozenset[str] = frozenset(),
        *,
        input_modality: str | None = None,
        output_modality: str | None = None,
        include_non_released: bool = True,
    ) -> tuple[ModelManifest, ...]:
        """Return all models satisfying every requested capability and modality."""
        matches = []
        for model in self.list_models():
            if not include_non_released and model.lifecycle != ModelLifecycle.RELEASED:
                continue
            if not required_capabilities.issubset(model.capabilities):
                continue
            if input_modality is not None and input_modality not in model.modalities_in:
                continue
            if output_modality is not None and output_modality not in model.modalities_out:
                continue
            matches.append(model)
        return tuple(matches)
