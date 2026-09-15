"""Shared LangChain prompt and structured-output behavior."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Generic, TypeVar

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError

from app.schemas.request import TaskRequest


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ChainOutputError(ValueError):
	"""Raised when a model response cannot be parsed into the task schema."""


class TaskChain(Generic[OutputModel]):
	"""Reusable task chain with an injected model and no routing decisions."""

	def __init__(
		self,
		model: Any,
		output_model: type[OutputModel],
		prompt: ChatPromptTemplate,
	) -> None:
		if not callable(getattr(model, "invoke", None)):
			raise TypeError("model must provide an invoke method")
		self.model = model
		self.output_model = output_model
		self.prompt = prompt

	def invoke(self, user_input: str | TaskRequest) -> OutputModel:
		"""Render the task prompt, invoke the selected model, and validate output."""

		request = user_input if isinstance(user_input, TaskRequest) else TaskRequest(text=user_input)
		rendered_prompt = self.prompt.format(input=request.text)
		result = self.model.invoke(rendered_prompt)
		return self._parse_result(result)

	def _parse_result(self, result: Any) -> OutputModel:
		if isinstance(result, self.output_model):
			return result
		content = getattr(result, "content", result)
		if isinstance(content, list):
			content = "".join(
				str(getattr(block, "text", block)) for block in content
			)
		if isinstance(content, Mapping):
			payload = content
		else:
			if not isinstance(content, str):
				raise ChainOutputError("Model response must contain JSON content")
			payload = self._decode_json(content)
		try:
			return self.output_model.model_validate(payload)
		except ValidationError as error:
			raise ChainOutputError(
				f"Invalid structured output for {self.output_model.__name__}"
			) from error

	@staticmethod
	def _decode_json(content: str) -> object:
		cleaned = content.strip()
		if cleaned.startswith("```"):
			lines = cleaned.splitlines()
			cleaned = "\n".join(lines[1:-1]).strip()
		try:
			return json.loads(cleaned)
		except json.JSONDecodeError as error:
			raise ChainOutputError("Model response was not valid JSON") from error