"""Least-privilege MCP permission checks."""

from __future__ import annotations

from enum import IntEnum


class Permission(IntEnum):
	READ = 1
	WRITE = 2
	ADMIN = 3


class PermissionDenied(PermissionError):
	"""Raised when a connector operation exceeds its granted permission."""


def normalize_permission(value: str | Permission) -> Permission:
	if isinstance(value, Permission):
		return value
	try:
		return Permission[str(value).upper()]
	except KeyError as error:
		raise ValueError(f"Unknown permission: {value}") from error


def check_permission(
	granted: str | Permission,
	required: str | Permission,
	*,
	confirmed: bool = False,
	confirm_writes: bool = True,
) -> None:
	granted_level = normalize_permission(granted)
	required_level = normalize_permission(required)
	if granted_level < required_level:
		raise PermissionDenied(f"Permission {required_level.name} is required")
	if required_level >= Permission.WRITE and confirm_writes and not confirmed:
		raise PermissionDenied("Write operations require explicit confirmation")