"""
Groww SIP Discovery Engine - Main Application Entrypoint.

Handles application configuration, session state initialization,
sidebar navigation router, view dispatching, and the universal footer.
"""

import streamlit as st
from lib.constants import FOOTER_TEXT, NAV_VIEWS, PERIOD_OPTIONS
from views.overview import render_overview
from views.themes import render_themes
from views.opportunities import render_opportunities
from views.evidence import render_evidence
from views.ask import render_ask
from views.tryit import render_tryit
from views.method import render_method

# Page configuration (spec §4)
st.set_page_config(
    page_title="Groww SIP Discovery Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global session state initialization
if "nav_radio" not in st.session_state:
    st.session_state["nav_radio"] = "Overview"
if "period_filter" not in st.session_state:
    st.session_state["period_filter"] = "All"
if "ai_call_count" not in st.session_state:
    st.session_state["ai_call_count"] = 0

# Sidebar Router (spec §6)
st.sidebar.title("SIP Discovery")
nav_selection = st.sidebar.radio(
    "Navigation",
    options=NAV_VIEWS,
    key="nav_radio",
)

# Global Period Filter on applicable views (spec §6, ARCHITECTURE §2.3)
if nav_selection in ["Overview", "Themes", "Opportunities", "Evidence"]:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Period Filter")
    st.sidebar.radio(
        "Period",
        options=PERIOD_OPTIONS,
        key="period_filter",
    )

# Dispatch view
VIEW_DISPATCHER = {
    "Overview": render_overview,
    "Themes": render_themes,
    "Opportunities": render_opportunities,
    "Evidence": render_evidence,
    "Ask the Data": render_ask,
    "Try It": render_tryit,
    "Method and Quality": render_method,
}

render_func = VIEW_DISPATCHER.get(nav_selection, render_overview)
render_func()

# Universal Footer (spec §4 rule 4, AT-7)
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: #64748B; font-size: 14px; padding: 8px 0;'>"
    f"{FOOTER_TEXT}"
    f"</div>",
    unsafe_allow_html=True,
)
