# TABHS — CIS 509 Final Project Build Strategy

**Prepared for:** Claude Code execution
**Author:** Matthew Cook (MCOOK20)
**Repo target:** Northstar org (TBD repo name)
**Course:** ASU W.P. Carey CIS 509 — Unstructured Data Analysis
**Instructor:** Prof. Xiao Liu
**Build governance:** Standard CLAUDEME.md compliance, T+2h / T+24h / T+48h gates

---

## BLUF (read this first)

Build a GitHub repo that delivers the CIS 509 final project as a **receipts-native experience** — the professor opens the link, clicks "Open in Codespaces," and within 90 seconds is looking at an interactive TABHS dashboard with cryptographically signed JSON receipts for the top 10 most-manipulated Arizona restaurants.

This is the TABHS proposal Bubba submitted as a course project, executed with the Inquiro receipts-native pattern. The professor must be able to run it without friction. The wow moment is the receipt — every business analyzed produces a court-admissible JSON object signed with dual hashes (SHA-256 + BLAKE3) that proves what was decided, on what input, by which models, at what time. RNA principles applied to academic work.

**No external claim should overstate what this is.** This is a verified prototype using the RNA foundation, applied to academic NLP analysis. Not a production system.

---

## What you must read before writing any code

1. `/PROJECT_BRIEF.md` — full project context, dataset, prior work
2. `/PROFESSOR_FEEDBACK.md` — exact constraints from Prof. Lu
3. `/RUBRIC.md` — six categories with weights and excellent-band requirements
4. `/PRIOR_WORK_INVENTORY.md` — what already exists from LA2 / LA4 / LA5 / LA6 / EDA
5. `/RECEIPT_SCHEMA.md` — the JSON receipt structure and signing approach
6. `CLAUDEME.md` — execution standards (already in repo per Bubba's standard)

Read all six before generating a single file. If any contradict, surface the contradiction back to Bubba — do not resolve it silently.

---

## What this repo is NOT

- Not a Colab notebook dumped into a folder
- Not a standalone script that runs once and dies
- Not a static HTML report
- Not a recreation of any prior lab assignment from scratch
- Not production RNA infrastructure — this is the academic application of the RNA pattern

---

## What this repo IS

- A reproducible, gated pipeline that loads `restaurant_reviews_az.csv` and produces TABHS receipts per business
- A Codespaces-ready environment that runs end-to-end on first launch
- A GitHub Actions workflow that runs on push and on a weekly schedule
- A static HTML dashboard committed to the repo that renders the latest results
- Five modular notebooks plus an orchestrator script
- A README that hits the professor with the headline finding before any setup
- Five committed sample receipts in `outputs/receipts/` so the repo demonstrates the pattern even without running the pipeline

---

## Repo layout (what to build)

```
tabhs-cis509/
├── README.md                    # Hero + headline finding + 1-click Codespaces button
├── CLAUDEME.md                  # Execution standards (read at session start)
├── LICENSE                      # MIT or Apache 2.0 — Bubba's call
├── .gitignore                   # Standard Python + Jupyter + .env exclusions
├── .devcontainer/
│   └── devcontainer.json        # Codespaces config — Python 3.11, pip install on attach
├── .github/
│   └── workflows/
│       ├── ci.yml               # Runs pipeline on push, 1k sample for speed
│       └── weekly_refresh.yml   # Picks 50 random businesses weekly, commits fresh top_10
├── notebooks/
│   ├── 01_eda.ipynb             # Curated from existing ProjectEDA
│   ├── 02_vader_sentiment.ipynb # Curated from existing EDA Section 7
│   ├── 03_bertopic.ipynb        # Curated from existing LA5
│   ├── 04_llm_methods.ipynb     # Curated from existing LA6
│   └── 05_xgboost_tabhs.ipynb   # NET-NEW — the only notebook that needs new code
├── src/
│   ├── __init__.py
│   ├── data_loader.py           # Single source of truth for loading the CSV
│   ├── tabhs_pipeline.py        # End-to-end pipeline runner
│   ├── receipts.py              # Receipt generation + dual-hash signing
│   ├── llm_client.py            # Groq client wrapper with rate limiting
│   └── config.py                # Constants (paths, thresholds, model names)
├── outputs/
│   ├── receipts/                # Committed sample receipts (5 anchor businesses)
│   ├── top_10_manipulated.csv   # Latest top 10 — refreshed weekly by Actions
│   ├── dashboard.html           # Static HTML dashboard, committed
│   └── figures/                 # PNG plots from EDA, BERTopic, LLM comparison
├── slides/
│   └── ProjectFinal_Cook_Matthew.pptx   # Final presentation deck
├── data/
│   └── README.md                # Instructions to download restaurant_reviews_az.csv
├── tests/
│   └── test_smoke.py            # Smoke tests for the pipeline (no LLM calls)
├── pyproject.toml               # Dependencies pinned
├── requirements.txt             # Codespaces-friendly fallback
└── run_pipeline.py              # Single-command pipeline runner for the professor
```

---

## The professor experience flow

This is the design target. Every decision should be evaluated against this flow.

1. Professor opens the repo link
2. README hero displays: ASU maroon/gold header, the headline finding ("28.3% of Arizona restaurant reviews flagged as inauthentic"), and a "Open in Codespaces" button at top
3. Professor clicks the button
4. Codespaces builds the environment in ~60 seconds (devcontainer pre-installs everything)
5. Codespaces auto-opens `run_pipeline.py` in the editor and `dashboard.html` in the preview pane
6. Professor runs `python run_pipeline.py --sample 100` (the README tells him to)
7. Pipeline executes in ~3 minutes on a 100-business sample, emitting receipts to `outputs/receipts/`
8. Dashboard auto-refreshes showing top 10 most-manipulated businesses, each with a clickable receipt
9. Professor clicks a receipt → sees the full evidence chain, dual-hash signature, model lineage

**Total time from click to wow: 90 seconds (dashboard already loads even before the pipeline runs, because committed sample receipts populate it).**

The pipeline run is the upgrade. The wow is immediate.

---

## Component build order (do these in sequence)

### Phase 1 — Foundation (T+0 to T+2h)

1. Create the repo structure exactly as laid out above
2. Write `CLAUDEME.md` (Bubba has a standard template — pull from his standards folder)
3. Write `README.md` with the hero, headline finding, and Codespaces button
4. Write `.devcontainer/devcontainer.json` for Python 3.11 + auto-install
5. Write `requirements.txt` and `pyproject.toml` with pinned versions:
   - pandas, numpy, scikit-learn, matplotlib
   - bertopic, umap-learn, hdbscan, sentence-transformers
   - xgboost
   - groq, python-dotenv
   - jupyter, nbconvert
6. Write `src/config.py` with all constants and paths
7. Write `src/data_loader.py` — single function `load_reviews()` that returns the dataframe
8. Write `tests/test_smoke.py` — verifies data loads, no LLM calls

**T+2h Gate:** `pytest tests/` passes. Repo clones cleanly. Codespaces builds without error.

### Phase 2 — Receipt Infrastructure (T+2h to T+8h)

9. Write `src/receipts.py`:
   - Function `compute_dual_hash(payload_dict)` returns `{sha256, blake3}`
   - Function `build_receipt(business_id, evidence, models, timestamp)` returns full JSON
   - Function `sign_receipt(receipt)` adds the dual_hash field
   - Function `write_receipt(receipt, path)` writes to `outputs/receipts/{business_id}.json`
10. Write `src/llm_client.py`:
   - Wrapper around Groq client with rate limiting (sleep between calls)
   - Functions for zero-shot, few-shot, and multi-model agreement
   - Reads `GROQ_API_KEY` from environment or `.env`
11. Generate 5 anchor sample receipts and commit them to `outputs/receipts/`
   - Pick 5 businesses with high review volume from the dataset
   - Run them through the pipeline manually
   - Commit the JSON files so the dashboard renders even before any pipeline run

**T+8h Gate:** Sample receipts validate against schema. Dual-hash verification works. LLM client handles rate limits gracefully.

### Phase 3 — Notebooks (T+8h to T+24h)

12. Build `notebooks/01_eda.ipynb` — curated from Bubba's existing ProjectEDA work. Six plots, summary stats, the 28.3% finding. Read the existing notebook from his Drive and adapt.
13. Build `notebooks/02_vader_sentiment.ipynb` — VADER divergence calculation. The 28.3% > 1.0 threshold. Save divergence scores to `outputs/vader_scores.csv`.
14. Build `notebooks/03_bertopic.ipynb` — curated from LA5. 80 topics → 15. Save topic assignments to `outputs/topic_assignments.csv`.
15. Build `notebooks/04_llm_methods.ipynb` — curated from LA6. Zero-shot, few-shot, multi-model agreement on a subset of suspicious reviews. Save to `outputs/llm_agreement.csv`.
16. Build `notebooks/05_xgboost_tabhs.ipynb` — **THE ONLY NEW NOTEBOOK**. See detailed spec below.

**T+24h Gate:** All five notebooks execute end-to-end on a 1,000-review sample without errors. All output CSVs land in `outputs/`. 80% test coverage on `src/`.

### Phase 4 — Pipeline + Dashboard (T+24h to T+48h)

17. Write `src/tabhs_pipeline.py` — orchestrates the five steps end-to-end programmatically
18. Write `run_pipeline.py` — CLI entry point with `--sample N` flag for the professor
19. Write `outputs/dashboard.html` — static HTML with embedded JS that reads from `outputs/receipts/` and `outputs/top_10_manipulated.csv`. Renders top 10 with clickable receipt detail views. ASU maroon/gold theme. Single file, no external deps beyond a CDN-loaded Tailwind.
20. Write `.github/workflows/ci.yml` — runs on every push, executes pipeline on 1k sample, validates receipts, fails on schema violations
21. Write `.github/workflows/weekly_refresh.yml` — runs Sundays at midnight UTC, picks 50 random businesses, runs full pipeline, commits fresh `top_10_manipulated.csv` and updated receipts
22. Add dynamic README badges that pull from the latest `top_10_manipulated.csv` so the README always shows current numbers

**T+48h Gate:** Full pipeline runs in CI. Dashboard renders correctly with sample data. Weekly refresh tested manually with a workflow_dispatch trigger. All receipts validate. Pre-flight checklist passes (see end of doc).

---

## NOTEBOOK 5 SPEC — the net-new piece (`05_xgboost_tabhs.ipynb`)

This is the only notebook that needs original code. Everything else is curation from existing work.

### Cell structure

**Cell 1 — Imports + load engineered features**

Load three CSVs from prior notebooks:
- `outputs/vader_scores.csv` — review-level VADER compound + divergence
- `outputs/topic_assignments.csv` — review-level BERTopic topic_id
- `outputs/llm_agreement.csv` — review-level multi-model agreement score (only on subset)

Merge into single `features_df` keyed on review_id.

**Cell 2 — Feature engineering**

Engineer the following features per review:
- `sentiment_star_divergence` (from VADER)
- `vader_compound` (from VADER)
- `topic_id` (from BERTopic, one-hot encode top 14 + other)
- `is_topic_outlier` (1 if topic_id == -1)
- `review_length_words`
- `useful_votes`, `funny_votes`, `cool_votes`
- `stars` (the rating itself)

Drop reviews with missing features. Print final feature matrix shape.

**Cell 3 — Proxy label generation**

```
suspicious_label = 1 if sentiment_star_divergence > 1.0 else 0
```

Print class distribution (expected ~28.3% positive class).

**Critical disclosure in markdown above the cell:** explicitly state this is a heuristic proxy label, not ground truth, and discuss why this is a reasonable proxy given the absence of labeled data. Cite the EDA finding directly.

**Cell 4 — Train/test split + XGBoost training**

Stratified 80/20 split. Train XGBoost classifier with default params (no tuning required for course project — keep it simple). Standard hyperparameters: `n_estimators=100`, `max_depth=6`, `learning_rate=0.1`, `objective='binary:logistic'`.

**Cell 5 — Evaluation**

Precision, recall, F1, accuracy on test set. Confusion matrix. Feature importance plot (top 10 features).

Critical: include a markdown cell after this that explicitly addresses the circularity — divergence is both an input feature AND the proxy label. Discuss what the classifier is actually learning (correlations among the OTHER features that align with high-divergence reviews). This is the graduate-level honesty the rubric rewards.

**Cell 6 — Per-business aggregation (TABHS score)**

For each business with at least 10 reviews:
- `raw_avg_stars` = mean of stars
- `suspicion_pct` = % of reviews predicted suspicious by XGBoost
- `tabhs_adjusted_stars` = mean of stars weighted by `(1 - suspicion_score)`
- `manipulation_delta` = `raw_avg_stars - tabhs_adjusted_stars`

Output per-business dataframe sorted by `manipulation_delta` descending.

**Cell 7 — Top 10 most-manipulated businesses table**

Display the top 10. Save to `outputs/top_10_manipulated.csv`.

**Cell 8 — Receipt generation**

For each of the top 100 businesses by review volume:
- Build receipt using `src.receipts.build_receipt()`
- Sign with dual hash
- Write to `outputs/receipts/{business_id}.json`

Print confirmation: "Receipts generated: 100 / 100 verified."

**Cell 9 — Final visualization**

Single bar chart: top 10 businesses by manipulation delta. ASU maroon for raw rating, gold for TABHS-adjusted rating. The visual story is the gap between the two bars.

---

## RECEIPT SCHEMA (write this into `RECEIPT_SCHEMA.md`)

```json
{
  "schema_version": "tabhs-v1.0",
  "business_id": "Wnk_QW8Vi5a01gmgZBFiLQ",
  "computed_at": "2026-04-27T18:34:42Z",

  "input": {
    "review_count": 47,
    "date_range": ["2020-03-15", "2022-01-10"],
    "data_source": "yelp_open_dataset_arizona_restaurants_subset"
  },

  "scores": {
    "raw_yelp_rating": 4.7,
    "tabhs_adjusted_rating": 3.2,
    "manipulation_delta": 1.5,
    "suspicious_review_pct": 42.3
  },

  "evidence": {
    "vader_mean_divergence": 0.73,
    "topic_outlier_pct": 0.31,
    "llm_few_shot_agreement_rate": 0.81,
    "xgboost_mean_suspicion_score": 0.47
  },

  "models": {
    "sentiment": {
      "name": "VADER + Llama-3.3-70B-Versatile (few-shot)",
      "version": "vader-3.3.2 + groq-llama-3.3-70b"
    },
    "topic": {
      "name": "BERTopic + all-MiniLM-L6-v2",
      "version": "bertopic-0.16 + sbert-2.7"
    },
    "classifier": {
      "name": "XGBoost binary",
      "version": "xgboost-2.1",
      "label_proxy": "sentiment_star_divergence > 1.0"
    }
  },

  "limitations": [
    "Suspicion labels are a heuristic proxy. No ground truth fake review labels exist in the Yelp Open Dataset.",
    "Classifier circularity: divergence score is both an input feature and a component of the proxy label.",
    "Geographic scope limited to Arizona restaurants. Findings may not generalize.",
    "Pre-COVID and post-COVID dynamics are mixed in the corpus."
  ],

  "dual_hash": {
    "sha256": "<computed at sign time>",
    "blake3": "<computed at sign time>"
  }
}
```

The dual_hash is computed over a canonical JSON serialization of all fields above it. Use SHA-256 from `hashlib` and BLAKE3 from the `blake3` Python package.

---

## RUBRIC ALIGNMENT — how each rubric category gets to the excellent band

Document this mapping explicitly in `RUBRIC.md`. Build decisions should be checked against it.

| Category | Weight | Excellent (9-10) requirement | How this repo delivers |
|---|---|---|---|
| Business Problem | 15% | Clearly defined, data-driven, strong justification | TABHS thesis in README + 28.3% headline finding hits the professor before any code |
| EDA | 10% | Thorough, insightful, clear visualizations | `01_eda.ipynb` curated from existing 6-plot dashboard |
| NLP Methodology | 25% | Advanced and well-justified methods aligned with problem | Three methods: VADER + BERTopic + LLM (zero-shot/few-shot/multi-model) |
| Results & Insights | 25% | Insightful, well-explained, clear business connection | Per-business TABHS receipts with manipulation delta + Top 10 table + dashboard |
| Presentation | 10% | Well-structured, visually engaging | Static HTML dashboard with ASU theme + recorded video walkthrough |
| Code Clarity | 15% | Modular, best practices, well-documented | Modular `src/` package + tested + CI/CD + receipts as audit trail |

---

## PROFESSOR FEEDBACK constraints (write into `PROFESSOR_FEEDBACK.md`)

Direct quotes from Prof. Lu's feedback to Bubba's project proposal:

> "Good idea. You might not need to use tip.json or checkin.json. The review.json is enough."

> "Both sentiment analysis and topic modeling (which will be covered by Week 6) are required for course project."

**Implication for build:** Do not engineer features that require `tip.json`, `checkin.json`, or `user.json`. Use only what is in `restaurant_reviews_az.csv`. The original TABHS proposal Layer 4 included account-level features (account age, friend graph) — those features are NOT in the CSV. Drop them. The XGBoost model uses only review-level features available in the CSV.

This is disclosed in the `limitations` field of every receipt.

---

## PRIOR WORK INVENTORY (write into `PRIOR_WORK_INVENTORY.md`)

Bubba has the following completed assignments using the same dataset (`restaurant_reviews_az.csv` — 48,147 reviews, 1,864 businesses, 22,435 users, 2020-01-01 to 2022-01-19):

| Asset | Status | Use in this build |
|---|---|---|
| LA2 — SVM TF-IDF baseline (95.70% accuracy) | Complete | Cite as comparison baseline in README |
| LA4 — GRU/LSTM with GloVe (95.15% best) | Complete | Cite as deep learning baseline in README |
| LA5 — BERTopic (80→15 topics) | Complete | Source for `notebooks/03_bertopic.ipynb` |
| LA6 — LLM zero-shot/few-shot/multi-model | Complete | Source for `notebooks/04_llm_methods.ipynb` |
| ProjectEDA — Section 1-8 EDA | Complete | Source for `notebooks/01_eda.ipynb` and Section 7 (VADER) |
| LA6 predictions saved to `LA6_predictions.csv` | Complete | Use directly in feature engineering |

Pull from the existing notebooks. Do not regenerate work that is already done. Validate that the existing outputs match the expected schema before importing.

---

## DESIGN SYSTEM

Match Bubba's existing visual identity:

- **Primary palette:** ASU Maroon `#8C1D40`, ASU Gold `#FFC627`
- **Background:** Dark `#0D1117` for the dashboard, bone for documents
- **Typography:** Consolas / IBM Plex Mono for data, system sans for prose
- **No emdashes anywhere** — use commas, periods, or sentence breaks
- **No LLM cliché phrases** — check copy against the TruthFirst voice doctrine

The README should feel designed, not generic. The dashboard should feel like Bloomberg with school colors, not a SaaS marketing page.

---

## TRUTHFIRST CONSTRAINTS

Every external claim must be verifiable. Specifically:

1. **The 28.3% finding** is the headline. Verify it computes correctly from the actual CSV before publishing it in the README.
2. **Model accuracies** — only cite numbers that this pipeline actually produced. Do not cite LA2's 95.70% in a way that implies this project achieves it. State it as "the LA2 baseline reached 95.70% on the same dataset with a simpler architecture."
3. **The receipt is not a kill switch** — it is forensic governance. Make this clear in the README. Frame it as "court-admissible evidence trail" not "real-time fraud detection."
4. **No production claims** — this is a verified prototype using the RNA pattern, not deployed RNA infrastructure.

If any copy violates these, surface it and rewrite before committing.

---

## DEPENDENCIES (pin these versions)

```
pandas==2.2.3
numpy==1.26.4
scikit-learn==1.5.2
matplotlib==3.9.2
xgboost==2.1.2
bertopic==0.16.4
umap-learn==0.5.6
hdbscan==0.8.40
sentence-transformers==3.2.1
groq==0.13.0
python-dotenv==1.0.1
blake3==0.4.1
jupyter==1.1.1
nbconvert==7.16.4
```

If any version conflicts arise during install, surface them — do not silently bump versions.

---

## ENVIRONMENT VARIABLES

`.env.example` (committed, no real values):

```
GROQ_API_KEY=your_groq_api_key_here
HF_TOKEN=optional_huggingface_token_for_sentence_transformers
```

`.env` (gitignored, populated locally + as Codespaces secret).

For the professor: README must instruct him to either set his own GROQ_API_KEY or use the pre-cached LLM outputs in `outputs/llm_agreement.csv`. Pipeline must support both paths — if no API key is set, load cached results and skip LLM calls.

---

## TESTING

`tests/test_smoke.py` must verify:

1. `data_loader.load_reviews()` returns 48,147 rows
2. `receipts.compute_dual_hash({"a": 1})` returns valid sha256 + blake3
3. `receipts.build_receipt()` produces valid schema
4. Sample receipts in `outputs/receipts/` validate against schema
5. `run_pipeline.py --sample 100 --skip-llm` completes without error

CI runs these on every push. Pipeline failures block merge.

---

## PRE-FLIGHT CHECKLIST (T+48h gate)

Before declaring this build complete, verify all of the following:

- [ ] Repo clones cleanly: `git clone <url> && cd tabhs-cis509`
- [ ] Codespaces builds in under 90 seconds
- [ ] `pip install -r requirements.txt` succeeds with no errors
- [ ] `pytest tests/` passes 100%
- [ ] `python run_pipeline.py --sample 100 --skip-llm` completes in under 3 minutes
- [ ] `outputs/dashboard.html` renders correctly with committed sample receipts
- [ ] All 5 notebooks execute end-to-end without errors
- [ ] All 5 sample receipts validate against the schema
- [ ] Dual-hash verification passes for all sample receipts
- [ ] CI workflow runs successfully on a test branch
- [ ] README has the headline finding visible without scrolling
- [ ] Codespaces button is in the first 100 lines of README
- [ ] All copy passes TruthFirst voice check (no emdashes, no LLM cliches)
- [ ] No mention of features that require `user.json` or `tip.json` or `checkin.json`
- [ ] No production claims anywhere in the repo
- [ ] Receipt limitations field accurately discloses heuristic proxy labeling

If any item fails, do not declare done. Surface it back to Bubba.

---

## What to escalate to Bubba (don't decide silently)

1. **Repo name** — Bubba will set this when he creates the repo
2. **License choice** — MIT vs Apache 2.0
3. **Public vs private repo** — Bubba's call, will affect whether professor needs to be added as collaborator
4. **Codespaces vs local-only** — both should work, but Codespaces is the wow path
5. **Whether to embed the slide deck PPTX** in the repo or link out to it
6. **Final dashboard hostname** if deploying anywhere beyond static GitHub Pages

For everything else, follow this strategy doc and the standard CLAUDEME.md gates.

---

## Done definition

This build is done when:

1. Bubba can send a single GitHub link to Prof. Xiao Liu
2. Prof. Liu opens the link, clicks the Codespaces button, and within 3 minutes is looking at the TABHS dashboard
3. Prof. Liu can click any business and see a signed receipt
4. The slide deck is in `slides/` ready for screen recording
5. The repo is the final project submission for CIS 509

No receipt → not real. No test → not shipped. No gate → not alive.

Build accordingly.