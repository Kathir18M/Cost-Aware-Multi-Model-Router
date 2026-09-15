"""Unit tests for dashboard event log loading and filtering utilities."""

from datetime import date
from app.utils.dashboard import filter_events, load_routing_events


def test_empty_event_log_returns_empty_state_data(tmp_path) -> None:
    assert load_routing_events(tmp_path / "missing.jsonl") == []


def test_dashboard_filters_actual_events() -> None:
    events = [
        {
            "request_id": "one",
            "timestamp": "2026-09-10T10:00:00+00:00",
            "task_type": "qa",
            "final_model": "gemini",
            "initial_model": "gemini",
            "status": "accepted",
        },
        {
            "request_id": "two",
            "timestamp": "2026-09-11T10:00:00+00:00",
            "task_type": "extraction",
            "final_model": "mistral",
            "initial_model": "gemini",
            "status": "escalated",
        },
    ]

    filtered = filter_events(
        events,
        date_range=(date(2026, 9, 11), date(2026, 9, 11)),
        task_type="extraction",
        model="mistral",
        escalated="Yes",
        status="escalated",
    )

    assert [event["request_id"] for event in filtered] == ["two"]
