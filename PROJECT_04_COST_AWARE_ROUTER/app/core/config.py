"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


class ConfigurationError(ValueError):
	"""Raised when application configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
	"""Validated non-secret application settings.

	The API key is kept private and excluded from the dataclass representation.
	"""

	haiku_model: str
	sonnet_model: str
	haiku_input_price: float
	haiku_output_price: float
	sonnet_input_price: float
	sonnet_output_price: float
	confidence_threshold: float
	complexity_threshold: float
	log_level: str
	_anthropic_api_key: str = field(default="", repr=False, compare=False)

	@property
	def has_api_key(self) -> bool:
		"""Return whether an Anthropic API key was configured."""

		return bool(self._anthropic_api_key)


def _get_float(name: str, default: float) -> float:
	value = os.getenv(name, str(default)).strip()
	try:
		return float(value)
	except ValueError as exc:
		raise ConfigurationError(f"{name} must be a number") from exc


def _get_threshold(name: str, default: float) -> float:
	value = _get_float(name, default)
	if not 0.0 <= value <= 1.0:
		raise ConfigurationError(f"{name} must be between 0 and 1")
	return value


def load_settings(*, require_api_key: bool = False) -> Settings:
	"""Load and validate settings from the environment and optional `.env` file.

	API access is not needed by the Phase 1 bootstrap, so the key is optional by
	default. Callers preparing for a model request can require it explicitly.
	"""

	load_dotenv()
	api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
	if require_api_key and not api_key:
		raise ConfigurationError(
			"ANTHROPIC_API_KEY is required but was not provided"
		)

	settings = Settings(
		haiku_model=os.getenv("HAIKU_MODEL", "claude-3-5-haiku-latest").strip(),
		sonnet_model=os.getenv("SONNET_MODEL", "claude-3-5-sonnet-latest").strip(),
		haiku_input_price=_get_float("HAIKU_INPUT_PRICE", 0.000001),
		haiku_output_price=_get_float("HAIKU_OUTPUT_PRICE", 0.000005),
		sonnet_input_price=_get_float("SONNET_INPUT_PRICE", 0.000003),
		sonnet_output_price=_get_float("SONNET_OUTPUT_PRICE", 0.000015),
		confidence_threshold=_get_threshold("CONFIDENCE_THRESHOLD", 0.7),
		complexity_threshold=_get_threshold("COMPLEXITY_THRESHOLD", 0.7),
		log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
		_anthropic_api_key=api_key,
	)

	if not settings.haiku_model or not settings.sonnet_model:
		raise ConfigurationError("HAIKU_MODEL and SONNET_MODEL must not be empty")
	if settings.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
		raise ConfigurationError("LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR")
	for name in (
		"haiku_input_price",
		"haiku_output_price",
		"sonnet_input_price",
		"sonnet_output_price",
	):
		if getattr(settings, name) < 0:
			raise ConfigurationError(f"{name.upper()} must not be negative")

	return settings
