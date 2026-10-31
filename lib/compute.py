"""
Computation module for Groww SIP Discovery Engine.

All derived counts, aggregations, funnel metrics, and headline findings
are computed dynamically from loaded data assets.
No reference numbers are hardcoded here.
"""

from typing import Dict, Any, List
import re
import pandas as pd
from lib.constants import (
    PERIOD_ALL,
    PERIOD_BEFORE,
    PERIOD_AFTER,
    LOST_OUTCOMES,
    MONEY_FLAG_THEMES,
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
            "source": "Play Store reviews pulled",
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


def compute_opportunity_table(
    df_filtered: pd.DataFrame,
    sort_by: str = "priority_score",
    group_by: str = "Theme only",
) -> pd.DataFrame:
    """
    Compute Opportunity priority table at runtime from period-filtered reviews (Spec §7.4).
    
    Formula:
      - Filter to relevant_final == 'Yes' in the active period slice.
      - If group_by == 'Theme only':
          Group by theme.
          scope = majority scope of the group.
          causes = cause count split string (e.g. 'Product side 91, Money side 27').
          priority_score = mentions * (1 + lost_rate_rounded) * (1 + money_flag), rounded to 1 decimal.
      - If group_by == 'Theme and cause':
          Group by (theme, cause).
          priority_score = mentions * (1 + lost_rate_raw) * (1 + money_flag), rounded to 1 decimal.
      - Exclude groups with mentions < 5.
      - share_of_relevant_pct = (mentions / total_relevant) * 100, rounded to 1 decimal.
      - n_outcome_known = count of rows where outcome_final != 'Unknown'.
      - lost_rate_among_known = (lost_count / n_outcome_known), set to 0.0 if n_outcome_known < 5,
        rounded to 2 decimals.
      - money_flag = 1 if theme in MONEY_FLAG_THEMES else 0.
      
    Args:
      df_filtered: Dataframe filtered by active period.
      sort_by: Column to sort descending by ('priority_score' or 'mentions').
      group_by: Grouping dimension ('Theme only' or 'Theme and cause').
      
    Returns:
      pd.DataFrame with columns:
        For 'Theme only': theme, scope, causes, mentions, share_of_relevant_pct,
          n_outcome_known, lost_rate_among_known, money_flag, priority_score
        For 'Theme and cause': theme, cause, mentions, share_of_relevant_pct,
          n_outcome_known, lost_rate_among_known, money_flag, priority_score
    """
    is_theme_only = str(group_by).strip().lower() in ["theme only", "theme", "theme_only"]

    rel_df = df_filtered[df_filtered["relevant_final"] == "Yes"]
    total_rel = len(rel_df)

    if total_rel == 0:
        if is_theme_only:
            return pd.DataFrame(
                columns=[
                    "theme",
                    "scope",
                    "causes",
                    "Causes",
                    "mentions",
                    "share_of_relevant_pct",
                    "n_outcome_known",
                    "lost_rate_among_known",
                    "money_flag",
                    "priority_score",
                ]
            )
        else:
            return pd.DataFrame(
                columns=[
                    "theme",
                    "cause",
                    "mentions",
                    "share_of_relevant_pct",
                    "n_outcome_known",
                    "lost_rate_among_known",
                    "money_flag",
                    "priority_score",
                ]
            )

    rows = []
    if is_theme_only:
        for theme, group in rel_df.groupby("theme"):
            mentions = len(group)
            if mentions < 5:
                continue

            share_pct = (mentions / total_rel) * 100
            known = group[group["outcome_final"] != "Unknown"]
            n_known = len(known)

            if n_known < 5:
                lost_rate_rounded = 0.0
            else:
                lost_count = int(known["outcome_final"].isin(LOST_OUTCOMES).sum())
                lost_rate_rounded = round(lost_count / n_known, 2)

            money_flag = 1 if theme in MONEY_FLAG_THEMES else 0
            priority_score_raw = mentions * (1 + lost_rate_rounded) * (1 + money_flag)

            # Majority scope of the group
            norm_scopes = group["scope"].apply(
                lambda s: "Entry" if isinstance(s, str) and "Entry" in s else "Continuation"
            )
            scope_counts = norm_scopes.value_counts()
            majority_scope = scope_counts.idxmax() if not scope_counts.empty else "Continuation"

            # Causes split
            cause_counts = group["cause"].value_counts()
            causes_str = ", ".join([f"{c} {cnt}" for c, cnt in cause_counts.items()])

            rows.append(
                {
                    "theme": theme,
                    "scope": majority_scope,
                    "causes": causes_str,
                    "Causes": causes_str,
                    "mentions": mentions,
                    "share_of_relevant_pct": round(share_pct, 1),
                    "n_outcome_known": n_known,
                    "lost_rate_among_known": lost_rate_rounded,
                    "money_flag": money_flag,
                    "priority_score": round(priority_score_raw, 1),
                }
            )
    else:
        for (theme, cause), group in rel_df.groupby(["theme", "cause"]):
            mentions = len(group)
            if mentions < 5:
                continue

            share_pct = (mentions / total_rel) * 100
            known = group[group["outcome_final"] != "Unknown"]
            n_known = len(known)

            if n_known < 5:
                lost_rate_raw = 0.0
                lost_rate_rounded = 0.0
            else:
                lost_count = int(known["outcome_final"].isin(LOST_OUTCOMES).sum())
                lost_rate_raw = lost_count / n_known
                lost_rate_rounded = round(lost_rate_raw, 2)

            money_flag = 1 if theme in MONEY_FLAG_THEMES else 0
            priority_score_raw = mentions * (1 + lost_rate_raw) * (1 + money_flag)

            rows.append(
                {
                    "theme": theme,
                    "cause": cause,
                    "mentions": mentions,
                    "share_of_relevant_pct": round(share_pct, 1),
                    "n_outcome_known": n_known,
                    "lost_rate_among_known": lost_rate_rounded,
                    "money_flag": money_flag,
                    "priority_score": round(priority_score_raw, 1),
                }
            )

    result_df = pd.DataFrame(rows)
    if len(result_df) == 0:
        return result_df

    if sort_by == "mentions":
        result_df = result_df.sort_values(
            by=["mentions", "priority_score"], ascending=[False, False]
        ).reset_index(drop=True)
    else:
        result_df = result_df.sort_values(
            by=["priority_score", "mentions"], ascending=[False, False]
        ).reset_index(drop=True)

    return result_df


def compute_stats_for_ask(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute structured stats from the review corpus for Ask the Data screen.
    Guarantees all counts and percentages match other screens without typed numbers.
    """
    rel_df = df[df["relevant_final"] == "Yes"]
    n_relevant = len(rel_df)
    wishes_df = df[df["issue"] == "Feature request"]
    wishes_total = len(wishes_df)

    theme_counts = rel_df["theme"].value_counts().to_dict()
    pay_fail_count = int(theme_counts.get("Payment failed or missed", 0))
    support_count = int(theme_counts.get("Support not solving", 0))
    cannot_edit_count = int(theme_counts.get("Cannot edit or pause or stop", 0))
    setup_count = int(theme_counts.get("Cannot start or set up SIP", 0))

    before_df = rel_df[rel_df["period"] == PERIOD_BEFORE]
    after_df = rel_df[rel_df["period"] == PERIOD_AFTER]
    before_rel_count = len(before_df)
    after_rel_count = len(after_df)

    before_pay_fail_count = int((before_df["theme"] == "Payment failed or missed").sum())
    before_pay_fail_pct = (
        round((before_pay_fail_count / before_rel_count) * 100, 1)
        if before_rel_count > 0
        else 0.0
    )
    after_cannot_edit_count = int((after_df["theme"] == "Cannot edit or pause or stop").sum())

    stated_outcomes = rel_df[rel_df["outcome_final"] != "Unknown"]
    n_outcome_stated = len(stated_outcomes)
    lost_mask = stated_outcomes["outcome_final"].isin(LOST_OUTCOMES)
    lost_count = int(lost_mask.sum())

    controls_series = rel_df["controls_mentioned"].dropna()
    controls = {
        "Pause": int(controls_series.str.contains("Pause").sum()),
        "Edit date or amount": int(controls_series.str.contains("Edit").sum()),
        "Skip": int(controls_series.str.contains("Skip").sum()),
    }

    money_delay_count = int(theme_counts.get("Processing or unit allocation delay", 0))
    money_debited_cancel_count = int(theme_counts.get("Debited after cancel or wrong amount", 0))

    pay_fail_ids = rel_df[rel_df["theme"] == "Payment failed or missed"]["evidence_id"].tolist()[:2]
    support_ids = rel_df[rel_df["theme"] == "Support not solving"]["evidence_id"].tolist()[:2]
    cannot_edit_ids = rel_df[rel_df["theme"] == "Cannot edit or pause or stop"]["evidence_id"].tolist()[:2]
    money_delay_ids = rel_df[rel_df["theme"] == "Processing or unit allocation delay"]["evidence_id"].tolist()[:2]
    money_debited_cancel_ids = rel_df[rel_df["theme"] == "Debited after cancel or wrong amount"]["evidence_id"].tolist()[:2]
    before_pay_fail_ids = rel_df[
        (rel_df["period"] == PERIOD_BEFORE) & (rel_df["theme"] == "Payment failed or missed")
    ]["evidence_id"].tolist()[:2]
    after_cannot_edit_ids = rel_df[
        (rel_df["period"] == PERIOD_AFTER) & (rel_df["theme"] == "Cannot edit or pause or stop")
    ]["evidence_id"].tolist()[:2]

    return {
        "n_relevant": n_relevant,
        "wishes_total": wishes_total,
        "theme_counts": theme_counts,
        "pay_fail_count": pay_fail_count,
        "support_count": support_count,
        "cannot_edit_count": cannot_edit_count,
        "setup_count": setup_count,
        "before_rel_count": before_rel_count,
        "after_rel_count": after_rel_count,
        "before_pay_fail_count": before_pay_fail_count,
        "before_pay_fail_pct": before_pay_fail_pct,
        "after_cannot_edit_count": after_cannot_edit_count,
        "n_outcome_stated": n_outcome_stated,
        "lost_count": lost_count,
        "controls": controls,
        "money_delay_count": money_delay_count,
        "money_debited_cancel_count": money_debited_cancel_count,
        "pay_fail_ids": pay_fail_ids,
        "support_ids": support_ids,
        "cannot_edit_ids": cannot_edit_ids,
        "money_delay_ids": money_delay_ids,
        "money_debited_cancel_ids": money_debited_cancel_ids,
        "before_pay_fail_ids": before_pay_fail_ids,
        "after_cannot_edit_ids": after_cannot_edit_ids,
        "period_dist": rel_df["period"].value_counts().to_dict(),
        "break_types": rel_df["break_type"].value_counts().to_dict(),
        "outcomes": rel_df["outcome_final"].value_counts().to_dict(),
        "hypotheses": rel_df["hypothesis_final"].value_counts().to_dict(),
    }


def filter_reviews_by_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Filter reviews by search query.
    - If query is empty or whitespace, returns df unchanged.
    - If query matches an evidence_id exactly (e.g. E0106, case-insensitive), returns that row.
    - If several words, ALL words must appear in review text (case-insensitive).
    """
    if not query or not str(query).strip():
        return df

    q = str(query).strip()

    # Exact typed evidence_id match (e.g. E0106)
    if re.match(r"^E\d{4}$", q, re.IGNORECASE):
        return df[df["evidence_id"].str.upper() == q.upper()]

    # Several words: ALL words must appear in review text (case-insensitive)
    words = [w.lower() for w in q.split() if w]
    if not words:
        return df

    def _matches_all(text: Any) -> bool:
        t = str(text).lower()
        return all(w in t for w in words)

    return df[df["text"].apply(_matches_all)]



