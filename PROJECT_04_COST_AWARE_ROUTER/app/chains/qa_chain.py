"""LangChain task processor for question answering."""

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.chains.base import TaskChain
from app.schemas.response import QAResponse


class QAChain(TaskChain[QAResponse]):
	"""Answer a question without selecting a model."""

	def __init__(self, model: Any) -> None:
		super().__init__(
			model,
			QAResponse,
			ChatPromptTemplate.from_messages(
				[
					("system", "Return JSON with answer and confidence."),
					("human", "Answer this question:\n{input}"),
				]
			),
		)
