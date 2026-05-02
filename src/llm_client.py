"""Groq-backed LLM client with cache fallback.

Three protocols, mirroring LA6:
  - zero_shot(text)                        -> {"label": int, "raw": str}
  - few_shot(text, examples=...)           -> {"label": int, "raw": str}
  - multi_model_agreement(text)            -> {"primary": int, "comparator": int, "agreement": bool}

Cache fallback path:
  - If GROQ_API_KEY is unset and outputs/llm_agreement.csv exists, load
    cached predictions keyed on review_id and serve from there.
  - If neither key nor cache, raise RuntimeError. Pipeline can run with
    --skip-llm to bypass entirely.

Receipts:
  - Every live LLM call emits a `llm_call` envelope receipt
  - Cache hits emit a `llm_cache_hit` envelope receipt
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.config import (
    LLM_CACHE_PATH,
    LLM_MODEL_COMPARATOR,
    LLM_MODEL_PRIMARY,
    LLM_RATE_LIMIT_SLEEP_SEC,
    TENANT_ID,
)
from src.receipts import emit_receipt


# --------------------------------------------------------------------------- #
# Prompts, lifted from LA6
# --------------------------------------------------------------------------- #

ZERO_SHOT_SYSTEM = (
    "You are a sentiment analysis classifier. Respond with exactly one word, "
    "either 'positive' or 'negative'. No other text."
)

FEW_SHOT_SYSTEM = (
    "You are a sentiment analysis classifier. Respond with exactly one word, "
    "either 'positive' or 'negative'. Examples follow.\n\n"
    "Review: 'Worst experience of my life. Cold food, rude staff.'\n"
    "Sentiment: negative\n\n"
    "Review: 'Absolutely loved it. Best meal in years.'\n"
    "Sentiment: positive\n\n"
    "Review: 'Service was slow and the food was bland.'\n"
    "Sentiment: negative\n\n"
    "Review: 'Quaint little spot, fantastic dishes and friendly servers.'\n"
    "Sentiment: positive\n\n"
    "Now classify the next review. Respond with one word only."
)


def _parse_label(raw: str) -> int | None:
    """Map free-text response to {0, 1}. Returns None for unparseable output."""
    s = raw.strip().lower()
    s = re.sub(r"[^a-z]", "", s.split("\n")[0])
    if "positive" in s or s == "pos":
        return 1
    if "negative" in s or s == "neg":
        return 0
    return None


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #

@dataclass
class LLMConfig:
    """Runtime config for a single client instance."""
    use_cache: bool
    cache_df: pd.DataFrame | None
    primary_model: str = LLM_MODEL_PRIMARY
    comparator_model: str = LLM_MODEL_COMPARATOR
    rate_limit_sleep: float = LLM_RATE_LIMIT_SLEEP_SEC


class LLMClient:
    """Groq client wrapper. Supports live calls or cache replay."""

    def __init__(self, *, allow_cache_only: bool = True) -> None:
        self.api_key: str | None = os.environ.get("GROQ_API_KEY")
        self._groq = None
        self.config = LLMConfig(use_cache=False, cache_df=None)

        if self.api_key:
            try:
                from groq import Groq
                self._groq = Groq(api_key=self.api_key)
            except Exception as e:
                if not allow_cache_only:
                    raise
                emit_receipt("anomaly", {
                    "metric": "llm_client_init",
                    "delta": -1,
                    "classification": "degradation",
                    "action": "alert",
                    "error": str(e),
                    "tenant_id": TENANT_ID,
                })
                self._groq = None

        if self._groq is None:
            if LLM_CACHE_PATH.exists():
                self.config.use_cache = True
                self.config.cache_df = pd.read_csv(LLM_CACHE_PATH)
            elif not allow_cache_only:
                raise RuntimeError(
                    f"GROQ_API_KEY unset and no cache at {LLM_CACHE_PATH}. "
                    "Set the API key or run with --skip-llm."
                )

    @property
    def is_live(self) -> bool:
        return self._groq is not None

    @property
    def is_cached(self) -> bool:
        return self.config.use_cache

    # ---- live call primitive ---------------------------------------------- #

    def _call(self, model: str, system: str, user: str) -> str:
        if not self._groq:
            raise RuntimeError("LLM client not initialized for live calls.")
        time.sleep(self.config.rate_limit_sleep)
        resp = self._groq.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Review: {user}\nSentiment:"},
            ],
            temperature=0.0,
            max_tokens=8,
        )
        out = resp.choices[0].message.content or ""
        emit_receipt("llm_call", {
            "tenant_id": TENANT_ID,
            "model": model,
            "input_chars": len(user),
            "output_chars": len(out),
        })
        return out

    # ---- protocol methods ------------------------------------------------- #

    def zero_shot(self, text: str, *, review_id: str | None = None) -> dict:
        if self.config.use_cache and review_id is not None:
            row = self._cache_lookup(review_id)
            if row is not None and "zero_shot_label" in row:
                emit_receipt("llm_cache_hit", {"tenant_id": TENANT_ID, "review_id": review_id, "protocol": "zero_shot"})
                return {"label": int(row["zero_shot_label"]), "raw": "cached"}
        raw = self._call(self.config.primary_model, ZERO_SHOT_SYSTEM, text)
        return {"label": _parse_label(raw), "raw": raw}

    def few_shot(self, text: str, *, review_id: str | None = None) -> dict:
        if self.config.use_cache and review_id is not None:
            row = self._cache_lookup(review_id)
            if row is not None and "few_shot_label" in row:
                emit_receipt("llm_cache_hit", {"tenant_id": TENANT_ID, "review_id": review_id, "protocol": "few_shot"})
                return {"label": int(row["few_shot_label"]), "raw": "cached"}
        raw = self._call(self.config.primary_model, FEW_SHOT_SYSTEM, text)
        return {"label": _parse_label(raw), "raw": raw}

    def multi_model_agreement(self, text: str, *, review_id: str | None = None) -> dict:
        """Run the same text through primary and comparator models, return agreement."""
        if self.config.use_cache and review_id is not None:
            row = self._cache_lookup(review_id)
            if row is not None and "multi_model_agreement" in row:
                emit_receipt("llm_cache_hit", {"tenant_id": TENANT_ID, "review_id": review_id, "protocol": "multi_model"})
                return {
                    "primary": int(row.get("primary_label", 0)),
                    "comparator": int(row.get("comparator_label", 0)),
                    "agreement": bool(row["multi_model_agreement"]),
                }
        # Reuse few-shot for the primary side, then call comparator
        primary_raw = self._call(self.config.primary_model, FEW_SHOT_SYSTEM, text)
        comparator_raw = self._call(self.config.comparator_model, FEW_SHOT_SYSTEM, text)
        primary_label = _parse_label(primary_raw)
        comparator_label = _parse_label(comparator_raw)
        return {
            "primary": primary_label,
            "comparator": comparator_label,
            "agreement": primary_label is not None and primary_label == comparator_label,
        }

    # ---- cache helpers ---------------------------------------------------- #

    def _cache_lookup(self, review_id: str) -> dict | None:
        if self.config.cache_df is None:
            return None
        df = self.config.cache_df
        if "review_id" not in df.columns:
            return None
        match = df[df["review_id"] == review_id]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    def write_cache(self, df: pd.DataFrame, *, path: Path | None = None) -> Path:
        """Persist a predictions dataframe so subsequent runs can use cache fallback.

        Expected columns: review_id, zero_shot_label, few_shot_label,
        primary_label, comparator_label, multi_model_agreement.
        """
        target = path or LLM_CACHE_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(target, index=False)
        emit_receipt("llm_cache_write", {
            "tenant_id": TENANT_ID,
            "rows": len(df),
            "path": str(target.relative_to(target.parent.parent.parent)),
        })
        return target


__all__ = ["LLMClient", "LLMConfig", "ZERO_SHOT_SYSTEM", "FEW_SHOT_SYSTEM"]
