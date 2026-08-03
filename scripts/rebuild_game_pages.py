"""Rebuild every game page (pm_players_{gid}.html) from its pbp CSV.

Walks the season/team tree (outputs/<season>/<tri>/csv/pbp_*.csv) and
writes each page next door in ../html/. Parallel across processes
(matplotlib Agg per worker). Game info comes from the box-score cache
via client.get_game_info. The pages are pure HTML now (no SVG render),
so a page builds in ~1.7s; a full 1,400-game fleet at 8 workers is
roughly 5 minutes.

    MPLBACKEND=Agg .venv/bin/python scripts/rebuild_game_pages.py [workers]
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "outputs"


def build_one(csv_path_s: str) -> tuple[str, str]:
    import matplotlib
    matplotlib.use("Agg")
    from nba_pbp import client
    from nba_pbp.plotting import plot_plus_minus_by_player_html
    csv_path = Path(csv_path_s)
    gid = csv_path.stem.split("_")[-1]
    out_path = csv_path.parent.parent / "html" / f"pm_players_{gid}.html"
    try:
        try:
            info = client.get_game_info(gid)
        except Exception:
            info = None
        plot_plus_minus_by_player_html(
            csv_path, out_path, game_info=info, tooltips=True)
        return gid, "ok"
    except Exception as err:
        return gid, f"FAIL {err}"


def main() -> None:
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    csvs = sorted(str(p) for p in OUT.glob("*/*/csv/pbp_*.csv"))
    print(f"{len(csvs)} games, {workers} workers", flush=True)
    done = fail = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(build_one, c): c for c in csvs}
        for f in as_completed(futs):
            gid, status = f.result()
            done += 1
            if status != "ok":
                fail += 1
                print(f"  {gid}: {status}", flush=True)
            if done % 100 == 0:
                print(f"  {done}/{len(csvs)} ({fail} failed)", flush=True)
    print(f"done: {done} pages, {fail} failed", flush=True)


if __name__ == "__main__":
    main()
