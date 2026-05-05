<div align="center">

<svg width="100%" height="120" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 120">
  <rect width="1200" height="120" fill="#8C1D40"/>
  <rect width="1200" height="6" y="114" fill="#FFC627"/>
  <text x="60" y="58" font-family="Consolas, 'IBM Plex Mono', monospace" font-size="36" font-weight="700" fill="#FFC627">TABHS</text>
  <text x="60" y="92" font-family="system-ui, sans-serif" font-size="18" fill="#FFFFFF">Trust-Adjusted Business Health Score, Arizona restaurants</text>
  <text x="1140" y="58" text-anchor="end" font-family="system-ui, sans-serif" font-size="14" fill="#FFC627">CIS 509, ASU W. P. Carey</text>
  <text x="1140" y="80" text-anchor="end" font-family="system-ui, sans-serif" font-size="12" fill="#FFFFFF">Matthew Cook, MCOOK20</text>
  <text x="1140" y="100" text-anchor="end" font-family="system-ui, sans-serif" font-size="12" fill="#FFFFFF">Receipts-native NLP, Spring 2026</text>
</svg>

### **10.3% of Arizona restaurant reviews show sentiment that does not match their star rating** (4,838 of 47,035 cleaned reviews, divergence > 1.0).

48,147 raw rows, 47,035 after dropping Excel-corrupted IDs, 1,864 restaurants. Every business produces a JSON receipt signed with SHA-256 plus BLAKE3.

[![View dashboard](https://img.shields.io/badge/View_dashboard-8C1D40?style=for-the-badge&logo=github&logoColor=FFC627)](https://inquiroairesearchlabsinc.github.io/CIS509_MCOOK20_FINAL_CODE/)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/InquiroAIResearchLabsInc/CIS509_MCOOK20_FINAL_CODE)

</div>

---

## What this is

A receipts-native NLP pipeline that scores Arizona restaurants on the gap between their headline Yelp rating and a trust-adjusted rating computed from sentiment-star divergence, BERTopic outliers, LLM authenticity verdicts, and an XGBoost classifier. Output is per-business, signed, and reproducible.

## Run it

| Path | Time | What you get |
|---|---|---|
| **[Live dashboard](https://inquiroairesearchlabsinc.github.io/CIS509_MCOOK20_FINAL_CODE/)** | ~1s | Mobile + desktop, no install |
| **Codespaces** (badge above) | ~30s with prebuilds | Lean Python env, fast pipeline |
| `git clone` + local | ~1min | Full ML stack on your machine |

Codespace and local fast path:

```bash
pip install -r requirements-base.txt
python run_pipeline.py --sample 100 --skip-llm --skip-topics
```

Heavy ML stack (BERTopic, sentence-transformers, CPU-only PyTorch) is opt-in:

```bash
bash .devcontainer/install-ml.sh
# or, locally:
pip install --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.4.1 bertopic==0.16.4 umap-learn==0.5.6 \
    hdbscan==0.8.40 sentence-transformers==3.2.1
```

## Pipeline

| Step | Method | Output |
|---|---|---|
| 1 | Load `data/restaurant_reviews_az.csv` (48,147 rows) | `pandas.DataFrame` |
| 2 | VADER lexicon sentiment, divergence vs star | `outputs/vader_scores.csv` |
| 3 | BERTopic, 80 topics reduced to 15 | `outputs/topic_assignments.csv` |
| 4 | LLM zero-shot, few-shot, multi-model agreement | `outputs/llm_agreement.csv` |
| 5 | XGBoost binary classifier, proxy-labeled by divergence | per-review suspicion scores |
| 6 | Per-business aggregation, write signed receipts | `outputs/receipts/{business_id}.json` |
| 7 | Top 10 most-manipulated businesses | `outputs/top_10_manipulated.csv` |

The classifier label is a heuristic proxy. There is no ground-truth fake-review label in the Yelp Open Dataset. Every receipt discloses this in its `limitations` field. See `RECEIPT_SCHEMA.md`.

## Layout

```
tabhs/
├── run_pipeline.py                 CLI entry
├── requirements-base.txt           lean install
├── requirements.txt                full install (lean + ML stack)
├── .devcontainer/                  Codespaces config, Python 3.11
├── .github/workflows/              CI, Pages deploy, weekly refresh
├── data/restaurant_reviews_az.csv  48,147 reviews
├── notebooks/
│   ├── 01_eda.ipynb                six plots, 10.3% finding
│   ├── 02_vader_sentiment.ipynb    VADER divergence
│   ├── 03_bertopic.ipynb           BERTopic 80 to 15
│   ├── 04_llm_methods.ipynb        Groq zero/few/multi-model
│   └── 05_xgboost_tabhs.ipynb      classifier + TABHS scoring
├── src/
│   ├── data_loader.py              single load_reviews() entry
│   ├── receipts.py                 dual-hash sign, schema validation
│   ├── llm_client.py               Groq wrapper with cache fallback
│   ├── tabhs_pipeline.py           orchestrator
│   ├── mcp_server.py               query_receipts, verify_chain, get_topology
│   └── config.py                   constants
├── outputs/
│   ├── receipts/                   per-business signed JSON
│   ├── figures/                    PNG plots
│   ├── dashboard.html              static, mobile-optimized
│   └── top_10_manipulated.csv      refreshed weekly by Actions
├── slides/TABHS_CLEAN.pptx         final presentation
└── tests/test_smoke.py             pytest smoke suite
```

## Baselines

Prior CIS 509 assignments on this dataset:

- **LA2, SVM TF-IDF:** 95.70% accuracy on 5-star vs 1-star binary sentiment (44,093 rows after dropping 3-star)
- **LA4, LSTM with trainable GloVe:** 95.15% on the same task

This project builds a different artifact (per-business signed receipt) on top of sentiment, topic modeling, and LLM agreement. Headline numbers are not the goal.

## Receipts

SHA-256 plus BLAKE3 over canonical JSON. Verification recomputes both hashes; both must match.

```json
{
  "schema_version": "tabhs-v1.0",
  "tenant_id": "cis509-mcook20",
  "business_id": "Wnk_QW8Vi5a01gmgZBFiLQ",
  "computed_at": "2026-04-27T18:34:42Z",
  "scores": {"raw_yelp_rating": 4.7, "tabhs_adjusted_rating": 3.2, "manipulation_delta": 1.5, ...},
  "evidence": {"vader_mean_divergence": 0.73, ...},
  "models": {...},
  "limitations": [...],
  "dual_hash": {"sha256": "...", "blake3": "..."}
}
```

Full schema in `RECEIPT_SCHEMA.md`.

## MCP server

Three tools over the receipt store:

- `query_receipts(filters)` — match by `business_id`, `manipulation_delta` threshold, or date range
- `verify_chain(start_id, end_id)` — recompute dual-hash on every receipt in range, halt on first failure
- `get_topology(business_id)` — meta-loop classification (open / hybrid / closed)

Attach via:

```json
{
  "mcpServers": {
    "tabhs": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

## Citation

```bibtex
@misc{cook2026tabhs,
  author = {Cook, Matthew},
  title  = {TABHS, Trust-Adjusted Business Health Score for Arizona Restaurants},
  year   = {2026},
  note   = {CIS 509 final project, ASU W. P. Carey}
}
```

## License

MIT. See `LICENSE`. Yelp Open Dataset under Yelp's academic-use terms, see `data/README.md`.
