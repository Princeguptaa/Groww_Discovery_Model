"""
Opportunities Screen View module for Groww SIP Discovery Engine.

Computes runtime-prioritized opportunities from period-filtered reviews (Spec §7.4).
Features:
1. Dynamic priority table computation from active period filter
2. Configurable sorting by Priority Score or Mentions
3. Transparent formula definitions expander
4. Prominent heuristic disclaimer (§4 rule 4)
5. Direct cross-page deep-linking into Evidence Browser via on_click callback
"""

import streamlit as st
import pandas as pd
from lib.constants import (
    OPPORTUNITY_DISCLAIMER,
    PERIOD_ALL,
    PERIOD_AFTER,
    MONEY_FLAG_THEMES,
)
from lib.data_loader import load_reviews
from lib.compute import apply_period_filter, compute_opportunity_table


def _go_to_evidence(theme: str, cause: str = None):
    """Callback to pre-populate Evidence filters and switch navigation."""
    st.session_state["evidence_theme"] = theme
    if cause:
        st.session_state["evidence_cause"] = cause
    else:
        st.session_state.pop("evidence_cause", None)
    st.session_state["nav_radio"] = "Evidence"


def render_opportunities():
    st.title("Opportunities Prioritisation")
    st.caption("Runtime-computed priority heuristic across continuation friction themes and cause dimensions.")

    # 1. Global Period Filter state
    current_period = st.session_state.get("period_filter", PERIOD_ALL)
    raw_df = load_reviews()
    filtered_df = apply_period_filter(raw_df, current_period)
    rel_in_period = (filtered_df["relevant_final"] == "Yes").sum()

    # Small sample banner when After 25 Dec 2024 is chosen (Spec §6)
    if current_period == PERIOD_AFTER:
        st.warning(
            f"After 25 Dec 2024 (n = {rel_in_period}). Small sample, patterns only.",
            icon="⚠️",
        )

    # 2. Mandatory Disclaimer (Spec §4 rule 4, §7.4)
    st.markdown(
        f"""
        <div style="background-color: #EFF6FF; border-left: 4px solid #3B82F6; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px;">
            <span style="font-weight: 600; color: #1E40AF;">Prioritisation Heuristic:</span>
            <span style="color: #1E3A8A; font-size: 14px;"> {OPPORTUNITY_DISCLAIMER}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3. Formula Expander
    with st.expander("Formula Definitions & Scoring Logic", expanded=False):
        st.markdown(
            """
            The priority score identifies where product and operations intervention can prevent the most unchosen SIP drop-offs:
            
            $$\\text{Priority Score} = \\text{Mentions} \\times (1 + \\text{Lost Rate}) \\times (1 + \\text{Money Flag})$$
            
            - **Mentions ($n \\ge 5$)**: Number of relevant reviews citing this group in the active period. Groups with fewer than 5 mentions are excluded.
            - **Share of Relevant (%)**: Percentage of total relevant reviews in this period ($\text{mentions} / n_{\\text{relevant}}$).
            - **Stated Outcomes ($n$)**: Count of reviews in this combination where `outcome_final != 'Unknown'`.
            - **Lost Rate**: Proportion of reviews with stated outcomes that stopped/cancelled, switched away, or stalled not by choice. **Set to 0.0 if stated outcomes $n < 5$**.
            - **Money Flag**: Binary multiplier ($1$ or $0$). Set to $1$ (yielding a $2\\times$ multiplier) for themes involving direct fund debits, allocation delays, or redemption friction.
            """
        )

    # 4. Controls: Group by switch and Sorting controls
    ctrl_col1, ctrl_col2 = st.columns([1, 1])
    with ctrl_col1:
        group_by = st.radio(
            "Group by",
            options=["Theme only", "Theme and cause"],
            index=0,
            horizontal=True,
            key="opp_group_toggle",
        )
    with ctrl_col2:
        sort_choice = st.radio(
            "Sort Order",
            options=["Priority Score (descending)", "Mentions (descending)"],
            horizontal=True,
            key="opp_sort_toggle",
        )
    sort_col = "mentions" if "Mentions" in sort_choice else "priority_score"

    # Compute Opportunity Table dynamically at runtime
    opp_df = compute_opportunity_table(
        filtered_df, sort_by=sort_col, group_by=group_by
    )

    if len(opp_df) == 0:
        st.info("No opportunity combinations found with at least 5 mentions for this period slice.")
        return

    is_theme_only = (group_by == "Theme only")

    # 5. Top KPI metric cards
    top_score_row = opp_df.sort_values("priority_score", ascending=False).iloc[0]
    top_volume_row = opp_df.sort_values("mentions", ascending=False).iloc[0]
    money_flag_count = int(opp_df["money_flag"].sum())

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            label="Themes (n ≥ 5)" if is_theme_only else "Combinations (n ≥ 5)",
            value=f"{len(opp_df)}",
            help="Number of distinct themes meeting the 5-mention threshold" if is_theme_only else "Number of distinct (theme, cause) pairs meeting the 5-mention threshold",
        )
    with kpi2:
        top_score_theme = (
            f"{top_score_row['theme']} (symptom)"
            if top_score_row["theme"] == "Support not solving"
            else top_score_row["theme"]
        )
        st.metric(
            label="Top Priority Opportunity",
            value=f"{top_score_row['priority_score']:.1f}",
            delta=top_score_theme[:24] + "...",
            help=top_score_theme if is_theme_only else f"{top_score_theme} ({top_score_row.get('cause', '')})",
        )
    with kpi3:
        top_vol_theme = (
            f"{top_volume_row['theme']} (symptom)"
            if top_volume_row["theme"] == "Support not solving"
            else top_volume_row["theme"]
        )
        st.metric(
            label="Top Volume Opportunity",
            value=f"{top_volume_row['mentions']} reviews",
            delta=top_vol_theme[:24] + "...",
            help=top_vol_theme if is_theme_only else f"{top_vol_theme} ({top_volume_row.get('cause', '')})",
        )
    with kpi4:
        st.metric(
            label="Money-Flagged Themes",
            value=f"{money_flag_count} / {len(opp_df)}",
            help="Opportunities carrying the direct monetary risk 2x multiplier",
        )

    st.markdown("---")

    # 6. Interactive Opportunity Table
    st.subheader(f"Priority Table ({current_period})")

    # Format dataframe for display
    display_df = opp_df.copy()

    # Precompute majority scope if not already present
    if "scope" not in display_df.columns:
        scope_lookup = {}
        rel_reviews = filtered_df[filtered_df["relevant_final"] == "Yes"]
        for (t, c), grp in rel_reviews.groupby(["theme", "cause"]):
            norm_scopes = grp["scope"].apply(
                lambda s: "Entry" if isinstance(s, str) and "Entry" in s else "Continuation"
            )
            counts = norm_scopes.value_counts()
            scope_lookup[(t, c)] = counts.idxmax() if not counts.empty else "Continuation"
        display_df["scope"] = display_df.apply(
            lambda r: scope_lookup.get((r["theme"], r["cause"]), "Continuation"), axis=1
        )

    display_df["theme"] = display_df["theme"].apply(
        lambda t: f"{t} (symptom)" if t == "Support not solving" else t
    )
    display_df["money_display"] = display_df["money_flag"].apply(
        lambda f: "💰 Yes (2x)" if f == 1 else "No (1x)"
    )

    if is_theme_only:
        table_columns = [
            "theme",
            "scope",
            "causes",
            "mentions",
            "share_of_relevant_pct",
            "n_outcome_known",
            "lost_rate_among_known",
            "money_display",
            "priority_score",
        ]
        col_cfg = {
            "theme": st.column_config.TextColumn("Theme", width="medium"),
            "scope": st.column_config.TextColumn("Scope", width="small"),
            "causes": st.column_config.TextColumn("Causes", width="medium"),
            "mentions": st.column_config.NumberColumn("Mentions", format="%d"),
            "share_of_relevant_pct": st.column_config.NumberColumn("Share (%)", format="%.1f%%"),
            "n_outcome_known": st.column_config.NumberColumn("Stated Outcomes (n)", format="%d"),
            "lost_rate_among_known": st.column_config.NumberColumn("Lost Rate", format="%.2f"),
            "money_display": st.column_config.TextColumn("Money Flag", width="small"),
            "priority_score": st.column_config.NumberColumn("Priority Score", format="%.1f"),
        }
    else:
        table_columns = [
            "theme",
            "scope",
            "cause",
            "mentions",
            "share_of_relevant_pct",
            "n_outcome_known",
            "lost_rate_among_known",
            "money_display",
            "priority_score",
        ]
        col_cfg = {
            "theme": st.column_config.TextColumn("Theme", width="medium"),
            "scope": st.column_config.TextColumn("Scope", width="small"),
            "cause": st.column_config.TextColumn("Cause", width="small"),
            "mentions": st.column_config.NumberColumn("Mentions", format="%d"),
            "share_of_relevant_pct": st.column_config.NumberColumn("Share (%)", format="%.1f%%"),
            "n_outcome_known": st.column_config.NumberColumn("Stated Outcomes (n)", format="%d"),
            "lost_rate_among_known": st.column_config.NumberColumn("Lost Rate", format="%.2f"),
            "money_display": st.column_config.TextColumn("Money Flag", width="small"),
            "priority_score": st.column_config.NumberColumn("Priority Score", format="%.1f"),
        }

    st.dataframe(
        display_df[table_columns],
        column_config=col_cfg,
        use_container_width=True,
        hide_index=True,
    )

    # 7. Drill down into Evidence
    st.markdown("---")
    st.subheader("Explore Opportunity Evidence")
    st.caption("Inspect verbatim user quotes and stated outcomes in the Evidence Browser for any opportunity.")

    d_col1, d_col2 = st.columns([3, 1])
    with d_col1:
        if is_theme_only:
            opp_labels = [
                f"{row['theme'] + (' (symptom)' if row['theme'] == 'Support not solving' else '')} — Score: {row['priority_score']:.1f} · {row['mentions']} reviews"
                for _, row in opp_df.iterrows()
            ]
        else:
            opp_labels = [
                f"{row['theme'] + (' (symptom)' if row['theme'] == 'Support not solving' else '')} ({row['cause']}) — Score: {row['priority_score']:.1f} · {row['mentions']} reviews"
                for _, row in opp_df.iterrows()
            ]
        selected_idx = st.selectbox(
            "Select Opportunity to inspect:",
            range(len(opp_labels)),
            format_func=lambda i: opp_labels[i],
            key="opp_inspect_select",
        )
    with d_col2:
        st.write("")
        st.write("")
        selected_row = opp_df.iloc[selected_idx]
        selected_cause = None if is_theme_only else selected_row["cause"]
        if st.button(
            "🔍 See these reviews",
            type="primary",
            use_container_width=True,
            on_click=_go_to_evidence,
            args=(selected_row["theme"], selected_cause),
        ):
            st.rerun()
