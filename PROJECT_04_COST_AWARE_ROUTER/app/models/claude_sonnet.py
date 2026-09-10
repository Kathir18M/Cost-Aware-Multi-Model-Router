"""Claude Sonnet model wrapper."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.models.base import ClaudeModel


class ClaudeSonnet(ClaudeModel):
	"""Anthropic Claude Sonnet adapter."""

	def __init__(
		self,
		*,
		client: Any | None = None,
		settings: Settings | None = None,
		max_tokens: int = 1024,
		max_attempts: int = 3,
		backoff_seconds: float = 0.5,
	) -> None:
		model = (settings.sonnet_model if settings else "claude-3-5-sonnet-latest")
		super().__init__(
			model,
			client=client,
			settings=settings,
			max_tokens=max_tokens,
			max_attempts=max_attempts,
			backoff_seconds=backoff_seconds,
		)
