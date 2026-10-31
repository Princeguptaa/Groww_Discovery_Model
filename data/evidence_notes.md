# Where the AI was wrong, and what we did

Source: 30-review golden set labelled by the researcher: the first list was drafted with AI help, then every label was reviewed and confirmed or changed, and a 40-review audit by a second AI model (Claude), not a human.
Test results come from `golden_comparison.csv` and `audit_result.csv`.

| # | What the AI got wrong | Example (evidence_id) | Fix | Result |
|---|---|---|---|---|
| 1 | Counted praise as a SIP event (relevant = Yes for "great app for SIP") | E0832 | Rule: if issue is Praise or Feature request, `relevant_final` = No | Relevance agreement on the golden set rose from 50.0% (15/30) to 86.7% (26/30). On the 40-row audit it rose from 60% to 90%. |
| 2 | Called setup trouble (autopay setup, cannot create a SIP) "controls not found" (hypothesis A) | E0106, E1778 | New hypothesis E "setup or autopay blocked" in `hypothesis_final` | A would have been overstated by 5 of 30 golden rows |
| 3 | Marked a missed deduction as "Paused" although the user did not pause | E0931, E1733 | Outcome becomes "Stalled, not by choice" in `outcome_final` | Keeps "chose to stop" apart from "payment failed" |
| 4 | Said confidence "High" on every answer, including wrong ones | all 30 golden rows, 39 of 40 audit rows | Confidence is not used anywhere as a quality gate | Quality gate is rule-based instead |
| 5 | Tagged 184 reviews "Confused about status or dashboard", a catch-all | n/a | Second AI pass split it into `sub_issue` values | Only 10 of 184 were real confusion |

## Honest limits
- The golden set started from an AI-drafted list, so it is not fully independent of AI.
- The rules in rows 1 to 3 were written after looking at the golden set. They were then checked on the 40-row audit, which is a second AI model (Claude), not a human.
- Stage, issue and cause were checked by a human on only 9 rows (the rows marked Yes).
- Hypotheses, outcomes, break types, controls and workarounds are AI-only and not verified. Treat them as directional.
- 8 of the 30 golden reviews do not contain the word SIP, so they are not in the 1,809-row data (their `evidence_id` is NOT_IN_MAIN_DATA). They were included to test how noisy the keyword filter is.
