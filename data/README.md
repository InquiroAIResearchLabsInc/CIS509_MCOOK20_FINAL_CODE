# data/

## restaurant_reviews_az.csv

The full dataset is committed at `data/restaurant_reviews_az.csv`. The pipeline loads it directly via `src/data_loader.py`. No external download is required.

### Provenance

- **Source:** Yelp Open Dataset, Arizona restaurants subset
- **Curated by:** Matthew Cook (MCOOK20) for CIS 509, ASU W. P. Carey
- **Filtering:** Restaurants in Arizona, reviews from 2020-01-01 to 2021-09-09

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
- Date range 2020-01-01 to 2021-09-09

The smoke test at `tests/test_smoke.py` asserts the row count. If a future contributor changes the dataset, the smoke test must be updated in the same commit and the change documented in `lessons.md`.

### Why the column names matter

The strategy doc referenced `useful_votes`, `funny_votes`, `cool_votes`. The actual columns drop the `_votes` suffix. `notebooks/05_xgboost_tabhs.ipynb` cell 2 maps to the actual column names. Anything in `src/` that references vote columns must use `useful`, `funny`, `cool`.

### License

The Yelp Open Dataset is provided by Yelp under their academic-use terms. This subset is redistributed for the CIS 509 academic project only. Do not use for commercial purposes without separate license review.
