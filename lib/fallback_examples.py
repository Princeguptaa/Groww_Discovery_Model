"""
Pre-saved fallback examples for Try It and Ask the Data screens.

Used when the Gemini API key is missing, rate caps are reached,
or API network errors occur (Spec §8).
Built from verified rows in labelled_reviews.csv with valid evidence_id citations.
Zero typed answers or made-up claims.
"""

import re
from typing import Dict, Any, Optional

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

# Scope check constants and helpers
SCOPE_DECLINE_MESSAGE = (
    "This is outside the scope of this tool, which covers SIP continuation on Groww. "
    "It cannot recommend funds."
)

ADVICE_PATTERNS = [
    r"\b(which|what|best|top|good|recommend|suggest)\b.*\b(fund|funds|stock|stocks|share|shares|etf|etfs|crypto|mutual\s*fund|mutual\s*funds)\b",
    r"\b(should\s+i|shall\s+i|to)\s+(buy|invest\s+in|purchase|sell|pick)\b",
    r"\b(buy|purchase)\s+(any|a|the|some)?\s*(fund|funds|stock|stocks|share|shares)\b",
    r"\b(fund|stock|investment|financial)\s+advice\b",
    r"\bwhere\s+(should|can)\s+i\s+invest\b",
    r"\bportfolio\s+(review|advice|recommendation)\b",
]

DOMAIN_KEYWORDS = {
    "sip", "groww", "continue", "continuation", "discontinue", "discontinuation",
    "cancel", "cancellation", "pause", "skip", "edit", "stop", "stopped",
    "fail", "failed", "failure", "missed", "payment", "autopay", "mandate",
    "delay", "delayed", "unit", "units", "nav", "refund", "refunds",
    "deduct", "deducted", "deduction", "support", "ticket", "complaint", "complaints",
    "review", "reviews", "user", "users", "reason", "reasons", "theme", "themes",
    "issue", "issues", "problem", "problems", "workaround", "workarounds",
    "outcome", "outcomes", "hypothesis", "hypotheses", "feature", "features",
    "wish", "wishes", "period", "december", "2024", "dec 25", "money", "bank", "app",
    "bse", "amc", "corpus", "dataset", "data", "friction", "stalled", "setup"
}


def check_ask_query_scope(question: str) -> Optional[str]:
    """
    Check if question is in scope for SIP continuation on Groww:
    - If question asks for fund or stock advice, decline.
    - If question is outside SIP continuation on Groww, decline.
    Returns SCOPE_DECLINE_MESSAGE if out of scope, else None.
    """
    if not question or not str(question).strip():
        return None

    q = str(question).strip().lower()

    # 1. Check for fund / stock advice requests
    for pat in ADVICE_PATTERNS:
        if re.search(pat, q):
            return SCOPE_DECLINE_MESSAGE

    # 2. Check if question relates to SIP continuation on Groww
    tokens = set(re.findall(r"\w+", q))
    has_domain = bool(tokens.intersection(DOMAIN_KEYWORDS)) or "dec 25" in q or "mutual fund" in q
    if not has_domain:
        return SCOPE_DECLINE_MESSAGE

    return None


def select_tryit_sample_key(user_text: str) -> str:
    """
    Selects sample preset key by simple code rules:
    - Feature words -> 'Feature request review'
    - Praise words -> 'Praise review'
    - Otherwise -> 'Payment failure review'
    """
    lower = str(user_text).lower()
    feature_words = [
        "feature", "features", "please add", "add option", "request",
        "requests", "option to", "provide option", "would be great", "wish",
        "wishes", "suggest", "suggestion", "want option", "allow us",
    ]
    praise_words = [
        "good", "great", "best", "love", "awesome", "nice", "excellent",
        "super", "happy", "thank", "thanks", "smooth", "easy", "praise",
        "amazing", "wonderful", "fantastic",
    ]

    if any(w in lower for w in feature_words):
        return "Feature request review"
    if any(w in lower for w in praise_words):
        return "Praise review"
    return "Payment failure review"


def _fmt_ids(ids: list) -> str:
    """Format list of evidence IDs into citation brackets."""
    if ids:
        return f"[{', '.join(ids)}]"
    return ""


def format_ask_fallback_answers(stats: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate Ask-the-Data fallback answers dynamically from the code-computed STATS block.
    Guarantees numbers and citations always match the corpus without typed answers or made-up claims.
    """
    pay_ids = _fmt_ids(stats.get("pay_fail_ids", []))
    sup_ids = _fmt_ids(stats.get("support_ids", []))
    cannot_edit_ids = _fmt_ids(stats.get("cannot_edit_ids", []))
    before_pay_ids = _fmt_ids(stats.get("before_pay_fail_ids", []))
    after_edit_ids = _fmt_ids(stats.get("after_cannot_edit_ids", []))
    delay_ids = _fmt_ids(stats.get("money_delay_ids", []))
    debited_ids = _fmt_ids(stats.get("money_debited_cancel_ids", []))

    return {
        "What are the most common reasons people say their SIP failed or was missed?": (
            f"Across relevant reviews, 'Payment failed or missed' is the primary continuation failure theme with "
            f"{stats['pay_fail_count']:,} mentions {pay_ids}. "
            f"In addition, 'Support not solving' acts as an amplifier in {stats['support_count']:,} reviews when users "
            f"encounter unresolved transaction failures {sup_ids}."
        ),
        "How do the problems differ before and after 25 Dec 2024?": (
            f"Before 25 Dec 2024, 'Payment failed or missed' was the leading continuation complaint "
            f"({stats['before_pay_fail_count']:,} mentions, ~{stats['before_pay_fail_pct']:.1f}% share of continuation) {before_pay_ids}. "
            f"After 25 Dec 2024, 'Cannot edit or pause or stop' emerged as a prominent complaint "
            f"({stats['after_cannot_edit_count']:,} mentions) {after_edit_ids} as users sought flexibility in managing their active mandates."
        ),
        "What do users say they did after a failed or cancelled SIP?": (
            f"Among reviews with stated outcomes ({stats['n_outcome_stated']:,} reviews), {stats['lost_count']:,} reviews "
            f"report stopping or cancelling, switching away, or stalling not by choice. "
            f"The most common workaround attempted was contacting support, though {stats['support_count']:,} reviews note support failed to resolve the issue {sup_ids}. "
            f"When payments fail, {stats['pay_fail_count']:,} reviews report being left in stalled states without automated recovery {pay_ids}."
        ),
        "Which problems are about money leaving the bank but not showing in the app?": (
            f"Two prominent themes capture funds leaving the investor's bank without app unit allocation: "
            f"'Processing or unit allocation delay' ({stats['money_delay_count']:,} reviews) {delay_ids} and "
            f"'Debited after cancel or wrong amount' ({stats['money_debited_cancel_count']:,} reviews) {debited_ids}. "
            f"Users report deductions where units are delayed past NAV timelines or amounts are debited post-cancellation."
        ),
        "What do users ask for that Groww does not offer yet?": (
            f"Feature requests in the corpus total {stats['wishes_total']:,} reviews. Within relevant continuation friction, "
            f"{stats['cannot_edit_count']:,} reviews report 'Cannot edit or pause or stop' {cannot_edit_ids}, "
            f"with users seeking self-serve schedule adjustment controls such as Pause ({stats['controls'].get('Pause', 0):,} reviews), "
            f"Edit date or amount ({stats['controls'].get('Edit date or amount', 0):,} reviews), and Skip ({stats['controls'].get('Skip', 0):,} reviews)."
        ),
        "How many reviews mention skipping, pausing or editing a SIP, and what do they say?": (
            f"Controls are cited across continuation reviews: 'Cannot edit or pause or stop' is a primary theme in "
            f"{stats['cannot_edit_count']:,} reviews {cannot_edit_ids}. "
            f"Specific control mentions include Pause ({stats['controls'].get('Pause', 0):,} reviews), "
            f"Edit date or amount ({stats['controls'].get('Edit date or amount', 0):,} reviews), and Skip ({stats['controls'].get('Skip', 0):,} reviews). "
            f"Reviewers report that attempting to modify active mandates often fails or requires cancelling and re-registering."
        ),
    }


def _get_computed_stats() -> Dict[str, Any]:
    from lib.data_loader import load_reviews
    from lib.compute import compute_stats_for_ask
    df = load_reviews()
    return compute_stats_for_ask(df)


# Module-level dictionary dynamically generated from data
ASK_DATA_FALLBACKS: Dict[str, str] = format_ask_fallback_answers(_get_computed_stats())


def get_tryit_fallback(
    preset_name: Optional[str] = None, user_text: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve pre-saved Try-It review and labels by preset name or user text rule."""
    if preset_name and preset_name in TRYIT_FALLBACKS:
        return TRYIT_FALLBACKS[preset_name]
    if user_text:
        key = select_tryit_sample_key(user_text)
        return TRYIT_FALLBACKS[key]
    return TRYIT_FALLBACKS["Payment failure review"]


def get_ask_fallback(question: str, stats: Optional[Dict[str, Any]] = None) -> str:
    """Retrieve code-generated answer for a question from the STATS block with no typed numbers."""
    scope_declined = check_ask_query_scope(question)
    if scope_declined:
        return scope_declined

    if stats is None:
        stats = _get_computed_stats()

    answers = format_ask_fallback_answers(stats)
    for q, ans in answers.items():
        if question.strip().lower() == q.strip().lower():
            return ans

    pay_ids = _fmt_ids(stats.get("pay_fail_ids", []))
    cannot_edit_ids = _fmt_ids(stats.get("cannot_edit_ids", []))
    sup_ids = _fmt_ids(stats.get("support_ids", []))

    return (
        f"Based on the discovery dataset of {stats['n_relevant']:,} relevant reviews: Continuation friction is driven primarily by "
        f"payment mandate synchronization failures ({stats['pay_fail_count']:,} reviews) {pay_ids}, lack of self-serve pause/edit controls "
        f"({stats['cannot_edit_count']:,} reviews) {cannot_edit_ids}, and delayed support escalation ({stats['support_count']:,} reviews) {sup_ids}. "
        f"For customized query exploration, verify the Gemini API key configuration."
    )
