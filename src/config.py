"""Constants for the TABHS pipeline.

Single source of truth for paths, thresholds, model identifiers, and the
receipt schema version. Anything pinned must be pinned here.
"""

from pathlib import Path

# Tenant, required on every receipt per CLAUDEME §7
TENANT_ID: str = "cis509-mcook20"

# Repo roots
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = REPO_ROOT / "data"
OUTPUTS_DIR: Path = REPO_ROOT / "outputs"
RECEIPTS_DIR: Path = OUTPUTS_DIR / "receipts"
FIGURES_DIR: Path = OUTPUTS_DIR / "figures"
NOTEBOOKS_DIR: Path = REPO_ROOT / "notebooks"
PRIOR_WORK_DIR: Path = NOTEBOOKS_DIR / "_prior_work"

# Dataset
DATASET_PATH: Path = DATA_DIR / "restaurant_reviews_az.csv"
EXPECTED_ROW_COUNT: int = 48_147
EXPECTED_BUSINESS_COUNT: int = 1_864
EXPECTED_USER_COUNT: int = 22_435
DATASET_COLUMNS: list[str] = [
    "review_id", "user_id", "business_id",
    "stars", "useful", "funny", "cool",
    "text", "date",
]

# TABHS parameters
DIVERGENCE_THRESHOLD: float = 1.0      # |normalized_stars - normalized_vader| > 1.0 → suspicious
MIN_REVIEWS_PER_BUSINESS: int = 10     # below this, business is not scored
TOP_N_MANIPULATED: int = 10            # dashboard table size
ANCHOR_RECEIPT_COUNT: int = 5          # committed sample receipts in outputs/receipts/

# BERTopic
BERTOPIC_NUM_TOPICS_RAW: int = 80
BERTOPIC_NUM_TOPICS_REDUCED: int = 15
BERTOPIC_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

# LLM, Groq
LLM_MODEL_PRIMARY: str = "llama-3.3-70b-versatile"
LLM_MODEL_COMPARATOR: str = "deepseek-r1-distill-llama-70b"
LLM_RATE_LIMIT_SLEEP_SEC: float = 0.5
LLM_CACHE_PATH: Path = OUTPUTS_DIR / "llm_agreement.csv"

# Receipt schema
SCHEMA_VERSION: str = "tabhs-v1.0"
DATA_SOURCE_LABEL: str = "yelp_open_dataset_arizona_restaurants_subset"

# Required limitations on every receipt, RECEIPT_SCHEMA.md §"Limitations field, required entries"
REQUIRED_LIMITATIONS: list[str] = [
    "Suspicion labels are a heuristic proxy. No ground truth fake review labels exist in the Yelp Open Dataset.",
    "Classifier circularity, divergence score is both an input feature and a component of the proxy label.",
    "Geographic scope limited to Arizona restaurants. Findings may not generalize.",
    "Pre-COVID and post-COVID dynamics are mixed in the corpus.",
    "Account-level signals are excluded per professor guidance, only restaurant_reviews_az.csv is used.",
]

# XGBoost, default params per strategy doc
XGBOOST_PARAMS: dict = {
    "n_estimators": 100,
    "max_depth": 6,
    "learning_rate": 0.1,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "random_state": 42,
}

# Model versions, pinned for receipt model lineage
MODEL_VERSIONS: dict = {
    "vader": "vader-3.3.2",
    "groq_primary": "groq-llama-3.3-70b",
    "groq_comparator": "groq-deepseek-r1-distill-llama-70b",
    "bertopic": "bertopic-0.16.4",
    "sbert": "sbert-2.7",
    "xgboost": "xgboost-2.1.2",
}
