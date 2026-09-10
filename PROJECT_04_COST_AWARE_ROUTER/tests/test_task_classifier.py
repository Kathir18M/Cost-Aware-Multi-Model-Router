import pytest

from app.core.constants import (
	TASK_CLASSIFICATION,
	TASK_EXTRACTION,
	TASK_QA,
	TASK_SUMMARIZATION,
)
from app.router.task_classifier import TaskClassificationError, classify_task


@pytest.mark.parametrize(
	("text", "expected"),
	[
		("Classify this customer message", TASK_CLASSIFICATION),
		("Extract the fields as JSON", TASK_EXTRACTION),
		("Summarize this report", TASK_SUMMARIZATION),
		("What time does the meeting start?", TASK_QA),
	],
)
def test_all_task_types(text: str, expected: str) -> None:
	assert classify_task(text) == expected


@pytest.mark.parametrize("value", ["", "   ", None, 42])
def test_invalid_input(value: object) -> None:
	with pytest.raises(TaskClassificationError):
		classify_task(value)  # type: ignore[arg-type]
