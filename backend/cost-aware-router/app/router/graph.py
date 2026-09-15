"""Compiled LangGraph workflow for initial request routing."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.router.nodes import (
	ModelExecutor,
	analyze_complexity_node,
	check_confidence_node,
	classify_task_node,
	execute_model_node,
	execute_sonnet_node,
	finalize_response_node,
	route_after_confidence,
	select_model_node,
)
from app.router.mcp_tools import mcp_tool_node
from app.mcp.manager import MCPManager
from app.schemas.router_state import RouterState


def _make_executor_node(executor: ModelExecutor | None) -> Callable[[RouterState], RouterState]:
	def execute(state: RouterState) -> RouterState:
		return execute_model_node(state, executor=executor)

	return execute


def _make_sonnet_node(executor: ModelExecutor | None) -> Callable[[RouterState], RouterState]:
	def execute(state: RouterState) -> RouterState:
		return execute_sonnet_node(state, executor=executor)

	return execute


def build_graph(*, executor: ModelExecutor | None = None, mcp_manager: MCPManager | None = None):
	"""Build and compile the routing workflow."""

	workflow = StateGraph(RouterState)
	workflow.add_node("classify_task", classify_task_node)
	workflow.add_node("analyze_complexity", analyze_complexity_node)
	workflow.add_node("select_model", select_model_node)
	workflow.add_node("mcp_tool", lambda state: mcp_tool_node(state, manager=mcp_manager))
	workflow.add_node("execute_model", _make_executor_node(executor))
	workflow.add_node("check_confidence", check_confidence_node)
	workflow.add_node("execute_sonnet", _make_sonnet_node(executor))
	workflow.add_node("finalize_response", finalize_response_node)
	workflow.add_edge(START, "classify_task")
	workflow.add_edge("classify_task", "analyze_complexity")
	workflow.add_edge("analyze_complexity", "select_model")
	workflow.add_edge("select_model", "mcp_tool")
	workflow.add_edge("mcp_tool", "execute_model")
	workflow.add_edge("execute_model", "check_confidence")
	workflow.add_conditional_edges(
		"check_confidence",
		route_after_confidence,
		{"execute_sonnet": "execute_sonnet", "finalize_response": "finalize_response"},
	)
	workflow.add_edge("execute_sonnet", "finalize_response")
	workflow.add_edge("finalize_response", END)
	return workflow.compile()


graph = build_graph()
