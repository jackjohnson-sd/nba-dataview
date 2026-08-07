#!/usr/bin/env python3
"""The showcase: the pages rebuilt after every change, in one place.

While the game pages are being worked on, rebuilding all 3,936 of them per
edit is minutes of nothing. This is the small set that gets rebuilt
instead — enough coverage to catch a regression, small enough to run in
seconds:

  * three SEASONS, because the older two are built from the same code but
    older feeds, and have caught things 2025-26 did not (a game with no
    overtime, a team whose name breaks a column width)
  * both TEAM pages and GAME pages, because they share `plotting.py` but
    lay out nothing else the same way
  * games with and without overtime, and one double-OT

Every game here is also in the staged gh-pages subset (each team's first
five per season), so the same page can be checked live after a publish.
Picking one outside that set means it 404s on the site — which is how
2024-25 okc 0022400018 came out of this list.

    .venv/bin/python scripts/showcase.py            # everything below
    .venv/bin/python scripts/showcase.py games      # game pages only
    .venv/bin/python scripts/showcase.py teams      # team pages only

A full publish still rebuilds the whole fleet — see LOG.md. This is for
the edit loop, not for shipping.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

# (season, team directory the game is filed under, game id)
GAMES: list[tuple[str, str, str]] = [
    # 2025-26 — the working set: OKC's opening run, one double-OT
    ("2025-26", "okc", "0022500001"),   # HOU @ OKC, double OT
    ("2025-26", "ind", "0022500005"),   # OKC @ IND
    ("2025-26", "atl", "0022500101"),   # OKC @ ATL
    ("2025-26", "dal", "0022500119"),   # OKC @ DAL
    ("2025-26", "okc", "0022500126"),   # SAC @ OKC
    # 2024-25 — the champions, and a full house at the Garden
    ("2024-25", "okc", "0022400100"),   # ATL @ OKC
    ("2024-25", "bos", "0022400061"),   # NYK @ BOS
    # 2023-24 — the champions, and the season before them
    ("2023-24", "bos", "0022300080"),   # MIA @ BOS
    ("2023-24", "den", "0022300006"),   # DAL @ DEN
]

# (season, tricode) — each game above should have its home team here, so a
# change is seen on both the game and the page that links to it
TEAMS: list[tuple[str, str]] = [
    ("2025-26", "OKC"),
    ("2024-25", "OKC"),
    ("2024-25", "BOS"),
    ("2023-24", "BOS"),
    ("2023-24", "DEN"),
]


def csv_for(season: str, team: str, gid: str) -> Path:
    return ROOT / "outputs" / season / team / "csv" / f"pbp_{gid}.csv"


def build_games() -> int:
    from rebuild_game_pages import build_one
    n = 0
    for season, team, gid in GAMES:
        path = csv_for(season, team, gid)
        if not path.exists():
            print(f"  MISSING {season} {team} {gid}")
            continue
        _, status = build_one(str(path))
        print(f"  {season} {team}/{gid}: {status}")
        n += status == "ok"
    return n


def build_teams() -> int:
    import matplotlib
    matplotlib.use("Agg")
    from nba_pbp.team2 import plot_team2_html
    n = 0
    for season, tri in TEAMS:
        out = (ROOT / "outputs" / season / tri.lower() / "html"
               / f"team_{tri.lower()}.html")
        plot_team2_html(season, tri, out)
        print(f"  {season} team_{tri.lower()}: ok")
        n += 1
    return n


def main() -> None:
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("all", "games"):
        print(f"game pages ({len(GAMES)}):")
        build_games()
    if what in ("all", "teams"):
        print(f"team pages ({len(TEAMS)}):")
        build_teams()


if __name__ == "__main__":
    main()
