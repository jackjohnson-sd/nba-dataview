#!/bin/bash
# Rebuild pages into the outputs tree:
#   outputs/<season>/html/nba_season.html
#   outputs/<season>/<tri>/html/team_<tri>.html
# Usage: ./scripts/rebuild.sh [all | season | TRI ...]
cd "$(dirname "$0")/.." || exit 1
MPLBACKEND=Agg .venv/bin/python - "$@" <<'PY'
import sys
from pathlib import Path
from nba_pbp.team2 import plot_team2_html
from nba_pbp.nba_season import plot_nba_season_2d_html

SEASON = "2025-26"
root = Path("outputs") / SEASON
args = [a.lower() for a in sys.argv[1:]] or ["okc"]
if "all" in args or "season" in args:
    plot_nba_season_2d_html(SEASON, root / "html" / "nba_season.html")
    print("season ok")
tris = (sorted(p.parent.parent.name.upper()
               for p in root.glob("*/html/team_*.html"))
        if "all" in args else
        [a.upper() for a in args if a not in ("all", "season")])
for t in tris:
    plot_team2_html(SEASON, t,
                    root / t.lower() / "html" / f"team_{t.lower()}.html")
if tris:
    print("teams rebuilt:", len(tris))
PY
