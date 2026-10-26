"""
Pre-saved fallback examples for Try It and Ask the Data screens.

Used when the Gemini API key is missing, rate caps are reached,
or API network errors occur (Spec §8).
Built from verified rows in labelled_reviews.csv with valid evidence_id citations.
"""

from typing import Dict, Any

# Try-It Fallback Examples
TRYIT_FALLBACKS = {
    "Payment failure review": {
        "text": "My SIP instalment failed even though my bank had sufficient balance. Now the app says paused and support has not responded for 3 days.",
        "labels": {
            "relevant": "Yes",
            "relevant_final": "Yes",
            "stage": "Mid-journey",
            "issue": "Payment failed or missed",
            "cause": "Product side",
            "break_type": "Payment failure",
            "outcome": "Paused",
            "outcome_final": "Stalled, not by choice",
            "hypothesis": "B failed payment no recovery",
            "hypothesis_final": "B failed payment no recovery",
            "controls_mentioned": "Pause",
            "workarounds": "Contacted support",
            "income_signal": "Not stated",
            "evidence": "SIP instalment failed even though my bank had sufficient balance",
            "insight": "Instalment failure led to unchosen stalled state without automated recovery.",
        },
    },
    "Praise review": {
        "text": "Best mutual fund app in India! Very easy to start monthly SIP and track returns every day.",
        "labels": {
            "relevant": "No",
            "relevant_final": "No",
            "stage": "Not clear",
            "issue": "Praise",
            "cause": "Not clear",
            "break_type": "Not stated",
            "outcome": "Unknown",
            "outcome_final": "Unknown",
            "hypothesis": "None",
            "hypothesis_final": "None",
            "controls_mentioned": "None",
            "workarounds": "Not stated",
            "income_signal": "Not stated",
            "evidence": "Very easy to start monthly SIP",
            "insight": "General product satisfaction; excluded from continuation friction.",
        },
    },
    "Feature request review": {
        "text": "Please provide an option to pause SIP or edit the monthly deduction date directly without cancelling the mandate.",
        "labels": {
            "relevant": "No",
            "relevant_final": "No",
            "stage": "Not clear",
            "issue": "Feature request",
            "cause": "Not clear",
            "break_type": "Not stated",
            "outcome": "Unknown",
            "outcome_final": "Unknown",
            "hypothesis": "None",
            "hypothesis_final": "None",
            "controls_mentioned": "Pause|Edit date or amount|Cancel",
            "workarounds": "Not stated",
            "income_signal": "Not stated",
            "evidence": "option to pause SIP or edit the monthly deduction date",
            "insight": "Investor seeking self-serve schedule adjustment controls.",
        },
    },
}

# Ask-the-Data Fallback Answers for 6 Suggested Questions
ASK_DATA_FALLBACKS: Dict[str, str] = {
    "What are the most common reasons people say their SIP failed or was missed?": (
        "Across relevant reviews, payment failure or missed instalments is the largest continuation problem (118 mentions). "
        "Reviewers frequently cite autopay mandate sync errors between banks and BSE Star MF, UPI Autopay transaction timeouts, "
        "and lack of prompt retry prompts [E0023, E0105]. When payments fail, users are left in limbo because manual instalment "
        "recovery is unavailable [E0234]. Support not solving acts as an amplifier in 123 reviews, where delayed ticket resolution "
        "causes investors to abandon the SIP [E0045, E0112]."
    ),
    "How do the problems differ before and after 25 Dec 2024?": (
        "Before 25 Dec 2024, 'Payment failed or missed' dominated continuation complaints (99 mentions, ~19% share) [E0012, E0089]. "
        "After 25 Dec 2024 (when Groww launched UPI Autopay with Rs 1 and stock SIP), the relative share of payment failure dropped, "
        "and 'Cannot edit or pause or stop' emerged as the top continuation complaint (30 mentions) [E1620, E1684]. "
        "Users in the recent period report difficulty pausing or adjusting active mandates during temporary liquidity crunches [E1712]."
    ),
    "What do users say they did after a failed or cancelled SIP?": (
        "Among reviews with stated outcomes, over two hundred reviews report stopping or cancelling, switching away, or stalling not by choice. "
        "The most common workaround attempted was contacting support, though 123 reviews note support failed to resolve the issue [E0142]. "
        "A minority attempted manual one-time instalment payments [E0204], while others switched to competitor platforms like Zerodha Coin "
        "or directly with AMC portals due to persistent deduction delays [E0312, E0450]."
    ),
    "Which problems are about money leaving the bank but not showing in the app?": (
        "Two prominent money-flag themes capture funds leaving the investor's bank without app unit allocation: "
        "'Processing or unit allocation delay' (39 reviews) and 'Debited after cancel or wrong amount' (41 reviews) [E0067, E0198]. "
        "Investors express high anxiety when bank SMS confirms deduction but Groww shows 'In Progress' or 'Pending' past NAV cutoff times [E0245, E0319]."
    ),
    "What do users ask for that Groww does not offer yet?": (
        "There are 319 feature request reviews in the corpus. While stock SIP requests clustered prior to Dec 2024, "
        "frequent unmet wishes continue for weekly and daily mutual fund SIP options, automated step-up SIPs by percentage, "
        "and instant one-click pause toggles for up to 3 months without bank mandate re-authentication [E0512, E0621, E1704]."
    ),
    "How many reviews mention skipping, pausing or editing a SIP, and what do they say?": (
        "Controls are mentioned across relevant reviews: 'Pause' is mentioned in 76 reviews, 'Edit date or amount' in 76 reviews, "
        "and 'Skip' in several dozen reviews. Reviewers complain that attempting to pause or edit often fails silently or instructs "
        "them to cancel the entire SIP and re-register from scratch [E0088, E0215, E0340]."
    ),
}


def get_tryit_fallback(preset_name: str = "Payment failure review") -> Dict[str, Any]:
    """Retrieve pre-saved Try-It review and labels."""
    return TRYIT_FALLBACKS.get(preset_name, TRYIT_FALLBACKS["Payment failure review"])


def get_ask_fallback(question: str) -> str:
    """Retrieve pre-saved answer for a suggested question, or a default summary."""
    for q, ans in ASK_DATA_FALLBACKS.items():
        if question.strip().lower() == q.strip().lower():
            return ans
    return (
        "Based on the discovery dataset: Continuation friction is driven primarily by payment mandate synchronization failures, "
        "lack of self-serve pause/edit controls, and delayed support escalation [E0023, E0118]. For customized query exploration, "
        "verify the Gemini API key configuration."
    )
