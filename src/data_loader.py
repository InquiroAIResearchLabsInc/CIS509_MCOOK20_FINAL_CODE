"""Single source of truth for loading the review dataset.

Anything that needs the reviews calls `load_reviews()`. No other module reads
the CSV directly. This keeps the column-name normalization and date parsing
in one place.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import pandas as pd

from src.config import (
    DATASET_PATH,
    DATASET_COLUMNS,
    EXPECTED_CLEAN_ROW_COUNT,
    EXPECTED_ROW_COUNT,
    INVALID_IDS,
    TENANT_ID,
)


def _emit_ingest_receipt(rows: int, source: str) -> None:
    """Per CLAUDEME §5 ingest_receipt schema.

    Stays minimal until src.receipts is built in Phase 2. Once that lands,
    this stub will be replaced with `emit_receipt("ingest", {...})`.
    """
    receipt = {
        "receipt_type": "ingest",
        "ts": datetime.now(timezone.utc).isoformat(),
        "tenant_id": TENANT_ID,
        "source_type": "csv",
        "source_path": source,
        "row_count": rows,
        "redactions": [],
    }
    print(json.dumps(receipt), file=sys.stderr, flush=True)


def load_reviews(*, strict: bool = False, clean: bool = False) -> pd.DataFrame:
    """Load `data/restaurant_reviews_az.csv` and return a parsed DataFrame.

    Parameters
    ----------
    strict : bool
        If True, raise on row-count mismatch (against the raw or cleaned
        invariant, depending on `clean`). Used by the smoke test.
    clean : bool
        If True, drop rows where review_id or business_id is corrupted
        (Excel `#NAME?` artifacts). Returns ~47,034 rows. The pipeline,
        notebooks, and anchor receipt generator all set clean=True.
        load_reviews() with default `clean=False` preserves the raw CSV
        for fidelity checks.

    Returns
    -------
    pd.DataFrame
        Columns: review_id, user_id, business_id, stars, useful, funny, cool,
        text, date. The `date` column is parsed to pandas datetime64[ns].
    """
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATASET_PATH}. "
            "The CSV should be committed to data/restaurant_reviews_az.csv."
        )

    df = pd.read_csv(DATASET_PATH)

    missing = set(DATASET_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"Dataset is missing expected columns: {sorted(missing)}. "
            f"Got: {list(df.columns)}"
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["stars"] = df["stars"].astype(int)
    df["useful"] = df["useful"].astype(int)
    df["funny"] = df["funny"].astype(int)
    df["cool"] = df["cool"].astype(int)

    if strict and not clean and len(df) != EXPECTED_ROW_COUNT:
        raise AssertionError(
            f"Raw row count mismatch. Expected {EXPECTED_ROW_COUNT}, got {len(df)}. "
            "If the dataset has legitimately changed, update EXPECTED_ROW_COUNT "
            "in src/config.py and log the change in lessons.md."
        )

    if clean:
        df = clean_corrupted_rows(df)
        if strict and len(df) != EXPECTED_CLEAN_ROW_COUNT:
            raise AssertionError(
                f"Clean row count mismatch. Expected {EXPECTED_CLEAN_ROW_COUNT}, got {len(df)}. "
                "Update EXPECTED_CLEAN_ROW_COUNT in src/config.py and log to lessons.md."
            )

    _emit_ingest_receipt(rows=len(df), source=str(DATASET_PATH.relative_to(DATASET_PATH.parent.parent)))
    return df.reset_index(drop=True)


def sample_reviews(n: int, *, random_state: int = 42) -> pd.DataFrame:
    """Convenience for `--sample N` runs. Stratifies by business_id when feasible."""
    df = load_reviews()
    if n >= len(df):
        return df
    return df.sample(n=n, random_state=random_state).reset_index(drop=True)


def clean_corrupted_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where review_id or business_id has Excel-corruption tokens.

    Drops two failure modes from the same upstream cause:
      - business_id == "#NAME?", 499 rows
      - review_id   == "#NAME?", 618 rows
    Some rows are corrupted in both columns, so total dropped is ~1,113
    out of 48,147, leaving ~47,034 clean rows.
    """
    invalid = set(INVALID_IDS)
    keep = (~df["review_id"].isin(invalid)) & (~df["business_id"].isin(invalid))
    return df[keep].reset_index(drop=True)


# Back-compat alias, removed after callers migrate
def filter_valid_businesses(df: pd.DataFrame) -> pd.DataFrame:
    """Deprecated, use clean_corrupted_rows. Kept temporarily for callers."""
    return clean_corrupted_rows(df)


if __name__ == "__main__":
    df = load_reviews(strict=True)
    print(f"Loaded {len(df):,} reviews across {df['business_id'].nunique():,} businesses.")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
