"""Smoke tests for the TABHS pipeline.

The strategy doc requires five smoke checks (lines 435-441):
  1. data_loader.load_reviews() returns 48,147 rows                    [Phase 1]
  2. receipts.compute_dual_hash({"a": 1}) returns valid sha256+blake3  [Phase 2]
  3. receipts.build_receipt() produces valid schema                    [Phase 2]
  4. Sample receipts in outputs/receipts/ validate against schema      [Phase 2]
  5. run_pipeline.py --sample 100 --skip-llm completes without error   [Phase 4]

T+2h gate covers item 1. Items 2-5 are scaffolded as skipped tests until
their modules land.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from src import config


# --------------------------------------------------------------------------- #
# Item 1, data loader (T+2h gate)
# --------------------------------------------------------------------------- #

def test_data_loader_returns_expected_row_count() -> None:
    from src.data_loader import load_reviews
    df = load_reviews(strict=True)
    assert len(df) == config.EXPECTED_ROW_COUNT, (
        f"Expected {config.EXPECTED_ROW_COUNT} rows, got {len(df)}"
    )


def test_data_loader_business_count() -> None:
    from src.data_loader import load_reviews
    df = load_reviews()
    assert df["business_id"].nunique() == config.EXPECTED_BUSINESS_COUNT


def test_data_loader_user_count() -> None:
    from src.data_loader import load_reviews
    df = load_reviews()
    assert df["user_id"].nunique() == config.EXPECTED_USER_COUNT


def test_data_loader_columns_present() -> None:
    from src.data_loader import load_reviews
    df = load_reviews()
    for col in config.DATASET_COLUMNS:
        assert col in df.columns, f"Missing expected column: {col}"


def test_data_loader_dates_parsed() -> None:
    import pandas as pd
    from src.data_loader import load_reviews
    df = load_reviews()
    assert pd.api.types.is_datetime64_any_dtype(df["date"]), (
        "date column should be datetime64, got " + str(df["date"].dtype)
    )


def test_sample_reviews_returns_requested_size() -> None:
    from src.data_loader import sample_reviews
    sample = sample_reviews(100)
    assert len(sample) == 100


# --------------------------------------------------------------------------- #
# Config invariants (T+2h gate)
# --------------------------------------------------------------------------- #

def test_tenant_id_is_pinned() -> None:
    assert config.TENANT_ID == "cis509-mcook20"


def test_required_limitations_count() -> None:
    assert len(config.REQUIRED_LIMITATIONS) == 5


def test_schema_version_pinned() -> None:
    assert config.SCHEMA_VERSION == "tabhs-v1.0"


def test_dataset_path_exists() -> None:
    assert config.DATASET_PATH.exists(), (
        f"Dataset missing at {config.DATASET_PATH}, "
        "should be committed to data/restaurant_reviews_az.csv"
    )


# --------------------------------------------------------------------------- #
# Items 2 + 3, receipts module (Phase 2 gate)
# --------------------------------------------------------------------------- #

_RECEIPTS_AVAILABLE = importlib.util.find_spec("src.receipts") is not None


@pytest.mark.skipif(not _RECEIPTS_AVAILABLE, reason="src.receipts lands in Phase 2")
def test_compute_dual_hash_returns_sha256_and_blake3() -> None:
    from src.receipts import compute_dual_hash
    result = compute_dual_hash({"a": 1})
    assert "sha256" in result and "blake3" in result
    assert len(result["sha256"]) == 64  # hex digest of sha256
    assert len(result["blake3"]) == 64  # hex digest of blake3-256


@pytest.mark.skipif(not _RECEIPTS_AVAILABLE, reason="src.receipts lands in Phase 2")
def test_build_receipt_produces_valid_schema() -> None:
    from src.receipts import build_receipt
    r = build_receipt(
        business_id="test_business_id",
        input_data={"review_count": 12, "date_range": ["2020-01-01", "2020-12-31"]},
        scores={"raw_yelp_rating": 4.5, "tabhs_adjusted_rating": 3.5,
                "manipulation_delta": 1.0, "suspicious_review_pct": 25.0},
        evidence={"vader_mean_divergence": 0.5, "topic_outlier_pct": 0.1,
                  "llm_few_shot_agreement_rate": 0.8, "xgboost_mean_suspicion_score": 0.3},
    )
    assert r["schema_version"] == config.SCHEMA_VERSION
    assert r["tenant_id"] == config.TENANT_ID
    assert r["business_id"] == "test_business_id"
    assert "limitations" in r and len(r["limitations"]) >= 5


# --------------------------------------------------------------------------- #
# Item 4, sample receipts on disk validate (Phase 2c gate)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not _RECEIPTS_AVAILABLE, reason="src.receipts lands in Phase 2")
def test_committed_sample_receipts_validate() -> None:
    from src.receipts import verify_receipt
    receipt_files = sorted(config.RECEIPTS_DIR.glob("*.json"))
    if len(receipt_files) == 0:
        pytest.skip("No anchor receipts committed yet (Phase 2c)")
    for path in receipt_files:
        receipt = json.loads(path.read_text())
        assert verify_receipt(receipt), f"Receipt failed dual-hash verify: {path}"


# --------------------------------------------------------------------------- #
# Item 5, end-to-end pipeline (Phase 4 gate)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(
    not Path(config.REPO_ROOT / "run_pipeline.py").exists(),
    reason="run_pipeline.py lands in Phase 4a",
)
def test_pipeline_runs_on_100_sample_skip_llm() -> None:
    """Smoke-runs the CLI end-to-end on a 100-row sample with --skip-llm.

    This is the strategy-doc T+48h gate test. Lives here because pytest is
    the unified entry for all gates.
    """
    import subprocess
    result = subprocess.run(
        ["python", "run_pipeline.py", "--sample", "100", "--skip-llm"],
        cwd=config.REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"run_pipeline.py exited {result.returncode}\n"
        f"stdout: {result.stdout[-2000:]}\n"
        f"stderr: {result.stderr[-2000:]}"
    )
