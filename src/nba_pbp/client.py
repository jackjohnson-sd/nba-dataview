"""Thin wrappers around nba_api stats endpoints."""
from __future__ import annotations

import pickle
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from nba_api.stats.endpoints import (
    boxscoresummaryv3,
    boxscoretraditionalv3,
    gamerotation,
    leaguegamefinder,
    playbyplayv3,
    scoreboardv2,
)
from nba_api.stats.static import teams as static_teams

REQUEST_TIMEOUT = 30
GAME_ROTATION_TIMEOUT = 60  # this endpoint is noticeably slower than the others
MAX_RETRIES = 3

# per-game supplementary data (box score, rotation, game info, live-feed
# timestamps) is finalized the moment a game ends and never changes, so it's
# cached indefinitely on disk — every chart re-render would otherwise re-hit
# the network for the same handful of endpoints
CACHE_DIR = Path.home() / ".cache" / "nba_pbp"


def _cached(key: str, fetch_fn):
    """Return the pickled result for `key` if present on disk, else call
    `fetch_fn()`, cache the result (if not None), and return it."""
    cache_path = CACHE_DIR / f"{key}.pkl"
    if cache_path.exists():
        try:
            with cache_path.open("rb") as f:
                return pickle.load(f)
        except Exception:
            pass  # corrupt/unreadable cache entry — refetch below

    result = fetch_fn()
    if result is not None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with cache_path.open("wb") as f:
            pickle.dump(result, f)
    return result

# cdn.nba.com (unlike stats.nba.com) 403s without a browser-like Referer/Origin
_LIVE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json",
}
RETRY_BACKOFF_SECONDS = 2


def _with_retries(fn):
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as err:  # nba_api raises plain requests/timeout errors
            last_err = err
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise last_err


def get_games_for_date(date_str: str) -> list[dict]:
    """Return games scheduled on date_str (YYYY-MM-DD), with game_id and matchup info."""

    def _fetch():
        return scoreboardv2.ScoreboardV2(game_date=date_str, timeout=REQUEST_TIMEOUT)

    sb = _with_retries(_fetch)
    header = sb.game_header.get_data_frame()
    line_score = sb.line_score.get_data_frame()

    abbrev_by_team_id = dict(zip(line_score["TEAM_ID"], line_score["TEAM_ABBREVIATION"]))

    games = []
    for _, row in header.iterrows():
        games.append(
            {
                "game_id": row["GAME_ID"],
                "date": date_str,
                "home_team": abbrev_by_team_id.get(row["HOME_TEAM_ID"], "?"),
                "away_team": abbrev_by_team_id.get(row["VISITOR_TEAM_ID"], "?"),
                "status": row["GAME_STATUS_TEXT"],
            }
        )
    return games


def resolve_team_id(team_query: str) -> int:
    """Resolve a team abbreviation, city, or nickname (case-insensitive) to a team_id."""
    query = team_query.strip().lower()
    for team in static_teams.get_teams():
        if query in (
            team["abbreviation"].lower(),
            team["nickname"].lower(),
            team["city"].lower(),
            team["full_name"].lower(),
        ):
            return team["id"]
    raise ValueError(f"Could not resolve team '{team_query}'")


def get_games_for_team_season(team_query: str, season: str) -> list[dict]:
    """Return all games for a team in a season, e.g. season='2023-24'."""
    team_id = resolve_team_id(team_query)

    def _fetch():
        return leaguegamefinder.LeagueGameFinder(
            team_id_nullable=team_id,
            season_nullable=season,
            timeout=REQUEST_TIMEOUT,
        )

    finder = _with_retries(_fetch)
    df = finder.get_data_frames()[0]

    games = []
    for _, row in df.iterrows():
        games.append(
            {
                "game_id": row["GAME_ID"],
                "date": row["GAME_DATE"],
                "team": row["TEAM_ABBREVIATION"],
                "matchup": row["MATCHUP"],
                "win_loss": row.get("WL"),
            }
        )
    return games


def get_game_info(game_id: str) -> dict:
    """Return date, tip-off time, matchup, and arena info for a single game_id."""

    def _fetch_all():
        def _fetch():
            return boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id, timeout=REQUEST_TIMEOUT)

        box = _with_retries(_fetch)
        summary = box.get_dict()["boxScoreSummary"]

        tipoff = datetime.fromisoformat(summary["gameEt"].replace("Z", ""))
        arena = summary["arena"]
        home = summary["homeTeam"]
        away = summary["awayTeam"]

        return {
            "date": tipoff.strftime("%A, %B %-d, %Y"),
            "time": tipoff.strftime("%-I:%M %p ET"),
            "duration": summary["duration"],
            "attendance": summary["attendance"],
            "home_team": f"{home['teamCity']} {home['teamName']}",
            "away_team": f"{away['teamCity']} {away['teamName']}",
            "location": f"{arena['arenaName']}, {arena['arenaCity']}, {arena['arenaState']}",
        }

    return _cached(f"game_info_{game_id}", _fetch_all)


def get_play_by_play(game_id: str) -> pd.DataFrame:
    """Fetch the full play-by-play log for a single game_id."""

    def _fetch():
        return playbyplayv3.PlayByPlayV3(game_id=game_id, timeout=REQUEST_TIMEOUT)

    pbp = _with_retries(_fetch)
    return pbp.get_data_frames()[0]


def _fetch_live_actions(game_id: str) -> list[dict] | None:
    """Fetch the raw action list from the NBA's live play-by-play feed —
    the only source with a real `timeActual` wall-clock timestamp per
    action (the stats.nba.com feed used everywhere else in this module has
    no such field). Returns None if the feed has no data for this game (it
    only retains a limited rolling window of recent games, not the full
    historical archive)."""

    def _fetch_all():
        url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json"

        def _fetch():
            response = requests.get(url, headers=_LIVE_HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()

        try:
            payload = _with_retries(_fetch)
            return payload["game"]["actions"] or None
        except Exception:
            return None

    return _cached(f"live_actions_{game_id}", _fetch_all)


def get_period_boundary_times(game_id: str) -> dict[str, datetime] | None:
    """Return the actual wall-clock time (US/Eastern) at the start of each
    period, plus the final buzzer. Keys are period numbers as strings
    ("1", "2", ...) and "end". None if the live feed has no data for this
    game."""
    actions = _fetch_live_actions(game_id)
    if actions is None:
        return None

    eastern = ZoneInfo("America/New_York")
    times: dict[str, datetime] = {}
    for action in actions:
        ts = action.get("timeActual")
        if not ts:
            continue
        when = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(eastern)
        if action.get("actionType") == "period" and action.get("subType") == "start":
            times.setdefault(str(action["period"]), when)
        elif action.get("actionType") == "game" and action.get("subType") == "end":
            times["end"] = when
    return times or None


def get_action_wall_times(game_id: str) -> pd.DataFrame | None:
    """Return one row per action with a real timestamp: period, clock
    (game-clock string, e.g. "PT11M58.00S"), and wall_time (US/Eastern
    datetime) — for mapping arbitrary points in game-clock time to actual
    wall-clock time (e.g. a stint's real elapsed duration, stoppages and
    all). None if the live feed has no data for this game."""
    actions = _fetch_live_actions(game_id)
    if actions is None:
        return None

    eastern = ZoneInfo("America/New_York")
    rows = []
    for action in actions:
        ts = action.get("timeActual")
        clock = action.get("clock")
        period = action.get("period")
        if not ts or not clock or period is None:
            continue
        when = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(eastern)
        rows.append({"period": period, "clock": clock, "wall_time": when})
    return pd.DataFrame(rows) if rows else None


def get_game_rotation(game_id: str) -> pd.DataFrame:
    """Fetch each player's on-court stints (IN_TIME_REAL/OUT_TIME_REAL, in
    tenths of a second of elapsed game time) straight from the NBA's own
    rotation tracking — the authoritative source for on-court intervals,
    unlike reconstructing them from substitution text in the play-by-play
    feed. Returns both teams concatenated into one frame."""

    def _fetch_all():
        def _fetch():
            return gamerotation.GameRotation(game_id=game_id, timeout=GAME_ROTATION_TIMEOUT)

        rotation = _with_retries(_fetch)
        away, home = rotation.get_data_frames()
        return pd.concat([away, home], ignore_index=True)

    return _cached(f"game_rotation_{game_id}", _fetch_all)


def get_game_recap(game_id: str) -> dict | None:
    """Fetch the AP game recap for a game via ESPN's public site API —
    stats.nba.com has no narrative text. The game is matched on ESPN's
    scoreboard for the game date by the two teams' full names ("Away Team
    at Home Team"). Returns {"headline": ..., "story": ...} where story is
    the recap's HTML, or None if the game or its recap can't be found."""

    def _fetch_all():
        try:
            info = get_game_info(game_id)
            date = datetime.strptime(info["date"], "%A, %B %d, %Y")
            matchup = f"{info['away_team']} at {info['home_team']}"

            def _fetch_scoreboard():
                response = requests.get(
                    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
                    params={"dates": date.strftime("%Y%m%d")},
                    headers=_LIVE_HEADERS, timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                return response.json()

            events = _with_retries(_fetch_scoreboard).get("events", [])
            event_id = next(ev["id"] for ev in events if ev.get("name") == matchup)

            def _fetch_summary():
                response = requests.get(
                    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary",
                    params={"event": event_id},
                    headers=_LIVE_HEADERS, timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                return response.json()

            article = _with_retries(_fetch_summary).get("article") or {}
            story = article.get("story")
            if not story:
                return None
            return {"headline": article.get("headline") or matchup, "story": story}
        except Exception:
            return None

    return _cached(f"game_recap_{game_id}", _fetch_all)


def get_box_score_traditional(game_id: str) -> pd.DataFrame:
    """Fetch the NBA's own official per-player traditional box score
    (minutes, shooting splits, rebounds, assists, steals, blocks, turnovers,
    fouls, points, plus/minus) — the authoritative stat line, unlike our own
    play-by-play-derived approximation."""

    def _fetch_all():
        def _fetch():
            return boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id, timeout=REQUEST_TIMEOUT)

        box = _with_retries(_fetch)
        return box.get_data_frames()[0]

    return _cached(f"box_score_traditional_{game_id}", _fetch_all)
