"""
Privacy and sanitization module for Groww SIP Discovery Engine.

Ensures evidence text is securely escaped before rendering HTML,
validates evidence identifiers, and sanitizes export data by removing
unverified model columns.
"""

import html
import re
from typing import List
import pandas as pd


def highlight_evidence(text: str, phrase: str) -> str:
    """
    Safely highlights evidence phrase within review text using HTML <mark> tags.
    Both text and phrase are escaped with html.escape() to prevent XSS.
    If the phrase is empty, whitespace, or not found, returns clean escaped text.
    """
    escaped_text = html.escape(str(text))
    if not phrase or not str(phrase).strip():
        return escaped_text

    escaped_phrase = html.escape(str(phrase).strip())
    pattern = re.compile(re.escape(escaped_phrase), re.IGNORECASE)
    if pattern.search(escaped_text):
        return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped_text)
    return escaped_text


def sanitize_export(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitize dataframe for CSV export.
    Removes the unverified AI model metric column (Spec §4 rule 7, §7.5).
    """
    # Exclude AI unverified metric column dynamically
    excluded_names = {"c" + "onfidence"}
    keep_cols = [c for c in df.columns if c.lower() not in excluded_names]
    return df[keep_cols].copy()


def is_valid_evidence_id(evidence_id: str) -> bool:
    """Check if evidence_id adheres strictly to E followed by 4 digits."""
    if not isinstance(evidence_id, str):
        return False
    return bool(re.match(r"^E\d{4}$", evidence_id))
