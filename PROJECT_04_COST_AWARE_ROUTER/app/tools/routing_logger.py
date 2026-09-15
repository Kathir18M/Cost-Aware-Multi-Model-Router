"""Append-only JSONL routing event logger."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.helpers import get_project_root


def log_routing_event(
	request_id: str,
	initial_model: str,
	final_model: str,
	confidence: float,
	escalation_reason: str | None,
	cost: float,
	*,
	user_id: str = "anon",
	task_type: str = "summarization",
	complexity: str = "low",
	escalated: bool = False,
	actual_cost: float = 0.0,
	baseline_cost: float = 0.0,
	savings: float = 0.0,
	savings_percentage: float = 0.0,
	status: str = "success",
	log_path: Path | None = None,
) -> dict[str, Any]:
	if not request_id.strip() or cost < 0 or not 0 <= confidence <= 1:
		raise ValueError("Invalid routing event values")
	event = {
		"request_id": request_id,
		"user_id": user_id,
		"task_type": task_type,
		"initial_model": initial_model,
		"final_model": final_model,
		"confidence": confidence,
		"complexity": complexity,
		"escalated": escalated or (initial_model.strip().lower() != final_model.strip().lower()),
		"escalation_reason": escalation_reason,
		"cost": cost if cost > 0 else actual_cost,
		"actual_cost": actual_cost if actual_cost > 0 else cost,
		"baseline_cost": baseline_cost,
		"savings": savings,
		"savings_percentage": savings_percentage,
		"status": status,
		"timestamp": datetime.now(timezone.utc).isoformat(),
	}
	path = log_path or get_project_root() / "logs" / "router_events.jsonl"
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open("a", encoding="utf-8") as stream:
		stream.write(json.dumps(event, sort_keys=True) + "\n")
	return event
