"""LangChain task processor for classification."""

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from app.chains.base import TaskChain
from app.schemas.response import ClassificationResponse


class ClassificationChain(TaskChain[ClassificationResponse]):
	"""Classify input without selecting a model or making routing decisions."""

	def __init__(self, model: Any) -> None:
		super().__init__(
			model,
			ClassificationResponse,
			ChatPromptTemplate.from_messages(
				[
					("system", "Return JSON with label, confidence, and reason."),
					("human", "Classify this input:\n{input}"),
				]
			),
		)
