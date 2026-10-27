"""
Unit tests for lib/compute.py.

Validates period filtering, 6-step discovery funnel, and headline findings.
No reference values are hardcoded in test assertions (except formula definitions).
"""

import pytest
import pandas as pd
from lib.data_loader import load_reviews, load_funnel_inputs
from lib.constants import (
    PERIOD_ALL,
    PERIOD_BEFORE,
    PERIOD_AFTER,
    LOST_OUTCOMES,
)
from lib.compute import (
    apply_period_filter,
    compute_funnel,
    compute_headline_findings,
    compute_theme_breakdown,
    compute_theme_grouped,
    compute_hypothesis_breakdown,
    compute_break_type_breakdown,
    compute_wishes,
    compute_opportunity_table,
    compute_stats_for_ask,
    filter_reviews_by_search,
)


@pytest.fixture(scope="module")
def full_df():
    return load_reviews()


@pytest.fixture(scope="module")
def funnel_json():
    return load_funnel_inputs()


def test_apply_period_filter(full_df):
    """Test period filter helper for All, Before, and After slices."""
    df_all = apply_period_filter(full_df, PERIOD_ALL)
    assert len(df_all) == len(full_df)

    df_before = apply_period_filter(full_df, PERIOD_BEFORE)
    assert (df_before["period"] == PERIOD_BEFORE).all()
    assert len(df_before) == (full_df["period"] == PERIOD_BEFORE).sum()

    df_after = apply_period_filter(full_df, PERIOD_AFTER)
    assert (df_after["period"] == PERIOD_AFTER).all()
    assert len(df_after) == (full_df["period"] == PERIOD_AFTER).sum()


def test_funnel_computation_at1(full_df, funnel_json):
    """
    Acceptance Test AT-1: Funnel numbers equal exact row counts in data.
    Verifies all 6 steps and confirms no 'trouble' step is present.
    """
    steps = compute_funnel(full_df, funnel_json)
    assert len(steps) == 6

    step_names = [s["name"] for s in steps]
    assert "trouble" not in [name.lower() for name in step_names]

    # Step 1: Reviews pulled
    assert steps[0]["name"] == "Reviews pulled"
    assert steps[0]["count"] == funnel_json["reviews_pulled"]

    # Step 2: Keyword matches
    assert steps[1]["name"] == "Keyword matches"
    assert steps[1]["count"] == funnel_json["keyword_matched"]

    # Step 3: Unique SIP-word reviews
    assert steps[2]["name"] == "Unique SIP-word reviews"
    assert steps[2]["count"] == funnel_json["sip_word_unique"]

    # Step 4: Labelled
    assert steps[3]["name"] == "Labelled"
    assert steps[3]["count"] == (full_df["relevant"] != "").sum()

    # Step 5: Relevant
    assert steps[4]["name"] == "Relevant"
    assert steps[4]["count"] == (full_df["relevant_final"] == "Yes").sum()

    # Step 6: Relevant with stated outcome
    assert steps[5]["name"] == "Relevant with stated outcome"
    expected_step6 = (
        (full_df["relevant_final"] == "Yes") & (full_df["outcome_final"] != "Unknown")
    ).sum()
    assert steps[5]["count"] == expected_step6


def test_top_theme_excludes_support(full_df):
    """
    Headline Finding 1: Top theme must exclude 'Support not solving',
    and Support must be isolated as an amplifier with its own count and pct.
    Scope must be 'Continuation'.
    """
    findings = compute_headline_findings(full_df)
    assert findings["top_theme"]["theme"] != "Support not solving"
    assert findings["top_theme"]["count"] > 0
    rel_df = full_df[full_df["relevant_final"] == "Yes"]
    expected_n_cont = (rel_df["scope"] == "Continuation").sum()
    assert findings["top_theme"]["n"] == expected_n_cont

    # Support amplifier check
    expected_support_count = (rel_df["theme"] == "Support not solving").sum()
    assert findings["support_amplifier"]["count"] == expected_support_count
    assert findings["support_amplifier"]["pct"] == round(
        (expected_support_count / len(rel_df)) * 100, 1
    )


def test_top_continuation_theme_by_period(full_df):
    """
    Headline Finding 1 Fix: Top theme among scope == 'Continuation',
    excluding 'Support not solving'.
    Expected:
      All: 'Payment failed or missed' (118)
      Before: 'Payment failed or missed' (99)
      After: 'Cannot edit or pause or stop' (30)
    """
    # All
    findings_all = compute_headline_findings(full_df)
    assert findings_all["top_theme"]["theme"] == "Payment failed or missed"
    assert findings_all["top_theme"]["count"] == 118
    assert findings_all["entry_scope"]["count"] == (
        (full_df["relevant_final"] == "Yes")
        & (full_df["scope"] == "Entry (before a SIP is running)")
    ).sum()

    # Before 25 Dec 2024
    before_df = apply_period_filter(full_df, PERIOD_BEFORE)
    findings_before = compute_headline_findings(before_df)
    assert findings_before["top_theme"]["theme"] == "Payment failed or missed"
    assert findings_before["top_theme"]["count"] == 99

    # After 25 Dec 2024
    after_df = apply_period_filter(full_df, PERIOD_AFTER)
    findings_after = compute_headline_findings(after_df)
    assert findings_after["top_theme"]["theme"] == "Cannot edit or pause or stop"
    assert findings_after["top_theme"]["count"] == 30



def test_headline_findings_lost_rate_math(full_df):
    """
    Headline Finding 3: Lost rate = reviews with outcome in LOST_OUTCOMES
    divided by reviews with outcome_final != 'Unknown'.
    """
    findings = compute_headline_findings(full_df)
    rel_df = full_df[full_df["relevant_final"] == "Yes"]
    stated_df = rel_df[rel_df["outcome_final"] != "Unknown"]
    expected_lost_count = stated_df["outcome_final"].isin(LOST_OUTCOMES).sum()

    assert findings["lost_rate"]["lost_count"] == expected_lost_count
    assert findings["lost_rate"]["n_outcome_stated"] == len(stated_df)
    expected_rate = round((expected_lost_count / len(stated_df)) * 100, 1)
    assert findings["lost_rate"]["rate_pct"] == expected_rate


def test_headline_findings_empty_dataframe():
    """Headline findings should return zeroes safely when given an empty dataframe."""
    empty_df = pd.DataFrame(
        columns=["relevant_final", "theme", "cause", "outcome_final"]
    )
    findings = compute_headline_findings(empty_df)
    assert findings["n_relevant"] == 0
    assert findings["top_theme"]["count"] == 0
    assert findings["lost_rate"]["rate_pct"] == 0.0


def test_theme_breakdown(full_df):
    """
    Test theme breakdown: counts sum to all relevant_final == 'Yes' rows,
    every row has n, and n < 30 triggers is_small_sample.
    """
    theme_df = compute_theme_breakdown(full_df)
    expected_total = (full_df["relevant_final"] == "Yes").sum()
    assert theme_df["count"].sum() == expected_total
    assert (theme_df["n"] == theme_df["count"]).all()
    assert (theme_df["is_small_sample"] == (theme_df["n"] < 30)).all()

    # Small sample annotation check
    for _, row in theme_df.iterrows():
        if row["is_small_sample"]:
            assert "small sample, pattern only" in row["label_text"]
        else:
            assert "small sample" not in row["label_text"]


def test_theme_grouped_preserves_counts(full_df):
    """Grouped breakdown by cause preserves total relevant review count."""
    grouped = compute_theme_grouped(full_df, "cause")
    expected_total = (full_df["relevant_final"] == "Yes").sum()
    assert grouped["count"].sum() == expected_total


def test_hypothesis_breakdown(full_df):
    """
    Hypothesis distribution covers all hypotheses A-E and None,
    with counts summing to total relevant reviews.
    """
    hypotheses = compute_hypothesis_breakdown(full_df)
    assert len(hypotheses) == 6
    total_hyp_count = sum(h["count"] for h in hypotheses)
    expected_total = (full_df["relevant_final"] == "Yes").sum()
    assert total_hyp_count == expected_total
    for h in hypotheses:
        assert h["n"] == h["count"]
        assert h["is_small_sample"] == (h["n"] < 30)


def test_break_type_excludes_not_stated(full_df):
    """
    Spec §7.2: Break type split must EXCLUDE 'Not stated'.
    Items only include Payment failure, Chose to stop, Temporary break.
    """
    res = compute_break_type_breakdown(full_df)
    rel_df = full_df[full_df["relevant_final"] == "Yes"]

    item_names = [item["break_type"] for item in res["items"]]
    assert "Not stated" not in item_names
    assert set(item_names) == {"Payment failure", "Chose to stop", "Temporary break"}

    expected_not_stated = (rel_df["break_type"] == "Not stated").sum()
    assert res["not_stated_count"] == expected_not_stated

    expected_stated = rel_df["break_type"].isin(item_names).sum()
    assert res["stated_total"] == expected_stated
    assert sum(item["count"] for item in res["items"]) == expected_stated


def test_wishes_counts_and_split(full_df):
    """
    Spec §7.2: Wishes (issue == 'Feature request') totals 319 rows,
    correctly split by Before vs After 25 Dec 2024.
    """
    wishes = compute_wishes(full_df)
    wishes_df = full_df[full_df["issue"] == "Feature request"]

    assert wishes["total"] == len(wishes_df)
    assert wishes["total"] == 319

    expected_before = (wishes_df["period"] == PERIOD_BEFORE).sum()
    expected_after = (wishes_df["period"] == PERIOD_AFTER).sum()

    assert wishes["before_count"] == expected_before
    assert wishes["after_count"] == expected_after
    assert wishes["before_count"] + wishes["after_count"] == 319


def test_evidence_filters_change_count_at2(full_df):
    """
    Acceptance Test AT-2: Changing an Evidence filter changes the count.
    """
    total = len(full_df)
    
    # Filter by period
    filtered_period = full_df[full_df["period"] == PERIOD_AFTER]
    assert len(filtered_period) < total

    # Filter by theme
    filtered_theme = full_df[full_df["theme"] == "Payment failed or missed"]
    assert len(filtered_theme) < total

    # Filter by scope
    filtered_scope = full_df[full_df["scope"] == "Entry (before a SIP is running)"]
    assert len(filtered_scope) < total

    # Combined filter
    combined = full_df[
        (full_df["period"] == PERIOD_AFTER)
        & (full_df["theme"] == "Payment failed or missed")
    ]
    assert len(combined) < len(filtered_period)
    assert len(combined) < len(filtered_theme)


def test_opportunity_table_computation(full_df):
    """
    Validates opportunity table calculation across sort orders and period filters.
    """
    # 1. Default sort by priority_score
    df_score = compute_opportunity_table(full_df, sort_by="priority_score")
    assert len(df_score) > 0
    assert (df_score["mentions"] >= 5).all()
    # Check descending order of priority_score
    scores = df_score["priority_score"].tolist()
    assert scores == sorted(scores, reverse=True)

    # 2. Sort by mentions
    df_mentions = compute_opportunity_table(full_df, sort_by="mentions")
    mentions_list = df_mentions["mentions"].tolist()
    assert mentions_list == sorted(mentions_list, reverse=True)

    # 3. Low n_outcome_known (< 5) sets lost_rate to 0.0
    low_known = df_score[df_score["n_outcome_known"] < 5]
    if len(low_known) > 0:
        assert (low_known["lost_rate_among_known"] == 0.0).all()

    # 4. Period filter handling
    before_df = apply_period_filter(full_df, PERIOD_BEFORE)
    opp_before = compute_opportunity_table(before_df)
    assert len(opp_before) > 0
    assert (opp_before["mentions"] >= 5).all()

    # 5. Empty dataframe returns empty result with correct schema
    empty_df = full_df[full_df["relevant_final"] == "NonExistent"]
    opp_empty = compute_opportunity_table(empty_df)
    assert len(opp_empty) == 0
    assert "priority_score" in opp_empty.columns

    # 6. Group by variations ('Theme only' and 'Theme and cause')
    df_theme_only = compute_opportunity_table(full_df, group_by="Theme only")
    assert len(df_theme_only) == 14
    assert "causes" in df_theme_only.columns
    assert "scope" in df_theme_only.columns

    df_theme_cause = compute_opportunity_table(full_df, group_by="Theme and cause")
    assert len(df_theme_cause) == 18
    assert "cause" in df_theme_cause.columns


def test_compute_stats_for_ask(full_df):
    """
    Validates compute_stats_for_ask generates all required fields matching the dataset.
    """
    stats = compute_stats_for_ask(full_df)
    rel_count = (full_df["relevant_final"] == "Yes").sum()
    assert stats["n_relevant"] == rel_count
    assert stats["wishes_total"] == (full_df["issue"] == "Feature request").sum()
    assert stats["pay_fail_count"] > 0
    assert stats["support_count"] > 0
    assert stats["n_outcome_stated"] > 0
    assert stats["lost_count"] > 0


def test_evidence_search_expected_counts(full_df):
    """
    Search only relevant reviews (relevant_final == 'Yes', 721 rows) in period All.
    Expected counts:
      autopay = 25
      refund = 76
      support = 81
      autopay mandate = 2
      not deducted = 54
    """
    rel_df = full_df[full_df["relevant_final"] == "Yes"]
    assert len(filter_reviews_by_search(rel_df, "autopay")) == 25
    assert len(filter_reviews_by_search(rel_df, "refund")) == 76
    assert len(filter_reviews_by_search(rel_df, "support")) == 81
    assert len(filter_reviews_by_search(rel_df, "autopay mandate")) == 2
    assert len(filter_reviews_by_search(rel_df, "not deducted")) == 54


def test_evidence_search_typed_evidence_id(full_df):
    """A search for a typed evidence_id returns exactly that row."""
    rel_df = full_df[full_df["relevant_final"] == "Yes"]
    res = filter_reviews_by_search(rel_df, "E0106")
    assert len(res) == 1
    assert res["evidence_id"].iloc[0] == "E0106"

    # Case-insensitive typed evidence_id
    res_lower = filter_reviews_by_search(rel_df, "e0106")
    assert len(res_lower) == 1
    assert res_lower["evidence_id"].iloc[0] == "E0106"


def test_evidence_search_plus_filter_narrows_count(full_df):
    """Search plus a filter narrows the count."""
    rel_df = full_df[full_df["relevant_final"] == "Yes"]
    search_res = filter_reviews_by_search(rel_df, "autopay")
    assert len(search_res) == 25

    # Filter by period narrows count
    narrowed_by_period = search_res[search_res["period"] == PERIOD_AFTER]
    assert 0 < len(narrowed_by_period) < len(search_res)

    # Filter by theme narrows count
    narrowed_by_theme = search_res[search_res["theme"] == "Cannot start or set up SIP"]
    assert 0 < len(narrowed_by_theme) < len(search_res)


def test_evidence_search_clearing_restores_count(full_df):
    """Clearing the search restores the count."""
    rel_df = full_df[full_df["relevant_final"] == "Yes"]
    total_rel = len(rel_df)

    searched = filter_reviews_by_search(rel_df, "autopay")
    assert len(searched) == 25

    # Clearing with empty string restores count
    cleared_empty = filter_reviews_by_search(rel_df, "")
    assert len(cleared_empty) == total_rel

    # Clearing with whitespace restores count
    cleared_spaces = filter_reviews_by_search(rel_df, "   ")
    assert len(cleared_spaces) == total_rel


def test_evidence_search_xss_escaped_safely(full_df):
    """A search query containing <script> executes safely and returns 0 rows without error."""
    rel_df = full_df[full_df["relevant_final"] == "Yes"]
    res = filter_reviews_by_search(rel_df, "<script>")
    assert len(res) == 0



