"""Registry for model wrappers exposed through a common interface."""

from __future__ import annotations

from typing import Any

from app.core.constants import MODEL_HAIKU, MODEL_SONNET
from app.core.config import Settings
from app.models.base import ClaudeModel
from app.models.claude_haiku import ClaudeHaiku
from app.models.claude_sonnet import ClaudeSonnet


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
		self._settings = settings
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


_default_registry = ModelRegistry()


def get_model(name: str) -> ClaudeModel:
	"""Return a model from the default registry."""

	return _default_registry.get_model(name)
