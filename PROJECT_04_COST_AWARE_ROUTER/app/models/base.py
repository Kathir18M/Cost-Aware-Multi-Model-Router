"""Compatibility wrapper for legacy model names without requiring Anthropic."""

from __future__ import annotations

import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.config import Settings, load_settings
from app.schemas.response import ModelResponse
from app.utils.retry import retry_call


Message = Mapping[str, Any]
Prompt = str | Sequence[Message]


class ClaudeModel:
	"""Common Anthropic Messages API adapter."""

	def __init__(
		self,
		model: str,
		*,
		client: Any | None = None,
		settings: Settings | None = None,
		max_tokens: int = 1024,
		max_attempts: int = 3,
		backoff_seconds: float = 0.5,
	) -> None:
		if max_tokens < 1:
			raise ValueError("max_tokens must be at least 1")
		self.model = model
		self.max_tokens = max_tokens
		self.max_attempts = max_attempts
		self.backoff_seconds = backoff_seconds
		if client is not None:
			self.client = client
		else:
			resolved_settings = settings or load_settings()
			if not resolved_settings.has_google_api_key and not resolved_settings.has_mistral_api_key:
				raise ValueError("No LLM provider is configured.")
			self.client = client

	def invoke(self, prompt: Prompt, *, system: str | None = None) -> ModelResponse:
		"""Send a prompt and normalize the provider response or error."""

		messages = self._normalize_prompt(prompt)
		started_at = time.perf_counter()
		try:
			response = retry_call(
				lambda: self.client.messages.create(
					model=self.model,
					max_tokens=self.max_tokens,
					messages=messages,
					**({"system": system} if system else {}),
				),
				max_attempts=self.max_attempts,
				is_retryable=self._is_retryable,
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

	@staticmethod
	def _normalize_prompt(prompt: Prompt) -> list[Message]:
		if isinstance(prompt, str):
			return [{"role": "user", "content": prompt}]
		return list(prompt)

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
	def _is_retryable(error: Exception) -> bool:
		return isinstance(error, (TimeoutError, ConnectionError, OSError)) or "429" in str(error) or "rate limit" in str(error).lower()

	@staticmethod
	def _safe_error_message(error: Exception) -> str:
		message = str(error).strip()
		if not message:
			return error.__class__.__name__
		message = re.sub(r"sk-ant-[A-Za-z0-9_-]+", "[REDACTED]", message)
		message = re.sub(
			r"(ANTHROPIC_API_KEY\s*[=:]\s*)\S+",
			r"\1[REDACTED]",
			message,
			flags=re.IGNORECASE,
		)
		return message