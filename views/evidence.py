"""
Evidence Browser screen view module for Groww SIP Discovery Engine.
Displays:
1. 10 interactive filters with inbound filter state integration
2. "Showing {n} of {total}" counter
3. Safe HTML evidence highlighting with XSS prevention
4. Scope badges (distinct badge for Entry before SIP running)
5. 25-row pagination with page controls
6. Sanitized CSV export omitting unverified model metrics
"""

import math
from typing import List, Set
import streamlit as st
import pandas as pd
from lib.data_loader import load_reviews
from lib.privacy import highlight_evidence, highlight_search_terms, sanitize_export
from lib.compute import filter_reviews_by_search
from lib.constants import (
    PERIOD_ALL,
    PERIOD_BEFORE,
    PERIOD_AFTER,
    PERIOD_OPTIONS,
    HYPOTHESIS_NOTE,
)


def _get_pipe_tokens(series: pd.Series) -> List[str]:
    """Extract sorted unique non-empty tokens from pipe-separated column values."""
    tokens: Set[str] = set()
    for val in series.dropna():
        if not val:
            continue
        for part in str(val).split("|"):
            clean_part = part.strip()
            if clean_part and clean_part.lower() != "none":
                tokens.add(clean_part)
    return sorted(tokens)


def render_evidence():
    st.title("Evidence Browser")
    st.caption("Inspect primary review quotes, AI classifications, and stated outcomes with verified safety filters.")

    # Search box at the top of Evidence
    search_query = st.text_input(
        "Search reviews (for example: autopay, refund, not deducted)",
        key="evidence_search_input",
    )

    # Reset to page 1 whenever a new search is typed
    if "prev_evidence_search" not in st.session_state:
        st.session_state["prev_evidence_search"] = ""

    if search_query != st.session_state["prev_evidence_search"]:
        st.session_state["evidence_page"] = 1
        st.session_state["prev_evidence_search"] = search_query

    # Search only relevant reviews (relevant_final == 'Yes')
    raw_df = load_reviews()
    df = raw_df[raw_df["relevant_final"] == "Yes"].copy()
    total_rows = len(df)

    # Inbound filter consumption from other screens (e.g., Journey or Opportunities)
    inbound_theme = st.session_state.pop("evidence_theme", None)
    inbound_stage = st.session_state.pop("evidence_stage", None)
    inbound_cause = st.session_state.pop("evidence_cause", None)

    # Filter section
    with st.expander("Filter Evidence (10 Dimensions)", expanded=True):
        col1, col2, col3, col4 = st.columns(4)

        # 1. Period (sync with global filter or allow override)
        period_options = [PERIOD_ALL, PERIOD_BEFORE, PERIOD_AFTER]
        curr_period = st.session_state.get("period_filter", PERIOD_ALL)
        period_idx = period_options.index(curr_period) if curr_period in period_options else 0
        with col1:
            f_period = st.selectbox("Period", options=period_options, index=period_idx)

        # 2. Source
        source_options = ["All"] + sorted(df["source"].dropna().unique().tolist())
        with col2:
            f_source = st.selectbox("Source", options=source_options)

        # 3. Scope
        scope_options = ["All"] + sorted(df["scope"].dropna().unique().tolist())
        with col3:
            f_scope = st.selectbox("Scope", options=scope_options)

        # 4. Stage
        stage_options = ["All"] + sorted(df["stage"].dropna().unique().tolist())
        stage_idx = 0
        if inbound_stage and inbound_stage in stage_options:
            stage_idx = stage_options.index(inbound_stage)
        with col4:
            f_stage = st.selectbox("Stage", options=stage_options, index=stage_idx)

        col5, col6, col7, col8 = st.columns(4)

        # 5. Theme
        theme_options = ["All"] + sorted(df["theme"].dropna().unique().tolist())
        theme_idx = 0
        if inbound_theme and inbound_theme in theme_options:
            theme_idx = theme_options.index(inbound_theme)
        with col5:
            f_theme = st.selectbox("Theme", options=theme_options, index=theme_idx)

        # 6. Cause
        cause_options = ["All"] + sorted(df["cause"].dropna().unique().tolist())
        cause_idx = 0
        if inbound_cause and inbound_cause in cause_options:
            cause_idx = cause_options.index(inbound_cause)
        with col6:
            f_cause = st.selectbox("Cause", options=cause_options, index=cause_idx)

        # 7. Hypothesis (directional)
        hyp_options = ["All"] + sorted(df["hypothesis_final"].dropna().unique().tolist())
        with col7:
            f_hyp = st.selectbox("Hypothesis (directional)", options=hyp_options)

        # 8. Outcome
        outcome_options = ["All"] + sorted(df["outcome_final"].dropna().unique().tolist())
        with col8:
            f_outcome = st.selectbox("Outcome", options=outcome_options)

        col9, col10 = st.columns(2)

        # 9. Controls mentioned (multi-select)
        available_controls = _get_pipe_tokens(df["controls_mentioned"])
        with col9:
            f_controls = st.multiselect("Controls Mentioned", options=available_controls)

        # 10. Workarounds (multi-select)
        available_workarounds = _get_pipe_tokens(df["workarounds"])
        with col10:
            f_workarounds = st.multiselect("Workarounds", options=available_workarounds)

    # Apply filters
    filtered_df = df.copy()

    if f_period != PERIOD_ALL:
        filtered_df = filtered_df[filtered_df["period"] == f_period]
    if f_source != "All":
        filtered_df = filtered_df[filtered_df["source"] == f_source]
    if f_scope != "All":
        filtered_df = filtered_df[filtered_df["scope"] == f_scope]
    if f_stage != "All":
        filtered_df = filtered_df[filtered_df["stage"] == f_stage]
    if f_theme != "All":
        filtered_df = filtered_df[filtered_df["theme"] == f_theme]
    if f_cause != "All":
        filtered_df = filtered_df[filtered_df["cause"] == f_cause]
    if f_hyp != "All":
        filtered_df = filtered_df[filtered_df["hypothesis_final"] == f_hyp]
    if f_outcome != "All":
        filtered_df = filtered_df[filtered_df["outcome_final"] == f_outcome]

    if f_controls:
        def match_controls(val: str) -> bool:
            tokens = set(t.strip() for t in str(val).split("|") if t.strip())
            return any(c in tokens for c in f_controls)
        filtered_df = filtered_df[filtered_df["controls_mentioned"].apply(match_controls)]

    if f_workarounds:
        def match_workarounds(val: str) -> bool:
            tokens = set(t.strip() for t in str(val).split("|") if t.strip())
            return any(w in tokens for w in f_workarounds)
        filtered_df = filtered_df[filtered_df["workarounds"].apply(match_workarounds)]

    # 11. Search filter
    if search_query and search_query.strip():
        filtered_df = filter_reviews_by_search(filtered_df, search_query)

    n_filtered = len(filtered_df)

    # Header counter & CSV Export (Spec §7.5)
    cnt_col, dl_col = st.columns([3, 1])
    with cnt_col:
        st.markdown(f"### Showing **{n_filtered:,}** of {total_rows:,} reviews")
    with dl_col:
        # Sanitized CSV export omitting unverified model metrics
        export_df = sanitize_export(filtered_df)
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Filtered CSV",
            data=csv_bytes,
            file_name="groww_sip_evidence_filtered.csv",
            mime="text/csv",
        )

    if n_filtered == 0:
        st.warning("No reviews match. Try fewer words or clear a filter.")
        return

    # Pagination: 25 rows per page (Spec §7.5)
    PAGE_SIZE = 25
    total_pages = math.ceil(n_filtered / PAGE_SIZE)

    if "evidence_page" not in st.session_state:
        st.session_state["evidence_page"] = 1

    # Keep page within bounds
    if st.session_state["evidence_page"] > total_pages:
        st.session_state["evidence_page"] = 1

    p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
    with p_col1:
        if st.button("Previous Page", disabled=(st.session_state["evidence_page"] <= 1)):
            st.session_state["evidence_page"] -= 1
            st.rerun()
    with p_col2:
        st.markdown(
            f"<div style='text-align: center; font-size: 14px; padding-top: 6px;'>"
            f"Page <b>{st.session_state['evidence_page']}</b> of <b>{total_pages}</b>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with p_col3:
        if st.button("Next Page", disabled=(st.session_state["evidence_page"] >= total_pages)):
            st.session_state["evidence_page"] += 1
            st.rerun()

    # Slice page
    start_idx = (st.session_state["evidence_page"] - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, n_filtered)
    page_rows = filtered_df.iloc[start_idx:end_idx]

    # Render review cards
    for _, row in page_rows.iterrows():
        eid = row.get("evidence_id", "Unknown")
        date_val = str(row.get("date", ""))[:10]
        source_val = row.get("source", "Play Store")
        scope_val = row.get("scope", "")
        theme_val = row.get("theme", "")
        cause_val = row.get("cause", "")
        stage_val = row.get("stage", "")
        hyp_val = row.get("hypothesis_final", "")
        outcome_val = row.get("outcome_final", "")
        raw_text = str(row.get("text", ""))
        evidence_phrase = str(row.get("evidence", ""))

        # Scope badge
        if scope_val == "Entry (before a SIP is running)":
            scope_badge = '<span style="background: #FEF3C7; color: #92400E; font-weight: 600; padding: 2px 8px; border-radius: 4px; font-size: 11px;">Entry Scope</span>'
        else:
            scope_badge = '<span style="background: #E0E7FF; color: #3730A3; font-weight: 600; padding: 2px 8px; border-radius: 4px; font-size: 11px;">Continuation</span>'

        # Highlight evidence and search words safely
        highlighted_body = highlight_search_terms(raw_text, search_query, fallback_phrase=evidence_phrase)

        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 14px; margin-bottom: 12px; background-color: #FFFFFF;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div>
                        <span style="font-family: monospace; font-weight: 700; color: #1E293B; font-size: 14px;">{eid}</span>
                        &nbsp;·&nbsp;<span style="color: #64748B; font-size: 12px;">{date_val} ({source_val})</span>
                    </div>
                    <div>
                        {scope_badge}
                    </div>
                </div>
                <div style="font-size: 14px; color: #1E293B; line-height: 1.5; margin: 8px 0; padding: 8px 12px; background: #F8FAFC; border-left: 3px solid #0284C7; border-radius: 2px;">
                    {highlighted_body}
                </div>
                <div style="font-size: 12px; color: #475569; display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px;">
                    <span><b>Theme:</b> {theme_val}</span>
                    <span>·</span>
                    <span><b>Cause:</b> {cause_val}</span>
                    <span>·</span>
                    <span><b>Stage:</b> {stage_val}</span>
                    <span>·</span>
                    <span><b>Outcome:</b> {outcome_val}</span>
                    <span>·</span>
                    <span><b>Hypothesis:</b> {hyp_val} (directional)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
