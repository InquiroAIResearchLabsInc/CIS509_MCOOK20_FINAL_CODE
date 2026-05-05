#!/usr/bin/env bash
# Optional heavy ML stack: PyTorch (CPU-only) + BERTopic + sentence-transformers
# + umap + hdbscan. Run this only if you need to re-run the topic-modeling
# notebook (03_bertopic.ipynb) or the full pipeline without --skip-topics.
#
# Why CPU-only torch: Codespaces has no GPU, and CUDA wheels are ~1.5 GB of
# pure waste. The CPU index gives a ~150 MB wheel and installs in seconds.
set -euo pipefail

LOG=/tmp/tabhs-install-ml.log
echo "[tabhs] installing ML stack (CPU-only torch), log: $LOG"
{
  pip install --extra-index-url https://download.pytorch.org/whl/cpu \
    "torch==2.4.1" "torchvision==0.19.1"
  pip install \
    bertopic==0.16.4 \
    umap-learn==0.5.6 \
    hdbscan==0.8.40 \
    sentence-transformers==3.2.1
  echo "[tabhs] ML stack install done"
} 2>&1 | tee -a "$LOG"
