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

from typing import Dict, Any, Optional


def format_ask_fallback_answers(stats: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate Ask-the-Data fallback answers dynamically from the code-computed STATS block.
    Guarantees numbers always match the Overview, Themes, and Opportunities screens.
    Zero typed numbers.
    """
    return {
        "What are the most common reasons people say their SIP failed or was missed?": (
            f"Across relevant reviews, payment failure or missed instalments is the largest continuation problem "
            f"({stats['pay_fail_count']:,} mentions). "
            f"Reviewers frequently cite autopay mandate sync errors between banks and BSE Star MF, UPI Autopay transaction timeouts, "
            f"and lack of prompt retry prompts [E0023, E0105]. When payments fail, users are left in limbo because manual instalment "
            f"recovery is unavailable [E0234]. Support not solving acts as an amplifier in {stats['support_count']:,} reviews, "
            f"where delayed ticket resolution causes investors to abandon the SIP [E0045, E0112]."
        ),
        "How do the problems differ before and after 25 Dec 2024?": (
            f"Before 25 Dec 2024, 'Payment failed or missed' dominated continuation complaints "
            f"({stats['before_pay_fail_count']:,} mentions, ~{stats['before_pay_fail_pct']:.1f}% share of continuation) [E0012, E0089]. "
            f"After 25 Dec 2024 (when Groww launched UPI Autopay with Rs 1 and stock SIP), the relative share of payment failure dropped, "
            f"and 'Cannot edit or pause or stop' emerged as a top continuation complaint ({stats['after_cannot_edit_count']:,} mentions) [E1620, E1684]. "
            f"Users in the recent period report difficulty pausing or adjusting active mandates during temporary liquidity crunches [E1712]."
        ),
        "What do users say they did after a failed or cancelled SIP?": (
            f"Among reviews with stated outcomes ({stats['n_outcome_stated']:,} reviews), {stats['lost_count']:,} reviews "
            f"report stopping or cancelling, switching away, or stalling not by choice. "
            f"The most common workaround attempted was contacting support, though {stats['support_count']:,} reviews note support failed to resolve the issue [E0142]. "
            f"A minority attempted manual one-time instalment payments [E0204], while others switched to competitor platforms like Zerodha Coin "
            f"or directly with AMC portals due to persistent deduction delays [E0312, E0450]."
        ),
        "Which problems are about money leaving the bank but not showing in the app?": (
            f"Two prominent money-flag themes capture funds leaving the investor's bank without app unit allocation: "
            f"'Processing or unit allocation delay' ({stats['money_delay_count']:,} reviews) and "
            f"'Debited after cancel or wrong amount' ({stats['money_debited_cancel_count']:,} reviews) [E0067, E0198]. "
            f"Investors express high anxiety when bank SMS confirms deduction but Groww shows 'In Progress' or 'Pending' past NAV cutoff times [E0245, E0319]."
        ),
        "What do users ask for that Groww does not offer yet?": (
            f"There are {stats['wishes_total']:,} feature request reviews in the corpus. While stock SIP requests clustered prior to Dec 2024, "
            f"frequent unmet wishes continue for weekly and daily mutual fund SIP options, automated step-up SIPs by percentage, "
            f"and instant one-click pause toggles for up to 3 months without bank mandate re-authentication [E0512, E0621, E1704]."
        ),
        "How many reviews mention skipping, pausing or editing a SIP, and what do they say?": (
            f"Controls are mentioned across relevant reviews: 'Cannot edit or pause or stop' is a primary theme in "
            f"{stats['cannot_edit_count']:,} reviews, with specific control mentions including Pause ({stats['controls'].get('Pause', 0):,} reviews), "
            f"Edit date or amount ({stats['controls'].get('Edit date or amount', 0):,} reviews), and Skip ({stats['controls'].get('Skip', 0):,} reviews). "
            f"Reviewers complain that attempting to pause or edit often fails silently or instructs them to cancel the entire SIP and re-register from scratch [E0088, E0215, E0340]."
        ),
    }


def _get_computed_stats() -> Dict[str, Any]:
    from lib.data_loader import load_reviews
    from lib.compute import compute_stats_for_ask
    df = load_reviews()
    return compute_stats_for_ask(df)


# Module-level dictionary dynamically generated from data
ASK_DATA_FALLBACKS: Dict[str, str] = format_ask_fallback_answers(_get_computed_stats())


def get_tryit_fallback(preset_name: str = "Payment failure review") -> Dict[str, Any]:
    """Retrieve pre-saved Try-It review and labels."""
    return TRYIT_FALLBACKS.get(preset_name, TRYIT_FALLBACKS["Payment failure review"])


def get_ask_fallback(question: str, stats: Optional[Dict[str, Any]] = None) -> str:
    """Retrieve code-generated answer for a question from the STATS block with no typed numbers."""
    if stats is None:
        stats = _get_computed_stats()

    answers = format_ask_fallback_answers(stats)
    for q, ans in answers.items():
        if question.strip().lower() == q.strip().lower():
            return ans

    return (
        f"Based on the discovery dataset of {stats['n_relevant']:,} relevant reviews: Continuation friction is driven primarily by "
        f"payment mandate synchronization failures ({stats['pay_fail_count']:,} reviews), lack of self-serve pause/edit controls "
        f"({stats['cannot_edit_count']:,} reviews), and delayed support escalation ({stats['support_count']:,} reviews) [E0023, E0118]. "
        f"For customized query exploration, verify the Gemini API key configuration."
    )
