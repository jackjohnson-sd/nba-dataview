"""Rebuild every game page (pm_players_{gid}.html) from its pbp CSV.

Parallel across processes (matplotlib Agg per worker). Game info comes
from the box-score cache via client.get_game_info. Roughly 5s a page
single-process; with the default 6 workers a full season is ~20 min.

    MPLBACKEND=Agg .venv/bin/python scripts/rebuild_game_pages.py [workers]
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "outputs"


def build_one(gid: str) -> tuple[str, str]:
    import matplotlib
    matplotlib.use("Agg")
    from nba_pbp import client
    from nba_pbp.plotting import plot_plus_minus_by_player_html
    try:
        try:
            info = client.get_game_info(gid)
        except Exception:
            info = None
        plot_plus_minus_by_player_html(
            OUT / f"pbp_{gid}.csv", OUT / f"pm_players_{gid}.html",
            game_info=info, tooltips=True)
        return gid, "ok"
    except Exception as err:
        return gid, f"FAIL {err}"


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    gids = sorted(p.stem.split("_")[-1] for p in OUT.glob("pbp_*.csv"))
    print(f"{len(gids)} games, {workers} workers", flush=True)
    done = fail = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(build_one, g): g for g in gids}
        for f in as_completed(futs):
            gid, status = f.result()
            done += 1
            if status != "ok":
                fail += 1
                print(f"  {gid}: {status}", flush=True)
            if done % 100 == 0:
                print(f"  {done}/{len(gids)} ({fail} failed)", flush=True)
    print(f"done: {done} pages, {fail} failed", flush=True)


if __name__ == "__main__":
    main()
