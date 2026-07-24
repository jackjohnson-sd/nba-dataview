#!/usr/bin/env python3
"""Stage a GitHub-Pages-sized subset of the built site.

The full outputs/ tree (~1.9 GB, 1,315 game pages) is too big for GitHub
Pages' ~1 GB soft cap. This gathers a curated subset into a staging
directory:

  * the season (league) page               nba_season.html
  * all 30 team pages                       season_events_2d_*.html
  * a few game pages per team               pm_players_*.html
      - the first 3 games
      - the last regular-season game
      - the first playoff game
    deduped across teams (~70 pages)

It also writes an index.html that redirects to the season page. Files are
COPIED from outputs/ (outputs/ is left intact). Total ~150 MB.

    .venv/bin/python scripts/stage_gh_pages.py [--out DIR] [--stage DIR]

To deploy, push the staged content to the gh-pages branch — see
scripts/publish_pages.sh for the parentless-commit approach (point it at
the staging dir instead of outputs/), or copy the staging dir onto that
branch and push.

Note: the team pages carry a "detail" link for EVERY game, but only the
games staged here resolve; links to the other games 404 by design.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from nba_pbp.edge import league_history

SEASON = "2025-26"


def curated_game_ids(out: Path) -> set[str]:
    """Per team: first 3 games, last regular-season game, first playoff
    game — as zero-padded GAME_IDs, deduped, restricted to games whose
    page actually exists in `out`."""
    hist = league_history(SEASON).copy()
    hist["GID"] = hist["GAME_ID"].astype(str).str.zfill(10)
    gids: set[str] = set()
    for _team, df in hist.groupby("TEAM_ABBREVIATION"):
        df = df.sort_values("GAME_DATE")
        reg = df[df["GID"].str.startswith("002")]   # regular season
        ply = df[df["GID"].str.startswith("004")]   # playoffs
        gids.update(df["GID"].head(3))
        if not reg.empty:
            gids.add(reg["GID"].iloc[-1])
        if not ply.empty:
            gids.add(ply["GID"].iloc[0])
    return {g for g in gids if (out / f"pm_players_{g}.html").exists()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs", type=Path,
                    help="built site directory (default: outputs)")
    ap.add_argument("--stage", default="gh_pages_dist", type=Path,
                    help="staging directory to (re)create (default: gh_pages_dist)")
    args = ap.parse_args()
    out, stage = args.out, args.stage

    season = out / "nba_season.html"
    team_pages = sorted(out.glob("season_events_2d_*.html"))
    game_pages = [out / f"pm_players_{g}.html"
                  for g in sorted(curated_game_ids(out))]
    files = [season, *team_pages, *game_pages]

    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    total, staged, missing = 0, 0, []
    for src in files:
        if not src.exists():
            missing.append(src.name)
            continue
        shutil.copy2(src, stage / src.name)
        total += src.stat().st_size
        staged += 1

    (stage / "index.html").write_text(
        '<!doctype html><meta charset="utf-8">'
        '<meta http-equiv="refresh" content="0; url=nba_season.html">'
        '<title>NBA 2025-26 Season</title>'
        '<a href="nba_season.html">NBA 2025-26 Season Averages</a>\n')

    for m in missing:
        print(f"  MISSING (skipped): {m}")
    print(f"staged {staged} files + index.html -> {stage}/")
    print(f"  season page: 1")
    print(f"  team pages:  {sum(1 for f in files if f.name.startswith('season_events'))}")
    print(f"  game pages:  {sum(1 for f in files if f.name.startswith('pm_players'))}"
          f"  (first 3 + last regular + first playoff per team, deduped)")
    print(f"  total size:  {total / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
