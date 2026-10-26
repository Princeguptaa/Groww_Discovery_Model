"""
Overview screen view module for Groww SIP Discovery Engine.
Displays:
1. 6-step discovery funnel (always all periods, labelled 'all periods')
2. 3 headline findings (period-filtered) with sample sizes (n)
3. 12-month cohort metric disclaimer note
4. Small-sample banner when 'After 25 Dec 2024' is selected
"""

import streamlit as st
import plotly.graph_objects as go
from lib.data_loader import load_reviews, load_funnel_inputs
from lib.compute import apply_period_filter, compute_funnel, compute_headline_findings
from lib.constants import (
    METRIC_NOTE_12M,
    PERIOD_ALL,
    PERIOD_AFTER,
    PALETTE_IBM,
)


def render_overview():
    st.title("SIP Continuation Discovery")
    st.caption("Evidence-based exploration of why first-time investors discontinue mutual fund SIPs on Groww.")

    # 1. Load data assets
    df = load_reviews()
    funnel_inputs = load_funnel_inputs()

    # Active period selection
    period_selection = st.session_state.get("period_filter", PERIOD_ALL)
    df_filtered = apply_period_filter(df, period_selection)

    # Small sample warning for After 25 Dec 2024 (Spec §6)
    if period_selection == PERIOD_AFTER:
        n_after = int((df_filtered["relevant_final"] == "Yes").sum())
        st.warning(f"After 25 Dec 2024 (n = {n_after}). Small sample, patterns only.")

    # 2. Discovery Funnel (Spec §7.1, always all periods)
    st.subheader("Discovery Funnel (all periods)")
    st.caption(
        "Shows full-corpus filtering from Play Store scraping to confirmed SIP continuation events with stated outcomes. "
        "Funnel counts are fixed across all periods."
    )

    funnel_steps = compute_funnel(df, funnel_inputs)

    # Metric summary cards in columns
    cols = st.columns(len(funnel_steps))
    for idx, step in enumerate(funnel_steps):
        with cols[idx]:
            delta_str = f"{step['pct_of_prev']}% from prev" if idx > 0 else "Baseline"
            st.metric(
                label=f"Step {step['step_id']}: {step['name']}",
                value=f"{step['count']:,}",
                delta=delta_str if idx > 0 else None,
            )
            st.caption(step["source"])

    # Funnel Horizontal Bar Chart (Plotly)
    step_names = [f"Step {s['step_id']}: {s['name']}" for s in funnel_steps]
    step_counts = [s["count"] for s in funnel_steps]
    step_text = [
        f"{s['count']:,} ({s['pct_of_prev']}% of prev)" if s["step_id"] > 1 else f"{s['count']:,}"
        for s in funnel_steps
    ]

    bar_colors = [
        PALETTE_IBM[0],
        PALETTE_IBM[1],
        PALETTE_IBM[0],
        PALETTE_IBM[1],
        PALETTE_IBM[2],
        PALETTE_IBM[3],
    ][: len(funnel_steps)]

    fig = go.Figure(
        go.Bar(
            x=step_counts,
            y=step_names,
            orientation="h",
            marker=dict(color=bar_colors),
            text=step_text,
            textposition="auto",
            hoverinfo="x+y",
        )
    )
    fig.update_layout(
        title=dict(text="Funnel Drop-off Progression (all periods)", font=dict(size=15)),
        yaxis=dict(autorange="reversed"),
        xaxis=dict(title="Review / Record Count"),
        height=320,
        margin=dict(l=10, r=20, t=40, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 3. Three Headline Findings (Spec §7.1, period-filtered)
    st.subheader(f"Headline Findings ({period_selection})")
    findings = compute_headline_findings(df_filtered)

    h_col1, h_col2, h_col3 = st.columns(3)

    with h_col1:
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 16px; background-color: #F8FAFC; min-height: 200px;">
                <div style="font-size: 13px; font-weight: 600; color: #64748B; text-transform: uppercase;">
                    Top Friction Theme <span style="background: #E2E8F0; color: #1E293B; padding: 2px 6px; border-radius: 4px; font-size: 11px;">n = {findings['top_theme']['n']}</span>
                </div>
                <div style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 8px 0 4px 0;">
                    {findings['top_theme']['theme']}
                </div>
                <div style="font-size: 14px; color: #334155; margin-bottom: 8px;">
                    <b>{findings['top_theme']['count']:,}</b> mentions ({findings['top_theme']['pct']}% of relevant reviews)
                </div>
                <div style="font-size: 12px; color: #64748B; border-top: 1px solid #E2E8F0; padding-top: 6px;">
                    Amplifier: <b>Support not solving</b> ({findings['support_amplifier']['count']:,} mentions, {findings['support_amplifier']['pct']}%)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with h_col2:
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 16px; background-color: #F8FAFC; min-height: 200px;">
                <div style="font-size: 13px; font-weight: 600; color: #64748B; text-transform: uppercase;">
                    Dominant Root Cause <span style="background: #E2E8F0; color: #1E293B; padding: 2px 6px; border-radius: 4px; font-size: 11px;">n = {findings['top_cause']['n']}</span>
                </div>
                <div style="font-size: 18px; font-weight: 700; color: #0F172A; margin: 8px 0 4px 0;">
                    {findings['top_cause']['cause']}
                </div>
                <div style="font-size: 14px; color: #334155;">
                    <b>{findings['top_cause']['count']:,}</b> occurrences ({findings['top_cause']['pct']}% of relevant reviews)
                </div>
                <div style="font-size: 12px; color: #64748B; margin-top: 10px;">
                    Primary structural driver identified across user complaints in this period.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with h_col3:
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 16px; background-color: #F8FAFC; min-height: 200px;">
                <div style="font-size: 13px; font-weight: 600; color: #64748B; text-transform: uppercase;">
                    Lost Continuation Rate <span style="background: #E2E8F0; color: #1E293B; padding: 2px 6px; border-radius: 4px; font-size: 11px;">n = {findings['lost_rate']['n']}</span>
                </div>
                <div style="font-size: 26px; font-weight: 700; color: #DC2626; margin: 8px 0 4px 0;">
                    {findings['lost_rate']['rate_pct']}%
                </div>
                <div style="font-size: 13px; color: #334155;">
                    <b>{findings['lost_rate']['lost_count']:,}</b> of {findings['lost_rate']['n_outcome_stated']:,} stated outcomes
                </div>
                <div style="font-size: 12px; color: #64748B; margin-top: 6px;">
                    Resulted in stopped/cancelled, switched away, or stalled not by choice.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 4. 12-Month Cohort Metric Note (Spec §2 & §7.1)
    st.info(f"**Measurement Scope Note:**\n\n{METRIC_NOTE_12M}")
