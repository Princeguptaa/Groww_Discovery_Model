"""
Design tokens, business constants, and schema definitions
for Groww SIP Discovery Engine.
"""

# Color-blind safe palettes (IBM Design & Wong)
PALETTE_IBM = ["#648fff", "#785ef0", "#dc267f", "#fe6100", "#ffb000"]
PALETTE_WONG = [
    "#0072B2",  # Blue
    "#D55E00",  # Vermilion
    "#009E73",  # Bluish green
    "#E69F00",  # Orange
    "#56B4E9",  # Sky blue
    "#CC79A7",  # Reddish purple
    "#F0E442",  # Yellow
    "#000000",  # Black
]

# Hypotheses A-E
HYPOTHESES = {
    "A": "A controls not found",
    "B": "B failed payment no recovery",
    "C": "C amount does not fit money",
    "D": "D chose to stop for other reasons",
    "E": "E setup or autopay blocked",
    "None": "None",
}

HYPOTHESIS_NOTE = "Directional — AI-assigned, not human-verified."

# Lost outcome values (spec §3.2, §7.1)
LOST_OUTCOMES = {
    "Stopped or cancelled",
    "Switched away",
    "Stalled, not by choice",
}

# Themes carrying the money flag (spec §7.4)
MONEY_FLAG_THEMES = {
    "Payment failed or missed",
    "Debited after cancel or wrong amount",
    "Extra or wrong amount debited",
    "Money not received after cancel or redeem",
}

# Periods
DATE_THRESHOLD = "25 Dec 2024"
PERIOD_ALL = "All"
PERIOD_BEFORE = "Before 25 Dec 2024"
PERIOD_AFTER = "After 25 Dec 2024"
PERIOD_OPTIONS = [PERIOD_ALL, PERIOD_BEFORE, PERIOD_AFTER]

# Navigation views
NAV_VIEWS = [
    "Overview",
    "Themes",
    "Journey",
    "Opportunities",
    "Evidence",
    "Ask the Data",
    "Try It",
    "Method and Quality",
]

# Mandatory disclaimers
FOOTER_TEXT = "Research tool. Not investment advice."
METRIC_NOTE_12M = (
    "Business outcome: % of first-time MF investors with an active SIP at 12 months. "
    "This engine does not measure 12-month retention. Measuring it requires cohort or "
    "transaction data. The engine shows what review writers say breaks SIP continuation."
)
OPPORTUNITY_DISCLAIMER = (
    "A prioritisation heuristic, not a measured impact. "
    "It tracks mentions closely (rank correlation about 0.94)."
)
TRYIT_WARNING = "Do not enter personal or account details."
