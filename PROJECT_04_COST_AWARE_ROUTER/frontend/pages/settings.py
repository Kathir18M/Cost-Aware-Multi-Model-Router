"""Safe configuration status view."""

import streamlit as st

from app.core.config import load_settings


def render() -> None:
	st.markdown('<div class="page-kicker">⚙️ / CONFIGURATION</div>', unsafe_allow_html=True)
	st.markdown('<h1>Runtime settings.</h1>', unsafe_allow_html=True)
	settings = load_settings()
	st.json({"gemini_model": settings.gemini_model, "mistral_model": settings.mistral_model, "google_api_key_configured": settings.has_google_api_key, "mistral_api_key_configured": settings.has_mistral_api_key, "log_level": settings.log_level})