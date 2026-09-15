"""Safe operational log status view."""

import streamlit as st

from app.tools.statistics_tool import get_router_statistics


def render() -> None:
	st.markdown('<div class="page-kicker">📜 / OPERATIONS</div>', unsafe_allow_html=True)
	st.markdown('<h1>Operational signals.</h1>', unsafe_allow_html=True)
	st.json(get_router_statistics())
	st.caption("Raw prompts, credentials, and provider secrets are not displayed.")