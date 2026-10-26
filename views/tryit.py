"""
Try It screen view module for Groww SIP Discovery Engine.
Displays:
1. Review text input box (max 600 chars) with privacy warning
2. Sample review preset buttons
3. Real-time AI classification with taxonomy normalization and 4 post-rules
4. Quality gate evaluation (Valid / Borderline / Not continuation)
5. Session and daily rate-limit monitoring
"""

import streamlit as st
from lib.ai_client import call_ai_label, MAX_SESSION_CALLS
from lib.labeller import evaluate_quality_gate
from lib.fallback_examples import TRYIT_FALLBACKS
from lib.constants import TRYIT_WARNING, HYPOTHESIS_NOTE


def render_tryit():
    st.title("Try the Labeller")
    st.caption("Test the automated review classification engine on custom or sample review text.")

    # 1. Privacy Warning (Spec §7.7)
    st.warning(f"⚠️ **Security Notice:** {TRYIT_WARNING}")

    # Session quota indicator
    session_calls = st.session_state.get("ai_call_count", 0)
    st.caption(f"Session AI usage: **{session_calls} / {MAX_SESSION_CALLS}** calls")

    # Sample preset buttons
    st.markdown("**Or load a verified sample review:**")
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    
    preset_chosen = None
    with btn_col1:
        if st.button("Sample: Payment Failure"):
            preset_chosen = "Payment failure review"
    with btn_col2:
        if st.button("Sample: Praise (Non-SIP)"):
            preset_chosen = "Praise review"
    with btn_col3:
        if st.button("Sample: Feature Request"):
            preset_chosen = "Feature request review"

    if preset_chosen:
        st.session_state["tryit_input_text"] = TRYIT_FALLBACKS[preset_chosen]["text"]

    default_text = st.session_state.get(
        "tryit_input_text",
        TRYIT_FALLBACKS["Payment failure review"]["text"],
    )

    # 2. Text Input Box (Max 600 characters, Spec §7.7)
    review_input = st.text_area(
        "Paste Play Store review text below (max 600 characters):",
        value=default_text,
        max_chars=600,
        height=130,
        key="tryit_text_area",
    )

    if st.button("Classify Review", type="primary"):
        clean_input = review_input.strip()
        if not clean_input:
            st.error("Please enter review text before submitting.")
            return

        with st.spinner("Classifying review with taxonomy and post-rules..."):
            labels, is_live, msg = call_ai_label(clean_input)

        # Status notification
        if is_live:
            st.success(msg)
        else:
            st.info(f"ℹ️ {msg}")

        # Broad tag rewrite for Try It (Spec §7.7)
        displayed_issue = labels.get("issue", "")
        if displayed_issue == "Confused about status or dashboard":
            displayed_issue = "Status or dashboard (broad tag, not split in Try it)"

        # Quality Gate Evaluation (Spec §7.7)
        gate = evaluate_quality_gate(labels, clean_input)
        if gate["type"] == "success":
            st.success(f"**Quality Gate:** {gate['status']} — {gate['reason']}")
        elif gate["type"] == "warning":
            st.warning(f"**Quality Gate:** {gate['status']} — {gate['reason']}")
        else:
            st.info(f"**Quality Gate:** {gate['status']} — {gate['reason']}")

        st.markdown("### Classification Results")

        r_col1, r_col2, r_col3 = st.columns(3)
        with r_col1:
            st.markdown(
                f"""
                <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; background: #F8FAFC;">
                    <div style="font-size: 14px; font-weight: 700; color: #64748B;">RELEVANCE & STAGE</div>
                    <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">{labels.get('relevant_final', 'No')}</div>
                    <div style="font-size: 14px; color: #334155;"><b>Raw:</b> {labels.get('relevant', 'No')}</div>
                    <div style="font-size: 14px; color: #334155;"><b>Stage:</b> {labels.get('stage', 'Not clear')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r_col2:
            st.markdown(
                f"""
                <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; background: #F8FAFC;">
                    <div style="font-size: 14px; font-weight: 700; color: #64748B;">FRICTION & CAUSE</div>
                    <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">{displayed_issue}</div>
                    <div style="font-size: 14px; color: #334155;"><b>Cause:</b> {labels.get('cause', 'Not clear')}</div>
                    <div style="font-size: 14px; color: #334155;"><b>Break Type:</b> {labels.get('break_type', 'Not stated')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with r_col3:
            st.markdown(
                f"""
                <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; background: #F8FAFC;">
                    <div style="font-size: 14px; font-weight: 700; color: #64748B;">OUTCOME & HYPOTHESIS</div>
                    <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">{labels.get('outcome_final', 'Unknown')}</div>
                    <div style="font-size: 14px; color: #334155;"><b>Raw Outcome:</b> {labels.get('outcome', 'Unknown')}</div>
                    <div style="font-size: 14px; color: #334155;"><b>Hypothesis:</b> {labels.get('hypothesis_final', 'None')} (directional)</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 8px; padding: 14px; margin-top: 14px; background: #FFFFFF;">
                <div style="font-size: 14px; color: #1E293B; margin-bottom: 6px;">
                    <b>Extracted Evidence:</b> <i>"{labels.get('evidence', 'None')}"</i>
                </div>
                <div style="font-size: 14px; color: #1E293B; margin-bottom: 6px;">
                    <b>Key Insight:</b> {labels.get('insight', 'None')}
                </div>
                <div style="font-size: 14px; color: #64748B; border-top: 1px solid #E2E8F0; padding-top: 6px;">
                    Controls mentioned: <b>{labels.get('controls_mentioned', 'None')}</b> &nbsp;|&nbsp; 
                    Workarounds: <b>{labels.get('workarounds', 'Not stated')}</b> &nbsp;|&nbsp; 
                    Income signal: <b>{labels.get('income_signal', 'Not stated')}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
