"""Schemas for normalized model responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelResponse(BaseModel):
	"""Provider-independent result returned by a model wrapper."""

	model_config = ConfigDict(extra="forbid")

	content: str = ""
	model: str
	input_tokens: int | None = Field(default=None, ge=0)
	output_tokens: int | None = Field(default=None, ge=0)
	latency: float | None = Field(default=None, ge=0)
	success: bool
	error: str | None = None
