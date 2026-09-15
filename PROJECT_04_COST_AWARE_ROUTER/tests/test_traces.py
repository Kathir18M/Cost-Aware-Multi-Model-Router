from frontend.pages.traces import filter_trace_events, load_trace_events, trace_stages


def test_empty_trace_log(tmp_path) -> None:
    missing_log = tmp_path / "missing_trace.jsonl"
    assert load_trace_events(missing_log) == []


def test_trace_search_filters_actual_metadata() -> None:
    events = [
        {
            "request_id": "req-1",
            "trace_id": "trace-a",
            "task_type": "qa",
            "initial_model": "gemini",
            "final_model": "gemini",
        },
        {
            "request_id": "req-2",
            "trace_id": "trace-b",
            "task_type": "extraction",
            "initial_model": "gemini",
            "final_model": "mistral",
        },
    ]

    assert filter_trace_events(events, query="trace-b")[0]["request_id"] == "req-2"
    assert filter_trace_events(events, model="mistral")[0]["request_id"] == "req-2"
    assert filter_trace_events(events, escalation="Yes")[0]["request_id"] == "req-2"


def test_trace_stages_only_mark_recorded_fields() -> None:
    stages = trace_stages({"request_id": "req-1", "task_type": "qa", "confidence": 0.8})

    recorded = {stage["name"] for stage in stages if stage["available"]}
    assert recorded == {"REQUEST", "TASK CLASSIFICATION", "CONFIDENCE"}
    assert all("api_key" not in str(stage).lower() for stage in stages)
