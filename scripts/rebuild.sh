#!/bin/bash
# Rebuild pages. Usage: ./scripts/rebuild.sh [all | season | TRI ...]
#   all      -> season page + all 30 team pages
#   season   -> season page only
#   TRI ...  -> those team pages (e.g. okc tor)
cd "$(dirname "$0")/.." || exit 1
MPLBACKEND=Agg .venv/bin/python - "$@" <<'PY'
import sys
from pathlib import Path
from nba_pbp.team2 import plot_team2_html
from nba_pbp.nba_season import plot_nba_season_2d_html

out = Path("outputs")
args = [a.lower() for a in sys.argv[1:]] or ["okc"]
if "all" in args or "season" in args:
    plot_nba_season_2d_html("2025-26", out / "nba_season.html")
    print("season ok")
tris = (sorted({p.stem.split("_")[1].upper() for p in out.glob("team_*.html")})
        if "all" in args else
        [a.upper() for a in args if a not in ("all", "season")])
for t in tris:
    plot_team2_html("2025-26", t, out / f"team_{t.lower()}.html")
if tris:
    print("teams rebuilt:", len(tris))
PY
