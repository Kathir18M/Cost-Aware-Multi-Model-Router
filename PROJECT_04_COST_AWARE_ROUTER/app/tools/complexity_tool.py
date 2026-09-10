"""Tool-facing complexity analysis wrapper."""

from app.router.complexity_analyzer import analyze_complexity


def analyze_request_complexity(user_input: str) -> dict[str, str]:
	return {"complexity": analyze_complexity(user_input)}
