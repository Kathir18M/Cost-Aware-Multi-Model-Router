"""Provider-neutral LangChain chat model adapter."""

from __future__ import annotations

import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.config import Settings, load_settings
from app.models.provider_error_classifier import classify_provider_error
from app.schemas.response import ModelResponse

Prompt = str | Sequence[Mapping[str, Any]]


class ProviderModel:
	"""Normalize LangChain-compatible provider clients behind one interface."""

	provider = "provider"

	def __init__(
		self,
		model: str,
		*,
		client: Any | None = None,
		settings: Settings | None = None,
		max_attempts: int = 3,
	) -> None:
		if max_attempts < 1:
			raise ValueError("max_attempts must be at least 1")
		self.model = model
		self.client = client or self._create_client(settings or load_settings())
		self.max_attempts = max_attempts

	def invoke(self, prompt: Prompt) -> ModelResponse:
		started = time.perf_counter()
		last_error: Exception | None = None
		# Enforce max 2 total attempts (1 initial + 1 bounded retry for 429)
		attempts_limit = min(self.max_attempts, 2)
		for attempt in range(attempts_limit):
			try:
				message = self.client.invoke(prompt)
				return ModelResponse(
					content=self._content(message),
					model=str(getattr(message, "response_metadata", {}).get("model_name", self.model)),
					input_tokens=self._usage(message, "input_tokens"),
					output_tokens=self._usage(message, "output_tokens"),
					latency=time.perf_counter() - started,
					success=True,
				)
			except Exception as error:
				last_error = error
				classification = classify_provider_error(error)
				# If rate limited and retry_after is small (<= 2s), sleep briefly before single retry
				if classification["error_type"] == "RATE_LIMITED" and attempt < attempts_limit - 1:
					delay = classification.get("retry_after_seconds")
					if delay and 0 < delay <= 2:
						time.sleep(delay)

		classified = classify_provider_error(last_error or RuntimeError("provider failed"))
		return ModelResponse(
			model=self.model,
			latency=time.perf_counter() - started,
			success=False,
			error=classified["message"],
			error_type=classified["error_type"],
			retry_after_seconds=classified["retry_after_seconds"],
		)

	def _create_client(self, settings: Settings) -> Any:
		raise NotImplementedError

	@staticmethod
	def _content(message: Any) -> str:
		content = getattr(message, "content", message)
		if isinstance(content, list):
			return "".join(str(getattr(item, "text", item)) for item in content)
		return str(content)

	@staticmethod
	def _usage(message: Any, key: str) -> int | None:
		usage = getattr(message, "usage_metadata", None) or getattr(message, "usage", None)
		value = usage.get(key) if isinstance(usage, Mapping) else getattr(usage, key, None)
		return int(value) if value is not None else None

	@staticmethod
	def _safe_error(error: Exception) -> str:
		return re.sub(r"(API_KEY\s*[=:]\s*)\S+", r"\1[REDACTED]", str(error))