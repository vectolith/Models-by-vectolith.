"""Policy-based selection over registry candidates; discovery itself remains non-selecting."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .registry import ModelLifecycle, ModelManifest, ModelRegistry


@dataclass(frozen=True, slots=True)
class DispatchRequirements:
    capabilities: frozenset[str]
    input_modality: str | None = None
    output_modality: str | None = None


@dataclass(frozen=True, slots=True)
class DispatchDecision:
    selected: ModelManifest | None
    candidates: tuple[ModelManifest, ...]
    rejected: tuple[tuple[str, str], ...]
    reason: str


QualificationPredicate = Callable[[ModelManifest], bool]


def select_model(
    registry: ModelRegistry,
    requirements: DispatchRequirements,
    *,
    qualified: QualificationPredicate,
    available: QualificationPredicate = lambda _: True,
) -> DispatchDecision:
    """Fail closed: production selection only among released, qualified, available candidates.

    Candidate discovery is transparent and deterministic. Selection currently chooses
    the lexicographically first eligible ID; callers needing optimization should supply
    a measured, explicit ranking policy in a future extension.
    """
    candidates = registry.discover(
        requirements.capabilities,
        input_modality=requirements.input_modality,
        output_modality=requirements.output_modality,
        include_non_released=True,
    )
    rejected: list[tuple[str, str]] = []
    eligible: list[ModelManifest] = []
    for model in candidates:
        if model.lifecycle != ModelLifecycle.RELEASED:
            rejected.append((model.model_id, "not_released"))
        elif not qualified(model):
            rejected.append((model.model_id, "qualification_missing_or_failed"))
        elif not available(model):
            rejected.append((model.model_id, "unavailable"))
        else:
            eligible.append(model)
    eligible.sort(key=lambda m: m.model_id)
    if not eligible:
        return DispatchDecision(None, candidates, tuple(rejected), "no_eligible_model")
    return DispatchDecision(eligible[0], candidates, tuple(rejected), "eligible_model_selected")
