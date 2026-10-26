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
    """
    findings = compute_headline_findings(full_df)
    assert findings["top_theme"]["theme"] != "Support not solving"
    assert findings["top_theme"]["count"] > 0
    assert findings["top_theme"]["n"] == (full_df["relevant_final"] == "Yes").sum()

    # Support amplifier check
    rel_df = full_df[full_df["relevant_final"] == "Yes"]
    expected_support_count = (rel_df["theme"] == "Support not solving").sum()
    assert findings["support_amplifier"]["count"] == expected_support_count
    assert findings["support_amplifier"]["pct"] == round(
        (expected_support_count / len(rel_df)) * 100, 1
    )


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
