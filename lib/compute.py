"""
Computation module for Groww SIP Discovery Engine.

All derived counts, aggregations, funnel metrics, and headline findings
are computed dynamically from loaded data assets.
No reference numbers are hardcoded here.
"""

from typing import Dict, Any, List
import pandas as pd
from lib.constants import (
    PERIOD_ALL,
    PERIOD_BEFORE,
    PERIOD_AFTER,
    LOST_OUTCOMES,
)


def apply_period_filter(df: pd.DataFrame, period_selection: str) -> pd.DataFrame:
    """
    Apply global period filter to the dataframe.
    
    Supports:
      - 'All' -> complete dataframe
      - 'Before 25 Dec 2024' -> rows where period == 'Before 25 Dec 2024'
      - 'After 25 Dec 2024' -> rows where period == 'After 25 Dec 2024'
    """
    if period_selection == PERIOD_BEFORE:
        return df[df["period"] == PERIOD_BEFORE].copy()
    elif period_selection == PERIOD_AFTER:
        return df[df["period"] == PERIOD_AFTER].copy()
    return df.copy()


def compute_funnel(df: pd.DataFrame, funnel_inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compute the 6-step discovery funnel from funnel_inputs and labelled_reviews.csv.
    
    CRITICAL RULE (Spec §7.1, Implementation Plan):
    The funnel ALWAYS displays all periods and is explicitly labelled "all periods".
    It is never filtered by the active period filter.
    
    The 6 steps are:
      1. Reviews pulled (upstream JSON)
      2. Keyword matches (upstream JSON)
      3. Unique SIP-word reviews (upstream JSON)
      4. Labelled (relevant != "")
      5. Relevant (relevant_final == "Yes")
      6. Relevant with stated outcome (relevant_final == "Yes" & outcome_final != "Unknown")
      
    Strictly omits any "trouble" step.
    """
    steps = [
        {
            "step_id": 1,
            "name": "Reviews pulled",
            "count": int(funnel_inputs.get("reviews_pulled", 0)),
            "source": "App Store extraction",
        },
        {
            "step_id": 2,
            "name": "Keyword matches",
            "count": int(funnel_inputs.get("keyword_matched", 0)),
            "source": "SIP keyword filter",
        },
        {
            "step_id": 3,
            "name": "Unique SIP-word reviews",
            "count": int(funnel_inputs.get("sip_word_unique", 0)),
            "source": "Deduplicated SIP corpus",
        },
        {
            "step_id": 4,
            "name": "Labelled",
            "count": int((df["relevant"] != "").sum()),
            "source": "AI classification pass",
        },
        {
            "step_id": 5,
            "name": "Relevant",
            "count": int((df["relevant_final"] == "Yes").sum()),
            "source": "SIP continuation events",
        },
        {
            "step_id": 6,
            "name": "Relevant with stated outcome",
            "count": int(((df["relevant_final"] == "Yes") & (df["outcome_final"] != "Unknown")).sum()),
            "source": "Stated continuation outcomes",
        },
    ]

    # Calculate step-over-step retention / conversion %
    prev_count = None
    for step in steps:
        if prev_count is not None and prev_count > 0:
            step["pct_of_prev"] = round((step["count"] / prev_count) * 100, 1)
        else:
            step["pct_of_prev"] = 100.0
        prev_count = step["count"]

    return steps


def compute_headline_findings(df_filtered: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute the 3 headline findings from the active period-filtered dataframe (Spec §7.1).
    
    Uses only rows where relevant_final == 'Yes'.
    
    Headline 1: Top theme, EXCLUDING "Support not solving".
                Mention "Support not solving" separately as an amplifier with its count.
    Headline 2: Top cause type with its count and percentage.
    Headline 3: Lost rate = reviews with outcome in {Stopped or cancelled, Switched away,
                Stalled not by choice} divided by reviews with outcome_final != "Unknown".
    
    Each headline returns its sample size n.
    """
    rel_df = df_filtered[df_filtered["relevant_final"] == "Yes"]
    n_relevant = len(rel_df)

    if n_relevant == 0:
        return {
            "n_relevant": 0,
            "top_theme": {"theme": "None", "count": 0, "pct": 0.0, "n": 0},
            "support_amplifier": {"count": 0, "pct": 0.0, "n": 0},
            "top_cause": {"cause": "None", "count": 0, "pct": 0.0, "n": 0},
            "lost_rate": {
                "lost_count": 0,
                "n_outcome_stated": 0,
                "rate_pct": 0.0,
                "n": 0,
            },
        }

    # 1. Top theme excluding "Support not solving"
    support_mask = rel_df["theme"] == "Support not solving"
    support_count = int(support_mask.sum())
    support_pct = round((support_count / n_relevant) * 100, 1) if n_relevant > 0 else 0.0

    non_support_df = rel_df[~support_mask]
    if len(non_support_df) > 0:
        theme_counts = non_support_df["theme"].value_counts()
        top_theme_name = str(theme_counts.index[0])
        top_theme_count = int(theme_counts.iloc[0])
        top_theme_pct = round((top_theme_count / n_relevant) * 100, 1)
    else:
        top_theme_name = "None"
        top_theme_count = 0
        top_theme_pct = 0.0

    # 2. Top cause type
    cause_counts = rel_df["cause"].value_counts()
    if len(cause_counts) > 0:
        top_cause_name = str(cause_counts.index[0])
        top_cause_count = int(cause_counts.iloc[0])
        top_cause_pct = round((top_cause_count / n_relevant) * 100, 1)
    else:
        top_cause_name = "None"
        top_cause_count = 0
        top_cause_pct = 0.0

    # 3. Lost rate among known outcomes
    stated_outcomes = rel_df[rel_df["outcome_final"] != "Unknown"]
    n_outcome_stated = len(stated_outcomes)
    lost_mask = stated_outcomes["outcome_final"].isin(LOST_OUTCOMES)
    lost_count = int(lost_mask.sum())
    lost_rate_pct = (
        round((lost_count / n_outcome_stated) * 100, 1) if n_outcome_stated > 0 else 0.0
    )

    return {
        "n_relevant": n_relevant,
        "top_theme": {
            "theme": top_theme_name,
            "count": top_theme_count,
            "pct": top_theme_pct,
            "n": n_relevant,
        },
        "support_amplifier": {
            "count": support_count,
            "pct": support_pct,
            "n": n_relevant,
        },
        "top_cause": {
            "cause": top_cause_name,
            "count": top_cause_count,
            "pct": top_cause_pct,
            "n": n_relevant,
        },
        "lost_rate": {
            "lost_count": lost_count,
            "n_outcome_stated": n_outcome_stated,
            "rate_pct": lost_rate_pct,
            "n": n_outcome_stated,
        },
    }
