#!/usr/bin/env python
"""TABHS pipeline CLI, single command for the professor.

Usage:
    python run_pipeline.py --sample 100 --skip-llm
    python run_pipeline.py                    # full corpus, all steps
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.tabhs_pipeline import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
