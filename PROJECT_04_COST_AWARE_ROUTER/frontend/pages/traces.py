"""Recorded routing trace explorer."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from app.utils.helpers import get_project_root


LOG_PATH = get_project_root() / "logs" / "router_events.jsonl"


def load_trace_events(path: Path = LOG_PATH) -> list[dict[str, Any]]:
	"""Load structured routing events without exposing prompt or secret data."""

	if not path.exists():
		return []
	events = []
	for line in path.read_text(encoding="utf-8").splitlines():
		try:
			event = json.loads(line)
			if isinstance(event, dict):
				events.append(event)
		except json.JSONDecodeError:
			continue
	return events


def filter_trace_events(
	events: list[dict[str, Any]],
	*,
	query: str = "",
	model: str = "All",
	task_type: str = "All",
	escalation: str = "All",
) -> list[dict[str, Any]]:
	needle = query.strip().lower()
	filtered = []
	for event in events:
		is_escalated = event.get("initial_model") != event.get("final_model")
		if needle and needle not in str(event.get("request_id", "")).lower() and needle not in str(event.get("trace_id", "")).lower():
			continue
		if model != "All" and event.get("final_model") != model:
			continue
		if task_type != "All" and event.get("task_type", "Unknown") != task_type:
			continue
		if escalation == "Yes" and not is_escalated:
			continue
		if escalation == "No" and is_escalated:
			continue
		filtered.append(event)
	return filtered


def trace_stages(event: dict[str, Any]) -> list[dict[str, Any]]:
	"""Return lifecycle stages backed only by fields present in an event."""

	fields = [
		("REQUEST", ("request_id", "timestamp")),
		("TASK CLASSIFICATION", ("task_type",)),
		("COMPLEXITY ANALYSIS", ("complexity",)),
		("MODEL SELECTION", ("initial_model",)),
		("MODEL EXECUTION", ("final_model", "latency")),
		("TOOL CALLING", ("tool", "tool_name")),
		("CONFIDENCE", ("confidence",)),
		("ESCALATION", ("escalation_reason",)),
		("COST CALCULATION", ("cost", "actual_cost", "baseline_cost", "savings")),
		("FINAL RESPONSE", ("response", "final_response")),
		("LANGSMITH TRACE", ("trace_id", "run_id", "trace_url")),
	]
	stages = []
	for name, supported_fields in fields:
		available = {key: event[key] for key in supported_fields if key in event and event[key] is not None}
		stages.append({"name": name, "available": bool(available), "details": available})
	return stages


def _render_stage(stage: dict[str, Any]) -> None:
	details = stage["details"]
	status = "RECORDED" if stage["available"] else "NOT RECORDED"
	st.markdown(f'<div class="trace-stage {"recorded" if stage["available"] else "unrecorded"}"><div><span>{stage["name"]}</span><small>{status}</small></div>', unsafe_allow_html=True)
	if details:
		st.json(details)
	else:
		st.caption("This event does not contain data for this stage.")
	st.markdown('</div>', unsafe_allow_html=True)


def _render_langsmith(event: dict[str, Any]) -> None:
	trace_id = event.get("trace_id")
	run_id = event.get("run_id")
	trace_url = event.get("trace_url")
	tracing = bool(trace_id or run_id or os.getenv("LANGSMITH_TRACING", "").lower() == "true")
	project = event.get("langsmith_project") or os.getenv("LANGSMITH_PROJECT")
	st.markdown('<div class="section-heading"><span>LANGSMITH OBSERVABILITY</span><i>Safe metadata only</i></div>', unsafe_allow_html=True)
	columns = st.columns(4)
	columns[0].metric("Tracing Status", "Enabled" if tracing else "Unavailable")
	columns[1].metric("Project", project or "Not configured")
	columns[2].metric("Trace ID", trace_id or "Not recorded")
	columns[3].metric("Run ID", run_id or "Not recorded")
	if trace_url:
		st.link_button("Open LangSmith Trace", str(trace_url))
	elif tracing:
		st.caption("Tracing is configured, but this event contains no trace URL.")


def render() -> None:
	st.markdown('<div class="page-kicker">🔀 / OBSERVABILITY</div>', unsafe_allow_html=True)
	st.markdown('<h1>Trace the decision path.</h1>', unsafe_allow_html=True)
	st.markdown('<p class="page-description">Explore recorded routing events without fabricating lifecycle stages or exposing provider secrets.</p>', unsafe_allow_html=True)
	events = load_trace_events()
	if not events:
		st.info("No routing traces available yet.")
		return
	columns = st.columns(4)
	with columns[0]:
		query = st.text_input("Request or trace ID", key="trace_query")
	with columns[1]:
		model = st.selectbox("Model", ["All"] + sorted({str(e.get("final_model", "Unknown")) for e in events}), key="trace_model")
	with columns[2]:
		task = st.selectbox("Task type", ["All"] + sorted({str(e.get("task_type", "Unknown")) for e in events}), key="trace_task")
	with columns[3]:
		escalation = st.selectbox("Escalation", ["All", "Yes", "No"], key="trace_escalation")
	filtered = filter_trace_events(events, query=query, model=model, task_type=task, escalation=escalation)
	if not filtered:
		st.info("No recorded traces match these filters.")
		return
	selected = st.selectbox("Trace event", range(len(filtered)), format_func=lambda index: str(filtered[index].get("request_id", f"Event {index + 1}")))
	event = filtered[selected]
	st.markdown('<div class="section-heading"><span>EXECUTION LIFECYCLE</span><i>Recorded event data</i></div>', unsafe_allow_html=True)
	for stage in trace_stages(event):
		_render_stage(stage)
	if event.get("initial_model") != event.get("final_model"):
		st.markdown('<div class="escalation-path"><strong>ESCALATION PATH</strong><p>{} → Confidence {} → {} → {}</p></div>'.format(event.get("initial_model", "Initial model"), event.get("confidence", "—"), event.get("escalation_reason", "Threshold check"), event.get("final_model", "Final model")), unsafe_allow_html=True)
	_render_langsmith(event)