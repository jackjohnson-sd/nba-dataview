#!/bin/bash
# Rebuild pages into the outputs tree:
#   outputs/<season>/html/nba_season.html
#   outputs/<season>/<tri>/html/team_<tri>.html
# Usage: [SEASON=2024-25] ./scripts/rebuild.sh [all | season | TRI ...]
cd "$(dirname "$0")/.." || exit 1
MPLBACKEND=Agg SEASON="${SEASON:-2025-26}" .venv/bin/python - "$@" <<'PY'
import os
import sys
from pathlib import Path
from nba_pbp.team2 import plot_team2_html, _TEAM_BRAND_COLORS
from nba_pbp.nba_season import plot_nba_season_2d_html

SEASON = os.environ["SEASON"]
root = Path("outputs") / SEASON
args = [a.lower() for a in sys.argv[1:]] or ["okc"]
# TEAM pages FIRST. The season page links a tricode only if that team's
# page already exists on disk (nba_season._team_href tests for the file),
# so building the season page first leaves a brand-new season linking only
# whatever teams happened to be there — which is exactly how 2023-24 first
# shipped with 1 of 30 tricodes clickable.
tris = (sorted(_TEAM_BRAND_COLORS)
        if "all" in args else
        [a.upper() for a in args if a not in ("all", "season")])
for t in tris:
    plot_team2_html(SEASON, t,
                    root / t.lower() / "html" / f"team_{t.lower()}.html")
if tris:
    print("teams rebuilt:", len(tris))
if "all" in args or "season" in args:
    plot_nba_season_2d_html(SEASON, root / "html" / "nba_season.html")
    print("season ok")
PY
