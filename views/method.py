"""
Method and Quality screen view module for Groww SIP Discovery Engine.
Displays:
1. 5-step data and research pipeline
2. Human golden-set benchmark (30 reviews) with confusion matrix
3. Second-model audit metrics (40 reviews)
4. Field verification level matrix
5. Rendered evidence notes ("Where the AI was wrong")
6. Study limits and corpus constraints
"""

import streamlit as st
import pandas as pd
from lib.data_loader import (
    load_reviews,
    load_golden,
    load_audit,
    load_evidence_notes,
    load_funnel_inputs,
)
from lib.quality import compute_golden_metrics, compute_audit_metrics


def render_method():
    st.title("Methodology & Model Quality")
    st.caption("Verification benchmarks, error analysis, and boundary constraints for the discovery engine.")

    df = load_reviews()
    golden_df = load_golden()
    audit_df = load_audit()
    funnel_inputs = load_funnel_inputs()
    notes_markdown = load_evidence_notes()

    golden_metrics = compute_golden_metrics(golden_df)
    audit_metrics = compute_audit_metrics(audit_df)

    # 1. Pipeline in 5 Steps (Spec §7.8)
    st.subheader("1. Five-Step Discovery Pipeline")
    
    total_reviews_pulled = funnel_inputs.get("reviews_pulled", 0)
    total_sip_unique = funnel_inputs.get("sip_word_unique", 0)
    total_labelled = (df["relevant"] != "").sum()
    total_relevant = (df["relevant_final"] == "Yes").sum()

    p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
    with p_col1:
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; background: #F8FAFC;">
                <div style="font-size: 14px; font-weight: 700; color: #64748B;">STEP 1: COLLECT</div>
                <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">{total_reviews_pulled:,}</div>
                <div style="font-size: 14px; color: #475569;">Play Store app reviews scraped across periods.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p_col2:
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; background: #F8FAFC;">
                <div style="font-size: 14px; font-weight: 700; color: #64748B;">STEP 2: FILTER</div>
                <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">{total_sip_unique:,}</div>
                <div style="font-size: 14px; color: #475569;">Unique deduplicated reviews mentioning SIP.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p_col3:
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; background: #F8FAFC;">
                <div style="font-size: 14px; font-weight: 700; color: #64748B;">STEP 3: LABEL</div>
                <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">{total_labelled:,}</div>
                <div style="font-size: 14px; color: #475569;">AI-classified reviews with normalized taxonomy.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p_col4:
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; background: #F8FAFC;">
                <div style="font-size: 14px; font-weight: 700; color: #64748B;">STEP 4: CHECK</div>
                <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">70 Audited</div>
                <div style="font-size: 14px; color: #475569;">30 reviews labelled by the researcher: the first list was drafted with AI help, then every label was reviewed and confirmed or changed + 40 second-model audits.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p_col5:
        st.markdown(
            f"""
            <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; background: #F8FAFC;">
                <div style="font-size: 14px; font-weight: 700; color: #64748B;">STEP 5: RANK</div>
                <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin: 4px 0;">{total_relevant:,} Relevant</div>
                <div style="font-size: 14px; color: #475569;">Opportunity scoring and loss prioritization.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 2. Golden Set Benchmark (Spec §7.8)
    st.subheader("2. Human Golden-Set Benchmark (30 Reviews)")
    st.caption(
        "Benchmarked against 30 reviews labelled by the researcher: the first list was drafted with AI help, then every label was reviewed and confirmed or changed. "
        "Includes 8 reviews (evidence_id = NOT_IN_MAIN_DATA) that lack the word 'SIP' but possess valid continuation labels. "
        "Stage, issue, and cause agreement are evaluated strictly on rows where Human Benchmark = 'Yes' (9 reviews)."
    )

    g_col1, g_col2, g_col3, g_col4 = st.columns(4)
    with g_col1:
        st.metric(
            label="Raw Relevance Agreement",
            value=golden_metrics["raw_relevance"]["display"],
            help="AI raw relevant vs Human benchmark across all 30 rows",
        )
    with g_col2:
        st.metric(
            label="Post-Rule Relevance",
            value=golden_metrics["final_relevance"]["display"],
            delta="+36.7% after Praise/Feature rule",
            help="relevant_final vs Human benchmark across all 30 rows",
        )
    with g_col3:
        st.metric(
            label="Stage Agreement",
            value=golden_metrics["stage"]["display"],
            help="Stage agreement on h_relevant == Yes (9 reviews)",
        )
    with g_col4:
        st.metric(
            label="Cause Agreement",
            value=golden_metrics["cause"]["display"],
            help="Cause agreement on h_relevant == Yes (9 reviews)",
        )

    st.markdown("#### Golden Set Confusion Matrix (Relevance: Raw vs Final)")
    cf_col1, cf_col2 = st.columns(2)
    with cf_col1:
        st.markdown("**Raw AI Output vs Human Benchmark:**")
        st.dataframe(golden_metrics["confusion_raw"], use_container_width=True)
    with cf_col2:
        st.markdown("**Post-Rule Final Output vs Human Benchmark:**")
        st.dataframe(golden_metrics["confusion_final"], use_container_width=True)

    st.markdown("---")

    # 3. Second-Model Audit (Spec §7.8)
    st.subheader("3. Second-Model Audit (40 Reviews)")
    st.caption(
        "Benchmarked against a second AI model (Claude), not a human. "
        "Unsure classifications count as mismatches. "
        "Stage, issue, and cause agreement are evaluated on rows where Second Model = 'Yes' (13 reviews)."
    )

    a_col1, a_col2, a_col3, a_col4 = st.columns(4)
    with a_col1:
        st.metric(
            label="Raw Relevance Agreement",
            value=audit_metrics["raw_relevance"]["display"],
            help="ai_relevant vs second_model_relevant across all 40 rows",
        )
    with a_col2:
        st.metric(
            label="Post-Rule Relevance",
            value=audit_metrics["final_relevance"]["display"],
            delta="+30.0% after rule",
            help="ai_relevant_after_rule vs second_model_relevant across all 40 rows",
        )
    with a_col3:
        st.metric(
            label="Stage Agreement",
            value=audit_metrics["stage"]["display"],
            help="Stage agreement on second_model_relevant == Yes (13 reviews)",
        )
    with a_col4:
        st.metric(
            label="Cause Agreement",
            value=audit_metrics["cause"]["display"],
            help="Cause agreement on second_model_relevant == Yes (13 reviews)",
        )

    st.markdown("---")

    # 4. Field Verification Level Matrix (Spec §7.8)
    st.subheader("4. Field Verification Level Matrix")
    st.caption("Explicit documentation of human verification vs automated labelling across dataset fields.")

    verification_data = [
        {
            "Field": "relevant_final",
            "Verification Level": "Human-checked + Audit-checked",
            "Details": "Human-checked on 30 rows; second-model audited on 40 rows; rule added after golden check.",
        },
        {
            "Field": "stage, issue, cause",
            "Verification Level": "Sample Verified",
            "Details": "Human-checked on 9 relevant rows; second-model audited on 13 relevant rows.",
        },
        {
            "Field": "theme, sub_issue",
            "Verification Level": "Spot-checked",
            "Details": "Spot-checked by hand on 30 rows; sub_issue refined via second AI pass; otherwise AI-only.",
        },
        {
            "Field": "hypothesis_final, outcome_final",
            "Verification Level": "Directional (AI-Only)",
            "Details": "AI-assigned and unverified. Rule-corrected for setup E and paused payment failure.",
        },
        {
            "Field": "break_type, controls_mentioned, workarounds, income_signal",
            "Verification Level": "Directional (AI-Only)",
            "Details": "AI-assigned, not human-verified. Directional indicators for patterns only.",
        },
    ]
    st.dataframe(pd.DataFrame(verification_data), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 5. Where the AI was wrong (Spec §7.8)
    st.subheader("5. Model Error Analysis & Mitigations")
    st.caption("Direct excerpt from evidence_notes.md documenting failure modes and systematic fixes.")
    with st.expander("Read Full Error Log (evidence_notes.md)", expanded=True):
        st.markdown(notes_markdown)

    st.markdown("---")

    # 6. Corpus Limits & Research Boundaries (Spec §7.8)
    st.subheader("6. Research Scope & Corpus Limitations")
    
    missing_income_count = (df["income_signal"] != "None").sum()
    unlabelled_count = (df["relevant"] == "").sum()
    total_reviews_count = len(df)

    st.markdown(
        f"""
        - **Play Store Source Only:** Findings reflect only public app store reviews, not private support tickets, emails, or call logs.
        - **Golden Set Origin:** The golden set started from an AI-drafted list, so it is not fully independent of AI.
        - **1-Star Negative Rating Skew:** Reviews with continuation problems skew heavily negative (67% one-star vs 30% across all SIP reviews). Mentions reflect patterns of friction, not total population prevalence.
        - **Language Distribution:** Primarily English with approximately 10% Hinglish and 2% Devanagari script reviews.
        - **Missing Demographic Signals:** Reviewers almost never disclose income ({missing_income_count} of {total_relevant:,} relevant reviews) or whether they are first-time investors; user segmentation requires separate survey research.
        - **Unlabelled Reviews:** Exactly {unlabelled_count} of {total_reviews_count:,} reviews failed automated classification and were excluded from relevant counts.
        - **Keyword Boundary:** The SIP keyword filter missed a small fraction of mandate/autopay reviews; sampling indicated those primarily discussed IPOs or secondary stock orders.
        """
    )
