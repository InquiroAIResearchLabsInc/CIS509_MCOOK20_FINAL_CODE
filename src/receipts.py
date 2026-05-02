"""Receipt construction, dual-hash signing, and verification.

Implements the schema in `RECEIPT_SCHEMA.md` and the dual-hash law in
`CLAUDEME.md` §2 ("SHA256:BLAKE3, dual always, never single").

Public API:
    compute_dual_hash(payload)          -> {"sha256": hex, "blake3": hex}
    build_receipt(business_id, ...)     -> dict (unsigned)
    sign_receipt(receipt)               -> dict (with dual_hash)
    write_receipt(receipt, path=None)   -> Path
    verify_receipt(receipt)             -> bool
    emit_receipt(receipt_type, data)    -> dict (and prints JSON to stdout)
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import blake3 as _blake3  # required, no fallback per CLAUDEME §2 "never single"

from src.config import (
    DATA_SOURCE_LABEL,
    MODEL_VERSIONS,
    RECEIPTS_DIR,
    REQUIRED_LIMITATIONS,
    SCHEMA_VERSION,
    TENANT_ID,
)


class StopRule(Exception):
    """Raised on any law violation. Per CLAUDEME §4, never catch silently."""


# --------------------------------------------------------------------------- #
# Canonical serialization + dual hash
# --------------------------------------------------------------------------- #

def _canonical_json(data: dict) -> bytes:
    """Sorted-key, no-whitespace JSON for stable hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_dual_hash(payload: dict | bytes | str) -> dict:
    """Return {sha256, blake3} hex digests over the payload.

    Dicts are canonicalized first. Bytes and strings are hashed directly.
    """
    if isinstance(payload, dict):
        data = _canonical_json(payload)
    elif isinstance(payload, str):
        data = payload.encode("utf-8")
    else:
        data = payload
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "blake3": _blake3.blake3(data).hexdigest(),
    }


# --------------------------------------------------------------------------- #
# Receipt construction
# --------------------------------------------------------------------------- #

def build_receipt(
    business_id: str,
    input_data: dict,
    scores: dict,
    evidence: dict,
    models: dict | None = None,
    extra_limitations: list[str] | None = None,
) -> dict:
    """Construct a TABHS receipt without the dual_hash field.

    Parameters
    ----------
    business_id : str
        Yelp business id.
    input_data : dict
        At minimum: review_count, date_range. data_source defaults to the
        Yelp Open Dataset label from config.
    scores : dict
        raw_yelp_rating, tabhs_adjusted_rating, manipulation_delta,
        suspicious_review_pct.
    evidence : dict
        vader_mean_divergence, topic_outlier_pct,
        llm_few_shot_agreement_rate, xgboost_mean_suspicion_score.
    models : dict, optional
        Override of the default model lineage. Defaults to the pinned
        versions in src.config.MODEL_VERSIONS.
    extra_limitations : list[str], optional
        Additional limitation strings to append to the required five.
    """
    if "data_source" not in input_data:
        input_data = {**input_data, "data_source": DATA_SOURCE_LABEL}

    if models is None:
        models = {
            "sentiment": {
                "name": "VADER + Llama-3.3-70B-Versatile (few-shot)",
                "version": f"{MODEL_VERSIONS['vader']} + {MODEL_VERSIONS['groq_primary']}",
            },
            "topic": {
                "name": "BERTopic + all-MiniLM-L6-v2",
                "version": f"{MODEL_VERSIONS['bertopic']} + {MODEL_VERSIONS['sbert']}",
            },
            "classifier": {
                "name": "XGBoost binary",
                "version": MODEL_VERSIONS["xgboost"],
                "label_proxy": "sentiment_star_divergence > 1.0",
            },
        }

    limitations = list(REQUIRED_LIMITATIONS)
    if extra_limitations:
        limitations.extend(extra_limitations)

    return {
        "schema_version": SCHEMA_VERSION,
        "tenant_id": TENANT_ID,
        "business_id": business_id,
        "computed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input": input_data,
        "scores": scores,
        "evidence": evidence,
        "models": models,
        "limitations": limitations,
    }


def sign_receipt(receipt: dict) -> dict:
    """Add the dual_hash field. Idempotent if already signed (re-signs)."""
    body = {k: v for k, v in receipt.items() if k != "dual_hash"}
    receipt["dual_hash"] = compute_dual_hash(body)
    return receipt


def verify_receipt(receipt: dict) -> bool:
    """Recompute dual hash over canonical body, compare to stored field.

    Both sha256 and blake3 must match. Returns False on any mismatch or
    missing hash field.
    """
    expected = receipt.get("dual_hash")
    if not expected or "sha256" not in expected or "blake3" not in expected:
        return False
    body = {k: v for k, v in receipt.items() if k != "dual_hash"}
    actual = compute_dual_hash(body)
    return (
        expected["sha256"] == actual["sha256"]
        and expected["blake3"] == actual["blake3"]
    )


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #

def write_receipt(receipt: dict, path: Path | None = None) -> Path:
    """Write the receipt to outputs/receipts/{business_id}.json by default."""
    if path is None:
        RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RECEIPTS_DIR / f"{receipt['business_id']}.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=False) + "\n")
    return path


def load_receipt(path: Path) -> dict:
    """Read a receipt JSON from disk. Does not verify, call verify_receipt for that."""
    return json.loads(Path(path).read_text())


# --------------------------------------------------------------------------- #
# CLAUDEME §4 emit_receipt envelope
# --------------------------------------------------------------------------- #

def emit_receipt(receipt_type: str, data: dict) -> dict:
    """Wrap arbitrary state in a CLAUDEME envelope and print to stdout.

    Used for ingest, anchor, anomaly, decision_health, and any other
    receipt types beyond the per-business TABHS receipt. The TABHS
    receipt itself is constructed via build_receipt + sign_receipt.
    """
    envelope = {
        "receipt_type": receipt_type,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tenant_id": data.get("tenant_id", TENANT_ID),
        "payload_hash": compute_dual_hash(data),
        **data,
    }
    print(json.dumps(envelope), flush=True)
    return envelope


# --------------------------------------------------------------------------- #
# Stoprule helpers (CLAUDEME §5)
# --------------------------------------------------------------------------- #

def stoprule_verify_failure(path: Path, expected: dict, actual: dict) -> None:
    """Emit anomaly receipt then halt. Used by MCP verify_chain."""
    emit_receipt("anomaly", {
        "metric": "receipt_verify",
        "delta": -1,
        "classification": "violation",
        "action": "halt",
        "path": str(path),
        "expected_sha256": expected.get("sha256"),
        "actual_sha256": actual.get("sha256"),
    })
    raise StopRule(f"Receipt verification failed for {path}")


# --------------------------------------------------------------------------- #
# CLI for ad-hoc verification
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.receipts <path-to-receipt.json>", file=sys.stderr)
        sys.exit(2)
    receipt = load_receipt(Path(sys.argv[1]))
    ok = verify_receipt(receipt)
    print(json.dumps({"path": sys.argv[1], "verified": ok, "business_id": receipt.get("business_id")}))
    sys.exit(0 if ok else 1)
