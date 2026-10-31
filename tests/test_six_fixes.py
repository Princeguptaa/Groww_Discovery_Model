"""
Tests validating the 6 fixes required for Groww SIP Discovery Engine:
1. Ask the data fallback: no Zerodha Coin, all citations exist and match theme/period, relevant_final = Yes.
2. Try it fallback: simple code rules (praise/feature/payment), returns sample's own text and labels.
3. Method screen and evidence notes wording: researcher-labelled, honest limit, audit wording kept.
4. Suggested question buttons: on_click callback updates st.session_state['ask_query_input'].
5. Scope check before any answer: rejects fund/stock advice and off-topic questions.
6. Overview wording & Ask HTML escaping: 'Play Store reviews pulled', removed driver sentence, html.escape + safe markup.
"""

import html
import re
import pytest
import streamlit as st
import pandas as pd
from lib.data_loader import load_reviews
from lib.compute import compute_funnel, compute_stats_for_ask
from lib.fallback_examples import (
    ASK_DATA_FALLBACKS,
    SCOPE_DECLINE_MESSAGE,
    check_ask_query_scope,
    select_tryit_sample_key,
    get_tryit_fallback,
    get_ask_fallback,
    TRYIT_FALLBACKS,
)
from views.ask import SUGGESTED_QUESTIONS, _set_suggested_query, format_answer_html


@pytest.fixture(scope="module")
def full_df():
    return load_reviews()



# =========================================================================
# Fix 1 Tests: Ask Data Fallback
# =========================================================================

def test_fix1_ask_fallback_no_zerodha_coin_or_typed_claims():
    """Verify fallback answers contain no claims about switching to Zerodha Coin."""
    for q, ans in ASK_DATA_FALLBACKS.items():
        assert "Zerodha" not in ans, f"Zerodha found in answer for '{q}'"
        assert "Coin" not in ans, f"Coin found in answer for '{q}'"


def test_fix1_ask_fallback_cited_ids_exist_and_match_theme_and_period(full_df):
    """
    Verify every cited evidence_id in fallback answers:
    1. Exists in labelled_reviews.csv
    2. Has relevant_final == 'Yes'
    3. Matches the claimed theme and period
    """
    rel_df = full_df[full_df["relevant_final"] == "Yes"].set_index("evidence_id")

    # Q1: Payment failed or missed & Support not solving
    q1 = "What are the most common reasons people say their SIP failed or was missed?"
    ans1 = ASK_DATA_FALLBACKS[q1]
    eids1 = re.findall(r"E\d{4}", ans1)
    assert len(eids1) >= 2, f"Expected at least 2 citations in Q1, got {eids1}"
    for eid in eids1:
        assert eid in rel_df.index, f"Cited ID {eid} not in dataset"
        assert rel_df.loc[eid, "theme"] in [
            "Payment failed or missed",
            "Support not solving",
        ], f"ID {eid} theme mismatch"

    # Q2: Before 25 Dec 2024 (Payment failed) & After 25 Dec 2024 (Cannot edit or pause or stop)
    q2 = "How do the problems differ before and after 25 Dec 2024?"
    ans2 = ASK_DATA_FALLBACKS[q2]
    # Match bracket citations
    brackets = re.findall(r"\[(.*?)\]", ans2)
    assert len(brackets) == 2, f"Expected 2 bracket citations in Q2, got {brackets}"
    before_ids = [x.strip() for x in brackets[0].split(",") if x.strip()]
    after_ids = [x.strip() for x in brackets[1].split(",") if x.strip()]

    for eid in before_ids:
        assert eid in rel_df.index, f"Before ID {eid} not in dataset"
        assert rel_df.loc[eid, "period"] == "Before 25 Dec 2024", f"ID {eid} period mismatch"
        assert rel_df.loc[eid, "theme"] == "Payment failed or missed", f"ID {eid} theme mismatch"

    for eid in after_ids:
        assert eid in rel_df.index, f"After ID {eid} not in dataset"
        assert rel_df.loc[eid, "period"] == "After 25 Dec 2024", f"ID {eid} period mismatch"
        assert rel_df.loc[eid, "theme"] == "Cannot edit or pause or stop", f"ID {eid} theme mismatch"

    # Q3: Outcome stated -> Support not solving & Payment failed or missed
    q3 = "What do users say they did after a failed or cancelled SIP?"
    ans3 = ASK_DATA_FALLBACKS[q3]
    eids3 = re.findall(r"E\d{4}", ans3)
    assert len(eids3) >= 2, f"Expected citations in Q3, got {eids3}"
    for eid in eids3:
        assert eid in rel_df.index
        assert rel_df.loc[eid, "theme"] in [
            "Support not solving",
            "Payment failed or missed",
        ]

    # Q4: Money delay & Debited after cancel
    q4 = "Which problems are about money leaving the bank but not showing in the app?"
    ans4 = ASK_DATA_FALLBACKS[q4]
    brackets4 = re.findall(r"\[(.*?)\]", ans4)
    assert len(brackets4) == 2, f"Expected 2 bracket citations in Q4, got {brackets4}"
    delay_ids = [x.strip() for x in brackets4[0].split(",") if x.strip()]
    debit_ids = [x.strip() for x in brackets4[1].split(",") if x.strip()]
    for eid in delay_ids:
        assert eid in rel_df.index
        assert rel_df.loc[eid, "theme"] == "Processing or unit allocation delay"
    for eid in debit_ids:
        assert eid in rel_df.index
        assert rel_df.loc[eid, "theme"] == "Debited after cancel or wrong amount"

    # Q5 & Q6: Cannot edit or pause or stop
    for q in [
        "What do users ask for that Groww does not offer yet?",
        "How many reviews mention skipping, pausing or editing a SIP, and what do they say?",
    ]:
        ans = ASK_DATA_FALLBACKS[q]
        eids = re.findall(r"E\d{4}", ans)
        assert len(eids) >= 1, f"Expected citations in '{q}', got {eids}"
        for eid in eids:
            assert eid in rel_df.index
            assert rel_df.loc[eid, "theme"] == "Cannot edit or pause or stop"


# =========================================================================
# Fix 2 Tests: Try It Fallback
# =========================================================================

def test_fix2_tryit_sample_selection_rules():
    """Verify simple code rules pick praise, feature, or payment sample."""
    # Praise words -> Praise review
    assert select_tryit_sample_key("This app is the best and very smooth, thank you!") == "Praise review"
    assert select_tryit_sample_key("Great experience, wonderful mutual fund investment") == "Praise review"

    # Feature words -> Feature request review
    assert select_tryit_sample_key("Please add feature to edit the monthly date") == "Feature request review"
    assert select_tryit_sample_key("Option to pause SIP indefinitely would be great") == "Feature request review"

    # Otherwise -> Payment failure review
    assert select_tryit_sample_key("Money was deducted but SIP shows pending") == "Payment failure review"
    assert select_tryit_sample_key("Bank autopay failed and support did not respond") == "Payment failure review"


def test_fix2_tryit_fallback_always_shows_sample_own_text_and_labels():
    """Verify fallback returns sample review's own text and verified labels, not user's text."""
    user_text = "I am a user with a unique custom complaint about payment"
    sample_data = get_tryit_fallback(user_text=user_text)

    # Must be sample's own text, not user's text
    assert sample_data["text"] == TRYIT_FALLBACKS["Payment failure review"]["text"]
    assert sample_data["text"] != user_text
    assert sample_data["labels"]["issue"] == "Payment failed or missed"
    assert sample_data["labels"]["relevant_final"] == "Yes"

    # For praise user text
    praise_data = get_tryit_fallback(user_text="I love this app, best platform ever")
    assert praise_data["text"] == TRYIT_FALLBACKS["Praise review"]["text"]
    assert praise_data["labels"]["issue"] == "Praise"
    assert praise_data["labels"]["relevant_final"] == "No"


# =========================================================================
# Fix 3 Tests: Method Screen & Evidence Notes Wording
# =========================================================================

def test_fix3_method_screen_and_evidence_notes_wording():
    """
    Verify:
    1. 'labelled independently by hand' and 'human golden rows' removed.
    2. 'labelled by the researcher: the first list was drafted with AI help, then every label was reviewed and confirmed or changed' present.
    3. Honest limit 'The golden set started from an AI-drafted list, so it is not fully independent of AI.' present.
    4. Audit wording 'a second AI model (Claude), not a human' preserved.
    """
    with open("views/method.py", "r", encoding="utf-8") as f:
        method_content = f.read()

    with open("data/evidence_notes.md", "r", encoding="utf-8") as f:
        notes_content = f.read()

    target_replacement = (
        "labelled by the researcher: the first list was drafted with AI help, "
        "then every label was reviewed and confirmed or changed"
    )
    target_limit = "The golden set started from an AI-drafted list, so it is not fully independent of AI."
    audit_wording = "a second AI model (Claude), not a human"

    # Check method.py
    assert "labelled independently by hand" not in method_content
    assert "human golden rows" not in method_content
    assert target_replacement in method_content
    assert target_limit in method_content
    assert audit_wording in method_content

    # Check evidence_notes.md
    assert "labelled independently by hand" not in notes_content
    assert target_replacement in notes_content
    assert target_limit in notes_content
    assert audit_wording in notes_content


# =========================================================================
# Fix 4 Tests: Suggested Question Buttons on_click Callback
# =========================================================================

def test_fix4_suggested_question_button_callback():
    """Verify on_click callback updates st.session_state['ask_query_input']."""
    test_q = SUGGESTED_QUESTIONS[2]
    _set_suggested_query(test_q)
    assert st.session_state["ask_query_input"] == test_q

    # Change to another suggested question
    test_q2 = SUGGESTED_QUESTIONS[4]
    _set_suggested_query(test_q2)
    assert st.session_state["ask_query_input"] == test_q2


# =========================================================================
# Fix 5 Tests: Scope Check Before Answering
# =========================================================================

def test_fix5_scope_check_which_fund_should_i_buy():
    """Verify 'Which fund should I buy?' is declined with scope message."""
    q = "Which fund should I buy?"
    declined = check_ask_query_scope(q)
    assert declined == SCOPE_DECLINE_MESSAGE
    # Fallback answer also returns scope decline message
    assert get_ask_fallback(q) == SCOPE_DECLINE_MESSAGE


def test_fix5_scope_check_capital_of_france():
    """Verify 'What is the capital of France?' is declined with scope message."""
    q = "What is the capital of France?"
    declined = check_ask_query_scope(q)
    assert declined == SCOPE_DECLINE_MESSAGE
    # Fallback answer also returns scope decline message
    assert get_ask_fallback(q) == SCOPE_DECLINE_MESSAGE


def test_fix5_scope_check_in_scope_questions_pass():
    """Verify all 6 suggested discovery questions are permitted by the scope checker."""
    for q in SUGGESTED_QUESTIONS:
        declined = check_ask_query_scope(q)
        assert declined is None, f"Suggested question '{q}' was unexpectedly declined"


# =========================================================================
# Fix 6 Tests: Overview Wording & Ask HTML Escaping
# =========================================================================

def test_fix6_overview_source_wording(full_df):
    """Verify Overview funnel step 1 source is 'Play Store reviews pulled'."""
    inputs = {"reviews_pulled": 25000}
    funnel = compute_funnel(full_df, inputs)
    assert funnel[0]["source"] == "Play Store reviews pulled"
    assert funnel[0]["source"] != "App Store extraction"


def test_fix6_overview_card2_removed_sentence():
    """Verify 'Primary structural driver identified across user complaints in this period.' is removed."""
    with open("views/overview.py", "r", encoding="utf-8") as f:
        overview_content = f.read()
    assert "Primary structural driver identified across user complaints in this period." not in overview_content


def test_fix6_ask_html_escape_and_safe_markup():
    """Verify format_answer_html escapes raw HTML, converts [E####] to safe tags, and newlines to <br>."""
    raw_answer = (
        "Failure happened <script>alert('hack')</script> & [E0023].\n"
        "Another issue noted in [E0105, E0234].\n\nFinal point."
    )
    formatted = format_answer_html(raw_answer)

    # 1. Raw HTML must be escaped
    assert "<script>" not in formatted
    assert "&lt;script&gt;alert(&#x27;hack&#x27;)&lt;/script&gt;" in formatted or "&lt;script&gt;" in formatted
    assert "&amp;" in formatted

    # 2. [E0023] converted to safe styled tags
    assert '<span style="background: #E2E8F0;' in formatted
    assert "[E0023]" in formatted
    assert "[E0105, E0234]" in formatted

    # 3. Newlines converted to <br>
    assert "\n" not in formatted
    assert "<br>" in formatted
