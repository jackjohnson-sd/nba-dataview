"""Cutoff sweep for the win-probability model: rebuild the dataset at
several game-completion fractions (one pass per game — team form is
computed once, only the live reading varies) and train at each, to show
how the live margin's weight and the model's accuracy grow as the game
progresses. Requires every game's play-by-play to be in the disk cache
(run winprob-build for the seasons first); no network needed after that.

Usage: python scripts/cutoff_sweep.py
Writes outputs/winprob_sweep_{fraction}.csv and prints the comparison.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nba_pbp import client
from nba_pbp.edge import league_history, live_reading_from_df, prepare_pbp, team_form
from nba_pbp.winprob import FEATURE_SETS, train

FRACTIONS = [0.10, 0.20, 0.25, 0.50, 0.75]
SEASONS = ["2023-24", "2024-25", "2025-26"]
N_GAMES, HALF_LIFE, MIN_PRIOR = 40, 15.0, 10
OUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def build_all():
    rows = {f: [] for f in FRACTIONS}
    for season in SEASONS:
        history = league_history(season)
        home_games = history[history["MATCHUP"].str.contains(" vs. ")].sort_values("GAME_DATE")
        done = 0
        for _, g in home_games.iterrows():
            game_id, home = g["GAME_ID"], g["TEAM_ABBREVIATION"]
            away = g["MATCHUP"].split(" vs. ")[-1]
            if not client.has_cached_play_by_play(game_id):
                continue  # sweep is local-only by design
            try:
                pbp = prepare_pbp(client.get_play_by_play_cached(game_id))
                hf = team_form(history, home, g["GAME_DATE"], N_GAMES, HALF_LIFE)
                af = team_form(history, away, g["GAME_DATE"], N_GAMES, HALF_LIFE)
            except ValueError:
                continue
            if hf["games"] < MIN_PRIOR or af["games"] < MIN_PRIOR:
                continue
            for frac in FRACTIONS:
                live = live_reading_from_df(pbp, frac)
                t = live["teams"]
                if home not in t or away not in t:
                    continue
                rows[frac].append({
                    "game_id": game_id, "date": g["GAME_DATE"].date().isoformat(),
                    "home": home, "away": away,
                    "net_diff": hf["net_rtg"] - af["net_rtg"],
                    "live_margin": live["score"][home] - live["score"][away],
                    "efg_d": t[home]["efg"] - t[away]["efg"],
                    "tov_d": t[home]["tov_pct"] - t[away]["tov_pct"],
                    "oreb_d": t[home]["oreb_pct"] - t[away]["oreb_pct"],
                    "ftr_d": t[home]["ftr"] - t[away]["ftr"],
                    "final_margin": int(g["PTS"] - g["OPP_PTS"]),
                    "home_win": int(g["PTS"] > g["OPP_PTS"]),
                })
            done += 1
            if done % 250 == 0:
                print(f"{season}: {done} games", flush=True)
    return {f: pd.DataFrame(r) for f, r in rows.items()}


def main():
    datasets = build_all()
    print(f"\n{'cutoff':>7}{'games':>7}{'set':>16}{'log loss':>10}{'brier':>8}"
          f"{'acc':>7}{'RMSE':>7}{'margin beta':>13}")
    for frac, df in datasets.items():
        df.to_csv(OUT_DIR / f"winprob_sweep_{frac:.2f}.csv", index=False)
        result = train(df)
        for name in FEATURE_SETS:
            m = result["sets"][name]
            # standardized live-margin coefficient, where present
            beta = ""
            if "live_margin" in m["features"]:
                i = m["features"].index("live_margin")
                beta = f"{m['beta_win'][i + 1]:+.3f}"
            print(f"{frac:>7.0%}{len(df):>7}{name:>16}{m['log_loss']:>10.4f}"
                  f"{m['brier']:>8.4f}{m['accuracy']:>7.3f}"
                  f"{m['margin_rmse']:>7.2f}{beta:>13}", flush=True)


if __name__ == "__main__":
    main()
