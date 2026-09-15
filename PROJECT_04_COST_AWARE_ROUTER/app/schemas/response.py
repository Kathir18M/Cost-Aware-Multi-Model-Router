"""Normalized model responses and structured task outputs."""

from __future__ import annotations

from typing import Any

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
	error_type: str | None = None
	retry_after_seconds: int | None = None


class ClassificationResponse(BaseModel):
	label: str = Field(min_length=1)
	confidence: float = Field(ge=0, le=1)
	reason: str = Field(min_length=1)


class ExtractionResponse(BaseModel):
	fields: dict[str, Any]
	confidence: float = Field(ge=0, le=1)


class SummarizationResponse(BaseModel):
	summary: str = Field(min_length=1)
	confidence: float = Field(ge=0, le=1)


class QAResponse(BaseModel):
	answer: str = Field(min_length=1)
	confidence: float = Field(ge=0, le=1)
