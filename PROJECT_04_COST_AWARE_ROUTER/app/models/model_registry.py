"""Registry for model wrappers exposed through a common interface."""

from __future__ import annotations

from typing import Any

from app.core.constants import MODEL_GEMINI, MODEL_HAIKU, MODEL_MISTRAL, MODEL_SONNET
from app.core.config import Settings, load_settings
from app.models.base import ClaudeModel
from app.models.claude_haiku import ClaudeHaiku
from app.models.claude_sonnet import ClaudeSonnet
from app.models.gemini import GeminiModel
from app.models.mistral import MistralModel


class ModelRegistry:
	"""Create and cache configured model wrappers."""

	def __init__(
		self,
		*,
		settings: Settings | None = None,
		client: Any | None = None,
		max_tokens: int = 1024,
		max_attempts: int = 3,
		backoff_seconds: float = 0.5,
	) -> None:
		self._settings = settings or load_settings()
		self._client = client
		self._options = {
			"max_tokens": max_tokens,
			"max_attempts": max_attempts,
			"backoff_seconds": backoff_seconds,
		}
		self._models: dict[str, ClaudeModel] = {}

	def get_model(self, name: str) -> ClaudeModel:
		"""Return a cached model wrapper by its logical name."""

		key = name.strip().lower()
		if key in {MODEL_GEMINI, MODEL_HAIKU}:
			canonical = MODEL_GEMINI
			model_class = GeminiModel if canonical == MODEL_GEMINI else ClaudeHaiku
			if canonical not in self._models:
				self._models[canonical] = model_class(
					client=self._client,
					settings=self._settings,
					max_attempts=self._options["max_attempts"],
				)
			return self._models[canonical]
		if key in {MODEL_MISTRAL, MODEL_SONNET}:
			canonical = MODEL_MISTRAL
			model_class = MistralModel if canonical == MODEL_MISTRAL else ClaudeSonnet
			if canonical not in self._models:
				self._models[canonical] = model_class(
					client=self._client,
					settings=self._settings,
					max_attempts=self._options["max_attempts"],
				)
			return self._models[canonical]
		if key not in {MODEL_HAIKU, MODEL_SONNET}:
			raise ValueError(f"Unsupported model: {name}")
		if key not in self._models:
			model_class = ClaudeHaiku if key == MODEL_HAIKU else ClaudeSonnet
			self._models[key] = model_class(
				client=self._client,
				settings=self._settings,
				**self._options,
			)
		return self._models[key]


_default_registry = ModelRegistry(settings=load_settings())


def get_model(name: str) -> ClaudeModel:
	"""Return a model from the default registry."""

	_default_registry._settings = load_settings()
	return _default_registry.get_model(name)
