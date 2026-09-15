"""LangChain task processor for summarization."""

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.chains.base import TaskChain
from app.schemas.response import SummarizationResponse


class SummarizationChain(TaskChain[SummarizationResponse]):
	"""Summarize input without selecting a model."""

	def __init__(self, model: Any) -> None:
		super().__init__(
			model,
			SummarizationResponse,
			ChatPromptTemplate.from_messages(
				[
					("system", "Return JSON with summary and confidence."),
					("human", "Summarize this input:\n{input}"),
				]
			),
		)
