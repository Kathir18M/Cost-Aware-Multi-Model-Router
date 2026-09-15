"""Validated inputs accepted by task-processing chains."""

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
	"""Common user input for classification, extraction, summary, and Q&A."""

	text: str = Field(min_length=1)
