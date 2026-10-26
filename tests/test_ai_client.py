"""
Unit tests for Phase 7: AI Infrastructure, Labeller Post-Rules, Quality Gate,
and Fallback Mode when GEMINI_API_KEY is not configured.
"""

from lib.labeller import normalise, apply_post_rules, evaluate_quality_gate
from lib.ai_client import call_ai_label, call_ai_ask, DailyQuotaTracker, MAX_DAILY_CALLS
from lib.fallback_examples import get_tryit_fallback, get_ask_fallback


def test_post_rule_1_praise_and_feature_request():
    """Rule 1: relevant_final = 'No' when issue is Praise or Feature request."""
    # Praise
    raw_praise = {"relevant": "Yes", "issue": "Praise", "hypothesis": "A controls not found"}
    res_praise = apply_post_rules(raw_praise)
    assert res_praise["relevant_final"] == "No"
    assert res_praise["hypothesis_final"] == "None"

    # Feature request
    raw_feat = {"relevant": "Yes", "issue": "Feature request", "hypothesis": "A controls not found"}
    res_feat = apply_post_rules(raw_feat)
    assert res_feat["relevant_final"] == "No"
    assert res_feat["hypothesis_final"] == "None"


def test_post_rule_2_hypothesis_e_for_setup():
    """Rule 2: hypothesis_final = 'E setup or autopay blocked' when issue is Cannot start or set up SIP."""
    raw_setup = {
        "relevant": "Yes",
        "issue": "Cannot start or set up SIP",
        "hypothesis": "A controls not found",
    }
    res_setup = apply_post_rules(raw_setup)
    assert res_setup["relevant_final"] == "Yes"
    assert res_setup["hypothesis_final"] == "E setup or autopay blocked"


def test_post_rule_3_stalled_for_paused_payment_failure():
    """Rule 3: outcome_final = 'Stalled, not by choice' when break_type is Payment failure and outcome is Paused."""
    raw_fail = {
        "relevant": "Yes",
        "issue": "Payment failed or missed",
        "break_type": "Payment failure",
        "outcome": "Paused",
    }
    res_fail = apply_post_rules(raw_fail)
    assert res_fail["outcome_final"] == "Stalled, not by choice"


def test_post_rule_4_non_relevant_hypothesis_none():
    """Rule 4: hypothesis_final = 'None' when relevant_final != 'Yes'."""
    raw_irrelevant = {
        "relevant": "No",
        "issue": "Other",
        "hypothesis": "B failed payment no recovery",
    }
    res = apply_post_rules(raw_irrelevant)
    assert res["hypothesis_final"] == "None"


def test_quality_gate_evaluations():
    """Validates the three Quality Gate tiers."""
    # 1. Not a SIP continuation event
    gate_praise = evaluate_quality_gate(
        {"relevant_final": "No", "issue": "Praise", "evidence": "Good app"},
        "Good app for investing",
    )
    assert gate_praise["status"] == "Not a SIP continuation event"

    # 2. Borderline: missing evidence phrase
    gate_missing = evaluate_quality_gate(
        {"relevant_final": "Yes", "issue": "Payment failed or missed", "evidence": "Unrelated phrase"},
        "My SIP stopped because of bank error",
    )
    assert gate_missing["status"] == "Borderline. Needs a human check."

    # 3. Borderline: broad status tag
    gate_broad = evaluate_quality_gate(
        {
            "relevant_final": "Yes",
            "issue": "Confused about status or dashboard",
            "evidence": "dashboard stuck",
        },
        "My dashboard stuck",
    )
    assert gate_broad["status"] == "Borderline. Needs a human check."

    # 4. Valid continuation event
    gate_valid = evaluate_quality_gate(
        {
            "relevant_final": "Yes",
            "issue": "Payment failed or missed",
            "evidence": "bank deduction failed",
        },
        "My bank deduction failed today",
    )
    assert gate_valid["status"] == "Valid SIP continuation event"


def test_daily_quota_tracker():
    """DailyQuotaTracker limits calls up to MAX_DAILY_CALLS."""
    tracker = DailyQuotaTracker()
    today = tracker.get_today_key()
    tracker.counts[today] = MAX_DAILY_CALLS
    allowed, count = tracker.increment()
    assert allowed is False
    assert count == MAX_DAILY_CALLS


def test_fallback_without_key():
    """With no GEMINI_API_KEY set, functions must return saved examples without error."""
    labels, is_live, msg = call_ai_label("Some test review text")
    assert is_live is False
    assert "Saved example" in msg
    assert "relevant_final" in labels

    answer, is_live_ask, ask_msg = call_ai_ask(
        "What are the most common reasons people say their SIP failed or was missed?",
        "STATS",
        "EXAMPLES",
        {"E0023"},
    )
    assert is_live_ask is False
    assert "Saved answer" in ask_msg
    assert len(answer) > 20
