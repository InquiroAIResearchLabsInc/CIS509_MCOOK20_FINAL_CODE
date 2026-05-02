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

### **28.3% of Arizona restaurant reviews show sentiment that does not match their star rating.**

Built on 48,147 reviews across 1,864 restaurants. Every business analyzed produces a JSON receipt signed with SHA-256 plus BLAKE3.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/InquiroAIResearchLabsInc/CIS509_MCOOK20_FINAL_CODE)

</div>

---

## What you are looking at

A receipts-native NLP pipeline that scores Arizona restaurants on the gap between their headline Yelp rating and a trust-adjusted rating computed from sentiment-star divergence, BERTopic outliers, LLM authenticity verdicts, and an XGBoost classifier. The output is per-business, signed, and reproducible.

Open the dashboard, click any business, see the receipt that justifies its score.

## Three-line setup, on the professor's machine

```bash
git clone https://github.com/InquiroAIResearchLabsInc/CIS509_MCOOK20_FINAL_CODE.git tabhs
cd tabhs
python run_pipeline.py --sample 100 --skip-llm
```

Or click **Open in GitHub Codespaces** above. The dev container builds in about 60 seconds, opens `run_pipeline.py` in the editor, and previews `outputs/dashboard.html`. The dashboard renders with five committed sample receipts even before the pipeline runs.

## What the pipeline does

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

## Repo layout

```
tabhs/
├── README.md                       this file
├── CLAUDEME.md                     execution standards (Inquiro v5.0)
├── PROJECT_BRIEF.md                what this project is
├── PROFESSOR_FEEDBACK.md           Prof. Liu's constraints, applied
├── RUBRIC.md                       grading rubric mapped to deliverables
├── PRIOR_WORK_INVENTORY.md         what came from LA2/LA4/LA5/LA6/EDA
├── RECEIPT_SCHEMA.md               JSON receipt structure and dual-hash protocol
├── Tabhs cis509 build strategy.md  build manifest
├── LICENSE                         MIT
├── run_pipeline.py                 CLI entry, --sample N --skip-llm
├── pyproject.toml / requirements.txt  pinned deps
├── .devcontainer/                  Codespaces config, Python 3.11
├── .github/workflows/              CI on push, weekly refresh of top 10
├── data/restaurant_reviews_az.csv  the dataset, 48,147 reviews
├── notebooks/
│   ├── 01_eda.ipynb                EDA, six plots, 28.3% finding
│   ├── 02_vader_sentiment.ipynb    VADER divergence
│   ├── 03_bertopic.ipynb           BERTopic 80 to 15
│   ├── 04_llm_methods.ipynb        Groq zero/few/multi-model
│   ├── 05_xgboost_tabhs.ipynb      classifier + TABHS scoring (net new)
│   └── _prior_work/                LA1, LA2, LA3, LA4, LA5, LA6, ProjectEDA, archived
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
│   ├── dashboard.html              static, ASU-themed
│   └── top_10_manipulated.csv      refreshed weekly by Actions
├── slides/TABHS_CLEAN.pptx         final presentation
└── tests/test_smoke.py             pytest smoke suite
```

## What it does not do

- Not real-time fraud detection
- Not a kill switch over Yelp ratings
- Not a recreation of any prior lab assignment from scratch
- Not production RNA infrastructure, this is the academic application of the receipts-native pattern

## Comparison baselines from prior work

Prior CIS 509 assignments on the same dataset establish reference points:

- **LA2, SVM TF-IDF:** 95.70% accuracy on 5-star vs 1-star binary sentiment (44,093 rows after dropping 3-star)
- **LA4, LSTM with trainable GloVe:** 95.15% on the same task

This project does not chase those headline numbers. It builds a different artifact, the per-business signed receipt, on top of methods that include sentiment, topic modeling, and LLM agreement.

## Receipts

Every business receipt is signed with SHA-256 and BLAKE3 over a canonical JSON serialization. The `dual_hash` field stores both hashes as separate hex strings. Verification recomputes the canonical bytes and re-hashes. Single-hash match is a verification failure, both must match.

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

A minimal MCP server exposes the receipt store to any MCP-compatible client. Three tools:

- `query_receipts(filters)` returns receipts matching `business_id`, `manipulation_delta` threshold, or date range
- `verify_chain(start_id, end_id)` recomputes dual-hash on every receipt in the range, halts on first failure
- `get_topology(business_id)` returns the meta-loop classification (open, hybrid, closed) for the business under the receipts-pattern audit lens

Attach by adding to your client's MCP config:

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

Then ask the client in plain English which businesses have manipulation delta over 1.0 and get verified receipts back.

## Citation

```bibtex
@misc{cook2026tabhs,
  author = {Cook, Matthew},
  title  = {TABHS, Trust-Adjusted Business Health Score for Arizona Restaurants},
  year   = {2026},
  note   = {CIS 509 final project, ASU W. P. Carey, advised by Prof. Xiao Liu}
}
```

## License

MIT. See `LICENSE`. The Yelp Open Dataset is included under Yelp's academic-use terms, see `data/README.md`.

---

<sub>No receipt, not real. No test, not shipped. No gate, not alive. Built per `CLAUDEME.md` v5.0.</sub>
