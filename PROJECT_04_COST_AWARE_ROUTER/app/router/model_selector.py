"""Configurable initial model-selection policy."""

from __future__ import annotations

from app.core.constants import (
	COMPLEXITY_HIGH,
	COMPLEXITY_LOW,
	COMPLEXITY_MEDIUM,
	MODEL_HAIKU,
	MODEL_SONNET,
)


def select_model(
	complexity: str,
	*,
	medium_complexity_model: str = MODEL_HAIKU,
) -> str:
	"""Select Haiku for low/medium work and Sonnet for high complexity."""

	if complexity == COMPLEXITY_HIGH:
		return MODEL_SONNET
	if complexity == COMPLEXITY_LOW:
		return MODEL_HAIKU
	if complexity == COMPLEXITY_MEDIUM and medium_complexity_model in {
		MODEL_HAIKU,
		MODEL_SONNET,
	}:
		return medium_complexity_model
	raise ValueError(f"Unsupported complexity or model policy: {complexity}")
