"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=False)


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
	gemini_model: str = "gemini-2.0-flash"
	mistral_model: str = "mistral-small-latest"
	gemini_input_price: float = 0.000001
	gemini_output_price: float = 0.000005
	mistral_input_price: float = 0.000003
	mistral_output_price: float = 0.000015
	_anthropic_api_key: str = field(default="", repr=False, compare=False)
	_google_api_key: str = field(default="", repr=False, compare=False)
	_mistral_api_key: str = field(default="", repr=False, compare=False)

	@property
	def has_api_key(self) -> bool:
		"""Return whether any configured provider key was configured."""
		return self.has_google_api_key or self.has_mistral_api_key

	@property
	def has_google_api_key(self) -> bool:
		return bool(self._google_api_key)

	@property
	def has_mistral_api_key(self) -> bool:
		return bool(self._mistral_api_key)

	@property
	def missing_provider_keys(self) -> list[str]:
		missing: list[str] = []
		if not self.has_google_api_key:
			missing.append("Gemini")
		if not self.has_mistral_api_key:
			missing.append("Mistral")
		return missing


def _get_float(name: str, default: float) -> float:
	value = os.getenv(name)
	if value is None or value.strip() == "":
		return float(default)
	try:
		return float(value.strip())
	except ValueError as exc:
		raise ConfigurationError(f"{name} must be a number") from exc


def _get_price(name: str, default: float) -> float:
	val = _get_float(name, default)
	if val >= 0.01:
		val = val / 1_000_000.0
	return val


def _get_threshold(name: str, default: float) -> float:
	value = _get_float(name, default)
	if not 0.0 <= value <= 1.0:
		raise ConfigurationError(f"{name} must be between 0 and 1")
	return value


def load_settings(*, require_api_key: bool = False) -> Settings:
	"""Load and validate settings from the environment and optional `.env` file.

	API access is not needed by the Phase 1 bootstrap, so the provider keys are
	optional by default. Callers preparing for a model request can require them
	explicitly, but the requirement is for Gemini/Mistral rather than Anthropic.
	"""

	load_dotenv(dotenv_path=ENV_PATH, override=False)
	google_api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")).strip()
	mistral_api_key = os.getenv("MISTRAL_API_KEY", "").strip()
	anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
	if require_api_key:
		missing = []
		if not google_api_key:
			missing.append("Gemini")
		if not mistral_api_key:
			missing.append("Mistral")
		if missing:
			if len(missing) == 1:
				raise ConfigurationError(f"{missing[0]} API key is not configured.")
			raise ConfigurationError("No LLM provider is configured.")

	gemini_model = os.getenv("GEMINI_MODEL") or os.getenv("GOOGLE_MODEL") or os.getenv("HAIKU_MODEL") or "gemini-2.0-flash"
	mistral_model = os.getenv("MISTRAL_MODEL") or os.getenv("SONNET_MODEL") or "mistral-small-latest"
	settings = Settings(
		haiku_model=gemini_model.strip(),
		sonnet_model=mistral_model.strip(),
		haiku_input_price=_get_price("GEMINI_INPUT_PRICE", _get_price("HAIKU_INPUT_PRICE", 0.000001)),
		haiku_output_price=_get_price("GEMINI_OUTPUT_PRICE", _get_price("HAIKU_OUTPUT_PRICE", 0.000005)),
		sonnet_input_price=_get_price("MISTRAL_INPUT_PRICE", _get_price("SONNET_INPUT_PRICE", 0.000003)),
		sonnet_output_price=_get_price("MISTRAL_OUTPUT_PRICE", _get_price("SONNET_OUTPUT_PRICE", 0.000015)),
		gemini_model=gemini_model.strip(),
		mistral_model=mistral_model.strip(),
		gemini_input_price=_get_price("GEMINI_INPUT_PRICE", _get_price("HAIKU_INPUT_PRICE", 0.000001)),
		gemini_output_price=_get_price("GEMINI_OUTPUT_PRICE", _get_price("HAIKU_OUTPUT_PRICE", 0.000005)),
		mistral_input_price=_get_price("MISTRAL_INPUT_PRICE", _get_price("SONNET_INPUT_PRICE", 0.000003)),
		mistral_output_price=_get_price("MISTRAL_OUTPUT_PRICE", _get_price("SONNET_OUTPUT_PRICE", 0.000015)),
		confidence_threshold=_get_threshold("CONFIDENCE_THRESHOLD", 0.7),
		complexity_threshold=_get_threshold("COMPLEXITY_THRESHOLD", 0.7),
		log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
		_anthropic_api_key=anthropic_api_key,
		_google_api_key=google_api_key,
		_mistral_api_key=mistral_api_key,
	)

	if not settings.gemini_model or not settings.mistral_model:
		raise ConfigurationError("GEMINI_MODEL and MISTRAL_MODEL must not be empty")
	if settings.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
		raise ConfigurationError("LOG_LEVEL must be DEBUG, INFO, WARNING, or ERROR")
	for name in (
		"haiku_input_price",
		"haiku_output_price",
		"sonnet_input_price",
		"sonnet_output_price",
		"gemini_input_price",
		"gemini_output_price",
		"mistral_input_price",
		"mistral_output_price",
	):
		if getattr(settings, name) < 0:
			raise ConfigurationError(f"{name.upper()} must not be negative")

	return settings
