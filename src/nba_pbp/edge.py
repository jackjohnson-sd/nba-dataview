"""Season game logs.

`league_history(season)` returns every team-game box score row of a
season (regular season + playoffs), each joined with its opponent's
counting stats as OPP_*. The season and team pages use it to enumerate a
team's schedule and compute season averages.
"""
from __future__ import annotations

import pandas as pd

from nba_pbp import client

_OPP_COLS = ["PTS", "FGM", "FGA", "FG3M", "FTM", "FTA", "OREB", "DREB", "TOV"]


def league_history(season: str) -> pd.DataFrame:
    """One row per team-game for the whole season (regular season +
    playoffs), with the opponent's counting stats joined on as OPP_*."""
    frames = []
    for season_type in ("Regular Season", "Playoffs"):
        df = client.get_league_team_games(season, season_type)
        if df is not None and not df.empty:
            frames.append(df)
    if not frames:
        raise ValueError(f"no league game logs for season {season}")
    df = pd.concat(frames, ignore_index=True)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    opp = df[["GAME_ID", "TEAM_ID"] + _OPP_COLS].rename(
        columns={c: f"OPP_{c}" for c in ["TEAM_ID"] + _OPP_COLS}
    )
    merged = df.merge(opp, on="GAME_ID")
    return merged[merged["TEAM_ID"] != merged["OPP_TEAM_ID"]].reset_index(drop=True)
