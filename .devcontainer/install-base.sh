#!/usr/bin/env bash
# Lean install for the Codespaces bootstrap.
#
# Runs in onCreateCommand so prebuilds (when enabled in repo settings) bake
# the result into the image and new Codespaces start in ~30s instead of ~10min.
#
# What this installs:
#   - requirements-base.txt: pandas/numpy/sklearn/xgboost/vader/notebook/mcp/pytest
#   - NOT installed by default: bertopic / sentence-transformers / umap / hdbscan
#     and their PyTorch dependency. Run .devcontainer/install-ml.sh on demand
#     if you need topic modeling.
set -euo pipefail

LOG=/tmp/tabhs-install.log
echo "[tabhs] installing lean base, log: $LOG"
{
  python -m pip install --upgrade pip wheel
  pip install -r requirements-base.txt
  echo "[tabhs] base install done"
} 2>&1 | tee -a "$LOG"
