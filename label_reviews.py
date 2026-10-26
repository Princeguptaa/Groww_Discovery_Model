"""
Discovery engine, labelling script v2 (Groww SIP continuation).

Run in Google Colab:
  Cell 1:  !pip install google-genai pandas openpyxl
  Cell 2:  paste this whole file and run

You will be asked to upload:
  1) your filled golden_set_to_label.xlsx   (the 30 reviews you labelled by hand)
  2) one or more review files (csv) with a 'text' column
     (groww_sip_only.csv now; later add Reddit / YouTube / App Store files)

Outputs (download them from the Colab file panel):
  golden_comparison.csv   AI labels next to your hand labels
  labelled_reviews.csv    every review with all labels   -> feeds the engine website
  opportunity_table.csv   problems ranked by score
  audit_sample.csv        40 random rows for a second-model check
"""
import json, os, re, time
from getpass import getpass
import pandas as pd
from google import genai
from google.colab import files

API_KEY = getpass("Paste your Gemini API key (hidden): ")
CANDIDATES = ["gemini-3.1-flash-lite", "gemini-3.1-flash-lite-preview", "gemini-3-flash-preview", "gemini-flash-latest"]  # lite first: faster, higher free limits
BATCH = 30                      # reviews per request (bigger = fewer requests)
PAUSE = 2                       # seconds between requests
MAX_REVIEWS = None              # set to 800 to label only a random sample (much faster)
MAX_CHARS = 450                 # characters of each review sent to the AI
STRICT_SIP_ONLY = True          # True = keep only reviews that contain the word SIP
client = genai.Client(api_key=API_KEY)


def pick_model():
    """Find a Gemini model your key can use today (model names change often)."""
    names = []
    try:
        names = [m.name.replace("models/", "") for m in client.models.list()]
    except Exception as e:
        print("could not list models:", str(e)[:100])
    extra = [n for n in names if "flash" in n and not any(
        x in n for x in ("tts", "live", "image", "audio", "native", "exp", "8b", "2.5", "2.0", "1.5"))]
    for cand in CANDIDATES + sorted(set(extra), reverse=True):
        try:
            client.models.generate_content(model=cand, contents="Reply with the single word OK")
            print("Using model:", cand)
            return cand
        except Exception as e:
            print("not usable:", cand, "-", str(e)[:80])
    raise SystemExit("No Gemini model worked. Check your key, then run again.")


MODEL = pick_model()

# ------------------------------------------------------------------
# Label schema. Fixed options only. The AI must pick from these.
# ------------------------------------------------------------------
SCHEMA = {
    "relevant": ["Yes", "No", "Unsure"],
    "stage": ["Setting up", "First 3 months", "Mid-journey", "Pausing or stopping", "Restarting", "Not clear"],
    "issue": ["Payment failed or missed", "Debited after cancel or wrong amount", "Cannot edit or pause or stop",
              "Support not solving", "Confused about status or dashboard", "Worried about returns",
              "Doubts about trust or timing", "Feature request", "Praise", "Cannot start or set up SIP", "Other"],
    "cause": ["Money side", "Product side", "Market side", "Understanding side", "Not clear"],
    "break_type": ["Payment failure", "Chose to stop", "Temporary break", "Not stated"],
    "outcome": ["Still investing", "Paused", "Stopped or cancelled", "Switched away", "Unknown"],
    "income_signal": ["Salaried", "Variable income", "Student", "Not stated"],
    "hypothesis": ["A controls not found", "B failed payment no recovery", "C amount does not fit money",
                   "D chose to stop for other reasons", "None"],
    "confidence": ["High", "Medium", "Low"],
}
MULTI = {  # a review can mention several
    "controls_mentioned": ["Skip", "Edit date or amount", "Pause", "Step-up", "One-time payment", "Cancel", "None"],
    "workarounds": ["Contacted support", "Paid one-time manually", "Re-created the SIP", "Switched to another app",
                    "Asked online or friends", "Did nothing", "Not stated"],
}
DEFAULTS = {"relevant": "Unsure", "stage": "Not clear", "issue": "Other", "cause": "Not clear",
            "break_type": "Not stated", "outcome": "Unknown", "income_signal": "Not stated",
            "hypothesis": "None", "confidence": "Low"}
GOLD_FIELDS = {"relevant": "h_relevant", "stage": "h_stage", "issue": "h_issue", "cause": "h_cause"}

PROMPT = f"""You label Play Store reviews of the Groww app (English, Hindi or Hinglish).
Goal: understand why first-time investors fail to continue a mutual fund SIP.
Return one JSON object per review with these keys. Use ONLY the allowed options.

- id: the id given
- relevant: {SCHEMA['relevant']}. Yes = about starting, running, failing, pausing or stopping a SIP. No = stocks, KYC only, general UI, or praise not about SIPs.
- stage: {SCHEMA['stage']}
- issue: {SCHEMA['issue']} (the single biggest point; 'Cannot start or set up SIP' = autopay setup trouble, KYC block, or the app failing when creating a SIP)
- cause: {SCHEMA['cause']}. Money side = balance, bank, income. Product side = app, mandate, support. Market side = returns, falls. Understanding side = confusion or wrong expectation.
- break_type: {SCHEMA['break_type']}
- outcome: {SCHEMA['outcome']}
- controls_mentioned: list from {MULTI['controls_mentioned']} (only controls the review actually mentions)
- workarounds: list from {MULTI['workarounds']}
- income_signal: {SCHEMA['income_signal']}. ONLY if the review says it. Never guess.
- hypothesis: {SCHEMA['hypothesis']}. Pick the one the review supports best, else None.
- confidence: High, Medium or Low
- evidence: the shortest phrase (max 10 words) copied from the review that supports your labels
- insight: one plain English sentence (max 15 words) on what this review shows

Rules:
1. Tag only what the text says. If unclear, use the unclear option and Low confidence.
2. If relevant is No: stage 'Not clear', cause 'Not clear', break_type 'Not stated', outcome 'Unknown', hypothesis None. The issue may be Praise, Feature request or Other.
3. A general rant with no event described gets stage "Not clear" and break_type "Not stated".
4. Never judge whether the user is right. Never give investment advice.
Return ONLY a JSON list."""


def normalise(d):
    """Force every value into the allowed options so bad AI output never breaks charts."""
    out = {"id": str(d.get("id", ""))}
    for k, allowed in SCHEMA.items():
        v = d.get(k, DEFAULTS[k])
        out[k] = v if v in allowed else DEFAULTS[k]
    for k, allowed in MULTI.items():
        v = d.get(k) or []
        if isinstance(v, str):
            v = [v]
        out[k] = "|".join(sorted({x for x in v if x in allowed})) or ("None" if k == "controls_mentioned" else "Not stated")
    out["evidence"] = str(d.get("evidence", "") or "")[:160]
    out["insight"] = str(d.get("insight", "") or "")[:200]
    if out["relevant"] == "No":
        out.update({"stage": "Not clear", "cause": "Not clear", "break_type": "Not stated",
                    "outcome": "Unknown", "hypothesis": "None"})
    return out


def label_batch(items):
    payload = [{"id": str(i), "review": str(t)[:MAX_CHARS]} for i, t in items]
    for attempt in range(5):
        try:
            r = client.models.generate_content(
                model=MODEL,
                contents=PROMPT + "\n\nREVIEWS:\n" + json.dumps(payload, ensure_ascii=False),
                config={"response_mime_type": "application/json", "temperature": 0},
            )
            data = json.loads(r.text)
            return {str(d.get("id")): normalise(d) for d in data}
        except Exception as e:
            print("  retry", attempt + 1, str(e)[:100])
            time.sleep(30)
    return {}


def label_all(df, id_col, text_col, ckpt=None):
    """Label every row. If ckpt is given, progress is saved after every batch and reused on re-run."""
    done = {}
    if ckpt and os.path.exists(ckpt):
        old = pd.read_csv(ckpt, dtype=str).fillna("")
        done = {r["id"]: r.to_dict() for _, r in old.iterrows()}
        print(f"resuming: {len(done)} already labelled")
    items = [(i, t) for i, t in zip(df[id_col].astype(str), df[text_col].fillna("")) if i not in done]
    t0 = time.time()
    for s in range(0, len(items), BATCH):
        done.update(label_batch(items[s:s + BATCH]))
        if ckpt:
            pd.DataFrame(list(done.values())).to_csv(ckpt, index=False)
        n = min(s + BATCH, len(items))
        per = (time.time() - t0) / n
        print(f"labelled {n}/{len(items)} | {per:.1f}s per review | about {int((len(items) - n) * per / 60)} min left")
        time.sleep(PAUSE)
    missing = len(items) - sum(1 for i, _ in items if i in done)
    if missing:
        print(f"WARNING: {missing} reviews failed. Run this cell again; finished ones are kept.")
    return pd.DataFrame(list(done.values()))


# ------------------------------------------------------------------
# Step 1. Check the AI against your hand labels
# ------------------------------------------------------------------
print("Step 1: upload your filled golden_set_to_label.xlsx")
up = files.upload()
gold = pd.read_excel([k for k in up if k.endswith(".xlsx")][0], sheet_name="Golden set")
gold.columns = ["ID", "text", "h_relevant", "h_stage", "h_issue", "h_cause"]
gold = gold.dropna(subset=["h_relevant"]).reset_index(drop=True)
ai = label_all(gold, "ID", "text").rename(columns={"id": "ID"})
cmp = gold.merge(ai, on="ID", how="left")
print("\n=== AGREEMENT WITH YOUR HAND LABELS (n =", len(cmp), ") ===")
for ai_col, h_col in GOLD_FIELDS.items():
    # relevance is checked on all rows; stage/issue/cause only where YOU said Yes (the hard rows)
    sub = cmp if ai_col == "relevant" else cmp[cmp["h_relevant"] == "Yes"]
    ok = (sub[ai_col].astype(str).str.lower() == sub[h_col].astype(str).str.lower())
    print(f"{ai_col:10s} {ok.mean()*100:5.1f}%   ({int(ok.sum())}/{len(sub)})")
cmp["relevant_final"] = cmp["relevant"].where(~cmp["issue"].isin(["Praise", "Feature request"]), "No")
ok2 = (cmp["relevant_final"].str.lower() == cmp["h_relevant"].str.lower())
print(f"relevant AFTER RULE (Praise and Feature request count as No): {ok2.mean()*100:5.1f}%   ({int(ok2.sum())}/{len(cmp)})")
print("Note: stage/issue/cause are scored only on rows you marked Yes, so n is small.")
cmp.to_csv("golden_comparison.csv", index=False)
print("Saved golden_comparison.csv. Open it. Pick 2-3 rows where the AI was wrong: they go in the Evidence Log.")

# ------------------------------------------------------------------
# Step 2. Label all reviews
# ------------------------------------------------------------------
print("\nStep 2: upload one or more review csv files (needs a 'text' column)")
up = files.upload()
frames = []
for name in [k for k in up if k.endswith(".csv")]:
    d = pd.read_csv(name)
    if "text" not in d.columns:
        print("skipping", name, "(no text column)")
        continue
    if "source" not in d.columns:
        d["source"] = "Play Store" if "groww" in name.lower() else name.replace(".csv", "")
    frames.append(d)
df = pd.concat(frames, ignore_index=True)
df["text"] = df["text"].fillna("").astype(str)
n_in = len(df)
if STRICT_SIP_ONLY:
    df = df[df.text.str.contains(r"\bsips?\b", case=False, regex=True)]
df = df.drop_duplicates("text").reset_index(drop=True)
if MAX_REVIEWS and len(df) > MAX_REVIEWS:
    df = df.sample(MAX_REVIEWS, random_state=1).reset_index(drop=True)
df["rid"] = df.index.astype(str)
print(f"{n_in} rows uploaded -> {len(df)} after SIP filter and de-duplication")

lab = label_all(df, "rid", "text", ckpt="labels_checkpoint.csv").rename(columns={"id": "rid"})
final = df.merge(lab, on="rid", how="left")
final.to_csv("labelled_reviews.csv", index=False)

# ------------------------------------------------------------------
# Step 3. Funnel, counts, opportunity score
# ------------------------------------------------------------------
# Rule learned from the golden set: Praise and Feature request are not SIP continuation events
final["relevant_final"] = final["relevant"].where(~final["issue"].isin(["Praise", "Feature request"]), "No")
# Rule 2 (found in golden-set check): setup trouble is not "controls not found". Give it its own bucket E.
final["hypothesis_final"] = final["hypothesis"].fillna("None")
final.loc[final["issue"] == "Cannot start or set up SIP", "hypothesis_final"] = "E setup or autopay blocked"
final.loc[final["relevant_final"] != "Yes", "hypothesis_final"] = "None"
# Rule 3: a payment failure is not the user pausing. Mark it as stalled, not by choice.
final["outcome_final"] = final["outcome"]
final.loc[(final["break_type"] == "Payment failure") & (final["outcome"] == "Paused"), "outcome_final"] = "Stalled, not by choice"
final.to_csv("labelled_reviews.csv", index=False)
rel = final[final.relevant_final == "Yes"]
trouble = rel[rel.issue.isin(["Payment failed or missed", "Debited after cancel or wrong amount",
                              "Cannot edit or pause or stop", "Support not solving",
                              "Confused about status or dashboard", "Doubts about trust or timing"])
              | rel.outcome.isin(["Paused", "Stopped or cancelled", "Switched away"])]
print("\n=== FUNNEL ===")
print("Uploaded rows         :", n_in)
print("Mention SIP (unique)  :", len(df))
print("Relevant (AI + rule)   :", len(rel))
print("Trouble or drop signal:", len(trouble))
print("\nHypothesis counts (relevant, after rules):\n", rel.hypothesis_final.value_counts())
print("\nBreak type (relevant):\n", rel.break_type.value_counts())
print("\nIssue x Cause (relevant):\n", pd.crosstab(rel.issue, rel.cause))
print("\nLow confidence share:", round((final.confidence == "Low").mean() * 100, 1), "%")

d = rel.copy()
d["lost"] = d.outcome_final.isin(["Stopped or cancelled", "Switched away", "Stalled, not by choice"])
d["money_pain"] = d.issue.isin(["Payment failed or missed", "Debited after cancel or wrong amount"])
g = d.groupby(["issue", "cause"]).agg(mentions=("rid", "count"), lost_rate=("lost", "mean"),
                                      money_rate=("money_pain", "mean")).reset_index()
g = g[g.mentions >= 5]
g["score"] = (g.mentions * (1 + g.lost_rate) * (1 + g.money_rate)).round(1)
g = g.sort_values("score", ascending=False)
g.to_csv("opportunity_table.csv", index=False)
print("\n=== TOP PROBLEMS (score = mentions x (1+lost rate) x (1+money-pain rate)) ===")
print(g.head(10).to_string(index=False))

# ------------------------------------------------------------------
# Step 4. Sample for the second-model audit
# ------------------------------------------------------------------
aud = final.sample(min(40, len(final)), random_state=7)[
    ["rid", "text", "relevant", "stage", "issue", "cause", "hypothesis", "confidence", "evidence"]]
aud.to_csv("audit_sample.csv", index=False)
print("\nSaved: labelled_reviews.csv, opportunity_table.csv, audit_sample.csv")
print("Download all 4 files and send them to me. I will audit the 40-row sample as the second model.")
