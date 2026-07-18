#!/usr/bin/env bash
# Fetch play-by-play for a game and render its shot chart in one step.
# Usage: scripts/shot_chart.sh <game_id> [output_dir]
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -lt 1 ]; then
  echo "Usage: $0 <game_id> [output_dir]" >&2
  exit 1
fi

GAME_ID="$1"
OUT_DIR="${2:-outputs}"

source .venv/bin/activate
nba-pbp fetch --game-id "$GAME_ID" --output "$OUT_DIR/pbp_${GAME_ID}.csv"
nba-pbp plot --input "$OUT_DIR/pbp_${GAME_ID}.csv" --output "$OUT_DIR/shot_chart_${GAME_ID}.html"
