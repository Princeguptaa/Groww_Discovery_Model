"""
Themes screen view module for Groww SIP Discovery Engine.
Displays:
1. Horizontal bar chart of themes with toggles for cause type and source
2. Sample sizes (n) on all bars and cards, with 'small sample, pattern only' for n < 30
3. Hypotheses A to E breakdown explicitly labelled 'directional'
4. Break-type split for Payment failure / Chose to stop / Temporary break (excluding 'Not stated')
5. 'Wishes' section: feature requests split by period with context note
"""

import streamlit as st
import plotly.graph_objects as go
from lib.data_loader import load_reviews
from lib.compute import (
    apply_period_filter,
    compute_theme_breakdown,
    compute_theme_grouped,
    compute_hypothesis_breakdown,
    compute_break_type_breakdown,
    compute_wishes,
)
from lib.constants import (
    PERIOD_ALL,
    PERIOD_AFTER,
    HYPOTHESIS_NOTE,
    PALETTE_IBM,
    PALETTE_WONG,
)


def render_themes():
    st.title("SIP Discontinuation Themes")
    st.caption(
        "Voice-of-customer breakdown of specific friction points, underlying causes, "
        "and stated investor intentions."
    )

    # 1. Load data
    df = load_reviews()
    period_selection = st.session_state.get("period_filter", PERIOD_ALL)
    df_filtered = apply_period_filter(df, period_selection)

    # Small-sample warning for After 25 Dec 2024 (Spec §6)
    if period_selection == PERIOD_AFTER:
        n_after = int((df_filtered["relevant_final"] == "Yes").sum())
        st.warning(f"After 25 Dec 2024 (n = {n_after}). Small sample, patterns only.")

    # 2. Themes Bar Chart Section (Spec §7.2)
    st.subheader(f"Theme Frequency ({period_selection})")
    st.caption("Distribution of confirmed SIP continuation problems (relevant_final = Yes).")

    # Toggles for cause type and source
    breakdown_toggle = st.radio(
        "Breakdown View",
        options=["Overall by Theme", "Grouped by Cause Type", "Grouped by Source"],
        horizontal=True,
    )

    theme_df = compute_theme_breakdown(df_filtered)

    if len(theme_df) == 0:
        st.info("No relevant reviews found for the selected period filter.")
    else:
        if breakdown_toggle == "Overall by Theme":
            # Sort ascending so highest appears on top with reversed y-axis
            sorted_themes = theme_df.sort_values("count", ascending=True)

            fig = go.Figure(
                go.Bar(
                    x=sorted_themes["count"],
                    y=sorted_themes["theme"],
                    orientation="h",
                    marker=dict(color=PALETTE_IBM[0]),
                    text=sorted_themes["label_text"],
                    textposition="auto",
                    hoverinfo="x+y",
                )
            )
            chart_height = max(420, len(sorted_themes) * 28)
            fig.update_layout(
                title=dict(
                    text=f"Themes Ranked by Frequency ({period_selection})",
                    font=dict(size=15),
                ),
                xaxis=dict(title="Review Mentions"),
                yaxis=dict(autorange="reversed"),
                height=chart_height,
                margin=dict(l=10, r=20, t=40, b=30),
            )
            st.plotly_chart(fig, use_container_width=True)

        elif breakdown_toggle == "Grouped by Cause Type":
            grouped_cause = compute_theme_grouped(df_filtered, "cause")
            distinct_causes = sorted(grouped_cause["cause"].unique())
            # Rank themes by total count across causes
            theme_order = (
                grouped_cause.groupby("theme")["count"]
                .sum()
                .sort_values(ascending=False)
                .index.tolist()
            )

            fig = go.Figure()
            for idx, cause in enumerate(distinct_causes):
                cause_subset = grouped_cause[grouped_cause["cause"] == cause]
                # Align counts with theme_order
                count_map = dict(zip(cause_subset["theme"], cause_subset["count"]))
                counts = [count_map.get(t, 0) for t in theme_order]
                text_labels = [
                    f"{c} (n={c}) · small sample, pattern only" if (0 < c < 30)
                    else (f"{c} (n={c})" if c > 0 else "")
                    for c in counts
                ]

                color = PALETTE_WONG[idx % len(PALETTE_WONG)]
                fig.add_trace(
                    go.Bar(
                        name=cause,
                        x=counts,
                        y=theme_order,
                        orientation="h",
                        marker=dict(color=color),
                        text=text_labels,
                        textposition="auto",
                        hoverinfo="name+x+y",
                    )
                )

            chart_height = max(480, len(theme_order) * 32)
            fig.update_layout(
                barmode="stack",
                title=dict(
                    text=f"Theme Frequency Stacked by Cause Type ({period_selection})",
                    font=dict(size=15),
                ),
                xaxis=dict(title="Review Mentions"),
                yaxis=dict(autorange="reversed"),
                height=chart_height,
                margin=dict(l=10, r=20, t=40, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

        else:  # Grouped by Source
            grouped_source = compute_theme_grouped(df_filtered, "source")
            distinct_sources = sorted(grouped_source["source"].unique())
            theme_order = (
                grouped_source.groupby("theme")["count"]
                .sum()
                .sort_values(ascending=False)
                .index.tolist()
            )

            fig = go.Figure()
            for idx, source in enumerate(distinct_sources):
                src_subset = grouped_source[grouped_source["source"] == source]
                count_map = dict(zip(src_subset["theme"], src_subset["count"]))
                counts = [count_map.get(t, 0) for t in theme_order]
                text_labels = [
                    f"{c} (n={c}) · small sample, pattern only" if (0 < c < 30)
                    else (f"{c} (n={c})" if c > 0 else "")
                    for c in counts
                ]

                color = PALETTE_IBM[idx % len(PALETTE_IBM)]
                fig.add_trace(
                    go.Bar(
                        name=source,
                        x=counts,
                        y=theme_order,
                        orientation="h",
                        marker=dict(color=color),
                        text=text_labels,
                        textposition="auto",
                        hoverinfo="name+x+y",
                    )
                )

            chart_height = max(450, len(theme_order) * 30)
            fig.update_layout(
                barmode="stack",
                title=dict(
                    text=f"Theme Frequency by Source ({period_selection})",
                    font=dict(size=15),
                ),
                xaxis=dict(title="Review Mentions"),
                yaxis=dict(autorange="reversed"),
                height=chart_height,
                margin=dict(l=10, r=20, t=40, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 3. Hypothesis Distribution Section (Spec §7.2)
    st.subheader(f"Hypothesis Distribution ({period_selection})")
    st.caption(f"**Notice:** {HYPOTHESIS_NOTE}")

    hypotheses = compute_hypothesis_breakdown(df_filtered)
    hyp_cols = st.columns(len(hypotheses))

    for idx, hyp in enumerate(hypotheses):
        with hyp_cols[idx]:
            sample_tag = (
                '<span style="background: #FEE2E2; color: #991B1B; padding: 2px 4px; border-radius: 4px; font-size: 10px;">small sample</span>'
                if hyp["is_small_sample"]
                else ""
            )
            st.markdown(
                f"""
                <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; background-color: #F8FAFC; min-height: 150px;">
                    <div style="font-size: 11px; font-weight: 700; color: #0284C7; text-transform: uppercase;">
                        Directional Label
                    </div>
                    <div style="font-size: 14px; font-weight: 700; color: #0F172A; margin: 4px 0;">
                        {hyp['hypothesis']}
                    </div>
                    <div style="font-size: 20px; font-weight: 700; color: #1E293B;">
                        {hyp['count']:,}
                    </div>
                    <div style="font-size: 12px; color: #64748B;">
                        {hyp['pct']}% of relevant (n = {hyp['n']}) {sample_tag}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # 4. Break-Type Split Section (Spec §7.2, excluding 'Not stated')
    st.subheader(f"Break-Type Distribution ({period_selection})")
    break_types = compute_break_type_breakdown(df_filtered)
    st.caption(
        f"Stated reason for SIP interruption among relevant reviews. "
        f"Excludes {break_types['not_stated_count']:,} reviews where break type is 'Not stated'."
    )

    bt_cols = st.columns(len(break_types["items"]))
    for idx, item in enumerate(break_types["items"]):
        with bt_cols[idx]:
            sample_badge = (
                '<div style="font-size: 11px; color: #B91C1C; margin-top: 4px;">small sample, pattern only</div>'
                if item["is_small_sample"]
                else ""
            )
            st.markdown(
                f"""
                <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 14px; background-color: #F8FAFC; min-height: 130px;">
                    <div style="font-size: 12px; font-weight: 600; color: #475569; text-transform: uppercase;">
                        Stated Break Type
                    </div>
                    <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">
                        {item['break_type']}
                    </div>
                    <div style="font-size: 22px; font-weight: 700; color: #2563EB;">
                        {item['count']:,}
                    </div>
                    <div style="font-size: 12px; color: #64748B;">
                        {item['pct']}% of stated breaks (n = {item['n']})
                    </div>
                    {sample_badge}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # 5. Wishes: Feature Requests Section (Spec §7.2)
    st.subheader("Wishes: Feature Requests")
    st.caption(
        "User requests for additional investment capabilities and tools (issue = Feature request). "
        "Separated from SIP continuation friction."
    )

    wishes = compute_wishes(df)

    w_col1, w_col2, w_col3 = st.columns(3)
    with w_col1:
        st.metric(
            label="Total Feature Requests",
            value=f"{wishes['total']:,}",
            help="Total feature requests in corpus (319 rows)",
        )
    with w_col2:
        st.metric(
            label="Before 25 Dec 2024",
            value=f"{wishes['before_count']:,}",
            delta=f"{wishes['before_pct']}% of wishes",
        )
    with w_col3:
        st.metric(
            label="After 25 Dec 2024",
            value=f"{wishes['after_count']:,}",
            delta=f"{wishes['after_pct']}% of wishes",
        )

    st.info(
        "**Context:** Most 'stock SIP' requests came before Groww launched stock SIP in Dec 2024; "
        "weekly/daily MF SIP requests continue."
    )
