"""Logging setup for the application foundation."""

from __future__ import annotations

import logging
import sys


_LOGGER_NAME = "cost_aware_router"
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


def configure_logging(level: str = "INFO") -> logging.Logger:
	"""Configure one application logger without duplicating handlers."""

	normalized_level = level.upper()
	if normalized_level not in _VALID_LEVELS:
		raise ValueError("Log level must be DEBUG, INFO, WARNING, or ERROR")

	logger = logging.getLogger(_LOGGER_NAME)
	logger.setLevel(getattr(logging, normalized_level))
	logger.propagate = False
	if not logger.handlers:
		handler = logging.StreamHandler(sys.stdout)
		handler.setFormatter(logging.Formatter(_LOG_FORMAT))
		logger.addHandler(handler)
	else:
		for handler in logger.handlers:
			handler.setLevel(getattr(logging, normalized_level))
	return logger


def get_logger(name: str | None = None) -> logging.Logger:
	"""Return an application logger, configuring the default level if needed."""

	configure_logging()
	return logging.getLogger(f"{_LOGGER_NAME}.{name}" if name else _LOGGER_NAME)
