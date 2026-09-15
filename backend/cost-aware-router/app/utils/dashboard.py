"""Dashboard event filtering and log loading utilities."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.utils.helpers import get_project_root

LOG_PATH = get_project_root() / "logs" / "router_events.jsonl"


def load_routing_events(path: Path = LOG_PATH) -> list[dict[str, Any]]:
    """Read recorded routing events, skipping malformed lines safely."""
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except json.JSONDecodeError:
            continue
    return events


def _timestamp(event: dict[str, Any]) -> datetime | None:
    value = event.get("timestamp")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def filter_events(
    events: list[dict[str, Any]],
    *,
    date_range: tuple[date, date] | None = None,
    task_type: str = "All",
    model: str = "All",
    escalated: str = "All",
    status: str = "All",
) -> list[dict[str, Any]]:
    """Filter log events by date range, task type, model, escalation, and status."""
    filtered = []
    for event in events:
        timestamp = _timestamp(event)
        if date_range and timestamp and not date_range[0] <= timestamp.date() <= date_range[1]:
            continue
        if task_type != "All" and event.get("task_type", "Unknown") != task_type:
            continue
        if model != "All" and event.get("final_model", "Unknown") != model:
            continue
        is_escalated = bool(event.get("initial_model") != event.get("final_model") or event.get("escalated"))
        if escalated == "Yes" and not is_escalated:
            continue
        if escalated == "No" and is_escalated:
            continue
        if status != "All" and event.get("status", "Unknown") != status:
            continue
        filtered.append(event)
    return filtered
