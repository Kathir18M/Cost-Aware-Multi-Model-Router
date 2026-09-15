"""Aggregated routing statistics from JSONL events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.helpers import get_project_root


def get_router_statistics(*, log_path: Path | None = None) -> dict[str, Any]:
	path = log_path or get_project_root() / "logs" / "router_events.jsonl"
	events = []
	if path.exists():
		for line in path.read_text(encoding="utf-8").splitlines():
			if line.strip():
				events.append(json.loads(line))
	total = len(events)
	escalations = sum(1 for event in events if event.get("initial_model") != event.get("final_model"))
	return {
		"total_requests": total,
		"escalations": escalations,
		"escalation_rate": round(escalations / total, 4) if total else 0.0,
		"total_cost": round(sum(float(event.get("cost", 0)) for event in events), 10),
		"models": {
			model: sum(1 for event in events if event.get("final_model") == model)
			for model in {event.get("final_model") for event in events}
			if model
		},
	}
