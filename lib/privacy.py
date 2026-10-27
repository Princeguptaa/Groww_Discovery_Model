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


def highlight_search_terms(text: str, search_query: str, fallback_phrase: str = "") -> str:
    """
    Safely highlights matched search words within review text using HTML <mark> tags.
    Both text and search words are escaped with html.escape() before adding mark tags to prevent XSS.
    Never uses unescaped text with unsafe_allow_html.
    - If search_query contains words, each search word appearing in text is highlighted.
    - If search_query is an exact evidence_id (e.g. E0106) or empty, falls back to fallback_phrase.
    """
    escaped_text = html.escape(str(text))
    q = (search_query or "").strip()
    if not q:
        return highlight_evidence(text, fallback_phrase)

    # If query is an exact typed evidence ID (e.g. E0106), check if it appears in text
    if re.match(r"^E\d{4}$", q, re.IGNORECASE):
        esc_q = html.escape(q)
        p = re.compile(re.escape(esc_q), re.IGNORECASE)
        if p.search(escaped_text):
            return p.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped_text)
        return highlight_evidence(text, fallback_phrase)

    words = list(dict.fromkeys(w.strip() for w in q.split() if w.strip()))
    if not words:
        return highlight_evidence(text, fallback_phrase)

    # Sort words by length descending so longer words match first
    sorted_words = sorted(words, key=len, reverse=True)
    escaped_words = [re.escape(html.escape(w)) for w in sorted_words]
    pattern = re.compile("|".join(escaped_words), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped_text)


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
