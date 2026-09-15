"""Centralized AI provider error classification and retry metadata extraction."""

from __future__ import annotations

import re
from typing import Any

ERROR_RATE_LIMITED = "RATE_LIMITED"
ERROR_AUTHENTICATION = "AUTHENTICATION_ERROR"
ERROR_PERMISSION = "PERMISSION_ERROR"
ERROR_MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
ERROR_TIMEOUT = "TIMEOUT"
ERROR_PROVIDER_FAIL = "PROVIDER_ERROR"


def classify_provider_error(error: Exception | str | None) -> dict[str, Any]:
    if error is None:
        return {
            "error_type": ERROR_PROVIDER_FAIL,
            "message": "Unknown provider error",
            "retry_after_seconds": None,
        }

    err_str = str(error)
    lowered = err_str.lower()

    # Redact potential API keys
    sanitized_msg = re.sub(r"(key|token|secret|authorization)\s*[:=]\s*\S+", r"\1=[REDACTED]", err_str, flags=re.IGNORECASE)

    retry_after: int | None = None

    # Try parsing retry_after from exception attributes if present
    if isinstance(error, Exception):
        for attr in ("retry_after", "retry_after_seconds", "retry_delay"):
            val = getattr(error, attr, None)
            if isinstance(val, (int, float)) and val > 0:
                retry_after = int(val)
                break

    # Parse retry after patterns in error message text
    if retry_after is None:
        match = re.search(r"retry[-_ ]after[:\s]+(\d+)|try again in\s+(\d+)\s*s|retry_after_seconds\s*=\s*(\d+)", lowered)
        if match:
            for g in match.groups():
                if g:
                    retry_after = int(g)
                    break

    # Classification rules
    if "429" in lowered or "resource_exhausted" in lowered or "rate limit" in lowered or "quota exceeded" in lowered:
        error_type = ERROR_RATE_LIMITED
    elif "401" in lowered or "unauthorized" in lowered or "invalid api key" in lowered or "authentication" in lowered:
        error_type = ERROR_AUTHENTICATION
    elif "403" in lowered or "forbidden" in lowered or "permission" in lowered:
        error_type = ERROR_PERMISSION
    elif "404" in lowered or "not_found" in lowered or "no longer available" in lowered or "model not found" in lowered:
        error_type = ERROR_MODEL_NOT_FOUND
    elif "408" in lowered or "timeout" in lowered or "timed out" in lowered or "deadline_exceeded" in lowered:
        error_type = ERROR_TIMEOUT
    elif re.search(r"5\d\d", lowered) or "internal server error" in lowered or "service unavailable" in lowered or "bad gateway" in lowered:
        error_type = ERROR_PROVIDER_FAIL
    else:
        error_type = ERROR_PROVIDER_FAIL

    return {
        "error_type": error_type,
        "message": sanitized_msg,
        "retry_after_seconds": retry_after,
    }
