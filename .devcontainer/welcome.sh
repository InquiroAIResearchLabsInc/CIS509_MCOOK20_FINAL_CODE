#!/usr/bin/env bash
# Friendly first-attach message. Tells the professor exactly what to click.
set -euo pipefail

GOLD='\033[1;33m'
MAROON='\033[0;35m'
DIM='\033[2m'
RESET='\033[0m'

cat <<EOF

${GOLD}TABHS, CIS 509 final project, ASU W. P. Carey${RESET}
${MAROON}Trust-Adjusted Business Health Score for Arizona restaurants${RESET}

${DIM}You don't have to install or run anything to grade this project.${RESET}

  1) Live dashboard (mobile + desktop, no setup):
     https://inquiroairesearchlabsinc.github.io/cis509_mcook20_final_code/

  2) Open the local copy in this Codespace:
     code outputs/dashboard.html
     Then right-click → "Open with Live Preview" or use VS Code's preview.

  3) Re-run the fast pipeline (lean deps only, ~30s):
     python run_pipeline.py --sample 100 --skip-llm --skip-topics

  4) Heavy ML stack (BERTopic, sentence-transformers, ~3min on first install):
     bash .devcontainer/install-ml.sh

EOF
