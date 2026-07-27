"""Point the game pages' corner team links at the team2 pages.

The game pages already carry corner navigation (each team's Prev/Next
game and a team-season link). The generator now emits team2_* as the
team link; this script retargets the ALREADY-BUILT pages in place so a
full multi-hour rebuild isn't needed:

  * href="season_events_2d_XXX.html"  ->  href="team_XXX.html"
  * href="team2_XXX.html"             ->  href="team_XXX.html"
  * strips any legacy <!--gpnav--> blocks from an earlier approach

Idempotent. Run after adding pages:

    MPLBACKEND=Agg .venv/bin/python scripts/link_game_pages.py
"""
from __future__ import annotations

import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "outputs"


def main() -> None:
    done = 0
    for path in sorted(OUT.glob("pm_players_*.html")):
        html = path.read_text()
        new = re.sub(r"<!--gpnav-->.*?<!--/gpnav-->", "", html, flags=re.S)
        new = new.replace('href="season_events_2d_', 'href="team_')
        new = new.replace('href="team2_', 'href="team_')
        if new != html:
            path.write_text(new)
            done += 1
    print(f"retargeted {done} game pages")


if __name__ == "__main__":
    main()
