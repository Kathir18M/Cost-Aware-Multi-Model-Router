"""LangChain task processor for information extraction."""

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.chains.base import TaskChain
from app.schemas.response import ExtractionResponse


class ExtractionChain(TaskChain[ExtractionResponse]):
	"""Extract structured fields without selecting a model."""

	def __init__(self, model: Any) -> None:
		super().__init__(
			model,
			ExtractionResponse,
			ChatPromptTemplate.from_messages(
				[
					("system", "Return JSON with a fields object and confidence."),
					("human", "Extract relevant fields from this input:\n{input}"),
				]
			),
		)
