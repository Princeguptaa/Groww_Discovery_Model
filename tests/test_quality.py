"""
Unit tests for lib/quality.py.
Validates golden set agreement, second-model audit metrics,
and confusion matrix integrity.
"""

from lib.data_loader import load_golden, load_audit
from lib.quality import compute_golden_metrics, compute_audit_metrics


def test_golden_metrics():
    golden_df = load_golden()
    metrics = compute_golden_metrics(golden_df)

    assert metrics["total_rows"] == 30
    assert metrics["denom_yes"] == 9

    assert metrics["raw_relevance"]["agree"] == 15
    assert metrics["raw_relevance"]["total"] == 30

    assert metrics["final_relevance"]["agree"] == 26
    assert metrics["final_relevance"]["total"] == 30

    assert metrics["stage"]["agree"] == 7
    assert metrics["stage"]["total"] == 9

    assert metrics["issue"]["agree"] == 7
    assert metrics["issue"]["total"] == 9

    assert metrics["cause"]["agree"] == 9
    assert metrics["cause"]["total"] == 9

    # Confusion matrix sum
    assert metrics["confusion_raw"].values.sum() == 30
    assert metrics["confusion_final"].values.sum() == 30


def test_audit_metrics():
    audit_df = load_audit()
    metrics = compute_audit_metrics(audit_df)

    assert metrics["total_rows"] == 40
    assert metrics["denom_sm_yes"] == 13

    assert metrics["raw_relevance"]["agree"] == 24
    assert metrics["raw_relevance"]["total"] == 40

    assert metrics["final_relevance"]["agree"] == 36
    assert metrics["final_relevance"]["total"] == 40

    assert metrics["stage"]["agree"] == 9
    assert metrics["stage"]["total"] == 13

    assert metrics["issue"]["agree"] == 9
    assert metrics["issue"]["total"] == 13

    assert metrics["cause"]["agree"] == 11
    assert metrics["cause"]["total"] == 13
