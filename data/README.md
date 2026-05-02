# data/

## restaurant_reviews_az.csv

The full dataset is committed at `data/restaurant_reviews_az.csv`. The pipeline loads it directly via `src/data_loader.py`. No external download is required.

### Provenance

- **Source:** Yelp Open Dataset, Arizona restaurants subset
- **Curated by:** Matthew Cook (MCOOK20) for CIS 509, ASU W. P. Carey
- **Filtering:** Restaurants in Arizona, reviews from 2020-01-01 to 2022-01-19

### Schema

| Column | Type | Notes |
|---|---|---|
| `review_id` | string | Primary key, one row per review |
| `user_id` | string | Reviewer id, may repeat across rows |
| `business_id` | string | Restaurant id, the business unit for TABHS aggregation |
| `stars` | int 1 to 5 | The numeric rating |
| `useful` | int | Useful-vote count |
| `funny` | int | Funny-vote count |
| `cool` | int | Cool-vote count |
| `text` | string | Free-text review body, may contain embedded newlines |
| `date` | string | M/D/YYYY H:MM format, parsed by pandas at load time |

### Invariants

- 48,147 rows
- 1,864 unique businesses
- 22,435 unique users
- Date range 2020-01-01 to 2022-01-19

The smoke test at `tests/test_smoke.py` asserts the row count. If a future contributor changes the dataset, the smoke test must be updated in the same commit and the change documented in `lessons.md`.

### Why the column names matter

The strategy doc referenced `useful_votes`, `funny_votes`, `cool_votes`. The actual columns drop the `_votes` suffix. `notebooks/05_xgboost_tabhs.ipynb` cell 2 maps to the actual column names. Anything in `src/` that references vote columns must use `useful`, `funny`, `cool`.

### Known data corruption, business_id `#NAME?`

499 rows in the CSV have `business_id="#NAME?"`. This is upstream Excel corruption: the original Yelp business IDs began with characters that Excel evaluated as formulas (`=`, `+`, etc.), so the cells display the formula-error string. We cannot recover the original IDs from the CSV.

**Treatment:**

- `src.data_loader.load_reviews()` returns the raw CSV unchanged, preserving the 48,147-row invariant
- `src.data_loader.filter_valid_businesses(df)` drops these rows
- All per-business aggregation (anchor receipts, full pipeline, dashboard top-10) calls `filter_valid_businesses()` first
- The smoke test counts the raw row count (48,147), the per-business counts use the filtered count

The list of invalid IDs is `src.config.INVALID_BUSINESS_IDS`. If new corruption is found, append to that tuple and document the addition in `lessons.md`.

### License

The Yelp Open Dataset is provided by Yelp under their academic-use terms. This subset is redistributed for the CIS 509 academic project only. Do not use for commercial purposes without separate license review.
