"""MCP connector status view backed by registered manager data when available."""

import streamlit as st


def render() -> None:
	st.markdown('<div class="page-kicker">🔌 / INTEGRATIONS</div>', unsafe_allow_html=True)
	st.markdown('<h1>Connector control plane.</h1>', unsafe_allow_html=True)
	st.markdown('<p class="page-description">Only configured MCP servers and discovered tools are shown. No credentials are displayed.</p>', unsafe_allow_html=True)
	st.info("No MCP manager is connected to the dashboard session yet.")
	st.dataframe([], use_container_width=True, hide_index=True)