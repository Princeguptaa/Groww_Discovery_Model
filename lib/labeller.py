"""
Labelling engine for Groww SIP Discovery Engine.
Ported from label_reviews.py with taxonomy schemas, normalisation,
four post-rules, and quality gating.
"""

from typing import Dict, Any, List

# Allowed taxonomy values (from label_reviews.py)
SCHEMA = {
    "relevant": ["Yes", "No", "Unsure"],
    "stage": [
        "Setting up",
        "First 3 months",
        "Mid-journey",
        "Pausing or stopping",
        "Restarting",
        "Not clear",
    ],
    "issue": [
        "Payment failed or missed",
        "Debited after cancel or wrong amount",
        "Cannot edit or pause or stop",
        "Support not solving",
        "Confused about status or dashboard",
        "Worried about returns",
        "Doubts about trust or timing",
        "Feature request",
        "Praise",
        "Cannot start or set up SIP",
        "Other",
    ],
    "cause": [
        "Money side",
        "Product side",
        "Market side",
        "Understanding side",
        "Not clear",
    ],
    "break_type": [
        "Payment failure",
        "Chose to stop",
        "Temporary break",
        "Not stated",
    ],
    "outcome": [
        "Still investing",
        "Paused",
        "Stopped or cancelled",
        "Switched away",
        "Unknown",
    ],
    "income_signal": ["Salaried", "Variable income", "Student", "Not stated"],
    "hypothesis": [
        "A controls not found",
        "B failed payment no recovery",
        "C amount does not fit money",
        "D chose to stop for other reasons",
        "None",
    ],
}

MULTI = {
    "controls_mentioned": [
        "Skip",
        "Edit date or amount",
        "Pause",
        "Step-up",
        "One-time payment",
        "Cancel",
        "None",
    ],
    "workarounds": [
        "Contacted support",
        "Paid one-time manually",
        "Re-created the SIP",
        "Switched to another app",
        "Asked online or friends",
        "Did nothing",
        "Not stated",
    ],
}

DEFAULTS = {
    "relevant": "Unsure",
    "stage": "Not clear",
    "issue": "Other",
    "cause": "Not clear",
    "break_type": "Not stated",
    "outcome": "Unknown",
    "income_signal": "Not stated",
    "hypothesis": "None",
}

LABEL_PROMPT = f"""You label Play Store reviews of the Groww app (English, Hindi or Hinglish).
Goal: understand why first-time investors fail to continue a mutual fund SIP.
Return one JSON object with these keys. Use ONLY the allowed options.

- relevant: {SCHEMA['relevant']}. Yes = about starting, running, failing, pausing or stopping a SIP. No = stocks, KYC only, general UI, or praise not about SIPs.
- stage: {SCHEMA['stage']}
- issue: {SCHEMA['issue']} (the single biggest point; 'Cannot start or set up SIP' = autopay setup trouble, KYC block, or the app failing when creating a SIP)
- cause: {SCHEMA['cause']}. Money side = balance, bank, income. Product side = app, mandate, support. Market side = returns, falls. Understanding side = confusion or wrong expectation.
- break_type: {SCHEMA['break_type']}
- outcome: {SCHEMA['outcome']}
- controls_mentioned: list from {MULTI['controls_mentioned']} (only controls the review actually mentions)
- workarounds: list from {MULTI['workarounds']}
- income_signal: {SCHEMA['income_signal']}. ONLY if the review says it. Never guess.
- hypothesis: {SCHEMA['hypothesis']}. Pick the one the review supports best, else None.
- evidence: the shortest phrase (max 10 words) copied from the review that supports your labels
- insight: one plain English sentence (max 15 words) on what this review shows

Rules:
1. Tag only what the text says. If unclear, use the unclear option.
2. If relevant is No: stage 'Not clear', cause 'Not clear', break_type 'Not stated', outcome 'Unknown', hypothesis None. The issue may be Praise, Feature request or Other.
3. A general rant with no event described gets stage "Not clear" and break_type "Not stated".
4. Never judge whether the user is right. Never give investment advice.
Return ONLY a valid JSON object."""


def normalise(d: Dict[str, Any]) -> Dict[str, Any]:
    """Force every AI output value into allowed options."""
    out = {}
    for k, allowed in SCHEMA.items():
        v = d.get(k, DEFAULTS.get(k, ""))
        out[k] = v if v in allowed else DEFAULTS.get(k, "")

    for k, allowed in MULTI.items():
        v = d.get(k) or []
        if isinstance(v, str):
            v = [v]
        valid_items = sorted({x for x in v if x in allowed})
        out[k] = "|".join(valid_items) or ("None" if k == "controls_mentioned" else "Not stated")

    out["evidence"] = str(d.get("evidence", "") or "")[:160]
    out["insight"] = str(d.get("insight", "") or "")[:200]

    if out["relevant"] == "No":
        out.update(
            {
                "stage": "Not clear",
                "cause": "Not clear",
                "break_type": "Not stated",
                "outcome": "Unknown",
                "hypothesis": "None",
            }
        )
    return out


def apply_post_rules(labels: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply the four deterministic post-rules (Spec §7.7, Implementation Plan Principle 8):
      Rule 1: relevant_final = 'No' when issue is 'Praise' or 'Feature request'.
      Rule 2: hypothesis_final = 'E setup or autopay blocked' when issue is 'Cannot start or set up SIP'.
      Rule 3: outcome_final = 'Stalled, not by choice' when break_type is 'Payment failure' and outcome is 'Paused'.
      Rule 4: hypothesis_final = 'None' when relevant_final is not 'Yes'.
    """
    res = dict(labels)

    # Rule 1
    if res.get("issue") in ["Praise", "Feature request"]:
        res["relevant_final"] = "No"
    else:
        res["relevant_final"] = res.get("relevant", "No")

    # Rule 2
    if res.get("issue") == "Cannot start or set up SIP":
        res["hypothesis_final"] = "E setup or autopay blocked"
    else:
        res["hypothesis_final"] = res.get("hypothesis", "None")

    # Rule 3
    if res.get("break_type") == "Payment failure" and res.get("outcome") == "Paused":
        res["outcome_final"] = "Stalled, not by choice"
    else:
        res["outcome_final"] = res.get("outcome", "Unknown")

    # Rule 4
    if res.get("relevant_final") != "Yes":
        res["hypothesis_final"] = "None"

    return res


def evaluate_quality_gate(labels: Dict[str, Any], review_text: str) -> Dict[str, str]:
    """
    Rule-based quality gate (Spec §7.7):
      - 'Not a SIP continuation event' for Praise or Feature request
      - 'Borderline. Needs a human check.' when relevant_final is Yes and:
          * issue is 'Other' or broad status tag
          * evidence phrase is missing in the review text
      - Otherwise: 'Valid SIP continuation event'
    """
    issue = labels.get("issue", "")
    relevant_final = labels.get("relevant_final", "No")
    evidence = labels.get("evidence", "").strip()

    if issue in ["Praise", "Feature request"] or relevant_final != "Yes":
        return {
            "status": "Not a SIP continuation event",
            "type": "info",
            "reason": f"Issue classified as {issue}; excluded from continuation friction.",
        }

    evidence_missing = evidence and (evidence.lower() not in review_text.lower())
    is_broad_status = issue == "Confused about status or dashboard"
    is_other = issue == "Other"

    if is_broad_status or is_other or evidence_missing:
        reasons = []
        if is_broad_status:
            reasons.append("broad status tag")
        if is_other:
            reasons.append("unspecified 'Other' issue")
        if evidence_missing:
            reasons.append("evidence phrase not found in original text")
        return {
            "status": "Borderline. Needs a human check.",
            "type": "warning",
            "reason": "; ".join(reasons),
        }

    return {
        "status": "Valid SIP continuation event",
        "type": "success",
        "reason": "Classified continuation friction with verified text evidence.",
    }
