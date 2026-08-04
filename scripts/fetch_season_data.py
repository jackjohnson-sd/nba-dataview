#!/usr/bin/env python3
"""Fetch every per-game endpoint a season's pages need, one game per tick.

Order of value, and why one pass covers it:

  * TEAM pages need only play-by-play, which is already cached for
    2023-24 — they build offline today, nothing to fetch.
  * The SEASON page needs the traditional box score for EVERY game, so
    it cannot render until the last one lands.
  * GAME pages need that box score too, plus game info, the rotation,
    live actions and the ESPN recap — and the play-by-play written out
    as CSV where the page builders look for it.

So a single pass that completes one game at a time reaches the season
page at the same moment a box-scores-only pass would, and finishes every
game page in the same run instead of a second one.

    .venv/bin/python scripts/fetch_season_data.py 2023-24 [--every 15]

Each game prints one line; every --report seconds a PROGRESS line lands
(that is what the monitor watches). Already-cached calls are free, so
re-running resumes rather than refetching.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from nba_pbp import client, storage
from nba_pbp.edge import league_history


def game_dirs(root: Path, g) -> tuple[Path, str]:
    """(csv_dir, season) for a game — root/<season>/<home>/csv, the home
    tricode from the MATCHUP text (same convention as the CLI)."""
    m = str(g["MATCHUP"])
    home = (m.split(" vs. ")[0] if " vs. " in m
            else m.split(" @ ")[-1]).strip().lower()
    y = int(str(g["SEASON_ID"])[-4:])
    season = f"{y}-{str(y + 1)[-2:]}"
    return root / season / home / "csv", season


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("season", help="e.g. 2023-24")
    ap.add_argument("--every", type=float, default=15.0,
                    help="seconds per game (default 15)")
    ap.add_argument("--gap", type=float, default=1.2,
                    help="seconds between calls within a game (default 1.2)")
    ap.add_argument("--report", type=float, default=300.0,
                    help="seconds between PROGRESS lines (default 300)")
    ap.add_argument("--out", default="outputs", type=Path)
    args = ap.parse_args()

    hist = league_history(args.season).copy()
    hist["GID"] = hist["GAME_ID"].astype(str).str.zfill(10)
    # one row per game (league history has a row per team per game)
    games = (hist.sort_values("GAME_DATE")
                 .drop_duplicates("GID", keep="first"))
    rows = list(games.itertuples())
    total = len(rows)
    started = time.time()
    last_report = started
    done = failed = 0
    fail_kinds: dict[str, int] = {}

    print(f"season {args.season}: {total} games, one per {args.every:g}s "
          f"(~{total * args.every / 3600:.1f}h)", flush=True)

    for i, g in enumerate(rows, 1):
        tick = time.time()
        gid = g.GID
        csv_dir, _season = game_dirs(args.out, {"MATCHUP": g.MATCHUP,
                                                "SEASON_ID": g.SEASON_ID})
        errs = []

        # play-by-play first: cached already, but this is what writes the
        # CSV the page builders read
        try:
            df = client.get_play_by_play_cached(gid)
            csv_dir.mkdir(parents=True, exist_ok=True)
            storage.save_dataframe(df, csv_dir / f"pbp_{gid}.csv", "csv")
        except Exception as e:
            errs.append(f"pbp:{type(e).__name__}")

        for name, fn in (("box", client.get_box_score_traditional),
                         ("info", client.get_game_info),
                         ("rotation", client.get_game_rotation),
                         ("live", client.get_period_boundary_times),
                         ("recap", client.get_game_recap)):
            try:
                fn(gid)
            except Exception as e:
                errs.append(f"{name}:{type(e).__name__}")
                fail_kinds[name] = fail_kinds.get(name, 0) + 1
            time.sleep(args.gap)

        if errs:
            failed += 1
            print(f"  {i}/{total} {gid} {str(g.GAME_DATE)[:10]} "
                  f"PARTIAL {','.join(errs)}", flush=True)
        else:
            done += 1

        now = time.time()
        if now - last_report >= args.report or i == total:
            rate = i / (now - started)
            left = (total - i) / rate if rate else 0
            print(f"PROGRESS {i}/{total} games "
                  f"({100 * i / total:.1f}%) — {done} complete, "
                  f"{failed} partial, ~{left / 3600:.1f}h left"
                  + (f" — misses: {fail_kinds}" if fail_kinds else ""),
                  flush=True)
            last_report = now

        # hold the per-game cadence (calls above already consumed some)
        rest = args.every - (time.time() - tick)
        if rest > 0 and i < total:
            time.sleep(rest)

    mins = (time.time() - started) / 60
    print(f"done: {total} games in {mins:.0f} min — "
          f"{done} complete, {failed} partial"
          + (f", misses: {fail_kinds}" if fail_kinds else ""), flush=True)


if __name__ == "__main__":
    main()
