"""End-to-end TABHS pipeline as a callable orchestrator.

The notebooks are the human-readable view of these same steps. Both call
into shared `src/` helpers where it makes sense, but for execution speed
the pipeline runs as plain Python.

Steps:
    1. Load + clean reviews
    2. VADER scoring (always)
    3. BERTopic (optional, slow; --skip-topics)
    4. LLM agreement (optional, paid; --skip-llm)
    5. XGBoost training + per-review suspicion scoring
    6. Per-business aggregation, top-10 + top-100 selection
    7. Receipt generation for the union, all dual-hash signed
    8. Optional, save vader/topic/llm CSVs for downstream reuse

Public entry: `run_pipeline(sample=None, skip_llm=False, skip_topics=False)`
returns a dict of results, also written to `outputs/`.

CLI is `run_pipeline.py` at the repo root.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split

from src.config import (
    DIVERGENCE_THRESHOLD,
    LLM_CACHE_PATH,
    MIN_REVIEWS_PER_BUSINESS,
    OUTPUTS_DIR,
    RECEIPTS_DIR,
    TOP_N_MANIPULATED,
    XGBOOST_PARAMS,
)
from src.data_loader import load_reviews
from src.receipts import build_receipt, emit_receipt, sign_receipt, write_receipt


@dataclass
class PipelineResult:
    """Summary of a pipeline run, returned to the CLI for printing."""
    n_reviews: int
    n_businesses_scored: int
    headline_pct: float
    classifier_accuracy: float
    classifier_f1: float
    receipts_written: int
    elapsed_seconds: float
    skipped: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Step 2, VADER
# --------------------------------------------------------------------------- #

def step_vader(df: pd.DataFrame) -> pd.DataFrame:
    """Compute VADER compound and divergence per review."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader = SentimentIntensityAnalyzer()
    out = df[["review_id", "stars"]].copy()
    out["vader_compound"] = df["text"].fillna("").map(
        lambda t: vader.polarity_scores(t)["compound"]
    )
    out["normalized_stars"] = (df["stars"] - 3) / 2.0
    out["sentiment_star_divergence"] = (out["vader_compound"] - out["normalized_stars"]).abs()
    out["suspicious"] = (out["sentiment_star_divergence"] > DIVERGENCE_THRESHOLD).astype(int)
    return out


# --------------------------------------------------------------------------- #
# Step 3, BERTopic, optional
# --------------------------------------------------------------------------- #

def step_topics(df: pd.DataFrame, *, sample_size: int | None = 5000) -> pd.DataFrame:
    """Run BERTopic, return review_id + topic_id + is_topic_outlier.

    On a sample by default. Set sample_size=None for the full corpus.
    """
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    from umap import UMAP
    from hdbscan import HDBSCAN

    from src.config import (
        BERTOPIC_EMBEDDING_MODEL,
        BERTOPIC_NUM_TOPICS_RAW,
        BERTOPIC_NUM_TOPICS_REDUCED,
    )

    if sample_size and sample_size < len(df):
        sub = df.sample(n=sample_size, random_state=42).reset_index(drop=True)
    else:
        sub = df.copy()

    model = SentenceTransformer(BERTOPIC_EMBEDDING_MODEL)
    embeds = model.encode(sub["text"].fillna("").tolist(), show_progress_bar=False, batch_size=64)

    topic_model = BERTopic(
        embedding_model=model,
        umap_model=UMAP(n_components=5, n_neighbors=15, min_dist=0.0,
                        metric="cosine", random_state=42),
        hdbscan_model=HDBSCAN(min_cluster_size=15, metric="euclidean",
                              cluster_selection_method="eom", prediction_data=True),
        nr_topics=BERTOPIC_NUM_TOPICS_RAW,
        verbose=False,
    )
    topics, _ = topic_model.fit_transform(sub["text"].fillna("").tolist(), embeds)
    topic_model.reduce_topics(sub["text"].fillna("").tolist(), nr_topics=BERTOPIC_NUM_TOPICS_REDUCED)
    out = sub[["review_id"]].copy()
    out["topic_id"] = topic_model.topics_
    out["is_topic_outlier"] = (out["topic_id"] == -1).astype(int)
    return out


# --------------------------------------------------------------------------- #
# Step 4, LLM agreement, optional
# --------------------------------------------------------------------------- #

def step_llm(df: pd.DataFrame, *, subset_size: int = 40) -> pd.DataFrame | None:
    """Run zero/few/multi-model on a 40-review balanced subset.

    Returns None if no API key and no cache. Caller should treat None as
    'skip the LLM evidence column'.
    """
    from src.llm_client import LLMClient
    client = LLMClient(allow_cache_only=True)
    if not (client.is_live or client.is_cached):
        return None

    # 20 negative + 20 positive
    neg = df[df["stars"] == 1]
    pos = df[df["stars"] == 5]
    if len(neg) < subset_size // 2 or len(pos) < subset_size // 2:
        return None
    sub = pd.concat([
        neg.sample(subset_size // 2, random_state=42),
        pos.sample(subset_size // 2, random_state=42),
    ]).reset_index(drop=True)

    rows = []
    for _, r in sub.iterrows():
        zs = client.zero_shot(r["text"], review_id=r["review_id"])
        fs = client.few_shot(r["text"], review_id=r["review_id"])
        ag = client.multi_model_agreement(r["text"], review_id=r["review_id"])
        rows.append({
            "review_id": r["review_id"],
            "true_label": int(r["stars"] >= 4),
            "zero_shot_label": zs["label"],
            "few_shot_label": fs["label"],
            "primary_label": ag["primary"],
            "comparator_label": ag["comparator"],
            "multi_model_agreement": bool(ag["agreement"]),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Step 5, classifier
# --------------------------------------------------------------------------- #

FEATURE_COLS = [
    "stars", "useful", "funny", "cool",
    "review_length_words",
    "vader_compound", "sentiment_star_divergence",
    "topic_id", "is_topic_outlier",
]


def step_features(df: pd.DataFrame, vader: pd.DataFrame, topics: pd.DataFrame | None) -> pd.DataFrame:
    f = df[["review_id", "business_id", "stars", "useful", "funny", "cool"]].copy()
    f["review_length_words"] = df["text"].fillna("").str.split().map(len)
    f = f.merge(
        vader[["review_id", "vader_compound", "sentiment_star_divergence", "suspicious"]],
        on="review_id", how="left",
    )
    if topics is not None:
        f = f.merge(topics[["review_id", "topic_id", "is_topic_outlier"]], on="review_id", how="left")
        f["topic_id"] = f["topic_id"].fillna(-1).astype(int)
        f["is_topic_outlier"] = f["is_topic_outlier"].fillna(1).astype(int)
    else:
        f["topic_id"] = -1
        f["is_topic_outlier"] = 1
    f = f.dropna(subset=["vader_compound", "sentiment_star_divergence"]).reset_index(drop=True)
    f["suspicious_label"] = (f["sentiment_star_divergence"] > DIVERGENCE_THRESHOLD).astype(int)
    return f


def step_classifier(features: pd.DataFrame) -> tuple[xgb.XGBClassifier, dict]:
    X = features[FEATURE_COLS]
    y = features["suspicious_label"]
    if y.sum() == 0 or y.sum() == len(y):
        # degenerate, skip training
        emit_receipt("anomaly", {
            "metric": "classifier_class_balance",
            "delta": -1,
            "classification": "degradation",
            "action": "alert",
            "n_positive": int(y.sum()),
        })
        return None, {"accuracy": float("nan"), "f1": float("nan")}
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42,
    )
    model = xgb.XGBClassifier(**XGBOOST_PARAMS, n_jobs=-1)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    from sklearn.metrics import accuracy_score, f1_score
    return model, {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
    }


# --------------------------------------------------------------------------- #
# Step 6, per-business aggregation
# --------------------------------------------------------------------------- #

def step_aggregate(features: pd.DataFrame, model: xgb.XGBClassifier | None) -> pd.DataFrame:
    if model is not None:
        features["suspicion_score"] = model.predict_proba(features[FEATURE_COLS])[:, 1]
    else:
        features["suspicion_score"] = features["suspicious_label"].astype(float)

    by_biz = features.groupby("business_id").agg(
        review_count=("review_id", "count"),
        raw_avg_stars=("stars", "mean"),
        suspicion_pct=("suspicion_score", lambda s: float((s > 0.5).mean() * 100)),
        mean_suspicion_score=("suspicion_score", "mean"),
    ).reset_index()

    weighted = (
        features.assign(weight=1 - features["suspicion_score"])
        .groupby("business_id")
        .apply(
            lambda g: (g["stars"] * g["weight"]).sum() / g["weight"].sum()
            if g["weight"].sum() > 0 else g["stars"].mean(),
            include_groups=False,
        )
        .rename("tabhs_adjusted_stars")
        .reset_index()
    )
    by_biz = by_biz.merge(weighted, on="business_id")
    by_biz["manipulation_delta"] = by_biz["raw_avg_stars"] - by_biz["tabhs_adjusted_stars"]
    by_biz = by_biz[by_biz["review_count"] >= MIN_REVIEWS_PER_BUSINESS]
    return by_biz.sort_values("manipulation_delta", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Step 7, receipt generation
# --------------------------------------------------------------------------- #

def step_receipts(
    df: pd.DataFrame,
    by_biz: pd.DataFrame,
    features: pd.DataFrame,
    llm: pd.DataFrame | None,
) -> int:
    """Write receipts for top-100-by-volume UNION top-N-by-manipulation."""
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

    top_volume = by_biz.nlargest(100, "review_count")
    top_manip = by_biz.nlargest(TOP_N_MANIPULATED, "manipulation_delta")
    covered = pd.concat([top_volume, top_manip]).drop_duplicates("business_id")

    review_dates = (
        df.groupby("business_id")["date"]
          .agg(["min", "max"])
          .reset_index()
          .rename(columns={"min": "date_min", "max": "date_max"})
    )
    topic_outlier_pct_by_biz = features.groupby("business_id")["is_topic_outlier"].mean()
    vader_div_by_biz = features.groupby("business_id")["sentiment_star_divergence"].mean()
    llm_rate = float(llm["multi_model_agreement"].mean()) if llm is not None and "multi_model_agreement" in llm.columns else None

    written = 0
    for _, row in covered.iterrows():
        bid = row["business_id"]
        drange = review_dates.loc[review_dates["business_id"] == bid].iloc[0]
        receipt = build_receipt(
            business_id=bid,
            input_data={
                "review_count": int(row["review_count"]),
                "date_range": [str(drange["date_min"].date()), str(drange["date_max"].date())],
            },
            scores={
                "raw_yelp_rating": round(float(row["raw_avg_stars"]), 3),
                "tabhs_adjusted_rating": round(float(row["tabhs_adjusted_stars"]), 3),
                "manipulation_delta": round(float(row["manipulation_delta"]), 3),
                "suspicious_review_pct": round(float(row["suspicion_pct"]), 2),
            },
            evidence={
                "vader_mean_divergence": round(float(vader_div_by_biz.get(bid, 0)), 4),
                "topic_outlier_pct": round(float(topic_outlier_pct_by_biz.get(bid, 0)), 4),
                "llm_few_shot_agreement_rate": llm_rate,
                "xgboost_mean_suspicion_score": round(float(row["mean_suspicion_score"]), 4),
            },
        )
        write_receipt(sign_receipt(receipt))
        written += 1
    return written


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #

def run_pipeline(
    *,
    sample: int | None = None,
    skip_llm: bool = False,
    skip_topics: bool = False,
    persist_intermediates: bool = True,
) -> PipelineResult:
    """Run all steps end-to-end. Returns a PipelineResult summary."""
    t0 = time.time()
    skipped: list[str] = []
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_reviews(clean=True)
    if sample and sample < len(df):
        df = df.sample(n=sample, random_state=42).reset_index(drop=True)
    print(f"[1/7] loaded {len(df):,} reviews, {df['business_id'].nunique():,} businesses")

    vader = step_vader(df)
    if persist_intermediates:
        vader.to_csv(OUTPUTS_DIR / "vader_scores.csv", index=False)
    pct = 100.0 * vader["suspicious"].mean()
    print(f"[2/7] VADER scored, {pct:.2f}% above divergence threshold")

    topics = None
    if not skip_topics:
        try:
            topics = step_topics(df, sample_size=min(5000, len(df)))
            if persist_intermediates:
                topics.to_csv(OUTPUTS_DIR / "topic_assignments.csv", index=False)
            print(f"[3/7] BERTopic on {len(topics):,} reviews, "
                  f"{topics['is_topic_outlier'].mean():.1%} outliers")
        except Exception as e:
            print(f"[3/7] BERTopic failed: {e}")
            skipped.append("topics")
    else:
        print("[3/7] BERTopic skipped (--skip-topics)")
        skipped.append("topics")

    llm = None
    if not skip_llm:
        try:
            llm = step_llm(df)
            if llm is not None and persist_intermediates:
                llm.to_csv(LLM_CACHE_PATH, index=False)
                print(f"[4/7] LLM agreement on {len(llm)} reviews")
            else:
                print("[4/7] LLM skipped, no API key and no cache")
                skipped.append("llm")
        except Exception as e:
            print(f"[4/7] LLM failed: {e}")
            skipped.append("llm")
    else:
        print("[4/7] LLM skipped (--skip-llm)")
        skipped.append("llm")

    features = step_features(df, vader, topics)
    print(f"[5a/7] features matrix: {features.shape[0]:,} rows, {features.shape[1]} cols")

    model, metrics = step_classifier(features)
    print(f"[5b/7] XGBoost test acc={metrics['accuracy']:.3f}, f1={metrics['f1']:.3f}")

    by_biz = step_aggregate(features, model)
    top_path = OUTPUTS_DIR / "top_10_manipulated.csv"
    by_biz.head(TOP_N_MANIPULATED).to_csv(top_path, index=False)
    print(f"[6/7] aggregated {len(by_biz):,} businesses, wrote top-{TOP_N_MANIPULATED}")

    written = step_receipts(df, by_biz, features, llm)
    print(f"[7/7] {written} receipts written and signed")

    # Always rebuild the dashboard so it reflects the latest receipts
    try:
        from scripts.build_dashboard import build_dashboard
        dash_path = build_dashboard()
        print(f"[8/7] dashboard refreshed at {dash_path.relative_to(OUTPUTS_DIR.parent)}")
    except Exception as e:
        print(f"[8/7] dashboard rebuild skipped: {e}")

    elapsed = time.time() - t0
    return PipelineResult(
        n_reviews=len(df),
        n_businesses_scored=len(by_biz),
        headline_pct=pct,
        classifier_accuracy=metrics["accuracy"],
        classifier_f1=metrics["f1"],
        receipts_written=written,
        elapsed_seconds=elapsed,
        skipped=skipped,
    )


def main() -> int:
    """Entry point for the `tabhs` console script."""
    import argparse
    parser = argparse.ArgumentParser(description="Run the TABHS pipeline.")
    parser.add_argument("--sample", type=int, default=None,
                        help="Subsample N reviews for fast runs.")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Skip LLM agreement step. Useful in CI.")
    parser.add_argument("--skip-topics", action="store_true",
                        help="Skip BERTopic step. Useful for fast smoke runs.")
    args = parser.parse_args()
    result = run_pipeline(
        sample=args.sample, skip_llm=args.skip_llm, skip_topics=args.skip_topics,
    )
    print()
    print(f"Done in {result.elapsed_seconds:.1f}s.")
    print(f"  Reviews:           {result.n_reviews:,}")
    print(f"  Businesses scored: {result.n_businesses_scored:,}")
    print(f"  Headline (>1.0):   {result.headline_pct:.2f}%")
    print(f"  Classifier acc:    {result.classifier_accuracy:.3f}")
    print(f"  Receipts written:  {result.receipts_written}")
    if result.skipped:
        print(f"  Skipped:           {', '.join(result.skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
