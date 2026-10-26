# Groww SIP Discovery Engine

A public, interactive discovery research engine analyzing why first-time mutual fund investors on Groww discontinue, cancel, or fail to continue systematic investment plans (SIPs).

The tool surfaces continuation friction from Play Store customer reviews, combining automated AI classification with transparent human-in-the-loop validation, opportunity scoring heuristics, and interactive evidence inspection.

---

## Live Application

The application is deployed on Streamlit Community Cloud:

🔗 **Live Link**: [https://princeguptaa-groww-discovery-model-app-dsac81.streamlit.app/](https://princeguptaa-groww-discovery-model-app-dsac81.streamlit.app/)

---

## Key Features

- **Overview Screen**: Complete 6-step discovery funnel (always showing all periods) alongside period-filtered headline findings (top continuation theme, top cause, lost continuation rate) and cohort measurement boundaries.
- **Themes & Hypotheses**: Interactive theme rankings, hypothesis distributions (A through E, marked directional), break-type breakdowns (excluding unstated outcomes), and feature request wishes split across periods.
- **Opportunities Prioritisation**: Runtime-computed opportunity ranking using mentions, lost rates, and monetary risk multipliers, tested against benchmark heuristics.
- **Evidence Browser**: Interactive multi-dimensional filter browser across 10 metadata dimensions with safe quote highlighting and sanitized CSV export.
- **Method & Quality**: Full documentation of the 5-step data pipeline, 30-review human golden benchmark, 40-review second-model audit (evaluated with Claude), field verification levels, and rendered evidence notes.
- **Try It**: Interactive review classifier with strict quality-gating and safety disclaimers.
- **Ask the Data**: Natural-language query interface grounded entirely in exact dataset distribution numbers with verified evidence citations.

> **Scope Note**: Phase 3 (Journey heatmap) was intentionally cut from the project scope to focus on data fidelity, runtime opportunity prioritization, and interactive query performance.

---

## Running Locally

### Prerequisites

- Python 3.11+
- Virtual environment (recommended)

### Installation

```bash
git clone https://github.com/Princeguptaa/Groww_Discovery_Model.git
cd Groww_Discovery_Model
pip install -r requirements.txt
```

### Run Application

```bash
streamlit run app.py
```

---

## Testing

Run the full automated test suite covering computations, validation oracles, privacy sanitization, quality gates, and AI rate limits:

```bash
pytest
```

---

## Disclaimers

Research tool. Not investment advice.
Business outcome metric: % of first-time MF investors with an active SIP at 12 months. This engine does not measure 12-month retention directly; measuring retention requires cohort transaction data. The engine shows what review writers report breaks SIP continuation.
