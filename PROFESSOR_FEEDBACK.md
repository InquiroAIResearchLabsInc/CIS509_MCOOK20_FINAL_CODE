# PROFESSOR_FEEDBACK

Direct quotes from Prof. Xiao Liu on the TABHS proposal, with implications for the build.

## Quote 1, scope

> "Good idea. You might not need to use tip.json or checkin.json. The review.json is enough."

**Implication:** All features must be derivable from `data/restaurant_reviews_az.csv`. Do not engineer features that require `tip.json`, `checkin.json`, or `user.json`. The original TABHS proposal Layer 4 included account-level signals such as account age and friend-graph density. Those signals are dropped from this build.

**What that removes from the original proposal:**

- Account age at time of review
- Friend count, fan count, elite status
- Reviewer review-count history
- Cross-business reviewer behavior patterns
- Tip-vs-review consistency
- Check-in-vs-review consistency

**What remains in scope, all derivable from the review CSV:**

- Star rating
- Review text length, content, lexical features
- VADER compound sentiment over the text
- Sentiment-star divergence
- BERTopic topic assignment, including outlier flag
- LLM zero-shot, few-shot, multi-model authenticity verdicts on a sampled subset
- Useful, funny, cool vote counts
- Per-business aggregations of all of the above

This restriction is disclosed in the `limitations` field of every receipt.

## Quote 2, methodology

> "Both sentiment analysis and topic modeling (which will be covered by Week 6) are required for course project."

**Implication:** Sentiment analysis and topic modeling are graded requirements, not optional. Both must appear as primary methods, not as add-ons. The build hits this with:

- **Sentiment:** VADER lexicon scoring on every review (`02_vader_sentiment.ipynb`), augmented by LLM zero-shot and few-shot sentiment on a subset (`04_llm_methods.ipynb`)
- **Topic modeling:** BERTopic with 80 auto-discovered topics reduced to 15 interpretable clusters (`03_bertopic.ipynb`)

Neither method is a wrapper around the other. Both contribute features to the XGBoost classifier in `05_xgboost_tabhs.ipynb`.

## Build constraints derived from feedback

| Constraint | Source | Enforcement |
|---|---|---|
| Use only `restaurant_reviews_az.csv` | Quote 1 | `src/data_loader.py` is the single load entry point, no other CSV is read |
| Sentiment analysis is required | Quote 2 | Notebook 02 produces `vader_scores.csv`, used by notebooks 04 and 05 |
| Topic modeling is required | Quote 2 | Notebook 03 produces `topic_assignments.csv`, used by notebook 05 |
| No account-level features | Quote 1 | Feature engineering in notebook 05 cell 2 references only review-level fields |

If any future contributor adds a feature that requires `tip.json`, `checkin.json`, or `user.json`, the smoke test in `tests/test_smoke.py` will fail because those files are not present and not loadable.
