# RECEIPT_SCHEMA

The TABHS receipt is a JSON object emitted once per analyzed business. It records the inputs, models, evidence, scores, limitations, and a dual hash signed over a canonical serialization of all the fields above the signature. The receipt is written to `outputs/receipts/{business_id}.json`.

## Schema version

`tabhs-v1.0`. The `schema_version` field is required on every receipt. Any change to the field layout or semantics requires a version bump and an entry in `lessons.md`.

## Full schema, with required fields and types

```json
{
  "schema_version": "tabhs-v1.0",
  "tenant_id": "cis509-mcook20",
  "business_id": "Wnk_QW8Vi5a01gmgZBFiLQ",
  "computed_at": "2026-04-27T18:34:42Z",

  "input": {
    "review_count": 47,
    "date_range": ["2020-03-15", "2021-01-10"],
    "data_source": "yelp_open_dataset_arizona_restaurants_subset"
  },

  "scores": {
    "raw_yelp_rating": 4.7,
    "tabhs_adjusted_rating": 3.2,
    "manipulation_delta": 1.5,
    "suspicious_review_pct": 42.3
  },

  "evidence": {
    "vader_mean_divergence": 0.73,
    "topic_outlier_pct": 0.31,
    "llm_few_shot_agreement_rate": 0.81,
    "xgboost_mean_suspicion_score": 0.47
  },

  "models": {
    "sentiment": {
      "name": "VADER + Llama-3.3-70B-Versatile (few-shot)",
      "version": "vader-3.3.2 + groq-llama-3.3-70b"
    },
    "topic": {
      "name": "BERTopic + all-MiniLM-L6-v2",
      "version": "bertopic-0.16 + sbert-2.7"
    },
    "classifier": {
      "name": "XGBoost binary",
      "version": "xgboost-2.1",
      "label_proxy": "sentiment_star_divergence > 1.0"
    }
  },

  "limitations": [
    "Suspicion labels are a heuristic proxy. No ground truth fake review labels exist in the Yelp Open Dataset.",
    "Classifier circularity, divergence score is both an input feature and a component of the proxy label.",
    "Geographic scope limited to Arizona restaurants. Findings may not generalize.",
    "Pre-COVID and post-COVID dynamics are mixed in the corpus.",
    "Account-level signals are excluded per professor guidance, only restaurant_reviews_az.csv is used."
  ],

  "dual_hash": {
    "sha256": "<computed at sign time>",
    "blake3": "<computed at sign time>"
  }
}
```

## Required fields

| Field | Type | Notes |
|---|---|---|
| `schema_version` | string | Pinned to `tabhs-v1.0` for this build |
| `tenant_id` | string | Pinned to `cis509-mcook20`, required by CLAUDEME §7 |
| `business_id` | string | Yelp business id, primary key |
| `computed_at` | ISO 8601 UTC | Timestamp at receipt construction |
| `input.review_count` | int | Number of reviews aggregated for this business |
| `input.date_range` | [string, string] | First and last review date |
| `input.data_source` | string | Pinned to `yelp_open_dataset_arizona_restaurants_subset` |
| `scores.raw_yelp_rating` | float | Mean of `stars` |
| `scores.tabhs_adjusted_rating` | float | Mean of `stars` weighted by `1 - suspicion_score` |
| `scores.manipulation_delta` | float | `raw - adjusted`, unsigned float |
| `scores.suspicious_review_pct` | float | Percent of reviews predicted suspicious |
| `evidence.*` | float | Per-method aggregates, see schema |
| `models.*.name` | string | Human-readable model name |
| `models.*.version` | string | Pinned versions, must reproduce |
| `models.classifier.label_proxy` | string | Discloses the proxy used to generate training labels |
| `limitations` | list[string] | Required, must include at least the four standard lines plus the professor-guidance line |
| `dual_hash.sha256` | hex string | SHA-256 over canonical JSON of all fields above |
| `dual_hash.blake3` | hex string | BLAKE3 over the same canonical JSON |

## Canonical serialization

The dual hash is computed over the JSON bytes produced by:

```python
canonical = json.dumps(receipt_without_dual_hash, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

The `dual_hash` field is then added to the receipt and the full receipt is written to disk. Verification recomputes the canonical bytes by serializing the receipt with the `dual_hash` field removed and re-hashing.

## Hash format

Per `CLAUDEME.md` §2:

```
HASH = "SHA256:BLAKE3"   # dual always, never single
```

The receipt stores both hashes as separate hex strings rather than the colon-joined CLAUDEME default, because per-receipt verification is more readable that way and a downstream verifier can reconstruct the colon form trivially as `f"{sha256}:{blake3}"`.

## Verification protocol

```python
def verify_receipt(receipt: dict) -> bool:
    expected = receipt.get("dual_hash")
    if not expected:
        return False
    body = {k: v for k, v in receipt.items() if k != "dual_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    actual_sha = hashlib.sha256(canonical).hexdigest()
    actual_b3 = blake3.blake3(canonical).hexdigest()
    return expected.get("sha256") == actual_sha and expected.get("blake3") == actual_b3
```

Both hashes must match. A single match is a verification failure. The MCP server's `verify_chain` tool runs this check across a contiguous range of receipts and emits an `anomaly` receipt on the first failure, then halts per CLAUDEME StopRule.

## Limitations field, required entries

Every receipt must include at least these five lines in `limitations`:

1. Heuristic proxy labeling, no ground truth
2. Classifier circularity, divergence is both feature and label component
3. Arizona-only geographic scope
4. Mixed pre-COVID and post-COVID temporal scope
5. Account-level signals excluded per professor guidance

Additional limitations may be appended for specific businesses if the evidence warrants. The MCP `query_receipts` tool can filter on limitation strings.

## Why this schema, in one paragraph

The receipt is the deliverable, not the dashboard. The dashboard is a viewer over the receipts. If the dashboard burns down tomorrow, the receipts still prove what was decided. SHA-256 anchors the receipt to legacy verification tools, BLAKE3 anchors it to the modern Merkle stack used elsewhere in the Inquiro RNA pattern, and storing both means a future verifier can pick either chain. The limitations field is required because graduate-level honesty about model boundaries is what separates a verified prototype from a vendor demo.
