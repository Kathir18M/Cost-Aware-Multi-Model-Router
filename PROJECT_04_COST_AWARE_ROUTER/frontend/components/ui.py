"""Reusable shell components for the frontend foundation."""

from __future__ import annotations

import streamlit as st


def render_header() -> None:
	left, right = st.columns([4, 1])
	with left:
		st.markdown('<div class="topbar"><span class="page-kicker">◈ COST-AWARE ROUTER</span><span class="topbar-sub">INTELLIGENT MULTI-MODEL ROUTING</span></div>', unsafe_allow_html=True)
	with right:
		st.markdown('<div class="system-state"><span class="status-dot"></span>SYSTEM ONLINE</div>', unsafe_allow_html=True)


def glass_card(title: str, body: str) -> None:
	"""Render a compact reusable glass card."""

	st.markdown(
		f'<div class="glass-card"><div class="card-label">{title}</div><p>{body}</p></div>',
		unsafe_allow_html=True,
	)


def status_badge(label: str, tone: str = "online") -> str:
	"""Return a consistent status badge fragment for future pages."""

	return f'<span class="status-badge {tone}">{label}</span>'