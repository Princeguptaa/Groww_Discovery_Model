# Implementation Plan: Groww SIP Discovery Engine

> **Specification:** `engine_spec.md` (v1, frozen)  
> **Architecture:** `ARCHITECTURE.md` (Approved)  
> **Status:** Phase 0 In-Progress  

---

## 1. Plan Overview & Core Principles

This phase-wise implementation plan executes the build phases defined in `ARCHITECTURE.md`, restructured into 4 strategic batches with exactly 4 review stops:
- **Batch 1 (Stop 1):** Phase 0 (Foundation, GitHub push, Streamlit Cloud deployment) -> **STOP: wait for my review**
- **Batch 2 (Stop 2):** Phase 1 (Overview) + Phase 2 (Themes) -> **STOP: wait for my review**
- **Batch 3 (Stop 3):** Phase 5 (Evidence) + Phase 6 (Method & Quality) + Phase 7 (AI & Labeller) -> **STOP: wait for my review**
- **Batch 4 (Stop 4):** Phase 4 (Opportunities) + Phase 3 (Journey, *Optional*) + Phase 8 (Polish & Acceptance) -> **STOP: wait for my review**

Every phase's tests must be run and passed before proceeding to the next phase.

### Core Engineering Directives:
1. **Daily AI Cap:** Stored in `@st.cache_resource`, keyed by UTC date string (`YYYY-MM-DD`), protected with a thread-safe `threading.Lock`. Resets automatically at 00:00 UTC.
2. **Cross-Page Buttons:** Filter updates and view transitions handled strictly inside Streamlit `on_click` callbacks, updating `st.session_state` before rerun.
3. **Opportunities Oracle Test:** Compared against `opportunity_table.csv` after rounding (`share_of_relevant_pct` to 1 decimal, `lost_rate_among_known` to 2 decimals, `priority_score` to 1 decimal).
4. **Journey Heatmap on Phone (Phase 3, Optional):** Responsive mobile layout using horizontal scroll or top 10 themes plus "Other", tested explicitly at 375 px viewport width. (Skip Phase 3 if time is short).
5. **Evidence Highlighting Safety:** Both raw text and evidence phrases escaped with `html.escape()` before match/replace; if the phrase is absent, display clean escaped text without `<mark>` tags.
6. **Data Storage & Loading:** Data files reside strictly in `data/` only, with **no root fallback**. All CSVs loaded with `pd.read_csv(..., keep_default_na=False)` so string `"None"` is preserved.
7. **Funnel Period Independence:** The funnel on Overview always displays all reviews across all periods and is explicitly labelled "all periods". The headline findings use the active period filter.
8. **Labeller Post-Rules:** Four post-rules applied in Try-it and batch labelling:
   - Rule 1: `relevant_final` = "No" when `issue` is "Praise" or "Feature request".
   - Rule 2: `hypothesis_final` = "E setup or autopay blocked" when `issue` is "Cannot start or set up SIP".
   - Rule 3: `outcome_final` = "Stalled, not by choice" when `break_type` is "Payment failure" and `outcome` is "Paused".
   - Rule 4: `hypothesis_final` = "None" when `relevant_final` is not "Yes".
9. **Reference Values Isolation:** Reference numbers exist **only** in `tests/validate_data.py`, never hardcoded in application logic or views.
10. **Clean Routing:** Views placed in `views/` (never `pages/`), driven by `st.sidebar.radio` or `st.navigation` (never `st.tabs`).

---

## 2. Phase-by-Phase Implementation Plan

---

### Batch 1: Foundation, Deployment & Test Harness

### Phase 0: Project Skeleton, Data Loading, Router, Footer, GitHub & Cloud Deployment

#### Objective
Establish repository layout with data files strictly in `data/`, setup dependencies and `.gitignore`, build read-only cached data loaders (no root fallback), create Streamlit shell with sidebar router and universal footer, implement reference test harness, push to GitHub, deploy to Streamlit Community Cloud, and confirm the public link opens.

#### Files to Create / Modify
- `data/*` — move all data files strictly into `data/` (`labelled_reviews.csv`, `opportunity_table.csv`, `golden_comparison.csv`, `audit_result.csv`, `funnel_inputs.json`, `evidence_notes.md`)
- `requirements.txt` — dependencies: `streamlit`, `pandas`, `google-genai`, `pytest`, `plotly`
- `.gitignore` — exclude `.streamlit/secrets.toml`, `.venv/`, `__pycache__/`, `.pytest_cache/`
- `.streamlit/config.toml` — headless server configuration and theme settings
- `lib/__init__.py` — package marker
- `lib/constants.py` — colour-blind-safe palettes (IBM / Wong), hypothesis definitions, lost outcomes set, money themes list, date thresholds
- `lib/data_loader.py` — `@st.cache_data` loaders for all 6 data assets from `data/` only using `keep_default_na=False`
- `views/__init__.py` — package marker
- `views/overview.py` — placeholder view function
- `views/themes.py` — placeholder view function
- `views/journey.py` — placeholder view function
- `views/opportunities.py` — placeholder view function
- `views/evidence.py` — placeholder view function
- `views/ask.py` — placeholder view function
- `views/tryit.py` — placeholder view function
- `views/method.py` — placeholder view function
- `app.py` — Streamlit entry point: `st.set_page_config`, state initialization, sidebar router, view dispatcher, universal footer
- `tests/__init__.py` — package marker
- `tests/validate_data.py` — reference assertions from spec §9

#### Tasks
1. **Directory Structure & Data Relocation**:
   - Create `data/` folder if not present.
   - Relocate all 6 data files into `data/` (`labelled_reviews.csv`, `opportunity_table.csv`, `golden_comparison.csv`, `audit_result.csv`, `funnel_inputs.json`, `evidence_notes.md`).
   - Remove duplicate copies from root to enforce strictly `data/` only.
2. **Dependency & Environment Setup**:
   - Create `requirements.txt` with locked major versions.
   - Configure `.gitignore` to ensure `.streamlit/secrets.toml` is never committed.
3. **Design Tokens & Constants (`lib/constants.py`)**:
   - Palette: IBM Design / Wong colour-blind safe hex codes.
   - Hypothesis dictionary: A to E full descriptions with "directional" notice.
   - Lost outcome set: `{"Stopped or cancelled", "Switched away", "Stalled, not by choice"}`.
   - Money flag themes: `{"Payment failed or missed", "Debited after cancel or wrong amount", "Extra or wrong amount debited", "Money not received after cancel or redeem"}`.
   - Date threshold: `"25 Dec 2024"`.
4. **Data Loader (`lib/data_loader.py`)**:
   - Implement `@st.cache_data load_reviews()`, `load_opportunity_oracle()`, `load_golden()`, `load_audit()`, `load_funnel_inputs()`, and `load_evidence_notes()`.
   - **Load strictly from `data/` only with no root fallback.**
   - Ensure every CSV loader passes `keep_default_na=False`.
   - Parse `date` in `labelled_reviews.csv` as datetime.
5. **App Shell & Router (`app.py`)**:
   - Set page configuration (title: "Groww SIP Discovery Engine", layout: "wide").
   - Initialize router via `st.sidebar.radio` (or `st.navigation`), routing between the 8 views in `views/`.
   - Inject the universal footer at the end of `app.py`: `"Research tool. Not investment advice."`
6. **Placeholder Views (`views/*.py`)**:
   - Create functions `render_overview()`, `render_themes()`, `render_journey()`, `render_opportunities()`, `render_evidence()`, `render_ask()`, `render_tryit()`, and `render_method()`.
7. **Validation Test Suite (`tests/validate_data.py`)**:
   - Total rows == 1809.
   - `relevant_final == "Yes"` == 721.
   - `relevant_final == "Yes"` Before 25 Dec 2024 == 513; After == 208.
   - Golden rows == 30; Audit rows == 40.
   - `evidence_id` format matches `^E\d{4}$` and is strictly unique.
   - Code search check: assert string `"confidence"` is never rendered in views or exports.
   - Code search check: assert no hardcoded funnel numbers exist in app code.
8. **Git, GitHub & Streamlit Community Cloud Deployment**:
   - Initialize git repo, commit files.
   - Create public GitHub repository via `gh repo create` and push `main` branch.
   - Deploy to Streamlit Community Cloud (via web / CLI / repo link) and confirm the public link opens.
   - Verify live app displays navigation and footer with no errors.

#### Tests to Run
- `pytest tests/validate_data.py`
- Headless execution check: `python -m streamlit run app.py --server.headless=true`
- HTTP check on deployed Streamlit Community Cloud public URL.

#### Done-Check
1. `pytest tests/validate_data.py` passes 100% with all reference assertions satisfied.
2. App starts with zero console errors or warnings; data files loaded strictly from `data/` with no root fallback.
3. Sidebar displays all 8 navigation items; clicking each shows its view placeholder.
4. Universal footer appears on every single screen.
5. GitHub repository is live, deployed to Streamlit Community Cloud, and the public URL opens successfully.
6. Public live URL is documented in the checkpoint report.

#### Estimate
**3.5 hours**

**STOP: wait for my review (Stop 1 of 4)**

---

### Batch 2: Core Discovery Views (Overview & Themes)

### Phase 1: Overview Screen & Core Funnel / Aggregation Logic

#### Objective
Build the Overview screen displaying the 6-step discovery funnel (always showing all periods and labelled "all periods"), three dynamically computed headline findings using the period filter (with Support separated as an amplifier), 12-month cohort metric note, global period filter, and small-sample warning.

#### Files to Create / Modify
- `lib/compute.py` — funnel aggregations (all periods), period filter helper, headline findings calculator (period-filtered)
- `views/overview.py` — full UI implementation for Overview
- `tests/test_compute.py` — unit tests for computation logic

#### Tasks
1. **Period Filter Helper (`lib/compute.py`)**:
   - Implement `apply_period_filter(df, period_selection)` supporting `"All"`, `"Before 25 Dec 2024"`, and `"After 25 Dec 2024"`.
2. **Funnel Computation (`lib/compute.py`)**:
   - **Crucial Rule**: The funnel always shows all periods and is labelled "all periods" (never filtered by the period selector).
   - Step 1: `reviews_pulled` (from `funnel_inputs.json`).
   - Step 2: `keyword_matched` (from `funnel_inputs.json`).
   - Step 3: `sip_word_unique` (from `funnel_inputs.json`).
   - Step 4: `labelled` (`df[df.relevant != ""].shape[0]`).
   - Step 5: `relevant` (`df[df.relevant_final == "Yes"].shape[0]`).
   - Step 6: `relevant_with_stated_outcome` (`df[(df.relevant_final == "Yes") & (df.outcome_final != "Unknown")].shape[0]`).
   - Strictly omit any "trouble" step.
3. **Headline Findings (`lib/compute.py`)**:
   - **Crucial Rule**: Headline findings respond to and use the active period filter (`apply_period_filter`).
   - Headline 1: Top `theme` excluding `"Support not solving"`. Compute count and share. Separately compute `"Support not solving"` count and percentage as an amplifier.
   - Headline 2: Top `cause` type with its count and percentage.
   - Headline 3: Lost rate = reviews with `outcome_final` in `{"Stopped or cancelled", "Switched away", "Stalled, not by choice"}` divided by reviews with `outcome_final != "Unknown"`.
   - Ensure every headline returns its sample size `n`.
4. **Overview UI (`views/overview.py`)**:
   - Sidebar global period filter radio button.
   - Metric cards / horizontal funnel representation labelled "Discovery Funnel (all periods)" showing counts and drop-offs.
   - Three headline callout cards with prominent `n` badges, reflecting active period selection.
   - Static 12-month retention metric callout: *"Business outcome: % of first-time MF investors with an active SIP at 12 months. This engine does not measure 12-month retention. Measuring it requires cohort or transaction data. The engine shows what review writers say breaks SIP continuation."*
   - Small-sample banner when "After 25 Dec 2024" is active: *"After 25 Dec 2024 (n = {n}). Small sample, patterns only."*
5. **Unit Tests (`tests/test_compute.py`)**:
   - Verify funnel numbers match exact full-dataset expectations regardless of period.
   - Verify Top Theme excludes "Support not solving".
   - Verify Lost Rate math against known period slices.

#### Tests to Run
- `pytest tests/test_compute.py -k "overview or funnel"`
- Acceptance Test AT-1: Funnel numbers equal the row counts in the data.
- UI validation: Switch period filter; verify funnel stays fixed at "all periods" while headlines recalculate dynamically.

#### Done-Check
1. AT-1 passes completely.
2. All 6 funnel steps match the underlying JSON and CSV counts dynamically, explicitly labelled "all periods".
3. Headline 1 displays top theme with Support isolated as amplifier, updating with period filter.
4. 12-month disclaimer is visible and styled prominently.
5. Small-sample warning dynamically displays actual `n` when "After" is selected.

#### Estimate
**3.0 hours**

---

### Phase 2: Themes Screen & Voice-of-Customer Breakdowns

#### Objective
Implement the Themes screen featuring a customizable horizontal bar chart, hypothesis distribution (A–E), break-type breakdown, and the "Wishes" (feature requests) section.

#### Files to Create / Modify
- `lib/compute.py` — add theme ranking, hypothesis breakdown, break-type split, and wishes aggregation
- `views/themes.py` — UI with Plotly horizontal bar chart, filters/toggles, and breakdown sections
- `tests/test_compute.py` — unit tests for theme and hypothesis aggregations

#### Tasks
1. **Themes Aggregation (`lib/compute.py`)**:
   - Compute counts of `theme` for `relevant_final == "Yes"`, filtered by period.
   - Support slicing/grouping by `cause` type and by `source`.
   - Compute hypothesis counts (A to E) using `hypothesis_final`.
   - Compute break-type counts from `break_type` for `{"Payment failure", "Chose to stop", "Temporary break"}` — explicitly **excluding `"Not stated"`**.
   - Compute Wishes from `issue == "Feature request"` (319 rows), split by period.
2. **Interactive Bar Chart (`views/themes.py`)**:
   - Horizontal bar chart using colour-blind-safe styling.
   - Annotate every bar with its sample size `n`.
   - Annotate any bar with `n < 30` as `"small sample, pattern only"`.
   - Radio/segmented controls to toggle breakdown by `cause` and `source`.
3. **Hypothesis & Break-Type Cards (`views/themes.py`)**:
   - Display counts for Hypothesis A through E with mandatory disclaimer: *"Directional — AI-assigned, not human-verified."*
   - Display break-type metrics with clear visual distinctions.
4. **Wishes Section (`views/themes.py`)**:
   - Render feature request volume split by Before vs After 25 Dec 2024.
   - Context note: *"Most 'stock SIP' requests came before Groww launched stock SIP in Dec 2024; weekly/daily MF SIP requests continue."*
5. **Unit Tests (`tests/test_compute.py`)**:
   - Assert `break_type` computation excludes `"Not stated"`.
   - Assert Wishes counts total 319 across periods.
   - Assert all bars have valid `n`.

#### Tests to Run
- `pytest tests/test_compute.py -k "theme or hypothesis or wishes"`
- Visual inspection: Toggle cause and source; verify bar chart labels and small-sample tags.

#### Done-Check
1. Horizontal bar chart renders with exact theme counts; every bar displays `n`.
2. Groups with `n < 30` bear the `"small sample, pattern only"` label.
3. Hypotheses A–E are explicitly marked "directional".
4. Break-type split omits `"Not stated"`.
5. Wishes section correctly splits 319 rows by 25 Dec 2024 with the contextual note.

#### Estimate
**3.0 hours**

**STOP: wait for my review (Stop 2 of 4)**

---

### Batch 3: Evidence, Quality & AI Engine

### Phase 5: Evidence Browser Screen & Highlighting Safety

#### Objective
Build the Evidence Browser with 10 interactive filters, safe HTML evidence highlighting (Note 5), scope callout badges, 25-row pagination, and sanitized CSV download omitting the `confidence` column.

#### Files to Create / Modify
- `lib/privacy.py` — CSV export sanitizer removing `confidence` column
- `views/evidence.py` — filter controls, paginated cards/table, safe HTML highlighter, CSV download
- `tests/test_privacy.py` — unit tests for citation format and export sanitization
- `tests/test_compute.py` — unit tests for evidence filtering and highlighting edge cases

#### Tasks
1. **Multi-Filter Engine (`views/evidence.py`)**:
   - Filters: `source`, `period`, `scope`, `theme`, `cause`, `hypothesis_final` (labelled "hypothesis (directional)"), `stage`, `outcome_final` (labelled "outcome"), `controls_mentioned`, `workarounds`.
   - Explode pipe-separated values for `controls_mentioned` and `workarounds` to create clean multi-select options.
   - Integrate inbound filters from `st.session_state` (set by Journey and Opportunities).
   - Display counter: `"Showing {n} of {total}"`.
2. **Safe Highlighting Implementation (`views/evidence.py`)**:
   - **Note 5 (Highlighting)**:
     ```python
     import html
     import re

     def highlight_evidence(text: str, phrase: str) -> str:
         escaped_text = html.escape(text)
         if not phrase or not phrase.strip():
             return escaped_text
         escaped_phrase = html.escape(phrase.strip())
         pattern = re.compile(re.escape(escaped_phrase), re.IGNORECASE)
         if pattern.search(escaped_text):
             return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped_text)
         return escaped_text  # Phrase not found: show clean escaped text without highlight
     ```
   - Never pass unescaped text to `unsafe_allow_html`.
3. **Card Presentation & Scope Badge (`views/evidence.py`)**:
   - Display `evidence_id`, formatted date/month, source, labels, and highlighted text.
   - For rows where `scope == "Entry (before a SIP is running)"`, apply a distinct visual badge.
   - Paginate at **25 rows per page** with Next/Previous page controls.
4. **Sanitized CSV Download (`lib/privacy.py` & `views/evidence.py`)**:
   - Export filtered DataFrame.
   - Explicitly drop `confidence` column before generating CSV.
5. **Unit & Safety Tests (`tests/test_privacy.py`, `tests/test_compute.py`)**:
   - Test XSS safety: pass `<script>alert(1)</script>` in text and evidence, assert clean escape.
   - Test missing evidence phrase: assert clean text returned without broken HTML.
   - Test CSV export: assert `"confidence"` column is absent.

#### Tests to Run
- `pytest tests/test_privacy.py`
- `pytest tests/test_compute.py -k "evidence or highlight"`
- Acceptance Test AT-2: Changing an Evidence filter changes the count.
- Verify downloaded CSV file header does not contain `confidence`.

#### Done-Check
1. AT-2 passes: selecting filters updates displayed count and rows immediately.
2. Evidence highlighting works without raw HTML injection; missing phrases fall back safely to unhighlighted text.
3. Rows with scope `"Entry (before a SIP is running)"` show distinct badge.
4. Pagination divides results strictly into 25-row chunks.
5. Downloaded CSV contains no `confidence` column.

#### Estimate
**4.0 hours**

---

### Phase 6: Method and Quality Screen & Audit Verification

#### Objective
Implement the Method and Quality screen detailing the 5-step collection pipeline, golden-set agreement metrics using exact column names (`relevant`, `relevant_final`, `stage`, `issue`, `cause` vs `h_relevant`, `h_stage`, `h_issue`, `h_cause`), second-model audit metrics (`ai_relevant`, `ai_relevant_after_rule`, `ai_stage`, `ai_issue`, `ai_cause` vs `second_model_*`), verification level table, rendered evidence notes, and data limits.

#### Files to Create / Modify
- `lib/quality.py` — agreement metrics calculation and confusion matrix generation using exact schema column names
- `views/method.py` — UI displaying pipeline, golden set, audit, verification matrix, markdown notes, and limits
- `tests/test_quality.py` — unit tests for agreement math and confusion matrix shapes

#### Tasks
1. **Agreement Metrics Logic (`lib/quality.py`)**:
   - **Golden Set (`data/golden_comparison.csv`)**:
     - Columns in file: Human labels are `h_relevant`, `h_stage`, `h_issue`, `h_cause`. AI labels are `relevant`, `relevant_final`, `stage`, `issue`, `cause`.
     - Use **ALL 30 rows** for relevance agreement (including the 8 `NOT_IN_MAIN_DATA` rows).
     - Calculate raw relevance agreement (`relevant == h_relevant`).
     - Calculate post-rule relevance agreement (`relevant_final == h_relevant`).
     - Calculate stage, issue, and cause agreement **strictly on rows where `h_relevant == "Yes"` (9 rows)** (`stage == h_stage`, `issue == h_issue`, `cause == h_cause`).
     - Generate 3x3 confusion matrix: Human (`h_relevant`: Yes/No/Unsure) vs AI (`relevant`: Yes/No/Unsure).
   - **Second-Model Audit (`data/audit_result.csv`)**:
     - Columns in file: AI labels are `ai_relevant`, `ai_relevant_after_rule`, `ai_stage`, `ai_issue`, `ai_cause`. Second model labels are `second_model_relevant`, `second_model_stage`, `second_model_issue`, `second_model_cause`.
     - 40 rows. Raw relevance agreement (`ai_relevant == second_model_relevant`) and post-rule relevance agreement (`ai_relevant_after_rule == second_model_relevant`).
     - Stage, issue, and cause agreement on rows where `second_model_relevant == "Yes"` (`ai_stage == second_model_stage`, `ai_issue == second_model_issue`, `ai_cause == second_model_cause`).
     - Count "Unsure" as a mismatch.
     - State clearly that the benchmark is a second AI model, not a human.
   - Ensure every agreement metric outputs its exact fraction denominator `x / y (z%)`.
2. **Method UI (`views/method.py`)**:
   - Pipeline flow: 5 steps (Collect -> Filter -> Label -> Check -> Rank) with counts.
   - Golden set metrics card and rendered confusion table.
   - Second-model audit metrics card.
   - Verification level table per field (spec §7.8).
   - Render `evidence_notes.md` via `st.markdown()`.
   - Data limitations callout: Play Store only, 1-star skew (67% vs 30%), language mix (English/Hinglish/Devanagari), unstated income, 30 unlabelled rows, SIP-word keyword filter boundary.
3. **Unit Tests (`tests/test_quality.py`)**:
   - Assert golden set relevance denominator is 30.
   - Assert golden set stage/issue/cause denominator is 9.
   - Assert audit relevance denominator is 40.
   - Verify confusion matrix shape and row sums.

#### Tests to Run
- `pytest tests/test_quality.py`
- Visual inspection: Verify all percentages display explicit denominators and `evidence_notes.md` renders cleanly.

#### Done-Check
1. `pytest tests/test_quality.py` passes 100%.
2. Golden set uses all 30 rows for relevance and exactly 9 rows for stage/issue/cause using exact columns (`relevant`, `relevant_final`, `stage`, `issue`, `cause` vs `h_*`).
3. Audit uses exact columns (`ai_relevant`, `ai_relevant_after_rule`, `ai_stage`, `ai_issue`, `ai_cause` vs `second_model_*`).
4. Every percentage displays its explicit denominator.
5. Confusion matrix renders correctly.
6. `evidence_notes.md` renders without raw markdown escaping flaws.

#### Estimate
**3.0 hours**

---

### Phase 7: Try It & Ask the Data (AI Infrastructure & Interfaces)

#### Objective
Build the AI engine: port the labelling prompt and normalization rules word-for-word from `label_reviews.py`, apply the four post-rules (including `hypothesis_final = "None"` when `relevant_final != "Yes"`), implement Gemini model fallback with a 15s timeout, enforce session (10) and UTC-keyed daily (300) rate limits with thread locking (Note 1), integrate curated fallback examples, and deliver the Try It and Ask the Data screens.

#### Files to Create / Modify
- `lib/labeller.py` — ported `PROMPT`, `SCHEMA`, `MULTI`, `DEFAULTS`, `normalise()` from `label_reviews.py` + 4 post-rules + quality gate
- `lib/fallback_examples.py` — pre-saved responses for Try-it and the 6 Ask-the-data questions
- `lib/ai_client.py` — Gemini API client, model fallback chain, UTC-keyed daily rate limiter with lock (Note 1), session counter
- `lib/privacy.py` — citation validation (`validate_citations`)
- `views/tryit.py` — Try It screen with 600-char limit, privacy warning, label output, and quality gate
- `views/ask.py` — Ask the Data screen with suggested questions, code-built STATS block, 150 context examples, and citation validation
- `tests/test_ai_client.py` — unit tests for rate limits, UTC lock, fallbacks, and citation stripping

#### Tasks
1. **Port Labeller Logic & Four Post-Rules (`lib/labeller.py`)**:
   - Port `SCHEMA`, `MULTI`, `DEFAULTS`, `PROMPT`, and `normalise()` word-for-word from `label_reviews.py`.
   - Apply the **four post-rules**:
     1. `relevant_final`: if `issue` is "Praise" or "Feature request" -> `"No"`.
     2. `hypothesis_final`: if `issue` is "Cannot start or set up SIP" -> `"E setup or autopay blocked"`.
     3. `outcome_final`: if `break_type` is "Payment failure" and `outcome` is "Paused" -> `"Stalled, not by choice"`.
     4. `hypothesis_final`: if `relevant_final != "Yes"` -> set `hypothesis_final = "None"`.
   - Rule-based quality gate:
     - Praise / Feature request -> "Not a SIP continuation event."
     - Issue "Confused about status or dashboard" -> "Status or dashboard (broad tag, not split in Try it)".
     - Flag "Borderline. Needs a human check." if `relevant_final == "Yes"` AND (`issue` is "Other" or broad status tag, OR evidence phrase not found in pasted text).
2. **AI Client & UTC-Keyed Daily Rate Limiter (`lib/ai_client.py`)**:
   - **Note 1 (Daily AI Cap with Lock)**:
     ```python
     import threading
     from datetime import datetime, timezone
     import streamlit as st

     class DailyRateLimiter:
         def __init__(self, limit: int = 300):
             self.limit = limit
             self.lock = threading.Lock()
             self.date_key = None
             self.count = 0

         def check_and_increment(self) -> bool:
             now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
             with self.lock:
                 if self.date_key != now_utc:
                     self.date_key = now_utc
                     self.count = 0
                 if self.count >= self.limit:
                     return False
                 self.count += 1
                 return True

     @st.cache_resource
     def get_daily_rate_limiter():
         return DailyRateLimiter(limit=300)
     ```
   - Session cap: `st.session_state.setdefault("ai_call_count", 0)`, max 10.
   - Model fallback chain: `gemini-3.1-flash-lite` -> `gemini-3-flash-preview` -> `gemini-flash-latest`. Timeout: 15 seconds.
   - Malformed JSON handling: show *"The AI returned an unexpected format. Please try again."* — **do not count against the cap**.
   - If key missing, cap hit, or API fails: serve pre-saved fallback examples from `lib/fallback_examples.py` and state it is a saved example.
3. **Try It View (`views/tryit.py`)**:
   - Privacy banner: *"Do not enter personal or account details."*
   - Text area capped at 600 characters.
   - Execute labelling, apply 4 post-rules, display labels in structured card, show quality gate badge. Never show `confidence`.
4. **Ask the Data View (`views/ask.py`)**:
   - 6 clickable suggested questions from spec §7.6.
   - Code-built `STATS` block: counts by theme, period, break_type, outcome_final, hypothesis_final, controls, and workarounds.
   - Context examples: select at most 150 rows by keyword overlap, truncated to 300 characters each, with `evidence_id`.
   - Post-processing: `validate_citations()` strips any cited `evidence_id` not present in sent examples.
5. **Unit Tests (`tests/test_ai_client.py`)**:
   - Verify daily limiter resets when UTC date changes.
   - Verify daily limiter blocks 301st call.
   - Verify session cap blocks 11th call.
   - Verify malformed JSON does not increment counter.
   - Verify missing API key triggers fallback gracefully without raw error.
   - Verify invalid citation IDs are stripped.
   - Verify fourth post-rule sets `hypothesis_final = "None"` on non-relevant reviews.

#### Tests to Run
- `pytest tests/test_ai_client.py`
- Acceptance Test AT-3: Try it labels 5 sample reviews in under 10 seconds.
- Acceptance Test AT-4: With API key removed, Try it and Ask show saved example, not an error.
- Acceptance Test AT-5: The 11th AI call in a session shows the limit message.

#### Done-Check
1. AT-3, AT-4, and AT-5 pass completely.
2. Daily cap uses UTC date key and `threading.Lock`.
3. Try-it reproduces labelling script word-for-word and executes all 4 post-rules.
4. Ask-the-data computes STATS in code, limits examples to 150 (<= 300 chars), and strips invalid citations.
5. No raw API or JSON error is ever exposed to the user.

#### Estimate
**5.5 hours**

**STOP: wait for my review (Stop 3 of 4)**

---

### Batch 4: Opportunities, Optional Journey, Polish & Acceptance

### Phase 4: Opportunities Screen & Oracle Verification

#### Objective
Compute the Opportunities priority table at runtime from filtered data, implement sorting toggles, provide full formula definitions and disclaimers, add per-row cross-page links, and verify the computation against `opportunity_table.csv` using strict rounding tolerances (Note 3).

#### Files to Create / Modify
- `lib/compute.py` — runtime opportunity table calculation
- `views/opportunities.py` — table display, sort controls, formula expander, and row action buttons
- `tests/validate_data.py` — test oracle comparison test with rounding rules

#### Tasks
1. **Runtime Opportunity Table Calculation (`lib/compute.py`)**:
   - Filter reviews by active period and `relevant_final == "Yes"`.
   - Group by `theme` and `cause`.
   - Filter groups to those with **at least 5 mentions** (`mentions >= 5`).
   - `share_of_relevant_pct` = `mentions / total_relevant_in_filter`.
   - `n_outcome_known` = reviews in group where `outcome_final != "Unknown"`.
   - `lost_rate_among_known` = reviews with outcome in `{"Stopped or cancelled", "Switched away", "Stalled, not by choice"}` / `n_outcome_known`. **Set to 0 if `n_outcome_known < 5`**.
   - `money_flag` = 1 if `theme` is in `{"Payment failed or missed", "Debited after cancel or wrong amount", "Extra or wrong amount debited", "Money not received after cancel or redeem"}`, else 0.
   - `priority_score` = `mentions * (1 + lost_rate_among_known) * (1 + money_flag)`.
2. **Oracle Comparison Test (`tests/validate_data.py`)**:
   - **Note 3 (Opportunities Test)**: Load `data/opportunity_table.csv` as oracle. Compute table for `"All"` at runtime. Round both computed table and oracle:
     - `share_of_relevant_pct`: round to 1 decimal place.
     - `lost_rate_among_known`: round to 2 decimal places.
     - `priority_score`: round to 1 decimal place.
   - Assert exact equality across all rows and columns.
3. **Opportunities UI (`views/opportunities.py`)**:
   - Sort toggles: default by `mentions` descending; secondary by `priority_score` descending.
   - Expander with explicit definitions of mentions, share, lost rate, money flag, and priority score.
   - Mandatory disclaimer: *"A prioritisation heuristic, not a measured impact. It tracks mentions closely (rank correlation about 0.94)."*
   - Per-row "See these reviews" button using `on_click` callback (Note 2) to filter Evidence by `(theme, cause)`.

#### Tests to Run
- `pytest tests/validate_data.py -k "opportunity"`
- `pytest tests/test_compute.py -k "opportunity"`
- Interactive test: Verify sort toggle switches ordering; verify period filter recalculates table.

#### Done-Check
1. Computed table for "All" matches `opportunity_table.csv` oracle 100% under Note 3 rounding rules.
2. Groups with `< 5` mentions are excluded.
3. Lost rate correctly resets to 0 when `n_outcome_known < 5`.
4. Formula definitions expander and correlation disclaimer are present.
5. Per-row buttons navigate to Evidence with pre-set `theme` and `cause` filters via `on_click` callback.

#### Estimate
**3.5 hours**

---

### Phase 3: Journey Screen & Mobile Adaptation (OPTIONAL)

> **Note on Scope**: Phase 3 (Journey) is marked **OPTIONAL**. If timeline or budget requires, this phase may be skipped. If implemented, execute all tasks and tests below.

#### Objective
Build the Stage-by-Theme journey heatmap with stage and theme selectors, mobile-responsive view handling (Note 4), and cross-page navigation into Evidence via `on_click` callbacks (Note 2).

#### Files to Create / Modify
- `lib/compute.py` — cross-tabulation matrix of `stage` rows by `theme` columns
- `views/journey.py` — heatmap visualization, mobile adaptation, selectors, and callback button
- `tests/test_compute.py` — unit tests for matrix calculation

#### Tasks
1. **Matrix Computation (`lib/compute.py`)**:
   - Cross-tabulate `stage` (rows) by `theme` (columns) for `relevant_final == "Yes"`, period-filtered.
   - Fill empty intersections with 0.
2. **Responsive Heatmap Visualization (`views/journey.py`)**:
   - Implement the matrix display using Plotly or styled DataFrame.
   - **Note 4 (Journey on Phone)**: To prevent horizontal blowout on mobile viewports (375 px), implement a scrollable container or a responsive mode providing Top 10 Themes + "Other". Test and ensure clean rendering at 375 px.
3. **Cross-Page Button with Callback (`views/journey.py`)**:
   - Selectors for `stage` and `theme` pre-populated from the matrix.
   - **Note 2 (Cross-Page Buttons)**: Implement `on_click` callback function to set `filter_stage`, `filter_theme`, and `selected_page = "Evidence"`.
4. **Unit Tests (`tests/test_compute.py`)**:
   - Verify matrix totals match total `relevant_final == "Yes"` for the period.

#### Tests to Run
- `pytest tests/test_compute.py -k "journey or matrix"`
- Interactive test: Select stage and theme, click "See these reviews", verify Evidence view opens with matching filters active.
- Responsive test: Validate rendering at 375 px viewport width via browser emulation.

#### Done-Check
1. Journey heatmap displays stage rows vs theme columns with cell counts.
2. Layout is fully readable and scrollable without page blowout at 375 px width.
3. "See these reviews" button triggers `on_click` callback, updates `st.session_state`, and navigates directly to Evidence with filters applied.

#### Estimate
**3.0 hours**

---

### Phase 8: Polish, Mobile Responsiveness, Performance & Acceptance Suite

#### Objective
Perform end-to-end polish: verify colour-blind safety and typography (>= 14px), test all screens on mobile width (375 px), verify load time (< 3s after first start), run full automated acceptance suite (AT-1 through AT-7), and verify negative code assertions.

#### Files to Create / Modify
- `views/*.py` & `app.py` — responsive layout tweaks, typography adjustments, contrast review
- `tests/test_acceptance.py` — complete automated suite for AT-1 to AT-7
- `README.md` — setup instructions, architecture summary, test commands, link to live demo

#### Tasks
1. **Mobile Width Verification (375 px)**:
   - **Acceptance Test AT-6**: Test every single page at 375 px width in Chrome DevTools / responsive emulation.
   - Ensure horizontal tables/heatmaps scroll smoothly without breaking page layout.
2. **Design & Accessibility Audit**:
   - Verify minimum font size of 14px across all views.
   - Verify palette matches colour-blind-safe guidelines.
   - Verify universal footer is present on all screens (**Acceptance Test AT-7**).
3. **Performance Optimization**:
   - Benchmark page load times after server start; assert load time < 3.0 seconds.
4. **Negative Security & Compliance Assertions**:
   - Search codebase: assert 0 occurrences of `confidence` rendered in UI or CSV export.
   - Search codebase: assert 0 hardcoded funnel counts in app code.
   - Search codebase: assert no Play Store review IDs or user names are displayed.
5. **Full Acceptance Test Suite (`tests/test_acceptance.py`)**:
   - Run combined regression: AT-1 through AT-7.

#### Tests to Run
- `pytest tests/` (full test suite execution: validate_data, test_compute, test_privacy, test_quality, test_ai_client, test_acceptance)
- Acceptance Tests AT-1 to AT-7 verification:
  - AT-1: Funnel numbers equal row counts in data.
  - AT-2: Changing Evidence filter changes count.
  - AT-3: Try it labels 5 samples in < 10s.
  - AT-4: With API key removed, Try it and Ask show saved example.
  - AT-5: 11th AI call in a session shows limit message.
  - AT-6: Every page is usable at 375 px width.
  - AT-7: The footer appears on every page.

#### Done-Check
1. 100% of automated tests pass across all test files.
2. All 7 Acceptance Tests (AT-1 through AT-7) verified and signed off.
3. Every page renders cleanly at 375 px without layout distortion.
4. Page load time is under 3 seconds after first start.
5. Zero occurrences of `confidence` column in UI or exports.

#### Estimate
**3.5 hours**

**STOP: wait for my review (Stop 4 of 4)**

---

## 3. Implementation Summary & Timeline

| Batch | Phase | Title | Primary Deliverables | Est. Hours | Review Checkpoint |
|:---:|:---:|---|---|:---:|---|
| **1** | **0** | Skeleton, GitHub & Cloud | `app.py`, loaders (`data/` only), router, footer, `validate_data.py`, live cloud deployment | 3.5 h | **STOP: wait for my review (Stop 1 of 4)** |
| **2** | **1** | Overview Screen | Funnel (all periods), 3 headlines (period-filtered), 12-month note | 3.0 h | |
| **2** | **2** | Themes Screen | Theme bar chart, hypothesis counts, break types, wishes | 3.0 h | **STOP: wait for my review (Stop 2 of 4)** |
| **3** | **5** | Evidence Browser | 10 filters, safe HTML highlighting, scope badge, export | 4.0 h | |
| **3** | **6** | Method & Quality | 5-step pipeline, 30-row golden set, 40-row audit (exact columns) | 3.0 h | |
| **3** | **7** | Try It & Ask the Data | Labeller (4 post-rules), Gemini chain, UTC lock cap, fallbacks | 5.5 h | **STOP: wait for my review (Stop 3 of 4)** |
| **4** | **4** | Opportunities Screen | Runtime priority table, oracle test with rounding, sort | 3.5 h | |
| **4** | **3** | Journey Screen (*Optional*) | Stage x Theme heatmap, 375px adaptation, cross-page buttons | 3.0 h | |
| **4** | **8** | Polish & Acceptance | 375px audit, AT-1 to AT-7 suite, performance, README | 3.5 h | **STOP: wait for my review (Stop 4 of 4)** |
| | | **Total** | | **32.0 h** | |

---

## 4. Acceptance Test Traceability Matrix

| Test ID | Requirement | Verification Method | Phase Validated |
|---|---|---|:---:|
| **AT-1** | Funnel numbers equal row counts in data | `pytest tests/validate_data.py` + Overview manual check | Phase 1 |
| **AT-2** | Changing an Evidence filter changes count | Interactive filter test in Evidence Browser | Phase 5 |
| **AT-3** | Try it labels 5 sample reviews in < 10s | Stopwatch / automated latency benchmark | Phase 7 |
| **AT-4** | Without API key, Try it & Ask show saved example | Remove key from secrets, verify fallback renders | Phase 7 |
| **AT-5** | 11th AI call in session shows limit message | Click action 11 times in one session, check warning | Phase 7 |
| **AT-6** | Every page is usable at 375 px width | DevTools responsive emulation at 375 px on all views | Phase 8 |
| **AT-7** | Footer appears on every page | Visual verification across all 8 views | Phase 0 & Phase 8 |
