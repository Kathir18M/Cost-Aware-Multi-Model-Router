"""Streamlit dashboard for the cost-aware multi-model router."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st

from app.core.config import ConfigurationError, load_settings
from app.models.model_registry import get_model
from app.router.graph import build_graph
from app.schemas.router_state import RouterState
from app.tools.routing_logger import log_routing_event
from app.tools.statistics_tool import get_router_statistics


TASK_OPTIONS = {
	"Classification": "classification",
	"Extraction": "extraction",
	"Summarization": "summarization",
	"Q&A": "qa",
}


def _model_executor(model_name: str, task_type: str, user_input: str) -> dict:
	"""Invoke one configured model and normalize JSON task output for the graph."""

	prompt = (
		f"Task type: {task_type}\n"
		"Return only a valid JSON object. Include the task-specific answer field "
		"and a confidence number from 0 to 1.\n"
		f"Input:\n{user_input}"
	)
	result = get_model(model_name).invoke(prompt)
	response = {
		"content": result.content,
		"model": result.model,
		"input_tokens": result.input_tokens or 0,
		"output_tokens": result.output_tokens or 0,
		"latency": result.latency,
		"success": result.success,
		"error": result.error,
	}
	if result.success:
		try:
			structured = json.loads(result.content)
			if isinstance(structured, dict):
				response.update(structured)
		except json.JSONDecodeError:
			response["error"] = "The model returned an invalid structured response"
	return response


def _history() -> list[dict]:
	if "request_history" not in st.session_state:
		st.session_state.request_history = []
	return st.session_state.request_history


def _run_request(task_type: str, user_input: str) -> RouterState:
	if not user_input.strip():
		raise ValueError("Enter a prompt or input before submitting")
	load_settings(require_api_key=True)
	started = time.perf_counter()
	request_id = str(uuid4())
	result = build_graph(executor=_model_executor).invoke(
		{"request_id": request_id, "user_input": user_input}
	)
	result["response"] = result.get("response") or {}
	result["response"]["latency"] = time.perf_counter() - started
	log_routing_event(
		request_id,
		result.get("initial_model", "unknown"),
		result.get("selected_model", "unknown"),
		float(result.get("confidence", 0.0)),
		result.get("escalation_reason"),
		float(result.get("actual_cost", 0.0)),
	)
	_history().append(
		{
			"Request ID": request_id,
			"Task": task_type,
			"Initial Model": result.get("initial_model", "unknown"),
			"Final Model": result.get("selected_model", "unknown"),
			"Confidence": round(float(result.get("confidence", 0.0)), 4),
			"Escalated": result.get("escalation_required", False),
			"Cost": float(result.get("actual_cost", 0.0)),
			"Baseline": float(result.get("baseline_cost", 0.0)),
			"Savings": float(result.get("savings", 0.0)),
			"Timestamp": datetime.now(timezone.utc).isoformat(),
			"Task Type": task_type,
			"Complexity": result.get("complexity", "unknown"),
			"Escalation Reason": result.get("escalation_reason"),
			"Answer": result["response"].get("content", ""),
			"Latency": result["response"].get("latency"),
		}
	)
	return result


def _render_kpis(history: list[dict]) -> None:
	if not history:
		st.info("No requests have been processed yet. Submit a task to populate the dashboard.")
		return
	stats = get_router_statistics()
	actual = sum(row["Cost"] for row in history)
	baseline = sum(row["Baseline"] for row in history)
	savings = sum(row["Savings"] for row in history)
	columns = st.columns(8)
	values = [
		("Total Requests", len(history)),
		("Haiku Usage", sum(row["Final Model"] == "haiku" for row in history)),
		("Sonnet Usage", sum(row["Final Model"] == "sonnet" for row in history)),
		("Escalation Rate", f"{stats['escalation_rate']:.1%}"),
		("Actual Cost", f"${actual:.6f}"),
		("Baseline Cost", f"${baseline:.6f}"),
		("Cumulative Savings", f"${savings:.6f}"),
		("Accuracy", "N/A until evaluation"),
	]
	for column, (label, value) in zip(columns, values):
		column.metric(label, value)


def _render_charts(history: list[dict]) -> None:
	if not history:
		return
	st.subheader("Analytics")
	model_counts = {"haiku": 0, "sonnet": 0}
	for row in history:
		model_counts[row["Final Model"]] = model_counts.get(row["Final Model"], 0) + 1
	st.caption("Model usage")
	st.bar_chart(model_counts)
	chart_rows = []
	cumulative = 0.0
	for index, row in enumerate(history, start=1):
		cumulative += row["Savings"]
		chart_rows.append(
			{
				"request": index,
				"cost": row["Cost"],
				"cumulative_savings": cumulative,
				"escalated": int(row["Escalated"]),
				"confidence": row["Confidence"],
			}
		)
	st.line_chart(chart_rows, x="request", y=["cost", "cumulative_savings"])
	st.line_chart(chart_rows, x="request", y=["confidence"])
	st.bar_chart({row["Task"]: sum(item["Task"] == row["Task"] for item in history) for row in history})


def main() -> None:
	st.set_page_config(page_title="Cost-Aware Router", page_icon=":bar_chart", layout="wide")
	st.title("Cost-Aware Multi-Model Router")
	st.caption("Route requests to the cheapest capable model and inspect the observed trade-offs.")

	with st.form("request_form"):
		task_label = st.selectbox("Task type", list(TASK_OPTIONS))
		user_input = st.text_area("User prompt or input", height=160)
		submitted = st.form_submit_button("Run request", type="primary")
	if submitted:
		try:
			result = _run_request(TASK_OPTIONS[task_label], user_input)
			if result.get("response", {}).get("success") is False:
				st.error(result["response"].get("error", "The model request failed"))
			else:
				st.success("Request completed")
		except ConfigurationError:
			st.error("An Anthropic API key is required to process requests.")
		except ValueError as error:
			st.error(str(error))
		except Exception:
			st.error("The routing request failed. Check the application logs for details.")

	history = _history()
	if history:
		latest = history[-1]
		st.subheader("Latest result")
		st.write(latest["Answer"] or "No final answer was returned.")
		result_columns = st.columns(6)
		for column, (label, key) in zip(
			result_columns,
			[("Task type", "Task"), ("Initial model", "Initial Model"), ("Final model", "Final Model"),
			 ("Confidence", "Confidence"), ("Complexity", "Complexity"), ("Escalation", "Escalated")],
		):
			column.metric(label, latest[key])
		st.caption(f"Reason: {latest['Escalation Reason'] or 'No escalation'}")
		st.write({"Actual cost": latest["Cost"], "Baseline Sonnet cost": latest["Baseline"], "Savings": latest["Savings"], "Latency": latest["Latency"]})

	_render_kpis(history)
	_render_charts(history)
	if history:
		st.subheader("Request history")
		columns = ["Request ID", "Task", "Initial Model", "Final Model", "Confidence", "Escalated", "Cost", "Baseline", "Savings"]
		st.dataframe([{column: row[column] for column in columns} for row in history], use_container_width=True, hide_index=True)


if __name__ == "__main__":
	main()
