"""Advanced LangGraph orchestration for multi-step MCP tool execution."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import load_settings
from app.core.constants import MODEL_GEMINI, MODEL_MISTRAL, STATUS_ACCEPTED, STATUS_FAILED
from app.mcp.manager import MCPManager
from app.router.confidence_engine import assess_response
from app.router.task_classifier import classify_task
from app.tools.cost_calculator import calculate_cost

MAX_TOOL_ITERATIONS = int(os.getenv("MAX_TOOL_ITERATIONS", "5"))
MAX_TOOL_RETRIES = int(os.getenv("MAX_TOOL_RETRIES", "2"))
MCP_TOOL_TIMEOUT_SECONDS = float(os.getenv("MCP_TOOL_TIMEOUT_SECONDS", "30"))


class AgentPlanStep(TypedDict):
    id: int
    description: str
    status: str
    provider: str | None
    tool: str | None


class AgentPlan(TypedDict):
    goal: str
    steps: list[AgentPlanStep]


class AgentState(TypedDict, total=False):
    request_id: str
    session_id: str
    user_id: str | None
    user_query: str
    intent: str
    task_type: str
    available_tools: list[dict[str, Any]]
    plan: AgentPlan
    current_step: int | None
    completed_steps: list[int]
    selected_tool: dict[str, Any] | None
    tool_arguments: dict[str, Any]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    context: str
    initial_model: str
    final_model: str
    model: str
    confidence: float
    escalated: bool
    escalation_reason: str | None
    cost: float
    baseline_cost: float
    savings: float
    errors: list[str]
    final_answer: str
    status: str
    tool_iteration_count: int
    tool_retry_count: int
    requires_more_tools: bool
    last_error: str | None


RELEVANT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "github": ("github", "repo", "repository", "code", "issue", "pull request", "commit"),
    "gmail": ("gmail", "email", "mail", "inbox", "sender", "subject", "interview"),
    "google_drive": ("drive", "document", "file", "folder", "proposal", "doc", "presentation"),
}

USER_REPOSITORY_LIST_PATTERNS = (
    "my repositories",
    "my repos",
    "my github",
    "my projects",
    "repositories i have",
    "repositories in my account",
    "repos i have",
    "show my repositories",
    "show my repos",
    "list my repositories",
    "list my repos",
    "list all my repos",
    "what repositories do i have",
    "what repos do i have",
    "what repos",
    "what repositories",
    "show my",
    "list my",
)

EXPLICIT_SEARCH_PATTERNS = (
    "search github",
    "find repository called",
    "find repo called",
    "find my repository called",
    "find my repo called",
    "search for",
    "find repositories about",
    "repos about",
    "repositories about",
)


def discover_available_tools(manager: MCPManager, *, session_id: str | None = None) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for server in manager.list_servers():
        if not server.get("enabled") or not server.get("connected"):
            continue
        try:
            discovered = manager.discover_tools(server["name"])
        except Exception:
            continue
        for tool in discovered:
            name = str(tool.get("name") or "").strip()
            if not name:
                continue
            tools.append({
                "provider": server["name"],
                "tool": name,
                "name": name,
                "description": str(tool.get("description") or "").strip(),
                "input_schema": tool.get("input_schema") or {},
                "connected": True,
                "allowed": True,
                "user_id": session_id,
            })
    return tools


def _tool_score(tool: dict[str, Any], user_query: str) -> int:
    text = (user_query or "").lower()
    provider = str(tool.get("provider", "")).lower()
    name = str(tool.get("name", "")).lower()
    keywords = RELEVANT_KEYWORDS.get(provider, ())
    if not text:
        return 0

    has_provider_or_keyword = (provider in text) or any(keyword in text for keyword in keywords)
    if not has_provider_or_keyword:
        return 0

    if provider == "github":
        has_user_list_intent = any(pattern in text for pattern in USER_REPOSITORY_LIST_PATTERNS)
        has_explicit_search = any(pattern in text for pattern in EXPLICIT_SEARCH_PATTERNS)

        if name == "list_my_repositories":
            if has_user_list_intent and not has_explicit_search:
                return 100
            if not has_explicit_search and ("repo" in text or "repository" in text or "github" in text):
                return 80
            return 5

        if name == "search_repositories":
            if has_explicit_search:
                return 100
            if has_user_list_intent:
                return 5
            if "search" in text or "find" in text:
                return 70
            return 10

    score = 0
    if provider in text:
        score += 6
    for keyword in keywords:
        if keyword in text:
            score += 4
    if name in text:
        score += 2
    if any(word in text for word in ("latest", "find", "search", "read", "summarize", "look for", "my")):
        score += 1
    return score


def select_tools_for_query(user_query: str, tools: list[dict[str, Any]], *, max_selection: int = 3) -> list[dict[str, Any]]:
    if not user_query or not tools:
        return []
    scored = sorted(tools, key=lambda tool: _tool_score(tool, user_query), reverse=True)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for tool in scored:
        pair = f"{tool.get('provider')}:{tool.get('tool')}"
        if pair in seen:
            continue
        score = _tool_score(tool, user_query)
        if score <= 0:
            continue
        selected.append(tool)
        seen.add(pair)
        if len(selected) >= max_selection:
            break
    return selected


def _schema_required_fields(tool: dict[str, Any]) -> list[str]:
    schema = tool.get("input_schema") or {}
    if isinstance(schema, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        return [str(item) for item in required if isinstance(properties, dict) and item in properties]
    return []


def _generate_tool_arguments(tool: dict[str, Any], user_query: str, *, prior_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    tool_name = str(tool.get("tool") or tool.get("name") or "")
    if tool_name == "list_my_repositories":
        return {}

    query = user_query.strip()
    if prior_results:
        prior_text = "\n".join(
            str(item.get("data") or item.get("provider") or "")
            for item in prior_results[-3:]
            if item
        )
        if prior_text:
            query = f"{query} {prior_text}"
    schema = tool.get("input_schema") or {}
    if isinstance(schema, dict):
        required = schema.get("required") or []
        props = schema.get("properties") or {}
        if isinstance(props, dict) and required:
            generated: dict[str, Any] = {}
            for field in required:
                if field in props:
                    generated[field] = query
            if generated:
                return generated
    return {"query": query}


def _validate_tool(tool: dict[str, Any], arguments: dict[str, Any]) -> None:
    if not tool.get("provider") or not tool.get("tool"):
        raise ValueError("Tool metadata is missing required fields")
    if not isinstance(arguments, dict):
        raise TypeError("Tool arguments must be an object")
    required_fields = _schema_required_fields(tool)
    for field in required_fields:
        if field not in arguments:
            raise ValueError(f"Missing required field: {field}")


def _normalize_tool_result(provider: str, tool_name: str, result: Any, *, duration_ms: float, success: bool, error: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "provider": provider,
        "tool": tool_name,
        "success": success,
        "metadata": {"duration_ms": round(float(duration_ms), 3)},
    }
    if error:
        payload["error"] = {"code": "tool_execution_failed", "message": error}
    else:
        payload["data"] = result
    return payload


def build_context(user_query: str, tool_results: list[dict[str, Any]]) -> str:
    lines = [f"User request: {user_query}"]
    for result in tool_results:
        provider = str(result.get("provider", "unknown"))
        tool = str(result.get("tool", "unknown"))
        data = result.get("data")

        if tool == "list_my_repositories":
            repos = None
            if isinstance(data, dict):
                repos = data.get("repositories")
                if repos is None and "data" in data and isinstance(data["data"], dict):
                    repos = data["data"].get("repositories")
            elif isinstance(data, list):
                repos = data

            if repos is None:
                repos = []

            if not repos:
                lines.append(f"[{provider}:{tool}] No repositories found for the authenticated user.")
            else:
                formatted_repos = []
                for index, repo in enumerate(repos, start=1):
                    if isinstance(repo, dict):
                        name = repo.get("name") or repo.get("full_name") or "Unnamed repo"
                        desc = repo.get("description") or "No description"
                        lang = repo.get("language") or "Unknown"
                        url = repo.get("html_url") or ""
                        formatted_repos.append(f"{index}. {name} - {desc} (Language: {lang}, URL: {url})")
                    else:
                        formatted_repos.append(f"{index}. {repo}")
                lines.append(f"[{provider}:{tool}] User Repositories:\n" + "\n".join(formatted_repos))
        else:
            if isinstance(data, dict):
                summary = str(data)[:600]
            elif isinstance(data, list):
                summary = str(data[:3])[:600]
            else:
                summary = str(data)[:600] if data is not None else "No result payload."
            lines.append(f"[{provider}:{tool}] {summary}")
    return "\n".join(lines)


def analyze_request(state: AgentState) -> AgentState:
    user_query = state.get("user_query", "")
    lowered = user_query.lower()
    intent = "tool_use" if any(keyword in lowered for keyword in ("find", "search", "latest", "repository", "email", "drive", "document", "project", "github", "gmail")) else "answer_only"
    state["intent"] = intent
    state["task_type"] = classify_task(user_query)
    state["status"] = "request_analyzed"
    return state


def discover_tools(state: AgentState, *, manager: MCPManager | None = None) -> AgentState:
    if manager is None:
        state["available_tools"] = []
        state["errors"] = ["No MCP manager connected"]
        state["status"] = "error"
        return state
    tools = discover_available_tools(manager, session_id=state.get("session_id"))
    state["available_tools"] = tools
    state["status"] = "tools_discovered"
    return state


def _default_plan(state: AgentState) -> AgentPlan:
    goal = state.get("user_query", "").strip() or "Complete the request"
    providers = sorted({str(tool.get("provider", "")).strip() for tool in state.get("available_tools", []) if str(tool.get("provider", "")).strip()})
    steps: list[AgentPlanStep] = []
    for index, provider in enumerate(providers, start=1):
        steps.append({
            "id": index,
            "description": f"Search {provider.replace('_', ' ').title()} for relevant information.",
            "status": "pending",
            "provider": provider,
            "tool": None,
        })
    if not steps:
        steps.append({
            "id": 1,
            "description": "Answer without external tool usage.",
            "status": "pending",
            "provider": None,
            "tool": None,
        })
    return {"goal": goal, "steps": steps}


def create_plan(state: AgentState) -> AgentState:
    plan = _default_plan(state)
    budget = min(MAX_TOOL_ITERATIONS, max(1, len(plan["steps"])))
    steps = list(plan["steps"])
    if len(steps) > budget:
        steps = steps[:budget]
    plan["steps"] = steps
    state["plan"] = plan
    state["current_step"] = steps[0]["id"] if steps else None
    state["completed_steps"] = []
    state["status"] = "plan_created"
    return state


def validate_plan(state: AgentState) -> AgentState:
    plan = state.get("plan") or {"goal": state.get("user_query", ""), "steps": []}
    errors: list[str] = []
    available = {str(tool.get("provider", "")).strip(): tool for tool in state.get("available_tools", [])}
    for step in plan["steps"]:
        provider = step.get("provider")
        if not provider:
            continue
        if provider not in available:
            errors.append(f"{provider.replace('_', ' ').title()} is not connected.")
            step["status"] = "skipped"
        else:
            step["status"] = "pending"
    state["errors"] = errors
    if errors:
        state["status"] = "disconnected"
        state["final_answer"] = "; ".join(errors)
    else:
        state["status"] = "plan_validated"
    return state


def _find_best_tool_for_step(step: AgentPlanStep, available_tools: list[dict[str, Any]], user_query: str) -> dict[str, Any] | None:
    provider = (step.get("provider") or "").strip()
    candidates = [tool for tool in available_tools if str(tool.get("provider", "")).strip() == provider]
    if not candidates:
        return None
    scored = sorted(candidates, key=lambda tool: _tool_score(tool, user_query), reverse=True)
    return scored[0]


def select_next_action(state: AgentState) -> AgentState:
    if state.get("intent") == "answer_only":
        state["selected_tool"] = None
        state["status"] = "answer_only"
        return state
    plan = state.get("plan") or {"goal": state.get("user_query", ""), "steps": []}
    current_iteration = int(state.get("tool_iteration_count", 0) or 0)
    if current_iteration >= MAX_TOOL_ITERATIONS:
        state["status"] = "partial"
        state["final_answer"] = "I completed the available steps but reached the maximum tool iteration limit."
        state["selected_tool"] = None
        return state
    for step in plan["steps"]:
        if step.get("status") == "pending":
            tool = _find_best_tool_for_step(step, state.get("available_tools", []), state.get("user_query", ""))
            if tool is None:
                step["status"] = "skipped"
                state["errors"] = state.get("errors", []) + [f"No tool available for {step['description']}"]
                continue
            step["status"] = "running"
            step["tool"] = tool.get("tool")
            state["selected_tool"] = tool
            state["current_step"] = step.get("id")
            state["tool_arguments"] = _generate_tool_arguments(
                tool,
                state.get("user_query", ""),
                prior_results=state.get("tool_results", []),
            )
            state["status"] = "tool_selected"
            return state
    state["selected_tool"] = None
    state["status"] = "ready_for_context"
    return state


def execute_tool(state: AgentState, *, manager: MCPManager | None = None) -> AgentState:
    tool = state.get("selected_tool")
    if tool is None:
        state["status"] = "tool_missing"
        state["errors"] = state.get("errors", []) + ["No selected tool to execute"]
        return state
    if manager is None:
        state["status"] = "error"
        state["errors"] = state.get("errors", []) + ["MCP manager unavailable"]
        state["last_error"] = "MCP manager unavailable"
        return state
    provider = str(tool.get("provider", "")).strip()
    tool_name = str(tool.get("tool", "")).strip()
    arguments = state.get("tool_arguments", {})
    try:
        _validate_tool(tool, arguments)
        result = manager.call_tool(provider, tool_name, arguments, required_permission="READ")
        entry = {
            "provider": provider,
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "success": True,
        }
        state.setdefault("tool_calls", [])
        state["tool_calls"].append(entry)
        state.setdefault("tool_results", [])
        state["tool_results"].append(_normalize_tool_result(provider, tool_name, result, duration_ms=42.0, success=True))
        state["status"] = "tool_executed"
        state["last_error"] = None
        return state
    except Exception as exc:  # pragma: no cover - exercised through graph/tests
        state.setdefault("tool_calls", [])
        state["tool_calls"].append({"provider": provider, "tool": tool_name, "arguments": arguments, "success": False, "error": str(exc)})
        state.setdefault("tool_results", [])
        state["tool_results"].append(_normalize_tool_result(provider, tool_name, None, duration_ms=42.0, success=False, error=str(exc)))
        state["errors"] = state.get("errors", []) + [str(exc)]
        state["last_error"] = str(exc)
        state["status"] = "tool_failed"
        return state


def observe_result(state: AgentState) -> AgentState:
    plan = state.get("plan") or {"goal": state.get("user_query", ""), "steps": []}
    current_step_id = state.get("current_step")
    if state.get("last_error"):
        for step in plan["steps"]:
            if step.get("id") == current_step_id:
                step["status"] = "failed"
        state["requires_more_tools"] = True
        state["status"] = "observation_complete"
        return state
    for step in plan["steps"]:
        if step.get("id") == current_step_id:
            step["status"] = "completed"
            state.setdefault("completed_steps", [])
            if current_step_id not in state["completed_steps"]:
                state["completed_steps"].append(current_step_id)
    state["requires_more_tools"] = bool(state.get("plan", {}).get("steps")) and any(step.get("status") == "pending" for step in state.get("plan", {}).get("steps", []))
    state["status"] = "observation_complete"
    return state


def replan(state: AgentState) -> AgentState:
    plan = state.get("plan") or {"goal": state.get("user_query", ""), "steps": []}
    current_iteration = int(state.get("tool_iteration_count", 0) or 0)
    if state.get("last_error"):
        retries = int(state.get("tool_retry_count", 0) or 0)
        if retries < MAX_TOOL_RETRIES:
            state["tool_retry_count"] = retries + 1
            state["status"] = "retrying"
            return state
    current_iteration += 1
    state["tool_iteration_count"] = current_iteration
    if current_iteration >= MAX_TOOL_ITERATIONS:
        state["status"] = "partial"
        state["final_answer"] = "The tool loop reached the configured iteration limit before completion."
        return state
    state["status"] = "replanned"
    return state


def build_context_from_state(state: AgentState) -> AgentState:
    context = build_context(state.get("user_query", ""), state.get("tool_results", []))
    state["context"] = context
    state["status"] = "context_built"
    return state


def _generate_final_model_response(state: AgentState, *, executor: Callable[[str, str, str], dict[str, Any]] | None = None) -> AgentState:
    executor_fn = executor or _default_executor
    task_type = state.get("task_type") or classify_task(state.get("user_query", ""))
    prompt = state.get("context") or state.get("user_query", "")

    state["initial_model"] = MODEL_GEMINI
    threshold = load_settings().confidence_threshold

    response = executor_fn(MODEL_GEMINI, task_type, prompt)
    response = dict(response)

    # Check if Gemini failed (e.g. 429 rate limit or provider error)
    if not response.get("success", True):
        err_type = str(response.get("error_type") or "PROVIDER_ERROR")
        err_msg = str(response.get("error") or "Gemini provider failure")
        retry_after = response.get("retry_after_seconds")

        state["gemini_error"] = err_type
        state["escalated"] = True
        state["initial_model"] = MODEL_GEMINI
        state["final_model"] = MODEL_MISTRAL
        state["model"] = MODEL_MISTRAL

        # Fallback to Mistral
        mistral_response = executor_fn(MODEL_MISTRAL, task_type, prompt)
        mistral_response = dict(mistral_response)

        if not mistral_response.get("success", True):
            # Both models failed!
            m_err_type = str(mistral_response.get("error_type") or "PROVIDER_ERROR")
            m_retry_after = mistral_response.get("retry_after_seconds")

            state["mistral_error"] = m_err_type
            state["status"] = "provider_unavailable"
            state["all_providers_failed"] = True
            state["final_answer"] = None
            state["confidence"] = None
            state["cost"] = 0.0
            state["baseline_cost"] = 0.0
            state["savings"] = 0.0

            g_desc = "rate limited" if err_type == "RATE_LIMITED" else err_type.lower().replace("_", " ")
            m_desc = "rate limited" if m_err_type == "RATE_LIMITED" else m_err_type.lower().replace("_", " ")
            state["escalation_reason"] = f"Gemini {g_desc}; Mistral {m_desc}"
            state["retry_after_seconds"] = retry_after or m_retry_after
            return state

        # Mistral succeeded after Gemini failure
        m_ans = str(mistral_response.get("answer") or mistral_response.get("summary") or mistral_response.get("content") or "")
        state["final_answer"] = m_ans
        state["confidence"] = float(mistral_response.get("confidence") or 0.85)
        state["escalation_reason"] = f"Gemini provider failure ({err_type}); fallback to Mistral."

        m_in_tok = int(mistral_response.get("input_tokens") or max(24, len(prompt) // 4))
        m_out_tok = int(mistral_response.get("output_tokens") or max(32, len(m_ans) // 4))
        m_cost_dict = calculate_cost(MODEL_MISTRAL, m_in_tok, m_out_tok)
        state["cost"] = m_cost_dict["cost"]
        state["baseline_cost"] = m_cost_dict["cost"]
        state["savings"] = 0.0
        state["status"] = STATUS_ACCEPTED
        return state

    # Gemini succeeded
    confidence = float(response.get("confidence") or assess_response(response, task_type))
    state["confidence"] = confidence
    state["escalated"] = False
    state["escalation_reason"] = None

    in_tok = int(response.get("input_tokens") or max(24, len(prompt) // 4))
    out_tok = int(response.get("output_tokens") or max(32, len(str(response.get("answer") or "")) // 4))
    gemini_cost = calculate_cost(MODEL_GEMINI, in_tok, out_tok)
    mistral_cost = calculate_cost(MODEL_MISTRAL, in_tok, out_tok)

    if confidence < threshold:
        state["escalated"] = True
        state["escalation_reason"] = f"Gemini confidence {confidence:.2f} below configured threshold {threshold:.2f}."
        state["final_model"] = MODEL_MISTRAL
        state["model"] = MODEL_MISTRAL
        mistral_response = executor_fn(MODEL_MISTRAL, task_type, prompt)
        mistral_response = dict(mistral_response)

        if mistral_response.get("success", True):
            m_ans = str(mistral_response.get("answer") or mistral_response.get("summary") or mistral_response.get("content") or "")
            state["final_answer"] = m_ans
            state["confidence"] = float(mistral_response.get("confidence") or confidence)
            m_in_tok = int(mistral_response.get("input_tokens") or in_tok)
            m_out_tok = int(mistral_response.get("output_tokens") or out_tok)
            m_cost_dict = calculate_cost(MODEL_MISTRAL, m_in_tok, m_out_tok)
            state["cost"] = gemini_cost["cost"] + m_cost_dict["cost"]
            state["baseline_cost"] = m_cost_dict["cost"]
            state["savings"] = 0.0
        else:
            g_ans = str(response.get("answer") or response.get("summary") or response.get("content") or "")
            state["final_answer"] = g_ans
            state["final_model"] = MODEL_GEMINI
            state["model"] = MODEL_GEMINI
            state["cost"] = gemini_cost["cost"]
            state["baseline_cost"] = mistral_cost["cost"]
            state["savings"] = max(0.0, mistral_cost["cost"] - gemini_cost["cost"])

        state["status"] = STATUS_ACCEPTED
        return state

    state["final_model"] = MODEL_GEMINI
    state["model"] = MODEL_GEMINI
    state["final_answer"] = str(response.get("answer") or response.get("summary") or response.get("content") or "No answer available")
    state["cost"] = gemini_cost["cost"]
    state["baseline_cost"] = mistral_cost["cost"]
    state["savings"] = max(0.0, mistral_cost["cost"] - gemini_cost["cost"])
    state["status"] = STATUS_ACCEPTED
    return state


def evaluate_confidence(state: AgentState) -> AgentState:
    if state.get("status") == "provider_unavailable" or state.get("all_providers_failed"):
        return state
    if state.get("escalated"):
        state["status"] = STATUS_ACCEPTED
        return state
    threshold = load_settings().confidence_threshold
    confidence = float(state.get("confidence") or 0.0)
    if confidence < threshold:
        state["escalated"] = True
        state["escalation_reason"] = f"Gemini confidence {confidence:.2f} below configured threshold {threshold:.2f}."
        state["status"] = "escalation_required"
    else:
        state["escalated"] = False
        state["escalation_reason"] = None
        state["status"] = STATUS_ACCEPTED
    return state


def finalize_response(state: AgentState) -> AgentState:
    if state.get("status") == "provider_unavailable" or state.get("all_providers_failed"):
        state["status"] = "provider_unavailable"
        state["cost"] = 0.0
        state["baseline_cost"] = 0.0
        state["savings"] = 0.0
        return state
    state["status"] = state.get("status") or STATUS_ACCEPTED
    state["cost"] = float(state.get("cost") or 0.0)
    state["baseline_cost"] = float(state.get("baseline_cost") or 0.0)
    state["savings"] = float(state.get("savings") or 0.0)
    return state


def _route_after_observation(state: AgentState) -> str:
    if state.get("last_error"):
        return "replan"
    if state.get("requires_more_tools"):
        return "replan"
    return "build_context"


def _route_after_plan_validation(state: AgentState) -> str:
    if state.get("status") == "disconnected":
        return "finalize"
    if state.get("status") == "partial":
        return "finalize"
    if state.get("intent") == "answer_only":
        return "build_context"
    return "select_next_action"


def _route_after_tool(state: AgentState) -> str:
    if state.get("status") == "tool_failed":
        return "replan"
    if state.get("requires_more_tools"):
        return "replan"
    return "build_context"


def _route_after_confidence(state: AgentState) -> str:
    if state.get("status") == "provider_unavailable" or state.get("all_providers_failed"):
        return "finalize"
    if state.get("escalated"):
        return "mistral_fallback"
    return "finalize"


def _default_executor(model: str, task_type: str, user_input: str) -> dict[str, Any]:
    if "[github:list_my_repositories]" in user_input:
        if "No repositories found" in user_input:
            ans = "I couldn't find any repositories accessible through your connected GitHub account."
        else:
            extracted = user_input.split("[github:list_my_repositories]")[1].strip()
            ans = f"Here are the repositories accessible through your GitHub account:\n\n{extracted}"
        return {
            "content": ans,
            "summary": ans,
            "answer": ans,
            "success": True,
            "confidence": 0.95,
            "input_tokens": 120,
            "output_tokens": 80,
        }
    response = f"{task_type} request processed by {model}. {user_input[:200]}"
    return {
        "content": response,
        "summary": response,
        "answer": response,
        "success": True,
        "confidence": 0.85,
        "input_tokens": 32,
        "output_tokens": 48,
    }


def build_agent_graph(*, executor: Callable[[str, str, str], dict[str, Any]] | None = None, manager: MCPManager | None = None, max_iterations: int = MAX_TOOL_ITERATIONS):
    workflow = StateGraph(AgentState)

    def analyze(state: AgentState) -> AgentState:
        return analyze_request(state)

    def discover(state: AgentState) -> AgentState:
        return discover_tools(state, manager=manager)

    def plan(state: AgentState) -> AgentState:
        return create_plan(state)

    def validate(state: AgentState) -> AgentState:
        return validate_plan(state)

    def select(state: AgentState) -> AgentState:
        return select_next_action(state)

    def execute(state: AgentState) -> AgentState:
        return execute_tool(state, manager=manager)

    def observe(state: AgentState) -> AgentState:
        return observe_result(state)

    def replan_node(state: AgentState) -> AgentState:
        return replan(state)

    def context_node(state: AgentState) -> AgentState:
        return build_context_from_state(state)

    def generate(state: AgentState) -> AgentState:
        return _generate_final_model_response(state, executor=executor)

    def confidence(state: AgentState) -> AgentState:
        return evaluate_confidence(state)

    def fallback(state: AgentState) -> AgentState:
        executor_fn = executor or _default_executor
        task_type = state.get("task_type") or classify_task(state.get("user_query", ""))
        prompt = state.get("context") or state.get("user_query", "")
        response = executor_fn(MODEL_MISTRAL, task_type, prompt)
        state["final_model"] = MODEL_MISTRAL
        state["model"] = MODEL_MISTRAL
        state["final_answer"] = str(response.get("answer") or response.get("summary") or response.get("content") or "No answer available")
        state["confidence"] = float(response.get("confidence") or 0.85)
        state["status"] = STATUS_ACCEPTED
        return state

    def fin(state: AgentState) -> AgentState:
        return finalize_response(state)

    workflow.add_node("analyze_request", analyze)
    workflow.add_node("discover_tools", discover)
    workflow.add_node("create_plan", plan)
    workflow.add_node("validate_plan", validate)
    workflow.add_node("select_next_action", select)
    workflow.add_node("execute_tool", execute)
    workflow.add_node("observe_result", observe)
    workflow.add_node("replan", replan_node)
    workflow.add_node("build_context", context_node)
    workflow.add_node("generate_answer", generate)
    workflow.add_node("confidence_check", confidence)
    workflow.add_node("mistral_fallback", fallback)
    workflow.add_node("finalize", fin)

    workflow.add_edge(START, "analyze_request")
    workflow.add_edge("analyze_request", "discover_tools")
    workflow.add_edge("discover_tools", "create_plan")
    workflow.add_edge("create_plan", "validate_plan")
    workflow.add_conditional_edges(
        "validate_plan",
        _route_after_plan_validation,
        {"select_next_action": "select_next_action", "build_context": "build_context", "finalize": "finalize"},
    )
    workflow.add_conditional_edges(
        "select_next_action",
        lambda state: "execute_tool" if state.get("selected_tool") else "build_context",
        {"execute_tool": "execute_tool", "build_context": "build_context"},
    )
    workflow.add_edge("execute_tool", "observe_result")
    workflow.add_conditional_edges(
        "observe_result",
        _route_after_observation,
        {"replan": "replan", "build_context": "build_context"},
    )
    workflow.add_conditional_edges(
        "replan",
        lambda state: "select_next_action" if state.get("status") == "replanned" else "finalize",
        {"select_next_action": "select_next_action", "finalize": "finalize"},
    )
    workflow.add_edge("build_context", "generate_answer")
    workflow.add_edge("generate_answer", "confidence_check")
    workflow.add_conditional_edges(
        "confidence_check",
        _route_after_confidence,
        {"mistral_fallback": "mistral_fallback", "finalize": "finalize"},
    )
    workflow.add_edge("mistral_fallback", "finalize")
    workflow.add_edge("finalize", END)
    return workflow.compile()


def run_agent_request(*, query: str, manager: MCPManager | None = None, executor: Callable[[str, str, str], dict[str, Any]] | None = None, user_id: str | None = None, max_iterations: int = MAX_TOOL_ITERATIONS) -> dict[str, Any]:
    graph = build_agent_graph(executor=executor, manager=manager, max_iterations=max_iterations)
    req_id = f"req_{uuid.uuid4().hex[:12]}"
    state = graph.invoke({
        "request_id": req_id,
        "session_id": user_id or "anon",
        "user_id": user_id,
        "user_query": query,
        "task_type": classify_task(query),
        "tool_iteration_count": 0,
        "tool_retry_count": 0,
        "errors": [],
        "tool_calls": [],
        "tool_results": [],
        "completed_steps": [],
    })

    if state.get("status") == "provider_unavailable" or state.get("all_providers_failed"):
        return {
            "request_id": req_id,
            "status": "provider_unavailable",
            "all_providers_failed": True,
            "answer": None,
            "model": None,
            "confidence": None,
            "escalated": True,
            "escalation_reason": state.get("escalation_reason") or "All configured AI providers are currently unavailable.",
            "cost": 0.0,
            "actual_cost": 0.0,
            "baseline_cost": 0.0,
            "savings": 0.0,
            "savings_percentage": 0.0,
            "retry_after_seconds": state.get("retry_after_seconds"),
            "error": {
                "code": "ALL_PROVIDERS_UNAVAILABLE",
                "message": "All configured AI providers are currently unavailable."
            },
            "tools_used": [
                {"provider": call.get("provider"), "tool": call.get("tool")}
                for call in state.get("tool_calls", [])
                if isinstance(call, dict) and call.get("provider") and call.get("tool")
            ],
            "tool_results": state.get("tool_results", []),
            "plan": state.get("plan"),
            "steps_completed": len(state.get("completed_steps", [])),
        }

    actual_cost = float(state.get("cost") or state.get("actual_cost") or 0.0)
    baseline_cost = float(state.get("baseline_cost") or 0.0)
    savings = float(state.get("savings") or max(0.0, baseline_cost - actual_cost))
    savings_percentage = round((savings / baseline_cost) * 100, 2) if baseline_cost else 0.0
    return {
        "request_id": req_id,
        "answer": state.get("final_answer") or "No answer available.",
        "model": state.get("model") or state.get("final_model") or MODEL_GEMINI,
        "confidence": float(state.get("confidence") or 0.0),
        "tools_used": [
            {"provider": call.get("provider"), "tool": call.get("tool")}
            for call in state.get("tool_calls", [])
            if isinstance(call, dict) and call.get("provider") and call.get("tool")
        ],
        "escalated": bool(state.get("escalated")),
        "escalation_reason": state.get("escalation_reason"),
        "cost": actual_cost,
        "actual_cost": actual_cost,
        "baseline_cost": baseline_cost,
        "savings": savings,
        "savings_percentage": savings_percentage,
        "status": state.get("status") or STATUS_ACCEPTED,
        "tool_results": state.get("tool_results", []),
        "plan": state.get("plan"),
        "steps_completed": len(state.get("completed_steps", [])),
    }
