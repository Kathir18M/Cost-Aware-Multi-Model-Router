"""Streamlit entry point for the frontend foundation."""

from __future__ import annotations

import streamlit as st

from frontend.components.ui import render_header
from frontend.pages.router import render as render_router_page
from frontend.pages.dashboard import render as render_dashboard_page
from frontend.pages.traces import render as render_traces_page
from frontend.pages.connectors import render as render_connectors_page
from frontend.pages.evaluation import render as render_evaluation_page
from frontend.pages.logs import render as render_logs_page
from frontend.pages.settings import render as render_settings_page
from frontend.styles.theme import apply_theme
from frontend.utils.navigation import NAV_ITEMS


def render_placeholder(title: str, description: str, icon: str) -> None:
	st.markdown(
		f'<div class="page-kicker">{icon} / WORKSPACE</div><h1>{title}</h1>',
		unsafe_allow_html=True,
	)
	st.markdown(f'<p class="page-description">{description}</p>', unsafe_allow_html=True)
	st.markdown(
		'<div class="empty-state"><div class="empty-icon">◈</div>'
		'<div><strong>Module ready for the next phase</strong>'
		'<p>This surface is connected to the navigation system and ready for backend capabilities.</p>'
		'</div></div>',
		unsafe_allow_html=True,
	)


def main() -> None:
	st.set_page_config(page_title="Cost-Aware Router", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
	apply_theme()
	with st.sidebar:
		st.markdown('<div class="brand-mark"><span>◈</span><div><strong>COST-AWARE</strong><small>ROUTER OS</small></div></div>', unsafe_allow_html=True)
		st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
		st.markdown('<div class="nav-caption">NAVIGATION</div>', unsafe_allow_html=True)
		navigation = st.navigation([
			st.Page(render_router_page, title="Router", icon="◈", url_path="router"),
			st.Page(render_dashboard_page, title="Dashboard", icon="📊", url_path="dashboard"),
			st.Page(render_traces_page, title="Traces", icon="🔀", url_path="traces"),
			st.Page(render_connectors_page, title="MCP Connectors", icon="🔌", url_path="mcp-connectors"),
			st.Page(render_evaluation_page, title="Evaluation", icon="🧪", url_path="evaluation"),
			st.Page(render_logs_page, title="Logs", icon="📜", url_path="logs"),
			st.Page(render_settings_page, title="Settings", icon="⚙️", url_path="settings"),
		])
		st.markdown('<div class="sidebar-footer"><span class="status-dot"></span> SYSTEM ONLINE<small>FRONTEND FOUNDATION · v0.1</small></div>', unsafe_allow_html=True)
	navigation.run()
	with st.container():
		render_header()


if __name__ == "__main__":
	main()