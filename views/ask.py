"""
Ask the Data screen view module for Groww SIP Discovery Engine.
Displays:
1. Question text input with 6 suggested discovery questions
2. Code-generated STATS block (no AI hallucination of metrics)
3. Keyword-ranked contextual review examples (max 150)
4. Citation validation against provided evidence_ids
5. Rate-limiting monitoring and seamless fallback mode
"""

import re
from typing import Tuple, Set
import streamlit as st
import pandas as pd
from lib.data_loader import load_reviews
from lib.ai_client import call_ai_ask, MAX_SESSION_CALLS
from lib.compute import compute_stats_for_ask
from lib.fallback_examples import ASK_DATA_FALLBACKS

SUGGESTED_QUESTIONS = [
    "What are the most common reasons people say their SIP failed or was missed?",
    "How do the problems differ before and after 25 Dec 2024?",
    "What do users say they did after a failed or cancelled SIP?",
    "Which problems are about money leaving the bank but not showing in the app?",
    "What do users ask for that Groww does not offer yet?",
    "How many reviews mention skipping, pausing or editing a SIP, and what do they say?",
]


def _build_stats_block(df: pd.DataFrame) -> Tuple[str, dict]:
    """Computes exact dataset distribution numbers in code."""
    stats_dict = compute_stats_for_ask(df)

    lines = [
        f"Total relevant reviews: {stats_dict['n_relevant']:,}",
        f"Distribution by period: {stats_dict['period_dist']}",
        f"Top themes: {dict(list(stats_dict['theme_counts'].items())[:10])}",
        f"Payment failed mentions: {stats_dict['pay_fail_count']:,}",
        f"Support not solving mentions: {stats_dict['support_count']:,}",
        f"Cannot edit or pause or stop mentions: {stats_dict['cannot_edit_count']:,}",
        f"Break types: {stats_dict['break_types']}",
        f"Stated outcomes: {stats_dict['outcomes']}",
        f"Lost count among stated outcomes: {stats_dict['lost_count']:,} of {stats_dict['n_outcome_stated']:,}",
        f"Hypotheses (directional): {stats_dict['hypotheses']}",
        f"Total feature requests (wishes): {stats_dict['wishes_total']:,} reviews",
        f"Controls mentioned: {stats_dict['controls']}",
    ]
    return "\n".join(lines), stats_dict


def _get_context_examples(
    df: pd.DataFrame, question: str, max_count: int = 150
) -> Tuple[str, Set[str]]:
    """Ranks and formats up to 150 evidence examples based on keyword overlap."""
    rel_df = df[df["relevant_final"] == "Yes"].copy()
    tokens = set(re.findall(r"\w+", question.lower())) - {
        "what", "are", "the", "how", "do", "and", "in", "is", "of", "to", "a", "or", "for", "say", "saying"
    }

    def overlap_score(text: str) -> int:
        words = set(re.findall(r"\w+", str(text).lower()))
        return len(tokens.intersection(words))

    rel_df["score"] = rel_df["text"].apply(overlap_score)
    ranked = rel_df.sort_values("score", ascending=False).head(max_count)

    allowed_ids = set(ranked["evidence_id"].tolist())
    lines = [
        f"[{row['evidence_id']}] ({row['theme']}): {str(row['text'])[:280]}"
        for _, row in ranked.iterrows()
    ]
    return "\n".join(lines), allowed_ids


def render_ask():
    st.title("Ask the Data")
    st.caption("Query the SIP continuation evidence corpus. All numbers are computed by code; AI provides contextual synthesis.")

    # Session quota indicator
    session_calls = st.session_state.get("ai_call_count", 0)
    st.caption(f"Session AI usage: **{session_calls} / {MAX_SESSION_CALLS}** calls")

    df = load_reviews()

    # Suggested Questions (Spec §7.6)
    st.markdown("**Suggested Discovery Questions:**")
    q_cols = st.columns(2)
    
    selected_question = None
    for idx, q_text in enumerate(SUGGESTED_QUESTIONS):
        col = q_cols[idx % 2]
        with col:
            if st.button(f"💡 {q_text}", key=f"q_btn_{idx}"):
                selected_question = q_text

    if selected_question:
        st.session_state["ask_input_text"] = selected_question

    current_query = st.session_state.get(
        "ask_input_text",
        SUGGESTED_QUESTIONS[0],
    )

    user_query = st.text_input(
        "Enter your question regarding SIP discontinuation:",
        value=current_query,
        key="ask_query_input",
    )

    if st.button("Query Corpus", type="primary"):
        clean_query = user_query.strip()
        if not clean_query:
            st.error("Please enter a question.")
            return

        with st.spinner("Synthesizing answer from verified evidence quotes and stats..."):
            stats_block, stats_dict = _build_stats_block(df)
            examples_block, allowed_ids = _get_context_examples(df, clean_query)
            answer, is_live, msg = call_ai_ask(
                clean_query, stats_block, examples_block, allowed_ids, stats_dict=stats_dict
            )

        if is_live:
            st.success(msg)
        else:
            st.info(f"ℹ️ {msg}")

        st.markdown("### Answer")
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 18px; background: #F8FAFC; line-height: 1.6; font-size: 15px; color: #0F172A;">
                {answer}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption("Citations formatted as `[E####]` reference verified review IDs in the evidence database.")
