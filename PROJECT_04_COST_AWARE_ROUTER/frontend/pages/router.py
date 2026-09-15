"""Router Playground page backed by the existing LangGraph workflow."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import streamlit as st

from app.router.graph import graph
from app.schemas.router_state import RouterState


TASK_TYPES = {
	"Classification": "classification",
	"Extraction": "extraction",
	"Summarization": "summarization",
	"Question answering": "qa",
}


def run_backend_request(task_type: str, user_input: str) -> RouterState:
	"""Submit a request to LangGraph without implementing routing policy here."""

	if not user_input.strip():
		raise ValueError("Enter a request before running the router.")
	return graph.invoke(
		{
			"request_id": str(uuid4()),
			"task_type": task_type,
			"user_input": user_input.strip(),
		}
	)


def _value(state: RouterState, key: str, fallback: Any = "—") -> Any:
	value = state.get(key)
	return fallback if value is None or value == "" else value


def _render_pipeline(state: RouterState) -> None:
	steps = [
		("REQUEST", _value(state, "user_input", "Submitted input")),
		("TASK TYPE", _value(state, "task_type")),
		("COMPLEXITY", _value(state, "complexity")),
		("INITIAL MODEL", _value(state, "initial_model")),
		("CONFIDENCE", f"{float(_value(state, 'confidence', 0.0)):.2f}"),
		("ESCALATION", "REQUIRED" if state.get("escalation_required") else "NOT REQUIRED"),
		("FINAL MODEL", _value(state, "selected_model")),
	]
	st.markdown('<div class="pipeline-card">', unsafe_allow_html=True)
	for index, (label, value) in enumerate(steps):
		st.markdown(
			f'<div class="pipeline-step"><span>{label}</span><strong>{value}</strong></div>',
			unsafe_allow_html=True,
		)
		if index < len(steps) - 1:
			st.markdown('<div class="pipeline-arrow">↓</div>', unsafe_allow_html=True)
	st.markdown('</div>', unsafe_allow_html=True)


def _render_result(state: RouterState) -> None:
	response = state.get("response") or {}
	st.markdown('<div class="section-heading"><span>FINAL RESPONSE</span><i>Backend result</i></div>', unsafe_allow_html=True)
	content = response.get("content") or response.get("answer") or response.get("summary")
	if content:
		st.markdown('<div class="response-card">', unsafe_allow_html=True)
		st.write(content)
		st.markdown('</div>', unsafe_allow_html=True)
	else:
		st.warning(response.get("error", "The backend returned no final response."))

	metrics = [
		("Initial Model", _value(state, "initial_model")),
		("Final Model", _value(state, "selected_model")),
		("Confidence", f"{float(_value(state, 'confidence', 0.0)):.2f}"),
		("Complexity", _value(state, "complexity")),
		("Escalation", "Yes" if state.get("escalation_required") else "No"),
		("Status", _value(state, "status")),
	]
	for row in range(0, len(metrics), 3):
		columns = st.columns(3)
		for column, (label, value) in zip(columns, metrics[row:row + 3]):
			column.metric(label, value)
	st.caption(f"Escalation reason: {_value(state, 'escalation_reason', 'None')}")

	st.markdown('<div class="section-heading"><span>COST & TELEMETRY</span><i>Backend-provided values</i></div>', unsafe_allow_html=True)
	telemetry = [
		("Actual Cost", _value(state, "actual_cost")),
		("Baseline Cost", _value(state, "baseline_cost")),
		("Savings", _value(state, "savings")),
		("Input Tokens", response.get("input_tokens", "—")),
		("Output Tokens", response.get("output_tokens", "—")),
		("Total Tokens", response.get("total_tokens", "—")),
		("Latency", response.get("latency", "—")),
	]
	columns = st.columns(4)
	for column, (label, value) in zip(columns, telemetry):
		column.metric(label, value)


def render() -> None:
	st.markdown('<div class="page-kicker">◈ / ROUTER PLAYGROUND</div>', unsafe_allow_html=True)
	st.markdown('<h1>Submit. Route. Understand.</h1>', unsafe_allow_html=True)
	st.markdown('<p class="page-description">Submit a task and let the routing engine select the appropriate model.</p>', unsafe_allow_html=True)

	with st.form("router_playground_form"):
		left, right = st.columns([1, 2], gap="large")
		with left:
			task_label = st.selectbox("Task type", list(TASK_TYPES), key="router_task_type")
		with right:
			user_input = st.text_area(
				"User input",
				placeholder="Describe the task, question, or document to route...",
				height=150,
				key="router_user_input",
			)
		submitted = st.form_submit_button("◈  RUN ROUTER", type="primary", use_container_width=True)

	if submitted:
		try:
			with st.status("Waiting for the routing engine...", expanded=False) as status:
				result = run_backend_request(TASK_TYPES[task_label], user_input)
				status.update(label="Backend response received", state="complete")
			st.session_state["router_result"] = result
		except ValueError as error:
			st.error(str(error))
		except TimeoutError:
			st.error("The routing engine timed out. Please retry the request.")
		except Exception:
			st.error("The routing engine is unavailable or the provider failed. No sensitive details were exposed.")

	result = st.session_state.get("router_result")
	if result:
		_render_pipeline(result)
		_render_result(result)
	else:
		st.markdown('<div class="empty-state compact"><div class="empty-icon">⌁</div><div><strong>Awaiting a request</strong><p>The backend will provide every routing stage and metric after you run a task.</p></div></div>', unsafe_allow_html=True)