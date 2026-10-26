"""
Unit tests for lib/privacy.py.
Validates safe HTML evidence highlighting, XSS prevention,
CSV export sanitization (omitting unverified model columns), and ID validation.
"""

import pandas as pd
from lib.privacy import (
    highlight_evidence,
    sanitize_export,
    is_valid_evidence_id,
)


def test_highlight_evidence_basic():
    text = "Groww stopped my SIP without notification"
    phrase = "stopped my SIP"
    result = highlight_evidence(text, phrase)
    assert "<mark>stopped my SIP</mark>" in result


def test_highlight_evidence_case_insensitive():
    text = "Payment failed on my account"
    phrase = "payment failed"
    result = highlight_evidence(text, phrase)
    assert "<mark>Payment failed</mark>" in result


def test_highlight_evidence_xss_safety():
    malicious_text = "<script>alert('hack')</script> SIP failed"
    malicious_phrase = "<script>alert('hack')</script>"
    result = highlight_evidence(malicious_text, malicious_phrase)
    # Ensure raw script tags are strictly escaped
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "<mark>&lt;script&gt;alert(&#x27;hack&#x27;)&lt;/script&gt;</mark>" in result


def test_highlight_evidence_missing_phrase():
    text = "Everything was normal"
    phrase = "totally different string"
    result = highlight_evidence(text, phrase)
    assert "<mark>" not in result
    assert result == "Everything was normal"


def test_highlight_evidence_empty_phrase():
    text = "Normal review text"
    assert highlight_evidence(text, "") == "Normal review text"
    assert highlight_evidence(text, "   ") == "Normal review text"
    assert highlight_evidence(text, None) == "Normal review text"


def test_sanitize_export_drops_unverified_column():
    df = pd.DataFrame(
        {
            "evidence_id": ["E0001"],
            "theme": ["Payment failed"],
            "confidence": ["High"],
        }
    )
    sanitized = sanitize_export(df)
    assert "confidence" not in sanitized.columns
    assert "evidence_id" in sanitized.columns
    assert "theme" in sanitized.columns


def test_is_valid_evidence_id():
    assert is_valid_evidence_id("E0001") is True
    assert is_valid_evidence_id("E1809") is True
    assert is_valid_evidence_id("E12") is False
    assert is_valid_evidence_id("NOT_IN_MAIN_DATA") is False
    assert is_valid_evidence_id(123) is False
