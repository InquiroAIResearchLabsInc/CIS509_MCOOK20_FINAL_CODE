# PRIOR_WORK_INVENTORY

What already exists from prior CIS 509 assignments, mapped to where it lands in this build. Source notebooks live in `notebooks/_prior_work/` and were carried over from Bubba's Colab Drive. They are reference artifacts, not active pipeline inputs. The pipeline reads the CSV directly and rebuilds outputs deterministically.

## Dataset facts, confirmed by `python3 csv` count

| Property | Value | Notes |
|---|---|---|
| Rows | 48,147 | Stable across LA1, LA2, LA4, LA5, ProjectEDA |
| Businesses | 1,864 | |
| Users | 22,435 | |
| Date range | 2020-01-01 to 2022-01-19 | Confirmed via chronological parse, matches the strategy doc |
| Columns | `review_id, user_id, business_id, stars, useful, funny, cool, text, date` | The strategy doc referenced `useful_votes`, `funny_votes`, `cool_votes`, the actual columns drop the `_votes` suffix. Notebook 5 cell 2 maps accordingly |

## Asset table

| Asset | Status | Method | Headline output | Reuse in this build |
|---|---|---|---|---|
| LA1 | Complete | Count Vectorizer vs TF-IDF feature comparison | Qualitative comparison of 1-star vs 5-star language | Skip, not in pipeline |
| LA2 | Complete | SVM TF-IDF baseline | 95.70% accuracy, VADER 86.50% | Cite as comparison baseline in README |
| LA3 | Complete | Gradient descent and single neuron exercises | Coursework artifact, not domain-relevant | Skip, not in pipeline |
| LA4 | Complete | GRU and LSTM with GloVe embeddings | LSTM trainable embeddings 95.15%, GRU frozen 94.10% | Cite as deep-learning baseline in README |
| LA5 | Complete | BERTopic, 80 topics auto-discovered, reduced to 15 | 15 interpretable topic clusters | Source for `notebooks/03_bertopic.ipynb`, regenerate locally because Colab embeddings are not portable |
| LA6 | Complete | LLM zero-shot, few-shot, multi-model agreement on 40-review subset | Few-shot beats zero-shot, Llama-3.3 and DeepSeek comparable | Source for `notebooks/04_llm_methods.ipynb`. `LA6_predictions.csv` is reused as cached output so the pipeline runs without a Groq key |
| ProjectEDA | Complete | Six-plot EDA dashboard, VADER divergence in Section 7 | 10.4% high-divergence reviews (5,002 of 48,147) | Source for `notebooks/01_eda.ipynb` and the divergence calculation in `notebooks/02_vader_sentiment.ipynb` |

## Reuse plan, by destination notebook

**`notebooks/01_eda.ipynb`** ← ProjectEDA Sections 1 to 6
- Six plots: review volume distribution, review length distribution, reviews over time, business volume distribution, VADER sentiment by star, sentiment-star divergence histogram
- Replace Colab paths with `data/restaurant_reviews_az.csv`
- Confirm the 10.3% figure recomputes from the actual CSV (notebook 02 produces 10.25% on the current CSV; ProjectEDA computed 10.4% on its run)

**`notebooks/02_vader_sentiment.ipynb`** ← ProjectEDA Section 7
- VADER compound score per review
- Divergence calculation, normalized stars vs normalized VADER
- Save `outputs/vader_scores.csv` with columns `review_id, vader_compound, sentiment_star_divergence`

**`notebooks/03_bertopic.ipynb`** ← LA5
- BERTopic with `all-MiniLM-L6-v2` embeddings
- 80 auto-discovered topics, reduce to 15
- Save `outputs/topic_assignments.csv` with `review_id, topic_id, is_topic_outlier`
- Embeddings recompute, Colab pickle is not portable

**`notebooks/04_llm_methods.ipynb`** ← LA6
- Zero-shot, few-shot, multi-model on 40 sampled reviews
- Reuse the existing `LA6_predictions.csv` as the cached source so the run does not require a live Groq key
- Save `outputs/llm_agreement.csv` with columns `review_id, zero_shot_label, few_shot_label, multi_model_agreement_score`

**`notebooks/05_xgboost_tabhs.ipynb`** NET-NEW
- This is the only notebook with original code
- Spec lives in `Tabhs cis509 build strategy.md`, lines 183 to 256
- Nine cells, includes circularity disclosure and heuristic-proxy disclosure

## Skip list

LA1 and LA3 are not used in the pipeline. LA1 is qualitative-only, no portable output. LA3 is a neural-network math exercise unrelated to the project domain. They live in `notebooks/_prior_work/` as historical artifacts but are not referenced by the pipeline.

## Portable artifacts ready to use as-is

- `LA6_predictions.csv`, embedded in the LA6 notebook, 40 rows, three LLM prediction columns. Extract once, save to `outputs/llm_agreement.csv` for the cached path.

## Artifacts that must regenerate

- All BERTopic embeddings, UMAP reductions, topic models. Colab artifacts do not unpickle cleanly across environments.
- All EDA plots, regenerated from `01_eda.ipynb` to keep the dashboard PNGs reproducible.

## Path cleanup required during port

Every prior notebook hardcodes paths under `/content/drive/MyDrive/Colab Notebooks/`. During port, replace with:

- `data/restaurant_reviews_az.csv` for the input CSV
- `outputs/` for produced CSVs, plots, receipts
- `outputs/figures/` for PNG plots
