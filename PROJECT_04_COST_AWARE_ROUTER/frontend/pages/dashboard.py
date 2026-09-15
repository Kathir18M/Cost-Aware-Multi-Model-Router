"""Cost and routing analytics backed by recorded routing events."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import plotly.express as px
import streamlit as st

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
	filtered = []
	for event in events:
		timestamp = _timestamp(event)
		if date_range and timestamp and not date_range[0] <= timestamp.date() <= date_range[1]:
			continue
		if task_type != "All" and event.get("task_type", "Unknown") != task_type:
			continue
		if model != "All" and event.get("final_model", "Unknown") != model:
			continue
		is_escalated = event.get("initial_model") != event.get("final_model")
		if escalated == "Yes" and not is_escalated:
			continue
		if escalated == "No" and is_escalated:
			continue
		if status != "All" and event.get("status", "Unknown") != status:
			continue
		filtered.append(event)
	return filtered


def _number(events: list[dict[str, Any]], key: str) -> list[float]:
	return [float(event[key]) for event in events if event.get(key) is not None]


def _metric(events: list[dict[str, Any]], key: str, aggregate: str = "sum") -> float | None:
	values = _number(events, key)
	if not values:
		return None
	return sum(values) if aggregate == "sum" else sum(values) / len(values)


def _display(value: float | None, *, money: bool = False, percent: bool = False) -> str:
	if value is None:
		return "—"
	if money:
		return f"${value:.6f}"
	if percent:
		return f"{value:.1%}"
	return f"{value:.3f}"


def _render_filters(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
	date_values = [_timestamp(event).date() for event in events if _timestamp(event)]
	min_date = min(date_values) if date_values else date.today()
	max_date = max(date_values) if date_values else date.today()
	with st.container():
		columns = st.columns(5)
		with columns[0]:
			selected_dates = st.date_input("Date range", (min_date, max_date), key="dashboard_dates")
		with columns[1]:
			task = st.selectbox("Task type", ["All"] + sorted({str(e.get("task_type", "Unknown")) for e in events}), key="dashboard_task")
		with columns[2]:
			model = st.selectbox("Model", ["All"] + sorted({str(e.get("final_model", "Unknown")) for e in events}), key="dashboard_model")
		with columns[3]:
			escalated = st.selectbox("Escalated", ["All", "Yes", "No"], key="dashboard_escalated")
		with columns[4]:
			status = st.selectbox("Status", ["All"] + sorted({str(e.get("status", "Unknown")) for e in events}), key="dashboard_status")
	if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
		date_filter = selected_dates
	else:
		date_filter = None
	return filter_events(events, date_range=date_filter, task_type=task, model=model, escalated=escalated, status=status)


def _render_kpis(events: list[dict[str, Any]]) -> None:
	total = len(events)
	escalations = sum(event.get("initial_model") != event.get("final_model") for event in events)
	columns = st.columns(8)
	values = [
		("Total Requests", str(total)),
		("Gemini Requests", str(sum(event.get("final_model") == "gemini" for event in events))),
		("Mistral Requests", str(sum(event.get("final_model") == "mistral" for event in events))),
		("Escalation Rate", _display(escalations / total if total else None, percent=True)),
		("Average Cost", _display(_metric(events, "cost", "avg"), money=True)),
		("Baseline Cost", _display(_metric(events, "baseline_cost"), money=True)),
		("Cumulative Savings", _display(_metric(events, "savings"), money=True)),
		("Average Latency", _display(_metric(events, "latency", "avg"))),
	]
	for column, (label, value) in zip(columns, values):
		column.metric(label, value)


def _render_charts(events: list[dict[str, Any]]) -> None:
	if not events:
		st.info("No routing data available yet.")
		return
	rows = []
	cumulative = 0.0
	for index, event in enumerate(events, start=1):
		savings = event.get("savings")
		if savings is not None:
			cumulative += float(savings)
		rows.append({**event, "request_number": index, "cumulative_savings": cumulative})
	data = rows
	left, right = st.columns(2)
	with left:
		st.plotly_chart(px.histogram(data, x="final_model", title="Model Distribution"), use_container_width=True)
		if any(row.get("cost") is not None for row in data):
			st.plotly_chart(px.line(data, x="request_number", y="cost", title="Cost per Request"), use_container_width=True)
		if any(row.get("confidence") is not None for row in data):
			st.plotly_chart(px.histogram(data, x="confidence", nbins=10, title="Confidence Distribution"), use_container_width=True)
		if any(row.get("task_type") for row in data):
			st.plotly_chart(px.histogram(data, x="task_type", title="Task Distribution"), use_container_width=True)
	with right:
		if any(row.get("savings") is not None for row in data):
			st.plotly_chart(px.line(data, x="request_number", y="cumulative_savings", title="Cumulative Savings"), use_container_width=True)
		st.plotly_chart(px.line(data, x="request_number", y=["initial_model", "final_model"], title="Escalation Trend"), use_container_width=True)
		if any(row.get("latency") is not None for row in data):
			st.plotly_chart(px.line(data, x="request_number", y="latency", title="Latency Trend"), use_container_width=True)


def render() -> None:
	st.markdown('<div class="page-kicker">📊 / OBSERVABILITY</div>', unsafe_allow_html=True)
	st.markdown('<h1>See the routing economy.</h1>', unsafe_allow_html=True)
	st.markdown('<p class="page-description">Actual request telemetry, model distribution, and cost movement from recorded router events.</p>', unsafe_allow_html=True)
	events = load_routing_events()
	if not events:
		st.info("No routing data available yet.")
		return
	filtered = _render_filters(events)
	_render_kpis(filtered)
	_render_charts(filtered)