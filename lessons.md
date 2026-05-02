# Lessons

Per CLAUDEME §12, every correction lands here before continuing. Append-only.

## 2026-05-02, headline finding correction, 28.3% to 10.3%

**Where the number came from:** `Tabhs cis509 build strategy.md` line 14 ("28.3% of Arizona restaurant reviews flagged as inauthentic") and line 16 ("the top 10 most-manipulated Arizona restaurants").

**What the data actually says:** ProjectEDA Section 7.3 output, embedded in `notebooks/_prior_work/ProjectEDA_Cook_Matthew.ipynb`, computes 5,002 reviews with sentiment-star divergence > 1.0 out of 48,147, which is 10.4%. Notebook `02_vader_sentiment.ipynb` regenerates this as 10.25% (the small delta is rounding plus the strategy doc's stated date range vs the slightly different one we now confirm).

**Lesson:** Trust the data, not the strategy doc, when they conflict. Recompute headline numbers from the actual CSV before publishing them. Keep the strategy doc's *direction* (the divergence threshold of 1.0 is fine, the proxy-label idea is fine) but verify the magnitudes.

**Files corrected:**
- `README.md`, hero callout
- `PROJECT_BRIEF.md`, headline finding section
- `RUBRIC.md`, EDA mapping
- `notebooks/01_eda.ipynb`, opening markdown

**Files preserved as historical artifacts:**
- `Tabhs cis509 build strategy.md`, kept verbatim with the wrong number, since editing the strategy doc retroactively would erase the audit trail of what the build was originally aiming for. Anyone reading the strategy doc and the corrected docs side by side will see the disagreement.

**Receipt impact:** No existing receipts encode the 28.3% figure. The five anchor receipts in `outputs/receipts/` use computed VADER divergence values per business, untouched by this correction. The TABHS scores per business are unaffected.

**Verification:**
```bash
PYTHONPATH=. python -c "
import pandas as pd
df = pd.read_csv('outputs/vader_scores.csv')
print(f'{100 * (df.sentiment_star_divergence > 1.0).mean():.2f}%')
"
# Output: 10.25%
```

## 2026-05-02, Excel `#NAME?` corruption hit BOTH columns

**What was found:** the source CSV has Excel-evaluation corruption in two
independent columns:
- 499 rows have `business_id == "#NAME?"`
- 618 rows have `review_id == "#NAME?"`

The earlier filter targeted only `business_id` and missed the
`review_id` corruption. Without the second filter, merges on
`review_id` cross-joined the 618 corrupted rows, exploding the feature
matrix from ~47k rows to 425k rows. Notebook 05's first run produced a
receipt with `review_count=6516` for what should have been a 346-review
business, because that business's reviews were duplicated through the
merge.

**Fix:** `src/data_loader.py` now exposes `load_reviews(clean=True)`,
which calls `clean_corrupted_rows(df)` and drops both ID corruptions.
The cleaned dataset has 47,035 rows (verified). Default `clean=False`
preserves the raw 48,147 rows for fidelity.

**Files corrected:**
- `src/config.py`, renamed `INVALID_BUSINESS_IDS` → `INVALID_IDS`,
  added `EXPECTED_CLEAN_ROW_COUNT = 47_035`
- `src/data_loader.py`, added `clean=False` param,
  `clean_corrupted_rows()` helper. Old `filter_valid_businesses()` aliased.
- `tests/test_smoke.py`, added clean-row-count assertion
- `scripts/generate_anchor_receipts.py`, calls `load_reviews(clean=True)`
- `scripts/build_notebooks.py`, all notebooks now use clean=True
- All five notebooks rebuilt with the corrected loader

**Lesson:** when a column is corrupted, check ALL columns from the same
source. Excel evaluates any cell starting with `=`, `+`, `-`, `@` as a
formula. The CSV had both review_ids and business_ids that started with
those characters, so both columns were independently affected.
