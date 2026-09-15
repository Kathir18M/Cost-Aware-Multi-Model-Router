"""Bounded retry helpers for transient operations."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def retry_call(
	operation: Callable[[], T],
	*,
	max_attempts: int = 3,
	is_retryable: Callable[[Exception], bool] | None = None,
	backoff_seconds: float = 0.5,
	sleep: Callable[[float], None] = time.sleep,
) -> T:
	"""Run an operation with bounded exponential backoff.

	The final exception is re-raised. By default, exceptions are not retried;
	callers must explicitly identify transient failures.
	"""

	if max_attempts < 1:
		raise ValueError("max_attempts must be at least 1")
	if backoff_seconds < 0:
		raise ValueError("backoff_seconds must not be negative")

	retryable = is_retryable or (lambda _error: False)
	for attempt in range(max_attempts):
		try:
			return operation()
		except Exception as error:
			if attempt == max_attempts - 1 or not retryable(error):
				raise
			sleep(backoff_seconds * (2**attempt))

	raise RuntimeError("retry operation exited unexpectedly")
