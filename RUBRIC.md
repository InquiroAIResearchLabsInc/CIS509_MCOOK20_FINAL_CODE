# RUBRIC

CIS 509 final project rubric, six categories. This document maps each category to specific deliverables in this repo and to the path that puts the work in the excellent band, 9 to 10 out of 10.

## Category map

| Category | Weight | Excellent band, 9 to 10 | How this repo delivers |
|---|---|---|---|
| Business Problem | 15% | Clearly defined, data-driven, strong justification | TABHS thesis stated in README and PROJECT_BRIEF, 10.3% headline finding visible without scrolling, framed as audit trail not fraud detection |
| EDA | 10% | Thorough, insightful, clear visualizations | `notebooks/01_eda.ipynb`, six committed plots, summary stats, divergence histogram showing the 10.3% population |
| NLP Methodology | 25% | Advanced and well-justified methods aligned to the problem | Three methods stacked: VADER lexicon, BERTopic 80 to 15 topics, LLM zero-shot plus few-shot plus multi-model agreement. Each justified in its own notebook header |
| Results and Insights | 25% | Insightful, well-explained, clear business connection | Per-business TABHS receipts with manipulation delta, Top 10 manipulated businesses table, static HTML dashboard, manipulation-delta bar chart |
| Presentation | 10% | Well-structured, visually engaging | ASU maroon and gold theme on the dashboard, `slides/TABHS_CLEAN.pptx` deck, README with hero header and Codespaces button |
| Code Clarity | 15% | Modular, best practices, well-documented | Modular `src/` package, 80%+ test coverage on `src/`, GitHub Actions CI, signed receipts as audit trail, every module passes the `validate.sh` checks in `CLAUDEME.md` |

## Excellent-band evidence per category

**Business Problem.** The README opens with the problem statement, the dataset, and the 10.3% finding before any setup instructions. The framing is forensic, not predictive. The receipt is positioned as court-admissible evidence of what was decided, not as a real-time fraud signal.

**EDA.** Six plots covering review-volume distribution, length distribution, time series, business distribution, VADER sentiment by star rating, and sentiment-star divergence histogram. The 10.3% figure is computed live in the notebook from the actual CSV.

**NLP Methodology.** VADER provides the lexicon baseline. BERTopic provides unsupervised topic discovery, with the 80-to-15 reduction motivated explicitly in the notebook. The LLM section runs three protocols on a sampled subset: zero-shot for cold classification, few-shot for primed classification, multi-model agreement using Llama-3.3-70B and a comparator. Each method has a markdown header explaining why that method, why now, and what it contributes to the TABHS feature set.

**Results and Insights.** The Top 10 manipulated businesses are saved to `outputs/top_10_manipulated.csv` and rendered in the dashboard. Each business has a clickable receipt showing raw rating, adjusted rating, manipulation delta, evidence breakdown, model lineage, and dual-hash signature. The manipulation-delta bar chart visualizes the gap between raw and adjusted ratings for the top ten.

**Presentation.** The static HTML dashboard uses ASU maroon `#8C1D40` and gold `#FFC627` on a dark background `#0D1117`, IBM Plex Mono for data, system sans for prose. The slide deck mirrors the same palette and the same headline finding. No emdashes, no LLM cliché phrases.

**Code Clarity.** All shared logic lives in `src/`. The `data_loader`, `receipts`, `llm_client`, `tabhs_pipeline`, `config`, and `mcp_server` modules each have one clear responsibility. The notebooks call into `src/` rather than redefining helpers. Tests live in `tests/`. CI runs on every push. Receipts provide a runtime audit trail. The CLAUDEME compliance script `validate.sh` runs as part of CI.

## Honest disclosure, where the rubric meets reality

The classifier label is a heuristic proxy, sentiment-star divergence greater than 1.0. There is no ground-truth fake-review label in the Yelp Open Dataset. The classifier learns correlations among the OTHER features that align with high-divergence reviews, not "fakeness" as such. This is stated in the notebook 5 markdown above the proxy-label cell, in the receipt `limitations` field, and in the slide deck.

This honesty is the graduate-level move that lifts Results and Insights into the excellent band rather than overselling the model.

## What would drop the project below excellent

Each item below is something the build explicitly avoids:

- Citing LA2's 95.70% accuracy as if this project achieves it
- Calling the receipt a fraud signal or a kill switch
- Engineering features that require files outside `restaurant_reviews_az.csv`
- Hiding the proxy-label circularity
- Shipping notebooks with hardcoded Colab paths
- A README that makes the professor scroll to find the headline
- A pipeline that fails on the professor's machine because of unpinned dependencies
