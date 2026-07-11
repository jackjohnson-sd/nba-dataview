#!/usr/bin/env bash
# Create a virtualenv and install nba-pbp into it.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

echo "Done. Activate the venv with: source .venv/bin/activate"
