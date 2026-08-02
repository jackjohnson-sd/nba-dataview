#!/usr/bin/env python3
"""Stage a GitHub-Pages-sized subset of the built site.

The full outputs/ tree (~1.9 GB, 1,315 game pages) is too big for GitHub
Pages' ~1 GB soft cap. This gathers a curated subset into a staging
directory:

  * the season (league) page               nba_season.html
  * all 30 team (game-by-game) pages        team_*.html
  * a few game pages per team               pm_players_*.html
      - games 1:4 (the first four)
      - the last game
    deduped across teams

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

SEASONS = ["2024-25", "2025-26"]
SEASON = SEASONS[-1]        # the index page's landing season


def game_home_map(season: str) -> dict[str, str]:
    """GID -> lowercase home tricode (a game files under its home
    team in the outputs tree)."""
    hist = league_history(season).copy()
    hist["GID"] = hist["GAME_ID"].astype(str).str.zfill(10)
    home = hist[hist["MATCHUP"].str.contains(" vs. ", regex=False)]
    return {r.GID: r.TEAM_ABBREVIATION.lower()
            for r in home.itertuples()}


def game_page(out: Path, season: str, gid: str,
              home: dict[str, str]) -> Path:
    return (out / season / home.get(gid, "?")
            / "html" / f"pm_players_{gid}.html")


def curated_game_ids(out: Path, season: str,
                     home: dict[str, str]) -> set[str]:
    """Per team: games 1:4 (the first four) and the last game — as
    zero-padded GAME_IDs, deduped, restricted to games whose page
    actually exists in `out`."""
    hist = league_history(season).copy()
    hist["GID"] = hist["GAME_ID"].astype(str).str.zfill(10)
    gids: set[str] = set()
    for _team, df in hist.groupby("TEAM_ABBREVIATION"):
        df = df.sort_values("GAME_DATE")
        gids.update(df["GID"].head(4))
        gids.add(df["GID"].iloc[-1])
    return {g for g in gids if game_page(out, season, g, home).exists()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="outputs", type=Path,
                    help="built site directory (default: outputs)")
    ap.add_argument("--stage", default="gh_pages_dist", type=Path,
                    help="staging directory to (re)create (default: gh_pages_dist)")
    args = ap.parse_args()
    out, stage = args.out, args.stage

    files: list[Path] = []
    for sn in SEASONS:
        home = game_home_map(sn)
        files.append(out / sn / "html" / "nba_season.html")
        files.extend(sorted(out.glob(f"{sn}/*/html/team_*.html")))
        files.extend(game_page(out, sn, g, home)
                     for g in sorted(curated_game_ids(out, sn, home)))

    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    total, staged, missing = 0, 0, []
    for src in files:
        if not src.exists():
            missing.append(src.name)
            continue
        dst = stage / src.relative_to(out)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        total += src.stat().st_size
        staged += 1

    shutil.copy2(Path("help.html"), stage / "help.html")
    _sp = f"{SEASON}/html/nba_season.html"
    (stage / "index.html").write_text(
        '<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url={_sp}">'
        '<title>NBA 2025-26 Season</title>'
        f'<a href="{_sp}">NBA 2025-26 Season Averages</a>\n')

    for m in missing:
        print(f"  MISSING (skipped): {m}")
    print(f"staged {staged} files + index.html -> {stage}/")
    print(f"  season pages: {len(SEASONS)}")
    print(f"  team pages:  {sum(1 for f in files if f.name.startswith('team_'))}")
    print(f"  game pages:  {sum(1 for f in files if f.name.startswith('pm_players'))}"
          f"  (first 3 + last regular + first playoff per team, deduped)")
    print(f"  total size:  {total / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
