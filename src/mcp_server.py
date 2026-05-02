"""TABHS MCP server, three tools.

Exposes the receipt store to any MCP-compatible client. The professor (or
anyone with Claude Desktop, Cursor, etc.) can attach this server and ask
in plain English which businesses have manipulation delta over 1.0, and
get verified receipts back.

Tools:
    query_receipts(filters)   filter by business_id, delta threshold, date range
    verify_chain(business_ids) recompute dual hash on each, return per-receipt result
    get_topology(business_id) per-business OPEN/HYBRID/CLOSED classification
                              (CLAUDEME §8 meta-loop applied to the audit lens)

Run as a stdio server:
    python -m src.mcp_server

Attach in client config:
    {
      "mcpServers": {
        "tabhs": {
          "command": "python",
          "args": ["-m", "src.mcp_server"],
          "cwd": "/path/to/repo"
        }
      }
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.config import RECEIPTS_DIR, TENANT_ID
from src.receipts import load_receipt, verify_receipt


mcp = FastMCP("tabhs")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _all_receipts() -> dict[str, dict]:
    """Load every receipt in outputs/receipts/, keyed by business_id."""
    receipts = {}
    for path in RECEIPTS_DIR.glob("*.json"):
        try:
            r = load_receipt(path)
            receipts[r["business_id"]] = r
        except Exception:
            continue
    return receipts


# --------------------------------------------------------------------------- #
# Tool 1, query_receipts
# --------------------------------------------------------------------------- #

@mcp.tool()
def query_receipts(
    business_id: str | None = None,
    min_manipulation_delta: float | None = None,
    max_manipulation_delta: float | None = None,
    min_suspicion_pct: float | None = None,
    date_after: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Filter the receipt store. Returns matching receipts and a summary count.

    Args:
        business_id: Exact match on business_id, returns at most one receipt.
        min_manipulation_delta: Lower bound on scores.manipulation_delta.
        max_manipulation_delta: Upper bound on scores.manipulation_delta.
        min_suspicion_pct: Lower bound on scores.suspicious_review_pct.
        date_after: ISO date, returns receipts whose computed_at is after this.
        limit: Max number of receipts in the response (default 20).
    """
    all_receipts = _all_receipts()
    matches = []
    for r in all_receipts.values():
        if business_id and r["business_id"] != business_id:
            continue
        d = r.get("scores", {}).get("manipulation_delta")
        if min_manipulation_delta is not None and (d is None or d < min_manipulation_delta):
            continue
        if max_manipulation_delta is not None and (d is None or d > max_manipulation_delta):
            continue
        s = r.get("scores", {}).get("suspicious_review_pct")
        if min_suspicion_pct is not None and (s is None or s < min_suspicion_pct):
            continue
        if date_after and r.get("computed_at", "") < date_after:
            continue
        matches.append(r)

    # Sort by manipulation_delta desc for the most useful default ordering
    matches.sort(key=lambda r: r.get("scores", {}).get("manipulation_delta", 0), reverse=True)

    return {
        "total_in_store": len(all_receipts),
        "match_count": len(matches),
        "returned": min(limit, len(matches)),
        "tenant_id": TENANT_ID,
        "receipts": matches[:limit],
    }


# --------------------------------------------------------------------------- #
# Tool 2, verify_chain
# --------------------------------------------------------------------------- #

@mcp.tool()
def verify_chain(business_ids: list[str] | None = None) -> dict[str, Any]:
    """Recompute SHA-256 + BLAKE3 over each named receipt's canonical body.

    Returns per-receipt verification results plus a summary. If `business_ids`
    is None, every receipt in the store is verified.

    Per CLAUDEME StopRule, the first failure in a real audit run halts and
    emits an anomaly receipt. This tool surfaces the result to the caller
    without halting, so the professor can see exactly which receipts (if
    any) fail to verify.
    """
    all_receipts = _all_receipts()
    if business_ids is None:
        targets = list(all_receipts.keys())
    else:
        targets = list(business_ids)

    results = []
    for bid in targets:
        receipt = all_receipts.get(bid)
        if receipt is None:
            results.append({"business_id": bid, "status": "missing"})
            continue
        ok = verify_receipt(receipt)
        results.append({
            "business_id": bid,
            "status": "verified" if ok else "MISMATCH",
            "sha256": receipt.get("dual_hash", {}).get("sha256", "")[:16] + "...",
            "blake3": receipt.get("dual_hash", {}).get("blake3", "")[:16] + "...",
        })

    failed = [r for r in results if r["status"] != "verified"]
    return {
        "total_checked": len(results),
        "verified": len(results) - len(failed),
        "failed": len(failed),
        "tenant_id": TENANT_ID,
        "results": results,
    }


# --------------------------------------------------------------------------- #
# Tool 3, get_topology
# --------------------------------------------------------------------------- #

@mcp.tool()
def get_topology(business_id: str) -> dict[str, Any]:
    """Apply the CLAUDEME §8 meta-loop classification to a single business.

    Mapping under the receipts-pattern audit lens:
        E (entropy)   = manipulation_delta
        A (autonomy)  = xgboost_mean_suspicion_score
        T (transfer)  = topic_outlier_pct

        IF  E >= 0.85 AND A > 0.75:  OPEN    needs human investigation
        ELIF T > 0.70:               HYBRID  pattern transfers across topics
        ELSE:                        CLOSED  contained, ratings are clean

    Returns the topology label, the three input metrics, and a one-line
    recommendation. Emits the classification as a topology_receipt would
    in production, but here just returns the dict.
    """
    receipt = _all_receipts().get(business_id)
    if receipt is None:
        return {
            "business_id": business_id,
            "status": "no_receipt",
            "message": f"No receipt found for {business_id}. "
                       "Run run_pipeline.py to generate, or check the spelling.",
        }
    scores = receipt.get("scores", {})
    evidence = receipt.get("evidence", {})
    E = float(scores.get("manipulation_delta", 0))
    A = float(evidence.get("xgboost_mean_suspicion_score", 0))
    T = float(evidence.get("topic_outlier_pct") or 0)

    if abs(E) >= 0.85 and A > 0.75:
        topology = "OPEN"
        recommendation = (
            "Strong evidence of rating manipulation. Recommend human "
            "investigation. Cascade five variant analyses."
        )
    elif T > 0.70:
        topology = "HYBRID"
        recommendation = (
            "Topic-outlier rate is high, the pattern transfers across "
            "topics. Recommend cross-domain comparison with similar businesses."
        )
    else:
        topology = "CLOSED"
        recommendation = (
            "Pattern is contained. Ratings are within expected bounds for "
            "this business. No escalation required."
        )

    return {
        "business_id": business_id,
        "topology": topology,
        "metrics": {
            "E_entropy_manipulation_delta": round(E, 4),
            "A_autonomy_xgboost_mean_suspicion": round(A, 4),
            "T_transfer_topic_outlier_pct": round(T, 4),
        },
        "thresholds": {"E_open": 0.85, "A_open": 0.75, "T_hybrid": 0.70},
        "recommendation": recommendation,
        "tenant_id": TENANT_ID,
    }


# --------------------------------------------------------------------------- #
# Entry
# --------------------------------------------------------------------------- #

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
