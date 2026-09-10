"""Lightweight response evaluation tool for MCP callers."""

from app.tools.token_counter import count_tokens


def evaluate_response(question: str, answer: str, task_type: str) -> dict[str, object]:
	if not question.strip() or not answer.strip() or not task_type.strip():
		raise ValueError("question, answer, and task_type must not be empty")
	question_terms = {term.lower() for term in question.split() if len(term) > 2}
	answer_terms = {term.lower() for term in answer.split() if len(term) > 2}
	overlap = len(question_terms & answer_terms)
	coverage = overlap / len(question_terms) if question_terms else 0.0
	return {
		"task_type": task_type,
		"question_tokens": count_tokens(question),
		"answer_tokens": count_tokens(answer),
		"relevance": round(coverage, 4),
		"has_answer": bool(answer.strip()),
	}
