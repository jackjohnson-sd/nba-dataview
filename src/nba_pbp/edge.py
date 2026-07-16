"""Stage 1 of the win-probability project: the matchup edge report.

Three pieces, each usable on its own and all reusable later as model
features:

- `league_history(season)` — every team-game box score row of a season
  (regular season + playoffs), each joined with its opponent's numbers.
- `team_form(...)` — one team's recency-weighted ratings from its last N
  games before a date: net/off/def rating, pace, and the four factors on
  both ends. Weights decay exponentially by games back (half-life in
  games), and every ratio is computed from weighted counting-stat sums,
  not by averaging per-game ratios.
- `live_reading(...)` — the same four factors and pace read from a
  game's play-by-play through some completion fraction (e.g. 0.2 = the
  first 9.6 minutes).

`edge_report(...)` renders all of it as text: season form side by side,
the live reading, the last head-to-head meetings, and where the live
game diverges from what the two teams' season numbers predict.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from nba_pbp import client
from nba_pbp.plusminus import _load_full_pbp

_OPP_COLS = ["PTS", "FGM", "FGA", "FG3M", "FTM", "FTA", "OREB", "DREB", "TOV"]


def _season_for_game_id(game_id: str) -> str:
    """NBA game ids encode the season's start year in characters 3:5
    (e.g. 0042500311 -> 25 -> 2025-26)."""
    start = 2000 + int(str(game_id)[3:5])
    return f"{start}-{str(start + 1)[-2:]}"


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


def _poss(fga, fta, tov, oreb):
    """Standard possession estimate from counting stats."""
    return fga + 0.44 * fta + tov - oreb


def _factors(fgm, fga, fg3m, ftm, fta, tov, oreb, opp_dreb):
    """The four factors from (weighted) counting sums."""
    return {
        "efg": (fgm + 0.5 * fg3m) / fga if fga else float("nan"),
        "tov_pct": 100 * tov / (fga + 0.44 * fta + tov) if fga else float("nan"),
        "oreb_pct": 100 * oreb / (oreb + opp_dreb) if (oreb + opp_dreb) else float("nan"),
        "ftr": ftm / fga if fga else float("nan"),
    }


def team_form(history: pd.DataFrame, team: str, before: pd.Timestamp,
              n_games: int = 40, half_life: float = 15.0) -> dict:
    """One team's recency-weighted form from its last `n_games` before
    `before`: net/off/def rating, pace, four factors on offense, and the
    defensive counterparts (what opponents managed against them)."""
    rows = history[
        (history["TEAM_ABBREVIATION"] == team) & (history["GAME_DATE"] < before)
    ].sort_values("GAME_DATE").tail(n_games)
    if rows.empty:
        raise ValueError(f"no games for {team} before {before.date()}")
    # most recent game gets weight 1, halving every `half_life` games back
    age = np.arange(len(rows))[::-1]
    w = 0.5 ** (age / half_life)

    def ws(col):
        return float((rows[col].to_numpy(dtype=float) * w).sum())

    poss = _poss(ws("FGA"), ws("FTA"), ws("TOV"), ws("OREB"))
    opp_poss = _poss(ws("OPP_FGA"), ws("OPP_FTA"), ws("OPP_TOV"), ws("OPP_OREB"))
    off_rtg = 100 * ws("PTS") / poss
    def_rtg = 100 * ws("OPP_PTS") / opp_poss
    # LeagueGameFinder MIN is summed player-minutes (~240 per regulation
    # game), so /5 recovers game minutes for the per-48 pace
    game_min = ws("MIN") / 5
    pace = (poss + opp_poss) / 2 / game_min * 48

    off = _factors(ws("FGM"), ws("FGA"), ws("FG3M"), ws("FTM"), ws("FTA"),
                   ws("TOV"), ws("OREB"), ws("OPP_DREB"))
    dfn = _factors(ws("OPP_FGM"), ws("OPP_FGA"), ws("OPP_FG3M"), ws("OPP_FTM"),
                   ws("OPP_FTA"), ws("OPP_TOV"), ws("OPP_OREB"), ws("DREB"))
    return {
        "team": team,
        "games": len(rows),
        "span": (rows["GAME_DATE"].iloc[0].date(), rows["GAME_DATE"].iloc[-1].date()),
        "net_rtg": off_rtg - def_rtg,
        "off_rtg": off_rtg,
        "def_rtg": def_rtg,
        "pace": pace,
        "off": off,
        "def": dfn,
    }


def league_net_ratings(history: pd.DataFrame, before: pd.Timestamp,
                       n_games: int = 40, half_life: float = 15.0) -> pd.Series:
    """Every team's weighted net rating (for ranking context), sorted
    best-first."""
    out = {}
    for team in sorted(history["TEAM_ABBREVIATION"].unique()):
        try:
            out[team] = team_form(history, team, before, n_games, half_life)["net_rtg"]
        except ValueError:
            continue
    return pd.Series(out).sort_values(ascending=False)


def live_reading(csv_path: Path, fraction: float = 0.2) -> dict:
    """Both teams' four factors, possessions, and the score, read from a
    game's play-by-play CSV through `fraction` of regulation time."""
    return live_reading_from_df(_load_full_pbp(csv_path), fraction)


def prepare_pbp(df: pd.DataFrame) -> pd.DataFrame:
    """Add game_seconds to a raw PlayByPlayV3 frame (the same transform
    _load_full_pbp applies to a CSV) so live_reading_from_df can use it."""
    from nba_pbp.plusminus import _game_seconds
    df = df.copy()
    df["game_seconds"] = [_game_seconds(p, c) for p, c in zip(df["period"], df["clock"])]
    return df.sort_values(["game_seconds", "actionNumber"]).reset_index(drop=True)


def live_reading_from_df(df: pd.DataFrame, fraction: float = 0.2) -> dict:
    """Both teams' four factors, possessions, and the score, read from a
    prepared play-by-play frame through `fraction` of regulation time.
    Rebound off/def is inferred as everywhere else in this project: a
    rebound by the team that just missed is offensive."""
    cutoff = fraction * 48 * 60
    sub = df[df["game_seconds"] <= cutoff]

    home_rows = df[(df["location"] == "h") & df["teamTricode"].notna()]
    home_team = home_rows["teamTricode"].iloc[0]
    teams = [t for t in df["teamTricode"].dropna().unique() if t]
    away_team = next(t for t in teams if t != home_team)

    scored = sub[sub["scoreHome"].notna() & (sub["scoreHome"].astype(str) != "")]
    if scored.empty:
        score = {home_team: 0, away_team: 0}
    else:
        last = scored.iloc[-1]
        score = {home_team: int(last["scoreHome"]), away_team: int(last["scoreAway"])}

    counts = {t: dict.fromkeys(
        ("FGM", "FGA", "FG3M", "FTM", "FTA", "TOV", "OREB", "DREB"), 0
    ) for t in (home_team, away_team)}
    last_miss_team = None
    for _, r in sub.sort_values("game_seconds").iterrows():
        team, action = r["teamTricode"], r["actionType"]
        if team not in counts:
            continue
        c = counts[team]
        desc = str(r["description"])
        if r.get("isFieldGoal") == 1:
            c["FGA"] += 1
            if r["shotResult"] == "Made":
                c["FGM"] += 1
                if r["shotValue"] == 3:
                    c["FG3M"] += 1
            else:
                last_miss_team = team
        elif action == "Free Throw":
            c["FTA"] += 1
            if desc.startswith("MISS"):
                last_miss_team = team
            else:
                c["FTM"] += 1
        elif action == "Turnover":
            c["TOV"] += 1
        elif action == "Rebound":
            if last_miss_team is not None and team == last_miss_team:
                c["OREB"] += 1
            else:
                c["DREB"] += 1

    minutes = min(cutoff, df["game_seconds"].max()) / 60
    reading = {"home": home_team, "away": away_team, "score": score,
               "minutes": minutes, "teams": {}}
    total_poss = 0.0
    for t in (home_team, away_team):
        c = counts[t]
        other = away_team if t == home_team else home_team
        poss = _poss(c["FGA"], c["FTA"], c["TOV"], c["OREB"])
        total_poss += poss
        reading["teams"][t] = {
            **_factors(c["FGM"], c["FGA"], c["FG3M"], c["FTM"], c["FTA"],
                       c["TOV"], c["OREB"], counts[other]["DREB"]),
            "poss": poss,
        }
    reading["pace"] = total_poss / 2 / minutes * 48 if minutes else float("nan")
    return reading


def head_to_head(history: pd.DataFrame, team_a: str, team_b: str,
                 before: pd.Timestamp, n: int = 2) -> pd.DataFrame:
    """The last `n` meetings between the two teams before `before`, one
    row per game from team_a's side."""
    rows = history[
        (history["TEAM_ABBREVIATION"] == team_a)
        & (history["MATCHUP"].str.contains(team_b))
        & (history["GAME_DATE"] < before)
    ].sort_values("GAME_DATE").tail(n)
    return rows


_FACTOR_LABELS = {
    "efg": ("eFG%", "{:.3f}"),
    "tov_pct": ("TOV%", "{:.1f}"),
    "oreb_pct": ("OREB%", "{:.1f}"),
    "ftr": ("FT/FGA", "{:.3f}"),
}


def _expected_factor(off_form: dict, def_form: dict, key: str) -> float:
    """Matchup expectation for one team's offensive factor: midpoint of
    what its offense produces and what the opponent's defense allows
    (def[...] is already opponents' production against that defense, so
    the midpoint form is uniform across all four factors)."""
    return (off_form["off"][key] + def_form["def"][key]) / 2


def edge_report(csv_path: Path, fraction: float = 0.2, n_games: int = 40,
                half_life: float = 15.0) -> str:
    """The Stage-1 report: season form, live reading at the cutoff, last
    head-to-heads, and live-vs-expected divergences."""
    raw = pd.read_csv(csv_path, usecols=["gameId"], dtype=str)
    game_id = raw.iloc[0, 0].zfill(10)
    season = _season_for_game_id(game_id)
    history = league_history(season)

    this_game = history[history["GAME_ID"] == game_id]
    if this_game.empty:
        raise ValueError(f"game {game_id} not found in {season} logs")
    game_date = this_game["GAME_DATE"].iloc[0]

    live = live_reading(csv_path, fraction)
    away, home = live["away"], live["home"]
    forms = {t: team_form(history, t, game_date, n_games, half_life)
             for t in (away, home)}
    ranks = league_net_ratings(history, game_date, n_games, half_life)
    rank_of = {t: int((ranks.index == t).argmax()) + 1 for t in (away, home)}

    a, h = forms[away], forms[home]
    lines = []
    lines.append(
        f"Edge report — {away} @ {home} ({game_id}), through "
        f"{live['minutes']:.1f} of 48 min ({fraction:.0%}) — "
        f"score {away} {live['score'][away]}, {home} {live['score'][home]}"
    )
    lines.append("")
    lines.append(
        f"Season form (last {n_games} games before {game_date.date()}, "
        f"half-life {half_life:g} games)"
    )
    lines.append(f"{'':14}{away:>12}{home:>12}")
    lines.append(f"{'net rating':14}{a['net_rtg']:>+9.1f} ({rank_of[away]}){h['net_rtg']:>+9.1f} ({rank_of[home]})")
    lines.append(f"{'off rating':14}{a['off_rtg']:>12.1f}{h['off_rtg']:>12.1f}")
    lines.append(f"{'def rating':14}{a['def_rtg']:>12.1f}{h['def_rtg']:>12.1f}")
    lines.append(f"{'pace':14}{a['pace']:>12.1f}{h['pace']:>12.1f}")
    for key, (label, fmt) in _FACTOR_LABELS.items():
        row = f"{label + ' off/def':14}"
        for f in (a, h):
            row += f"{fmt.format(f['off'][key]) + '/' + fmt.format(f['def'][key]):>12}"
        lines.append(row)

    lines.append("")
    lines.append(f"Live reading (first {live['minutes']:.1f} min, pace {live['pace']:.1f})")
    lines.append(f"{'':14}{away:>12}{home:>12}")
    for key, (label, fmt) in _FACTOR_LABELS.items():
        row = f"{label:14}"
        for t in (away, home):
            row += f"{fmt.format(live['teams'][t][key]):>12}"
        lines.append(row)

    h2h = head_to_head(history, away, home, game_date)
    if not h2h.empty:
        lines.append("")
        lines.append("Last head-to-head meetings")
        for _, r in h2h.iterrows():
            lines.append(
                f"  {r['GAME_DATE'].date()}  {r['MATCHUP']:<12} "
                f"{r['WL']}  {int(r['PTS'])}-{int(r['OPP_PTS'])}"
            )

    # divergences: each team's live factor vs the matchup expectation
    divs = []
    for t, other in ((away, home), (home, away)):
        for key, (label, fmt) in _FACTOR_LABELS.items():
            expected = _expected_factor(forms[t], forms[other], key)
            actual = live["teams"][t][key]
            scale = 100 if key in ("efg", "ftr") else 1  # report all in points
            divs.append((abs(actual - expected) * scale, t, label,
                         fmt.format(expected), fmt.format(actual),
                         (actual - expected) * scale))
    divs.sort(reverse=True)
    lines.append("")
    lines.append("Divergences (live vs matchup expectation, biggest first)")
    for _, t, label, exp_s, act_s, delta in divs:
        lines.append(f"  {t}  {label:<7} expected {exp_s:>6}  live {act_s:>6}  ({delta:+.1f})")
    return "\n".join(lines)
