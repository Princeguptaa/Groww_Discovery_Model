"""
Unit tests for Phase 7: AI Infrastructure, Labeller Post-Rules, Quality Gate,
and Fallback Mode when GEMINI_API_KEY is not configured.
"""

from lib.labeller import normalise, apply_post_rules, evaluate_quality_gate
from lib.ai_client import (
    call_ai_label,
    call_ai_ask,
    DailyQuotaTracker,
    MAX_DAILY_CALLS,
    MAX_SESSION_CALLS,
)
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


def test_session_cap_blocks_11th_call(monkeypatch):
    """Session cap of 10 blocks the 11th call for both labelling and ask."""
    import streamlit as st
    monkeypatch.setattr("lib.ai_client.get_gemini_api_key", lambda: "mock-key")
    st.session_state["ai_call_count"] = MAX_SESSION_CALLS

    # 1. Label call blocked
    labels, is_live, msg = call_ai_label("Some review text")
    assert is_live is False
    assert f"Session limit reached ({MAX_SESSION_CALLS} calls)" in msg
    assert st.session_state["ai_call_count"] == MAX_SESSION_CALLS

    # 2. Ask call blocked
    ans, is_live_ask, ask_msg = call_ai_ask("Question", "STATS", "EXAMPLES", {"E0023"})
    assert is_live_ask is False
    assert f"Session limit reached ({MAX_SESSION_CALLS} calls)" in ask_msg
    assert st.session_state["ai_call_count"] == MAX_SESSION_CALLS


def test_malformed_json_does_not_increment_either_counter(monkeypatch):
    """Malformed JSON response must not increment session counter or daily tracker."""
    import streamlit as st
    from unittest.mock import MagicMock
    from lib.ai_client import get_daily_tracker

    monkeypatch.setattr("lib.ai_client.get_gemini_api_key", lambda: "mock-key")
    st.session_state["ai_call_count"] = 2
    tracker = get_daily_tracker()
    initial_daily = tracker.get_count()

    # Mock genai client to return malformed JSON
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "{invalid json string without closing brace"
    mock_client.models.generate_content.return_value = mock_response

    monkeypatch.setattr("google.genai.Client", lambda api_key: mock_client)

    labels, is_live, msg = call_ai_label("My review")
    assert is_live is False
    assert "temporarily unavailable" in msg

    # Both counters must remain unchanged
    assert st.session_state["ai_call_count"] == 2
    assert tracker.get_count() == initial_daily


def test_invalid_citation_ids_are_stripped():
    """Citations containing IDs not in allowed_ids are stripped."""
    from lib.ai_client import strip_invalid_citations

    allowed = {"E0023", "E0105"}

    # Mixed valid and invalid citation inside brackets
    text1 = "Mandate failure occurred [E0023, E9999] due to timeout."
    res1 = strip_invalid_citations(text1, allowed)
    assert res1 == "Mandate failure occurred [E0023] due to timeout."

    # Bracket with only invalid citation ID is completely stripped
    text2 = "Another issue occurred [E8888] during processing."
    res2 = strip_invalid_citations(text2, allowed)
    assert res2 == "Another issue occurred during processing."

    # Multiple valid citations preserved
    text3 = "Multiple issues verified [E0023, E0105]."
    res3 = strip_invalid_citations(text3, allowed)
    assert res3 == "Multiple issues verified [E0023, E0105]."


def test_model_chain_switches_on_503_429_and_404(monkeypatch):
    """Model fallback chain switches to next model on 503, 429, and 404 errors."""
    import streamlit as st
    from unittest.mock import MagicMock
    from lib.ai_client import MODEL_CHAIN

    monkeypatch.setattr("lib.ai_client.get_gemini_api_key", lambda: "mock-key")
    st.session_state["ai_call_count"] = 0

    attempted_models = []

    def mock_generate_content(model, contents, config):
        attempted_models.append(model)
        if model == MODEL_CHAIN[0]:
            raise Exception("503 Service Unavailable")
        elif model == MODEL_CHAIN[1]:
            raise Exception("429 Resource Exhausted")
        elif model == MODEL_CHAIN[2]:
            resp = MagicMock()
            resp.text = '{"relevant": "Yes", "issue": "Payment failed or missed", "break_type": "Payment failure"}'
            return resp
        raise Exception("404 Not Found")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = mock_generate_content
    monkeypatch.setattr("google.genai.Client", lambda api_key: mock_client)

    labels, is_live, msg = call_ai_label("Review text")
    assert is_live is True
    assert MODEL_CHAIN[2] in msg
    assert attempted_models == [MODEL_CHAIN[0], MODEL_CHAIN[1], MODEL_CHAIN[2]]

    # Test all 3 fail with 503, 429, 404 -> graceful fallback
    attempted_models.clear()
    def mock_all_fail(model, contents, config):
        attempted_models.append(model)
        if len(attempted_models) == 1:
            raise Exception("503 Service Unavailable")
        elif len(attempted_models) == 2:
            raise Exception("429 Resource Exhausted")
        else:
            raise Exception("404 Not Found")

    mock_client.models.generate_content.side_effect = mock_all_fail
    labels_fail, is_live_fail, msg_fail = call_ai_label("Review text")
    assert is_live_fail is False
    assert "temporarily unavailable" in msg_fail
    assert attempted_models == MODEL_CHAIN


def test_daily_cap_resets_when_utc_date_changes():
    """Daily cap resets to 0 when the UTC date changes."""
    tracker = DailyQuotaTracker()
    day1 = "2026-10-25"
    day2 = "2026-10-26"

    # Fill up day 1 to cap
    tracker.counts[day1] = MAX_DAILY_CALLS
    tracker.get_today_key = lambda: day1
    assert tracker.get_count() == MAX_DAILY_CALLS
    allowed, count = tracker.increment()
    assert allowed is False

    # Simulate UTC date change to day 2
    tracker.get_today_key = lambda: day2
    assert tracker.get_count() == 0
    allowed2, count2 = tracker.increment()
    assert allowed2 is True
    assert count2 == 1
    assert tracker.get_count() == 1

