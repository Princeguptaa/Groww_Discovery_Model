"""
Data loader module for Groww SIP Discovery Engine.

Loads all required data assets from data/ strictly with no root fallback.
All CSVs are loaded with keep_default_na=False to prevent pandas from turning
the valid label string "None" into NaN.
"""

from pathlib import Path
import json
import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@st.cache_data
def load_reviews() -> pd.DataFrame:
    """Load labelled_reviews.csv (1,809 rows x 26 cols) from data/ strictly."""
    file_path = DATA_DIR / "labelled_reviews.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"Required data file missing: {file_path}")
    df = pd.read_csv(file_path, keep_default_na=False)
    # Parse date column safely
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@st.cache_data
def load_opportunity_oracle() -> pd.DataFrame:
    """Load opportunity_table.csv (test oracle only) from data/ strictly."""
    file_path = DATA_DIR / "opportunity_table.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"Required data file missing: {file_path}")
    return pd.read_csv(file_path, keep_default_na=False)


@st.cache_data
def load_golden() -> pd.DataFrame:
    """Load golden_comparison.csv (30 rows) from data/ strictly."""
    file_path = DATA_DIR / "golden_comparison.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"Required data file missing: {file_path}")
    return pd.read_csv(file_path, keep_default_na=False)


@st.cache_data
def load_audit() -> pd.DataFrame:
    """Load audit_result.csv (40 rows) from data/ strictly."""
    file_path = DATA_DIR / "audit_result.csv"
    if not file_path.exists():
        raise FileNotFoundError(f"Required data file missing: {file_path}")
    return pd.read_csv(file_path, keep_default_na=False)


@st.cache_data
def load_funnel_inputs() -> dict:
    """Load funnel_inputs.json from data/ strictly."""
    file_path = DATA_DIR / "funnel_inputs.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Required data file missing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_evidence_notes() -> str:
    """Load evidence_notes.md content from data/ strictly."""
    file_path = DATA_DIR / "evidence_notes.md"
    if not file_path.exists():
        raise FileNotFoundError(f"Required data file missing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
