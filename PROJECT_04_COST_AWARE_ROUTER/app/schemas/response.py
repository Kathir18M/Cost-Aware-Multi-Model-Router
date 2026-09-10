"""Structured outputs returned by task-processing chains."""

from typing import Any

from pydantic import BaseModel, Field


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
