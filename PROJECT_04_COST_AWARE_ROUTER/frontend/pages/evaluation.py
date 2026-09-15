"""Evaluation status view without fabricated metrics."""

import json
from pathlib import Path

import streamlit as st


def render() -> None:
	st.markdown('<div class="page-kicker">🧪 / EVALUATION</div>', unsafe_allow_html=True)
	st.markdown('<h1>Measure before claiming.</h1>', unsafe_allow_html=True)
	result_path = Path(__file__).resolve().parents[2] / "evaluation" / "results.json"
	result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {"status": "not_run"}
	if result.get("status") != "completed":
		st.info("Evaluation has not been executed with live providers yet. No metrics are displayed.")
	else:
		st.json(result)