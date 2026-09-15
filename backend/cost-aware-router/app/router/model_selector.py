"""Configurable initial model-selection policy."""

from __future__ import annotations

from app.core.constants import (
	COMPLEXITY_HIGH,
	COMPLEXITY_LOW,
	COMPLEXITY_MEDIUM,
	MODEL_GEMINI,
	MODEL_MISTRAL,
)


def select_model(
	complexity: str,
	*,
	medium_complexity_model: str = MODEL_GEMINI,
) -> str:
	"""Select the initial provider from the active Gemini/Mistral routing policy."""

	if complexity == COMPLEXITY_HIGH:
		return MODEL_MISTRAL
	if complexity == COMPLEXITY_LOW:
		return MODEL_GEMINI
	if complexity == COMPLEXITY_MEDIUM and medium_complexity_model in {
		MODEL_GEMINI,
		MODEL_MISTRAL,
	}:
		return medium_complexity_model
	raise ValueError(f"Unsupported complexity or model policy: {complexity}")
