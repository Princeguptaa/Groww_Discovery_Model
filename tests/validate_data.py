"""
Reference-value assertions and schema validation tests.
These values come from engine_spec.md section 9 and ARCHITECTURE.md section 8.1.
They exist only in this test file, never hardcoded in app code.
"""

from pathlib import Path
import re
import pytest
from lib.data_loader import (
    load_reviews,
    load_golden,
    load_audit,
    load_funnel_inputs,
    load_evidence_notes,
    DATA_DIR,
)

BASE_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def reviews_df():
    return load_reviews()


@pytest.fixture(scope="module")
def golden_df():
    return load_golden()


@pytest.fixture(scope="module")
def audit_df():
    return load_audit()


def test_total_rows(reviews_df):
    """Reference check: labelled_reviews.csv has exactly 1,809 rows."""
    assert len(reviews_df) == 1809


def test_relevant_final_yes(reviews_df):
    """Reference check: relevant_final == 'Yes' has exactly 721 rows."""
    assert (reviews_df["relevant_final"] == "Yes").sum() == 721


def test_relevant_before(reviews_df):
    """Reference check: relevant_final == 'Yes' Before 25 Dec 2024 is 513 rows."""
    before = reviews_df[reviews_df["period"] == "Before 25 Dec 2024"]
    assert (before["relevant_final"] == "Yes").sum() == 513


def test_relevant_after(reviews_df):
    """Reference check: relevant_final == 'Yes' After 25 Dec 2024 is 208 rows."""
    after = reviews_df[reviews_df["period"] == "After 25 Dec 2024"]
    assert (after["relevant_final"] == "Yes").sum() == 208


def test_golden_rows(golden_df):
    """Reference check: golden_comparison.csv has exactly 30 rows."""
    assert len(golden_df) == 30


def test_audit_rows(audit_df):
    """Reference check: audit_result.csv has exactly 40 rows."""
    assert len(audit_df) == 40


def test_evidence_id_format(reviews_df):
    """Every evidence_id matches E followed by 4 digits and is unique."""
    assert reviews_df["evidence_id"].str.match(r"^E\d{4}$").all()
    assert reviews_df["evidence_id"].is_unique


def test_data_files_location_strictly_data_dir():
    """Data files must exist in data/ only with no root duplicates."""
    required_files = [
        "labelled_reviews.csv",
        "opportunity_table.csv",
        "golden_comparison.csv",
        "audit_result.csv",
        "funnel_inputs.json",
        "evidence_notes.md",
    ]
    for filename in required_files:
        data_path = DATA_DIR / filename
        root_path = BASE_DIR / filename
        assert data_path.exists(), f"File missing from data/: {filename}"
        assert not root_path.exists(), f"Data file must NOT exist in root: {filename}"


def test_no_confidence_rendered():
    """Code search: confidence column is never rendered in views or app.py."""
    code_files = list((BASE_DIR / "views").glob("*.py")) + [BASE_DIR / "app.py"]
    for file_path in code_files:
        content = file_path.read_text(encoding="utf-8")
        # Check for direct rendering of confidence column
        assert '["confidence"]' not in content, f"Direct confidence access in {file_path}"
        assert "['confidence']" not in content, f"Direct confidence access in {file_path}"


def test_no_hardcoded_funnel_counts():
    """Code search: assert no hardcoded funnel reference counts in app or views."""
    code_files = list((BASE_DIR / "views").glob("*.py")) + [BASE_DIR / "app.py"]
    pattern = re.compile(r"\b(1809|721|513|208)\b")
    for file_path in code_files:
        content = file_path.read_text(encoding="utf-8")
        matches = pattern.findall(content)
        assert len(matches) == 0, f"Found hardcoded counts {matches} in {file_path}"
