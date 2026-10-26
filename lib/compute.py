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

    # 1. Top Continuation theme excluding "Support not solving", with Entry scope and Support amplifier
    entry_mask = rel_df["scope"] == "Entry (before a SIP is running)"
    entry_count = int(entry_mask.sum())
    entry_pct = round((entry_count / n_relevant) * 100, 1) if n_relevant > 0 else 0.0

    cont_mask = rel_df["scope"] == "Continuation"
    cont_df = rel_df[cont_mask]
    n_continuation = len(cont_df)

    support_mask = rel_df["theme"] == "Support not solving"
    support_count = int(support_mask.sum())
    support_pct = round((support_count / n_relevant) * 100, 1) if n_relevant > 0 else 0.0

    cont_non_support = cont_df[cont_df["theme"] != "Support not solving"]
    if len(cont_non_support) > 0:
        theme_counts = cont_non_support["theme"].value_counts()
        top_theme_name = str(theme_counts.index[0])
        top_theme_count = int(theme_counts.iloc[0])
        top_theme_pct = (
            round((top_theme_count / n_continuation) * 100, 1) if n_continuation > 0 else 0.0
        )
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
        "n_continuation": n_continuation,
        "top_theme": {
            "theme": top_theme_name,
            "count": top_theme_count,
            "pct": top_theme_pct,
            "n": n_continuation,
        },
        "entry_scope": {
            "count": entry_count,
            "pct": entry_pct,
            "n": entry_count,
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



def compute_theme_breakdown(df_filtered: pd.DataFrame) -> pd.DataFrame:
    """
    Compute theme counts and shares for relevant reviews (relevant_final == 'Yes').
    
    Includes sample size n and a small sample flag (n < 30).
    """
    rel_df = df_filtered[df_filtered["relevant_final"] == "Yes"]
    n_relevant = len(rel_df)

    if n_relevant == 0:
        return pd.DataFrame(
            columns=["theme", "count", "pct_of_relevant", "n", "is_small_sample", "label_text"]
        )

    theme_counts = rel_df["theme"].value_counts().reset_index()
    theme_counts.columns = ["theme", "count"]
    theme_counts["pct_of_relevant"] = (
        (theme_counts["count"] / n_relevant) * 100
    ).round(1)
    theme_counts["n"] = theme_counts["count"]
    theme_counts["is_small_sample"] = theme_counts["n"] < 30
    theme_counts["label_text"] = theme_counts.apply(
        lambda row: f"{row['count']:,} (n={row['n']}) · small sample, pattern only"
        if row["is_small_sample"]
        else f"{row['count']:,} (n={row['n']})",
        axis=1,
    )

    return theme_counts


def compute_theme_grouped(
    df_filtered: pd.DataFrame, group_col: str
) -> pd.DataFrame:
    """
    Compute theme breakdown cross-tabulated by another dimension (e.g. 'cause' or 'source').
    Only considers relevant_final == 'Yes'.
    """
    rel_df = df_filtered[df_filtered["relevant_final"] == "Yes"]
    if len(rel_df) == 0:
        return pd.DataFrame(columns=["theme", group_col, "count", "n", "is_small_sample", "label_text"])

    grouped = (
        rel_df.groupby(["theme", group_col])
        .size()
        .reset_index(name="count")
    )
    grouped["n"] = grouped["count"]
    grouped["is_small_sample"] = grouped["n"] < 30
    grouped["label_text"] = grouped.apply(
        lambda row: f"{row['count']:,} (n={row['n']}) · small sample, pattern only"
        if row["is_small_sample"]
        else f"{row['count']:,} (n={row['n']})",
        axis=1,
    )
    return grouped


def compute_hypothesis_breakdown(df_filtered: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Compute hypothesis distribution for relevant reviews (relevant_final == 'Yes').
    Hypotheses are unverified AI-assigned labels and must be labelled 'directional'.
    """
    rel_df = df_filtered[df_filtered["relevant_final"] == "Yes"]
    n_relevant = len(rel_df)

    counts = rel_df["hypothesis_final"].value_counts().to_dict()
    
    # Standard ordering for Hypotheses A to E and None
    hypothesis_keys = [
        "A controls not found",
        "B failed payment no recovery",
        "C amount does not fit money",
        "D chose to stop for other reasons",
        "E setup or autopay blocked",
        "None",
    ]

    results = []
    for hyp in hypothesis_keys:
        cnt = int(counts.get(hyp, 0))
        pct = round((cnt / n_relevant) * 100, 1) if n_relevant > 0 else 0.0
        results.append(
            {
                "hypothesis": hyp,
                "count": cnt,
                "pct": pct,
                "n": cnt,
                "is_small_sample": cnt < 30,
            }
        )
    return results


def compute_break_type_breakdown(df_filtered: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute break-type counts from break_type for relevant reviews (relevant_final == 'Yes').
    
    CRITICAL RULE (Spec §7.2):
    Includes: 'Payment failure', 'Chose to stop', 'Temporary break'.
    EXPLICITLY EXCLUDES 'Not stated'.
    """
    rel_df = df_filtered[df_filtered["relevant_final"] == "Yes"]
    
    counts = rel_df["break_type"].value_counts().to_dict()
    not_stated_count = int(counts.get("Not stated", 0))

    allowed_types = ["Payment failure", "Chose to stop", "Temporary break"]
    stated_total = sum(int(counts.get(bt, 0)) for bt in allowed_types)

    breakdowns = []
    for bt in allowed_types:
        cnt = int(counts.get(bt, 0))
        pct = round((cnt / stated_total) * 100, 1) if stated_total > 0 else 0.0
        breakdowns.append(
            {
                "break_type": bt,
                "count": cnt,
                "pct": pct,
                "n": cnt,
                "is_small_sample": cnt < 30,
            }
        )

    return {
        "stated_total": stated_total,
        "not_stated_count": not_stated_count,
        "items": breakdowns,
    }


def compute_wishes(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute Wishes (Feature Requests) volume from issue == 'Feature request'.
    
    CRITICAL RULE (Spec §7.2):
    Split by period: Before 25 Dec 2024 vs After 25 Dec 2024.
    """
    wishes_df = df[df["issue"] == "Feature request"]
    total = len(wishes_df)
    before_count = int((wishes_df["period"] == PERIOD_BEFORE).sum())
    after_count = int((wishes_df["period"] == PERIOD_AFTER).sum())

    before_pct = round((before_count / total) * 100, 1) if total > 0 else 0.0
    after_pct = round((after_count / total) * 100, 1) if total > 0 else 0.0

    return {
        "total": total,
        "before_count": before_count,
        "before_pct": before_pct,
        "after_count": after_count,
        "after_pct": after_pct,
    }

