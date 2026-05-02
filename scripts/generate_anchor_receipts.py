"""Generate the 5 committed anchor receipts in outputs/receipts/.

These receipts let the dashboard render before any pipeline run. They use
real VADER divergence and real raw_yelp_rating from the dataset, with
explicit limitations disclosing that topic_outlier_pct,
llm_few_shot_agreement_rate, and xgboost_mean_suspicion_score are
provisional pending the full pipeline run.

Pick the 5 highest-volume businesses with mean stars >= 4.0 (so the
manipulation-delta story is meaningful).

Usage:
    python scripts/generate_anchor_receipts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.config import (
    ANCHOR_RECEIPT_COUNT,
    DIVERGENCE_THRESHOLD,
    MIN_REVIEWS_PER_BUSINESS,
    RECEIPTS_DIR,
)
from src.data_loader import load_reviews
from src.receipts import (
    build_receipt,
    sign_receipt,
    verify_receipt,
    write_receipt,
)


ANCHOR_LIMITATIONS = [
    "Anchor receipt, generated before full pipeline run. "
    "evidence.topic_outlier_pct, evidence.llm_few_shot_agreement_rate, and "
    "evidence.xgboost_mean_suspicion_score are provisional. "
    "Re-running run_pipeline.py replaces this receipt with the full-pipeline result.",
]


def normalize_stars(stars: int) -> float:
    """Map 1..5 stars to -1..+1 for divergence computation."""
    return (stars - 3.0) / 2.0


def compute_business_evidence(reviews: pd.DataFrame, vader: SentimentIntensityAnalyzer) -> dict:
    """Compute the evidence fields we can produce without the full pipeline.

    Returns the partial evidence dict and the suspicious-review percentage.
    """
    compounds = reviews["text"].fillna("").map(lambda t: vader.polarity_scores(t)["compound"])
    norm_stars = reviews["stars"].map(normalize_stars)
    divergence = (norm_stars - compounds).abs()
    suspicious = (divergence > DIVERGENCE_THRESHOLD).astype(int)

    suspicion_pct = float(suspicious.mean() * 100)
    raw_avg = float(reviews["stars"].mean())
    # First-order TABHS approximation: weight stars by (1 - suspicion).
    # Replaced by full XGBoost-driven score in run_pipeline.py.
    weights = 1.0 - suspicious
    if weights.sum() > 0:
        adjusted = float((reviews["stars"] * weights).sum() / weights.sum())
    else:
        adjusted = raw_avg

    evidence = {
        "vader_mean_divergence": float(divergence.mean()),
        "topic_outlier_pct": None,
        "llm_few_shot_agreement_rate": None,
        # Anchor-time approximation: divergence proxy stands in for the
        # classifier output until 05_xgboost_tabhs.ipynb runs.
        "xgboost_mean_suspicion_score": float(suspicious.mean()),
    }
    scores = {
        "raw_yelp_rating": round(raw_avg, 3),
        "tabhs_adjusted_rating": round(adjusted, 3),
        "manipulation_delta": round(raw_avg - adjusted, 3),
        "suspicious_review_pct": round(suspicion_pct, 2),
    }
    return evidence, scores


def pick_anchor_businesses(df: pd.DataFrame, k: int) -> list[str]:
    """Pick k high-volume businesses with mean stars >= 4.0 for visible delta."""
    grp = (
        df.groupby("business_id")
        .agg(review_count=("review_id", "count"), avg_stars=("stars", "mean"))
        .reset_index()
    )
    candidates = grp[
        (grp["review_count"] >= MIN_REVIEWS_PER_BUSINESS) & (grp["avg_stars"] >= 4.0)
    ].sort_values("review_count", ascending=False)
    return candidates.head(k)["business_id"].tolist()


def main() -> int:
    df = load_reviews(clean=True)
    vader = SentimentIntensityAnalyzer()

    business_ids = pick_anchor_businesses(df, ANCHOR_RECEIPT_COUNT)
    print(f"Selected {len(business_ids)} anchor businesses by review volume + avg stars >= 4.0")

    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for bid in business_ids:
        reviews = df[df["business_id"] == bid]
        evidence, scores = compute_business_evidence(reviews, vader)
        date_min = reviews["date"].min().strftime("%Y-%m-%d")
        date_max = reviews["date"].max().strftime("%Y-%m-%d")

        receipt = build_receipt(
            business_id=bid,
            input_data={
                "review_count": int(len(reviews)),
                "date_range": [date_min, date_max],
            },
            scores=scores,
            evidence=evidence,
            extra_limitations=ANCHOR_LIMITATIONS,
        )
        receipt = sign_receipt(receipt)
        path = write_receipt(receipt)
        ok = verify_receipt(receipt)
        print(
            f"  {bid}: reviews={len(reviews):4d} "
            f"raw={scores['raw_yelp_rating']:.2f} "
            f"adj={scores['tabhs_adjusted_rating']:.2f} "
            f"delta={scores['manipulation_delta']:+.2f} "
            f"susp%={scores['suspicious_review_pct']:.1f} "
            f"verify={'PASS' if ok else 'FAIL'}"
        )
        if not ok:
            return 1
        written.append(path)

    print(f"\nReceipts generated: {len(written)} / {len(business_ids)} verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
