# PROJECT_BRIEF

**Course:** ASU W. P. Carey CIS 509, Unstructured Data Analysis
**Instructor:** Prof. Xiao Liu
**Author:** Matthew Cook (MCOOK20)
**Term:** Spring 2026
**Project:** TABHS, Trust-Adjusted Business Health Score for Arizona restaurants

## What this is

A receipts-native NLP pipeline that ingests 48,147 Yelp reviews of Arizona restaurants and produces, per business, a TABHS score along with a cryptographically signed JSON receipt that records the inputs, models, evidence, limitations, and dual hash. The professor opens the repo in Codespaces, clicks one button, and within minutes is looking at the top ten most-manipulated businesses with clickable per-business receipts.

## Headline finding

**10.3% of reviews in the corpus exhibit sentiment-star divergence greater than 1.0** (4,838 of 47,035 cleaned reviews), indicating a written sentiment that does not match the numeric star rating. This is the proxy signal that drives the TABHS adjustment. The strategy doc cited 28.3%, that number was incorrect, see `lessons.md` for the audit trail.

## Dataset

| Property | Value |
|---|---|
| File | `data/restaurant_reviews_az.csv` |
| Rows | 48,147 reviews |
| Businesses | 1,864 |
| Users | 22,435 |
| Date range | 2020-01-01 to 2022-01-19 |
| Source | Yelp Open Dataset, Arizona restaurants subset |
| Columns | `review_id, user_id, business_id, stars, useful, funny, cool, text, date` |

The dataset is committed to the repo so the pipeline runs without external downloads.

## TABHS thesis

For each business with at least ten reviews:

```
raw_avg_stars         = mean(stars)
suspicion_pct         = % reviews predicted suspicious by XGBoost classifier
tabhs_adjusted_stars  = mean(stars) weighted by (1 - suspicion_score)
manipulation_delta    = raw_avg_stars - tabhs_adjusted_stars
```

The top ten businesses by `manipulation_delta` are the ones whose Yelp ratings are most inflated by reviews that fail the multi-method authenticity check.

## Method stack

1. **VADER** lexicon sentiment, divergence vs star rating
2. **BERTopic** topic modeling, 80 topics auto-discovered then reduced to 15 interpretable clusters
3. **LLM authenticity scoring** via Groq, three protocols (zero-shot, few-shot, multi-model agreement)
4. **XGBoost** binary classifier over engineered features, proxy-labeled by divergence threshold
5. **TABHS aggregation** at the business level, written as signed receipts

The classifier label is a heuristic proxy. The receipt explicitly discloses this in the `limitations` field.

## Receipts-native pattern

Every business analysis produces a JSON receipt signed with both SHA-256 and BLAKE3 hashes over a canonical serialization. The receipt records what was decided, on what input, by which models, at what timestamp, and what the known limitations are. See `RECEIPT_SCHEMA.md` for the exact structure.

This is the academic application of the Inquiro receipts-native pattern. It is not production RNA infrastructure.

## Prior work

Five prior assignments use the same dataset. Three feed directly into this build (LA5 BERTopic, LA6 LLM methods, ProjectEDA). Two are cited as comparison baselines (LA2 SVM 95.70%, LA4 LSTM 95.15%). See `PRIOR_WORK_INVENTORY.md`.

## What this repo is not

- Not a Colab notebook dump
- Not a recreation of any prior lab
- Not production infrastructure
- Not a real-time fraud detection system
- Not a kill switch over Yelp ratings

## What this repo delivers

- One command, `python run_pipeline.py --sample 100`, runs end to end
- A static HTML dashboard committed to the repo, populated from sample receipts
- Five anchor receipts committed so the dashboard renders before any pipeline run
- A minimal MCP server exposing `query_receipts`, `verify_chain`, `get_topology`
- A GitHub Actions workflow that re-runs the pipeline weekly on 50 random businesses
- A presentation deck in `slides/` aligned to the headline finding and the receipts pattern

## Done definition

The build is done when Bubba can send Prof. Liu a single GitHub link, the professor clicks the Codespaces button, and within three minutes is looking at the dashboard with clickable signed receipts.
