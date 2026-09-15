"""Small, dependency-free helpers used by the application foundation."""

from __future__ import annotations

from pathlib import Path


def get_project_root() -> Path:
	"""Return the project root directory."""

	return Path(__file__).resolve().parents[2]


def is_non_empty(value: str | None) -> bool:
	"""Return whether a string contains non-whitespace characters."""

	return bool(value and value.strip())
