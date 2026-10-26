"""
Quality and audit module for Groww SIP Discovery Engine.

Computes agreement metrics, confusion matrices, and validation scores
against the 30-row human golden set and the 40-row second-model audit.
No reference values are hardcoded in application logic.
"""

from typing import Dict, Any
import pandas as pd


def compute_golden_metrics(golden_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute golden set agreement metrics (Spec §7.8).
    
    Uses ALL 30 rows for relevance agreement (including NOT_IN_MAIN_DATA rows).
    Stage, issue, and cause agreements are computed strictly on rows where h_relevant == 'Yes' (9 rows).
    Every metric returns count, total, percentage, and formatted denominator string.
    """
    total = len(golden_df)
    
    # 1. Relevance agreement across all 30 rows
    raw_agree = int((golden_df["relevant"] == golden_df["h_relevant"]).sum())
    raw_pct = round((raw_agree / total) * 100, 1) if total > 0 else 0.0

    final_agree = int((golden_df["relevant_final"] == golden_df["h_relevant"]).sum())
    final_pct = round((final_agree / total) * 100, 1) if total > 0 else 0.0

    # 2. Stage, issue, cause on h_relevant == 'Yes' rows
    h_yes = golden_df[golden_df["h_relevant"] == "Yes"]
    denom_yes = len(h_yes)

    stage_agree = int((h_yes["stage"] == h_yes["h_stage"]).sum())
    stage_pct = round((stage_agree / denom_yes) * 100, 1) if denom_yes > 0 else 0.0

    issue_agree = int((h_yes["issue"] == h_yes["h_issue"]).sum())
    issue_pct = round((issue_agree / denom_yes) * 100, 1) if denom_yes > 0 else 0.0

    cause_agree = int((h_yes["cause"] == h_yes["h_cause"]).sum())
    cause_pct = round((cause_agree / denom_yes) * 100, 1) if denom_yes > 0 else 0.0

    # Confusion matrix
    conf_raw = pd.crosstab(
        golden_df["h_relevant"],
        golden_df["relevant"],
        rownames=["Human Benchmark"],
        colnames=["AI Classification"],
    )
    conf_final = pd.crosstab(
        golden_df["h_relevant"],
        golden_df["relevant_final"],
        rownames=["Human Benchmark"],
        colnames=["AI Final (Post-Rule)"],
    )

    return {
        "total_rows": total,
        "denom_yes": denom_yes,
        "raw_relevance": {
            "agree": raw_agree,
            "total": total,
            "pct": raw_pct,
            "display": f"{raw_agree} / {total} ({raw_pct}%)",
        },
        "final_relevance": {
            "agree": final_agree,
            "total": total,
            "pct": final_pct,
            "display": f"{final_agree} / {total} ({final_pct}%)",
        },
        "stage": {
            "agree": stage_agree,
            "total": denom_yes,
            "pct": stage_pct,
            "display": f"{stage_agree} / {denom_yes} ({stage_pct}%)",
        },
        "issue": {
            "agree": issue_agree,
            "total": denom_yes,
            "pct": issue_pct,
            "display": f"{issue_agree} / {denom_yes} ({issue_pct}%)",
        },
        "cause": {
            "agree": cause_agree,
            "total": denom_yes,
            "pct": cause_pct,
            "display": f"{cause_agree} / {denom_yes} ({cause_pct}%)",
        },
        "confusion_raw": conf_raw,
        "confusion_final": conf_final,
    }


def compute_audit_metrics(audit_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute second-model audit metrics across 40 reviews (Spec §7.8).
    
    Evaluates primary AI model against a second AI model (Claude), not a human.
    Stage, issue, and cause agreement evaluated on rows where second_model_relevant == 'Yes'.
    Unsure counts as a mismatch.
    """
    total = len(audit_df)

    raw_agree = int((audit_df["ai_relevant"] == audit_df["second_model_relevant"]).sum())
    raw_pct = round((raw_agree / total) * 100, 1) if total > 0 else 0.0

    final_agree = int((audit_df["ai_relevant_after_rule"] == audit_df["second_model_relevant"]).sum())
    final_pct = round((final_agree / total) * 100, 1) if total > 0 else 0.0

    # Subset where second_model_relevant == 'Yes'
    sm_yes = audit_df[audit_df["second_model_relevant"] == "Yes"]
    denom_sm = len(sm_yes)

    stage_agree = int((sm_yes["ai_stage"] == sm_yes["second_model_stage"]).sum())
    stage_pct = round((stage_agree / denom_sm) * 100, 1) if denom_sm > 0 else 0.0

    issue_agree = int((sm_yes["ai_issue"] == sm_yes["second_model_issue"]).sum())
    issue_pct = round((issue_agree / denom_sm) * 100, 1) if denom_sm > 0 else 0.0

    cause_agree = int((sm_yes["ai_cause"] == sm_yes["second_model_cause"]).sum())
    cause_pct = round((cause_agree / denom_sm) * 100, 1) if denom_sm > 0 else 0.0

    return {
        "total_rows": total,
        "denom_sm_yes": denom_sm,
        "raw_relevance": {
            "agree": raw_agree,
            "total": total,
            "pct": raw_pct,
            "display": f"{raw_agree} / {total} ({raw_pct}%)",
        },
        "final_relevance": {
            "agree": final_agree,
            "total": total,
            "pct": final_pct,
            "display": f"{final_agree} / {total} ({final_pct}%)",
        },
        "stage": {
            "agree": stage_agree,
            "total": denom_sm,
            "pct": stage_pct,
            "display": f"{stage_agree} / {denom_sm} ({stage_pct}%)",
        },
        "issue": {
            "agree": issue_agree,
            "total": denom_sm,
            "pct": issue_pct,
            "display": f"{issue_agree} / {denom_sm} ({issue_pct}%)",
        },
        "cause": {
            "agree": cause_agree,
            "total": denom_sm,
            "pct": cause_pct,
            "display": f"{cause_agree} / {denom_sm} ({cause_pct}%)",
        },
    }
