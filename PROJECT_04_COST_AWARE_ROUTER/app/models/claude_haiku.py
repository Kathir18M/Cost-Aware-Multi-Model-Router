"""Legacy haiku wrapper mapped to the Gemini provider."""

from __future__ import annotations

import re
import time
from typing import Any

from app.core.config import Settings, load_settings
from app.models.gemini import GeminiModel
from app.schemas.response import ModelResponse
from app.utils.retry import retry_call


class ClaudeHaiku(GeminiModel):
	"""Compatibility wrapper that keeps the old logical name while using Gemini."""

	def __init__(
		self,
		*,
		client: Any | None = None,
		settings: Settings | None = None,
		max_tokens: int = 1024,
		max_attempts: int = 3,
		backoff_seconds: float = 0.5,
	) -> None:
		super().__init__(client=client, settings=settings, max_attempts=max_attempts)
		self.model = (settings.haiku_model if settings and settings.haiku_model else settings.gemini_model if settings else "gemini-2.0-flash")
		self.max_tokens = max_tokens
		self.max_attempts = max_attempts
		self.backoff_seconds = backoff_seconds

	def invoke(self, prompt: str | list[dict[str, str]], *, system: str | None = None) -> ModelResponse:
		if hasattr(self.client, "messages") and hasattr(self.client.messages, "create"):
			started_at = time.perf_counter()
			try:
				response = retry_call(
					lambda: self.client.messages.create(
						model=self.model,
						max_tokens=self.max_tokens,
						messages=[{"role": "user", "content": prompt}] if isinstance(prompt, str) else list(prompt),
						**({"system": system} if system else {}),
					),
					max_attempts=self.max_attempts,
					is_retryable=lambda error: isinstance(error, (TimeoutError, ConnectionError, OSError)) or "429" in str(error) or "rate limit" in str(error).lower(),
					backoff_seconds=self.backoff_seconds,
				)
				return ModelResponse(
					content=self._extract_content(response),
					model=str(getattr(response, "model", self.model)),
					input_tokens=self._usage_value(response, "input_tokens"),
					output_tokens=self._usage_value(response, "output_tokens"),
					latency=time.perf_counter() - started_at,
					success=True,
				)
			except Exception as error:
				return ModelResponse(
					model=self.model,
					latency=time.perf_counter() - started_at,
					success=False,
					error=self._safe_error_message(error),
				)
		return super().invoke(prompt)

	@staticmethod
	def _extract_content(response: Any) -> str:
		parts = []
		for block in getattr(response, "content", []) or []:
			text = getattr(block, "text", None)
			if text is not None:
				parts.append(str(text))
		return "".join(parts)

	@staticmethod
	def _usage_value(response: Any, name: str) -> int | None:
		usage = getattr(response, "usage", None)
		value = getattr(usage, name, None)
		return int(value) if value is not None else None

	@staticmethod
	def _safe_error_message(error: Exception) -> str:
		message = str(error).strip()
		if not message:
			return error.__class__.__name__
		message = re.sub(r"sk-ant-[A-Za-z0-9_-]+", "[REDACTED]", message)
		message = re.sub(r"(ANTHROPIC_API_KEY\s*[=:]\s*)\S+", r"\1[REDACTED]", message, flags=re.IGNORECASE)
		return message
