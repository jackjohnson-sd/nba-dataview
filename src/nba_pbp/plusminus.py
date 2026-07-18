"""Reconstruct each player's on-court plus/minus over time from full play-by-play."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from nba_pbp.plotting import _game_seconds, _period_label, _period_length_seconds

_SUB_RE = re.compile(r"SUB: (?P<in_name>.+) FOR (?P<out_name>.+)")


def _period_of_seconds(game_seconds: float) -> int:
    """Which period (1=Q1 ... 5=OT1 ...) a given elapsed-game-seconds falls in."""
    period = 1
    remaining = max(game_seconds, 0)
    while remaining > _period_length_seconds(period):
        remaining -= _period_length_seconds(period)
        period += 1
    return period


def _period_end_seconds(period: int) -> float:
    """Cumulative elapsed seconds at the end of the given period."""
    return sum(_period_length_seconds(p) for p in range(1, period + 1))


def _load_full_pbp(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["game_seconds"] = [_game_seconds(p, c) for p, c in zip(df["period"], df["clock"])]
    return df.sort_values(["game_seconds", "actionNumber"]).reset_index(drop=True)


def _home_away_map(df: pd.DataFrame) -> dict[str, str]:
    loc = df.dropna(subset=["location", "teamTricode"])
    return loc.groupby("teamTricode")["location"].agg(lambda s: s.mode().iat[0]).to_dict()


def _resolve_player_ids(df: pd.DataFrame) -> dict[str, int]:
    """Map every substitution display-name (already disambiguated for same-team
    same-surname players, e.g. "Jal. Williams" vs "Jay. Williams") to a personId."""
    name_to_id: dict[str, int] = {}
    subs = df[df["actionType"] == "Substitution"]
    for _, row in subs.iterrows():
        match = _SUB_RE.match(str(row["description"]))
        if match and pd.notna(row["personId"]):
            name_to_id[match.group("out_name").strip()] = int(row["personId"])

    # players never subbed out: resolve by (team, last name) when unambiguous
    non_sub = df[df["actionType"] != "Substitution"].dropna(subset=["personId", "playerName", "teamTricode"])
    for (_, last_name), group in non_sub.groupby(["teamTricode", "playerName"]):
        ids = group["personId"].astype(int).unique()
        if len(ids) == 1 and last_name not in name_to_id:
            name_to_id[last_name] = int(ids[0])

    return name_to_id


def extract_substitutions(csv_path: Path) -> pd.DataFrame:
    """Return every SUB IN / SUB OUT event as its own row, in chronological
    order: game_minutes, period, clock, team, player_in, player_out, and the
    resolved personId of each (player_in_id may be None if that player's entry
    is a genuine gap in the NBA's play-by-play feed)."""
    df = _load_full_pbp(csv_path)
    name_to_id = _resolve_player_ids(df)
    subs = df[df["actionType"] == "Substitution"].copy()

    records = []
    for _, row in subs.iterrows():
        match = _SUB_RE.match(str(row["description"]))
        if not match:
            continue
        in_name = match.group("in_name").strip()
        out_name = match.group("out_name").strip()
        records.append(
            {
                "game_minutes": row["game_seconds"] / 60,
                "period": row["period"],
                "clock": row["clock"],
                "teamTricode": row["teamTricode"],
                "player_out": out_name,
                "player_out_id": int(row["personId"]) if pd.notna(row["personId"]) else None,
                "player_in": in_name,
                "player_in_id": name_to_id.get(in_name),
            }
        )
    return pd.DataFrame.from_records(records)


_STARTERS_PER_TEAM = 5


def _starting_lineups(df: pd.DataFrame, name_to_id: dict[str, int]) -> dict[str, set[int]]:
    """A player started on the court if their earliest appearance in the game
    (a live action, or the OUT side of a sub) comes before their earliest
    appearance as the IN side of a sub. This handles starters who get subbed
    out and later subbed back in (they still show up as an "IN" event
    eventually, just not as their *first* appearance).

    Occasionally a bench player's IN event is simply missing from the feed
    (a real gap in the NBA's play-by-play data), which would wrongly pass
    this test too. As a tiebreak, if more than 5 players per team pass, keep
    only the 5 with the earliest first appearance — genuine starters show up
    within the first couple minutes of the game; a data-gap bench player's
    first action typically comes much later.
    """
    subs = df[df["actionType"] == "Substitution"]
    earliest_in: dict[int, float] = {}
    earliest_other: dict[int, float] = {}

    for _, row in subs.iterrows():
        match = _SUB_RE.match(str(row["description"]))
        if not match:
            continue
        t = row["game_seconds"]
        if pd.notna(row["personId"]):
            out_id = int(row["personId"])
            earliest_other[out_id] = min(earliest_other.get(out_id, t), t)
        in_id = name_to_id.get(match.group("in_name").strip())
        if in_id is not None:
            earliest_in[in_id] = min(earliest_in.get(in_id, t), t)

    non_sub = df[df["actionType"] != "Substitution"].dropna(subset=["personId"])
    for pid, t in zip(non_sub["personId"].astype(int), non_sub["game_seconds"]):
        earliest_other[pid] = min(earliest_other.get(pid, t), t)

    starters: dict[str, set[int]] = {}
    for team in df["teamTricode"].dropna().unique():
        team_ids = set(df.loc[df["teamTricode"] == team, "personId"].dropna().astype(int).unique())
        candidates = [
            (earliest_other.get(pid, float("inf")), pid)
            for pid in team_ids
            if earliest_other.get(pid, float("inf")) <= earliest_in.get(pid, float("inf"))
        ]
        candidates.sort()
        starters[team] = {pid for _, pid in candidates[:_STARTERS_PER_TEAM]}
    return starters


def _fill_missing_entries(
    df: pd.DataFrame, name_to_id: dict[str, int], starters: dict[str, set[int]]
) -> pd.DataFrame:
    """The NBA's play-by-play feed occasionally has gaps in its substitution
    log: a player registers an action (a shot, rebound, foul, even a SUB OUT)
    while our tracked on-court set says they're on the bench, because their
    actual entry was never logged. Whenever that happens, synthesize an entry
    event for them right at (just before) the gap-revealing event itself —
    the tightest bound we have any evidence for, rather than assuming they
    were there since the start of the period. This walks the feed
    chronologically so it catches every such gap for a player, not just
    their first appearance."""
    id_to_display_name = {v: k for k, v in name_to_id.items()}
    pid_to_player_name = (
        df.dropna(subset=["personId", "playerName"]).drop_duplicates("personId").set_index("personId")["playerName"]
    ).to_dict()
    known_player_ids = set(name_to_id.values()) | set(pid_to_player_name.keys())
    game_id = df["gameId"].iloc[0] if "gameId" in df.columns else None

    on_court: dict[str, set[int]] = {team: set(ids) for team, ids in starters.items()}
    last_exit: dict[int, float] = {}  # pid -> game_seconds of their most recent real exit
    synthetic_rows = []

    for _, row in df.iterrows():
        team = row["teamTricode"]
        is_sub = row["actionType"] == "Substitution"
        in_id = None
        if is_sub:
            match = _SUB_RE.match(str(row["description"]))
            if not match:
                continue
            acting_pid = int(row["personId"]) if pd.notna(row["personId"]) else None
            in_id = name_to_id.get(match.group("in_name").strip())
        else:
            acting_pid = int(row["personId"]) if pd.notna(row["personId"]) else None

        if pd.notna(team) and acting_pid is not None and acting_pid in known_player_ids:
            court = on_court.setdefault(team, set())
            if acting_pid not in court:
                entry_period = int(row["period"])
                # nudge just past the exact boundary so format_game_clock reads
                # this as the start of entry_period, not the end of the prior one
                entry_time = sum(_period_length_seconds(p) for p in range(1, entry_period)) + 0.01
                # guard against colliding with (and being silently absorbed by)
                # this player's own still-open or just-closed prior real stint
                if acting_pid in last_exit and last_exit[acting_pid] >= entry_time:
                    entry_time = last_exit[acting_pid] + 0.01
                display_name = id_to_display_name.get(acting_pid, pid_to_player_name.get(acting_pid, str(acting_pid)))
                synthetic_rows.append(
                    {
                        "gameId": game_id,
                        "game_seconds": entry_time,
                        "actionNumber": -1,
                        "period": entry_period,
                        "teamTricode": team,
                        "personId": None,
                        "description": f"SUB: {display_name} FOR (gap)",
                        "actionType": "Substitution",
                    }
                )
                court.add(acting_pid)

        if is_sub:
            court = on_court.setdefault(team, set())
            if acting_pid is not None:
                court.discard(acting_pid)
                last_exit[acting_pid] = row["game_seconds"]
            if in_id is not None:
                court.add(in_id)

    if not synthetic_rows:
        return df

    combined = pd.concat([df, pd.DataFrame(synthetic_rows)], ignore_index=True, sort=False)
    return combined.sort_values(["game_seconds", "actionNumber"]).reset_index(drop=True)


def _prepare_simulation(csv_path: Path):
    """Shared setup for every on-court simulation in this module: load the
    full pbp, resolve player ids and starters, and patch in synthetic entries
    for any feed gaps."""
    df = _load_full_pbp(csv_path)
    home_away = _home_away_map(df)
    home_team = next(t for t, ha in home_away.items() if ha == "h")
    away_team = next(t for t, ha in home_away.items() if ha == "v")

    name_to_id = _resolve_player_ids(df)
    starters = _starting_lineups(df, name_to_id)
    df = _fill_missing_entries(df, name_to_id, starters)
    on_court = {team: set(ids) for team, ids in starters.items()}

    return df, home_team, away_team, name_to_id, on_court


_rotation_df_cache: dict[str, pd.DataFrame | None] = {}


def _game_id_from_df(df: pd.DataFrame) -> str | None:
    if "gameId" not in df.columns or df["gameId"].dropna().empty:
        return None
    return str(int(df["gameId"].dropna().iloc[0])).zfill(10)


def _fetch_game_rotation(game_id: str) -> pd.DataFrame | None:
    """Fetch (and cache) the raw GameRotation table for a game_id. Cached
    since a single CLI command typically triggers this indirectly several
    times (once per compute_* function) and the endpoint is slow."""
    if game_id in _rotation_df_cache:
        return _rotation_df_cache[game_id]
    try:
        from nba_pbp.client import get_game_rotation
        rotation = get_game_rotation(game_id)
    except Exception:
        rotation = None
    if rotation is not None and rotation.empty:
        rotation = None
    _rotation_df_cache[game_id] = rotation
    return rotation


def _intervals_from_game_rotation(df: pd.DataFrame) -> dict[int, list[tuple[float, float, str]]] | None:
    """Try to build on-court intervals from the NBA's own GameRotation
    endpoint — IN_TIME_REAL/OUT_TIME_REAL (tenths of a second of elapsed game
    time), straight from the NBA's tracking data. This is authoritative and
    sidesteps every failure mode of reconstructing stints from substitution
    text (missing entries, duplicate entries, silent periods, ...). Returns
    None if the endpoint is unavailable or unusable for this game, so callers
    can fall back to the play-by-play reconstruction."""
    game_id = _game_id_from_df(df)
    if game_id is None:
        return None
    rotation = _fetch_game_rotation(game_id)
    if rotation is None:
        return None

    team_id_to_tricode = (
        df.dropna(subset=["teamId", "teamTricode"]).drop_duplicates("teamId").set_index("teamId")["teamTricode"]
    ).to_dict()

    intervals: dict[int, list[tuple[float, float, str]]] = {}
    for _, row in rotation.iterrows():
        team = team_id_to_tricode.get(int(row["TEAM_ID"]))
        if team is None:
            continue
        entry_t = float(row["IN_TIME_REAL"]) / 10.0
        exit_t = float(row["OUT_TIME_REAL"]) / 10.0
        if exit_t <= entry_t:
            continue
        intervals.setdefault(int(row["PERSON_ID"]), []).append((entry_t, exit_t, team))
    return intervals or None


def _rotation_display_names(df: pd.DataFrame) -> dict[int, str]:
    """Last-name fallback for players who never appear by name anywhere in
    the play-by-play feed (no shots, rebounds, or substitutions logged for
    them at all) but do show up in GameRotation — otherwise they'd display
    as a bare personId."""
    game_id = _game_id_from_df(df)
    if game_id is None:
        return {}
    rotation = _fetch_game_rotation(game_id)
    if rotation is None:
        return {}
    names = {}
    for _, row in rotation.iterrows():
        last = str(row.get("PLAYER_LAST", "")).strip()
        if last:
            names[int(row["PERSON_ID"])] = last
    return names


def _merge_adjacent_intervals(
    intervals: dict[int, list[tuple[float, float, str]]]
) -> dict[int, list[tuple[float, float, str]]]:
    """Merge consecutive same-team intervals for a player where one stint's
    exit time is the other's entry time (e.g. a zero-gap split at a period
    boundary, or a substitution immediately reversed at the same timestamp)
    — those are one continuous stretch of playing time, not two stints."""
    merged: dict[int, list[tuple[float, float, str]]] = {}
    for pid, pid_intervals in intervals.items():
        ordered = sorted(pid_intervals, key=lambda iv: iv[0])
        result: list[tuple[float, float, str]] = []
        for entry_t, exit_t, team in ordered:
            if result and result[-1][2] == team and result[-1][1] == entry_t:
                prev_entry, _prev_exit, prev_team = result[-1]
                result[-1] = (prev_entry, exit_t, prev_team)
            else:
                result.append((entry_t, exit_t, team))
        merged[pid] = result
    return merged


def _rotation_is_complete(
    intervals: dict[int, list[tuple[float, float, str]]], df: pd.DataFrame
) -> bool:
    """Whether GameRotation data covers both teams well enough to trust.

    The endpoint occasionally returns a truncated response — a handful of
    players instead of both full rotations. Because it's preferred over the
    play-by-play reconstruction, trusting a partial response silently
    collapses every stint, lineup and plus/minus figure downstream (one
    observed game came back with 3 players, which left the lineup tables
    empty). A team cannot field fewer than five, so require at least a
    starting five per team before preferring it; otherwise fall back to
    reconstructing from the substitution log.
    """
    per_team: dict[str, set[int]] = {}
    for pid, ivals in intervals.items():
        for _entry, _exit, team in ivals:
            per_team.setdefault(team, set()).add(pid)
    teams = {t for t in df["teamTricode"].dropna().unique() if str(t).strip()}
    if not teams:
        return False
    return all(len(per_team.get(t, ())) >= _STARTERS_PER_TEAM for t in teams)


def _resolve_on_court_intervals(
    df: pd.DataFrame, name_to_id: dict[str, int], on_court: dict[str, set[int]]
) -> dict[int, list[tuple[float, float, str]]]:
    """The single source of truth for "when was each player actually on the
    court", shared by every plus/minus and stint computation in this module.
    Returns {personId: [(entry_seconds, exit_seconds, teamTricode), ...]}.

    Prefers the NBA's own GameRotation data when it's available (see
    `_intervals_from_game_rotation`) since it's authoritative. Only falls
    back to reconstructing intervals from substitution text in the
    play-by-play feed if that endpoint is unavailable.

    The fallback reconstruction handles missing-entry gaps (already patched
    into df by `_fill_missing_entries`), the regulation-end split, and the
    confirmed/unconfirmed duplicate-entry correction: a player still open at
    the end of any period is split there and reopened unconfirmed for the
    next one; if a later real entry contradicts that assumption (same period,
    no witnessed action yet) the start is moved to the real entry instead,
    and if it's contradicted in a later period entirely, the unconfirmed
    stretch is discarded rather than recorded.

    On top of that: if a player registers literally zero events of any kind
    (not just substitutions — shots, rebounds, fouls, everything) during a
    period they were speculatively auto-continued through, that speculation
    is discarded the moment that period ends, rather than waiting for some
    later duplicate entry to contradict it. This catches players who go
    quiet for a full period (or more) with no logged exit — the same failure
    mode as the regulation-end gap, just occurring at an ordinary quarter
    break instead. See compute_stints' history for why each rule exists."""
    rotation_intervals = _intervals_from_game_rotation(df)
    if rotation_intervals is not None and _rotation_is_complete(rotation_intervals, df):
        return _merge_adjacent_intervals(rotation_intervals)

    activity_periods: dict[int, set[int]] = {}
    for _, row in df.iterrows():
        period = int(row["period"])
        if row["actionType"] == "Substitution":
            match = _SUB_RE.match(str(row["description"]))
            if not match:
                continue
            if pd.notna(row["personId"]):
                activity_periods.setdefault(int(row["personId"]), set()).add(period)
            in_id = name_to_id.get(match.group("in_name").strip())
            if in_id is not None:
                activity_periods.setdefault(in_id, set()).add(period)
        elif pd.notna(row["personId"]):
            activity_periods.setdefault(int(row["personId"]), set()).add(period)

    open_stint: dict[int, tuple] = {}  # pid -> (team, entry_seconds, confirmed)
    for team, pids in on_court.items():
        for pid in pids:
            open_stint[pid] = (team, 0.0, True)

    intervals: dict[int, list[tuple[float, float, str]]] = {}

    def _record(pid: int, team: str, entry_t: float, exit_t: float) -> None:
        intervals.setdefault(pid, []).append((entry_t, exit_t, team))

    last_time = 0.0
    current_period = 1
    for _, row in df.iterrows():
        last_time = max(last_time, row["game_seconds"])

        row_period = int(row["period"])
        while row_period > current_period:
            period_end = _period_end_seconds(current_period)
            for pid, (team, entry_t, confirmed) in list(open_stint.items()):
                if not confirmed and current_period not in activity_periods.get(pid, set()):
                    # this player was silent the entire period we speculated
                    # they continued through — drop the speculation entirely
                    del open_stint[pid]
                    continue
                _record(pid, team, entry_t, period_end)
                open_stint[pid] = (team, period_end + 0.01, False)
            current_period += 1

        if row["actionType"] != "Substitution":
            pid = int(row["personId"]) if pd.notna(row["personId"]) else None
            if pid is not None and pid in open_stint:
                team, entry_t, confirmed = open_stint[pid]
                if not confirmed:
                    open_stint[pid] = (team, entry_t, True)
            continue

        match = _SUB_RE.match(str(row["description"]))
        if not match:
            continue
        t = row["game_seconds"]
        team = row["teamTricode"]
        out_id = int(row["personId"]) if pd.notna(row["personId"]) else None
        in_id = name_to_id.get(match.group("in_name").strip())

        if out_id is not None and out_id in open_stint:
            entry_team, entry_t, _confirmed = open_stint.pop(out_id)
            _record(out_id, entry_team, entry_t, t)
        if in_id is not None:
            if in_id not in open_stint:
                open_stint[in_id] = (team, t, True)
            else:
                entry_team, entry_t, confirmed = open_stint[in_id]
                dup_period = int(row["period"])
                if dup_period > _period_of_seconds(entry_t):
                    if confirmed:
                        _record(in_id, entry_team, entry_t, _period_end_seconds(dup_period - 1))
                    open_stint[in_id] = (team, t, True)
                elif not confirmed:
                    open_stint[in_id] = (team, t, True)

    for pid, (team, entry_t, confirmed) in open_stint.items():
        if not confirmed and current_period not in activity_periods.get(pid, set()):
            # silent for the entire final period they were speculatively
            # carried into — same discard rule as at a mid-game boundary
            continue
        _record(pid, team, entry_t, last_time)

    return _merge_adjacent_intervals(intervals)


def _boundary_events(intervals: dict[int, list[tuple[float, float, str]]]) -> list[tuple[float, int, int, str]]:
    """Flatten resolved on-court intervals into a chronological list of
    (time, is_entry, personId, teamTricode) boundary events, for replaying
    on-court membership in lockstep with a play-by-play row scan. Exits sort
    before entries at the same timestamp: a player's stint can end and their
    next one begin at the exact same instant (e.g. a zero-gap boundary
    between regulation and overtime), and processing the exit first lets
    interval_index advance before the new stint's entry is recorded —
    otherwise the entry gets written into the old (about-to-be-vacated) slot
    and the new stint's entry_pm is left unset.

    Every consumer applies a boundary only to rows strictly AFTER its
    timestamp (`events[ev_idx][0] < t`, not `<=`): points logged at the same
    frozen game clock as a substitution belong to the lineup that was on the
    floor before it. Subs commonly land mid-free-throw-sequence at the exact
    clock of the free throws themselves; charging same-instant points to the
    pre-sub lineup is what makes each player's summed stint +/- reproduce
    the official box score exactly."""
    events = []
    for pid, ivals in intervals.items():
        for entry_t, exit_t, team in ivals:
            events.append((entry_t, 1, pid, team))
            events.append((exit_t, 0, pid, team))
    events.sort(key=lambda e: (e[0], e[1]))
    return events


def format_game_clock(game_seconds: float) -> str:
    """e.g. 156.0 -> 'Q1 02:36' (2 minutes 36 seconds elapsed into Q1)."""
    period = 1
    remaining = max(game_seconds, 0)
    while remaining > _period_length_seconds(period):
        remaining -= _period_length_seconds(period)
        period += 1
    minutes, seconds = divmod(int(round(remaining)), 60)
    label = f"Q{period}" if period <= 4 else f"OT{period - 4}"
    return f"{label} {minutes:02d}:{seconds:02d}"


def format_broadcast_clock(game_seconds: float) -> str:
    """Same instant as `format_game_clock`, but displayed as the broadcast
    game clock counts down: from 12:00 at the start of a quarter, or 5:00 at
    the start of an overtime period. e.g. 156.0 -> 'Q1 09:24'."""
    period = 1
    remaining = max(game_seconds, 0)
    while remaining > _period_length_seconds(period):
        remaining -= _period_length_seconds(period)
        period += 1
    countdown = _period_length_seconds(period) - remaining
    minutes, seconds = divmod(int(round(countdown)), 60)
    label = f"Q{period}" if period <= 4 else f"OT{period - 4}"
    return f"{label} {minutes:02d}:{seconds:02d}"


def format_duration(minutes_float: float) -> str:
    total_seconds = int(round(minutes_float * 60))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def compute_stints(csv_path: Path) -> pd.DataFrame:
    """Return one row per on-court stint: teamTricode, displayName, personId,
    entry/exit game clock and elapsed minutes, and stint duration in minutes.
    Every player still on the court at the end of any period gets their stint
    split there (an exit at the end of that period, immediately followed by a
    fresh, unconfirmed entry at the start of the next one), even if no
    substitution actually happens at that boundary. A later real event can
    still confirm or contradict that assumption (see the `confirmed` flag)."""
    df, _home_team, _away_team, name_to_id, on_court = _prepare_simulation(csv_path)
    id_to_display_name = {v: k for k, v in name_to_id.items()}
    pid_to_player_name = (
        df.dropna(subset=["personId", "playerName"]).drop_duplicates("personId").set_index("personId")["playerName"]
    ).to_dict()

    intervals = _resolve_on_court_intervals(df, name_to_id, on_court)
    stints = [
        {"personId": pid, "teamTricode": team, "entry_seconds": entry_t, "exit_seconds": exit_t}
        for pid, ivals in intervals.items()
        for entry_t, exit_t, team in ivals
    ]

    result = pd.DataFrame.from_records(stints)
    result["displayName"] = result["personId"].map(id_to_display_name).fillna(
        result["personId"].map(pid_to_player_name)
    ).fillna(result["personId"].map(_rotation_display_names(df))).fillna(result["personId"].astype(str))
    result["entry_clock"] = result["entry_seconds"].map(format_game_clock)
    result["exit_clock"] = result["exit_seconds"].map(format_game_clock)
    result["entry_minutes"] = result["entry_seconds"] / 60
    result["exit_minutes"] = result["exit_seconds"] / 60
    result["duration_minutes"] = result["exit_minutes"] - result["entry_minutes"]
    result = result.sort_values(["teamTricode", "displayName", "entry_seconds"]).reset_index(drop=True)
    return result[
        [
            "teamTricode", "displayName", "personId", "entry_clock", "exit_clock",
            "entry_minutes", "exit_minutes", "duration_minutes",
        ]
    ]


def compute_stint_plus_minus(csv_path: Path) -> pd.DataFrame:
    """Return one row per on-court stint, like compute_stints, but with each
    player's cumulative plus/minus at the moment they entered and left — for
    marking stint start/stop points on the plus/minus chart. Plus/minus is not
    reset per stint: a player re-entering starts from whatever value they left
    with, since it stays flat while they're on the bench."""
    df, home_team, away_team, name_to_id, on_court = _prepare_simulation(csv_path)
    id_to_display_name = {v: k for k, v in name_to_id.items()}
    pid_to_player_name = (
        df.dropna(subset=["personId", "playerName"]).drop_duplicates("personId").set_index("personId")["playerName"]
    ).to_dict()

    # resolve the validated on-court intervals once (shared with compute_stints),
    # then replay the score progression a single time against those exact
    # boundaries to capture each stint's plus/minus at entry and exit
    intervals = _resolve_on_court_intervals(df, name_to_id, on_court)
    events = _boundary_events(intervals)
    interval_index = {pid: 0 for pid in intervals}

    live_on_court: dict[str, set[int]] = {}
    plus_minus: dict[int, float] = {}
    prev_home, prev_away = 0.0, 0.0
    entry_pm: dict[tuple[int, int], float] = {}
    exit_pm: dict[tuple[int, int], float] = {}
    ev_idx = 0

    for _, row in df.iterrows():
        t = row["game_seconds"]
        while ev_idx < len(events) and events[ev_idx][0] < t:
            _e_t, is_entry, pid, team = events[ev_idx]
            court = live_on_court.setdefault(team, set())
            i = interval_index[pid]
            if is_entry:
                entry_pm[(pid, i)] = plus_minus.get(pid, 0)
                court.add(pid)
            else:
                exit_pm[(pid, i)] = plus_minus.get(pid, 0)
                court.discard(pid)
                interval_index[pid] += 1
            ev_idx += 1

        cur_home = row["scoreHome"] if pd.notna(row["scoreHome"]) else prev_home
        cur_away = row["scoreAway"] if pd.notna(row["scoreAway"]) else prev_away
        delta_home = cur_home - prev_home
        delta_away = cur_away - prev_away
        prev_home, prev_away = cur_home, cur_away

        if delta_home > 0:
            for pid in live_on_court.get(home_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) + delta_home
            for pid in live_on_court.get(away_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) - delta_home
        if delta_away > 0:
            for pid in live_on_court.get(away_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) + delta_away
            for pid in live_on_court.get(home_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) - delta_away

    # flush any boundary events that land exactly at (or after) the last row
    while ev_idx < len(events):
        _e_t, is_entry, pid, team = events[ev_idx]
        i = interval_index[pid]
        if is_entry:
            entry_pm[(pid, i)] = plus_minus.get(pid, 0)
        else:
            exit_pm[(pid, i)] = plus_minus.get(pid, 0)
            interval_index[pid] += 1
        ev_idx += 1

    stints = [
        {
            "personId": pid, "teamTricode": team,
            "entry_seconds": entry_t, "exit_seconds": exit_t,
            "entry_pm": entry_pm.get((pid, i), 0), "exit_pm": exit_pm.get((pid, i), 0),
        }
        for pid, ivals in intervals.items()
        for i, (entry_t, exit_t, team) in enumerate(ivals)
    ]

    result = pd.DataFrame.from_records(stints)
    result["displayName"] = result["personId"].map(id_to_display_name).fillna(
        result["personId"].map(pid_to_player_name)
    ).fillna(result["personId"].map(_rotation_display_names(df))).fillna(result["personId"].astype(str))
    result["entry_minutes"] = result["entry_seconds"] / 60
    result["exit_minutes"] = result["exit_seconds"] / 60
    result = result.sort_values(["teamTricode", "displayName", "entry_seconds"]).reset_index(drop=True)
    return result[
        ["teamTricode", "displayName", "personId", "entry_minutes", "entry_pm", "exit_minutes", "exit_pm"]
    ]


def compute_team_margin_timeline(csv_path: Path):
    """Return (timeline, home_team, away_team). timeline has one row per
    scoring play: game_minutes, home_margin (home score minus away),
    away_margin (away score minus home), and each team's own cumulative
    score (home_score, away_score) — the team-level score differential over
    time, independent of any single player's on-court status. Used to trace
    the actual shape of the game during a stint, rather than a straight line
    between the player's plus/minus at entry and exit."""
    df = _load_full_pbp(csv_path)
    home_away = _home_away_map(df)
    home_team = next(t for t, ha in home_away.items() if ha == "h")
    away_team = next(t for t, ha in home_away.items() if ha == "v")

    prev_home, prev_away = 0.0, 0.0
    records = [{"game_minutes": 0.0, "home_margin": 0.0, "away_margin": 0.0, "home_score": 0.0, "away_score": 0.0}]
    for _, row in df.iterrows():
        cur_home = row["scoreHome"] if pd.notna(row["scoreHome"]) else prev_home
        cur_away = row["scoreAway"] if pd.notna(row["scoreAway"]) else prev_away
        if cur_home != prev_home or cur_away != prev_away:
            records.append(
                {
                    "game_minutes": row["game_seconds"] / 60,
                    "home_margin": cur_home - cur_away,
                    "away_margin": cur_away - cur_home,
                    "home_score": cur_home,
                    "away_score": cur_away,
                }
            )
        prev_home, prev_away = cur_home, cur_away

    timeline = pd.DataFrame.from_records(records)
    return timeline, home_team, away_team


def compute_period_scores(csv_path: Path):
    """Return (periods, home_team, away_team, home_final, away_final).
    `periods` has one row per period (Q1, Q2, ... OT1, ...) with each team's
    points scored in that period specifically (not cumulative) — the
    standard box-score linescore."""
    df = _load_full_pbp(csv_path)
    home_away = _home_away_map(df)
    home_team = next(t for t, ha in home_away.items() if ha == "h")
    away_team = next(t for t, ha in home_away.items() if ha == "v")

    max_period = int(df["period"].max())
    prev_home, prev_away = 0.0, 0.0
    records = []
    for period in range(1, max_period + 1):
        period_rows = df[df["period"] == period]
        cur_home = period_rows["scoreHome"].dropna().iloc[-1] if period_rows["scoreHome"].notna().any() else prev_home
        cur_away = period_rows["scoreAway"].dropna().iloc[-1] if period_rows["scoreAway"].notna().any() else prev_away
        records.append(
            {
                "period": _period_label(period),
                "home_points": int(cur_home - prev_home),
                "away_points": int(cur_away - prev_away),
            }
        )
        prev_home, prev_away = cur_home, cur_away

    periods = pd.DataFrame.from_records(records)
    return periods, home_team, away_team, int(prev_home), int(prev_away)


def compute_shot_plus_minus(csv_path: Path) -> pd.DataFrame:
    """Return scoring events — field goals (isFieldGoal==1) plus made free
    throws (shotValue forced to 1) — with a `plusMinus` column: the shooter's
    cumulative on-court point differential at the moment of that shot."""
    df, home_team, away_team, name_to_id, on_court = _prepare_simulation(csv_path)
    intervals = _resolve_on_court_intervals(df, name_to_id, on_court)
    events = _boundary_events(intervals)
    ev_idx = 0

    plus_minus: dict[int, float] = {}
    prev_home, prev_away = 0.0, 0.0
    shot_pm: dict[int, float] = {}
    made_ft_idx = []
    live_on_court: dict[str, set[int]] = {}

    for idx, row in df.iterrows():
        t = row["game_seconds"]
        while ev_idx < len(events) and events[ev_idx][0] < t:
            _e_t, is_entry, pid, team = events[ev_idx]
            court = live_on_court.setdefault(team, set())
            if is_entry:
                court.add(pid)
            else:
                court.discard(pid)
            ev_idx += 1

        cur_home = row["scoreHome"] if pd.notna(row["scoreHome"]) else prev_home
        cur_away = row["scoreAway"] if pd.notna(row["scoreAway"]) else prev_away
        delta_home = cur_home - prev_home
        delta_away = cur_away - prev_away
        prev_home, prev_away = cur_home, cur_away

        if delta_home > 0:
            for pid in live_on_court.get(home_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) + delta_home
            for pid in live_on_court.get(away_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) - delta_home
        if delta_away > 0:
            for pid in live_on_court.get(away_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) + delta_away
            for pid in live_on_court.get(home_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) - delta_away

        if row["isFieldGoal"] == 1 and pd.notna(row["personId"]):
            shot_pm[idx] = plus_minus.get(int(row["personId"]), 0)
        elif (
            row["actionType"] == "Free Throw"
            and pd.notna(row["personId"])
            and not str(row["description"]).startswith("MISS")
        ):
            shot_pm[idx] = plus_minus.get(int(row["personId"]), 0)
            made_ft_idx.append(idx)

    # id_to_display_name disambiguates same-team same-surname players (e.g. two
    # "Williams") using the name text NBA's own feed already disambiguates with
    # in substitution descriptions ("Jal. Williams" vs "Jay. Williams"); grouping
    # shots by playerName alone would silently merge such players together.
    id_to_display_name = {v: k for k, v in name_to_id.items()}

    fg = df[df["isFieldGoal"] == 1].dropna(subset=["shotResult", "playerName"]).copy()
    made_ft = df.loc[made_ft_idx].copy()
    made_ft["shotResult"] = "Made"
    made_ft["shotValue"] = 1
    shots = pd.concat([fg, made_ft], ignore_index=False).sort_index()
    shots["game_minutes"] = shots["game_seconds"] / 60
    shots["plusMinus"] = shots.index.map(shot_pm).fillna(0)
    shots["displayName"] = shots["personId"].map(id_to_display_name).fillna(shots["playerName"])
    return shots, plus_minus


_AST_RE = re.compile(r"\(([A-Za-z][\w\.\-' ]*?)\s+(\d+)\s+AST\)$")
_PTS_RE = re.compile(r"\((\d+)\s+PTS\)")
_REB_RE = re.compile(r"Off:(\d+)\s+Def:(\d+)")
_STL_RE = re.compile(r"\((\d+)\s+STL\)")
_BLK_RE = re.compile(r"\((\d+)\s+BLK\)")


def compute_official_box_score(csv_path: Path, team: str | None = None) -> pd.DataFrame:
    """See compute_official_box_score_for_game — this variant reads the
    game id out of a play-by-play CSV first, and passes the play-by-play's
    own player names through so both sides agree (see `pbp_names` there)."""
    df = _load_full_pbp(csv_path)
    return compute_official_box_score_for_game(
        _game_id_from_df(df), team, pbp_names={v: k for k, v in _resolve_player_ids(df).items()}
    )


def compute_official_box_score_for_game(
    game_id: str, team: str | None = None, pbp_names: dict[int, str] | None = None
) -> pd.DataFrame:
    """Fetch the NBA's own official traditional box score for one game (via
    BoxScoreTraditionalV3) and return one row per player with: displayName,
    teamTricode, MIN, FGM, FGA, FG_PCT, FG3M, FG3A, FG3_PCT, FTM, FTA,
    FT_PCT, OREB, DREB, REB, AST, STL, BLK, TO, PF, PTS, PLUS_MINUS — sorted
    by minutes played, descending. If `team` is given, only that team's
    players are returned.

    Same-surname teammates (e.g. two "Williams") have to be disambiguated,
    and the play-by-play feed already does it — but not always the way we
    would guess. For 0042500317 the feed calls Jaylin and Kenrich Williams
    "J. Williams" and "K. Williams", while a first-name-prefix rule yields
    "Jay." and "Ken.". Callers that join this table to play-by-play-derived
    data (stints, lineups) by name break on that disagreement, so pass
    `pbp_names` — {personId: play-by-play name} — and those names win.
    The prefix rule is only the fallback for players the feed never named."""
    from nba_pbp.client import get_box_score_traditional

    box = get_box_score_traditional(game_id)
    if team:
        box = box[box["teamTricode"] == team]

    dup_surnames = set(box["familyName"][box["familyName"].duplicated(keep=False)])
    pbp_names = pbp_names or {}

    def _display(row) -> str:
        from_pbp = pbp_names.get(row["personId"])
        if from_pbp:
            return from_pbp
        if row["familyName"] in dup_surnames:
            return f"{row['firstName'][:3]}. {row['familyName']}"
        return row["familyName"]

    minutes_played = box["minutes"].fillna("").str.split(":").str[0]
    result = pd.DataFrame(
        {
            "displayName": box.apply(_display, axis=1),
            "teamTricode": box["teamTricode"],
            "MIN": pd.to_numeric(minutes_played, errors="coerce").fillna(0).astype(int),
            "FGM": box["fieldGoalsMade"],
            "FGA": box["fieldGoalsAttempted"],
            "FG_PCT": box["fieldGoalsPercentage"],
            "FG3M": box["threePointersMade"],
            "FG3A": box["threePointersAttempted"],
            "FG3_PCT": box["threePointersPercentage"],
            "FTM": box["freeThrowsMade"],
            "FTA": box["freeThrowsAttempted"],
            "FT_PCT": box["freeThrowsPercentage"],
            "OREB": box["reboundsOffensive"],
            "DREB": box["reboundsDefensive"],
            "REB": box["reboundsTotal"],
            "AST": box["assists"],
            "STL": box["steals"],
            "BLK": box["blocks"],
            "TO": box["turnovers"],
            "PF": box["foulsPersonal"],
            "PTS": box["points"],
            "PLUS_MINUS": box["plusMinusPoints"].fillna(0),
        }
    )
    return result.sort_values("MIN", ascending=False).reset_index(drop=True)


def compute_statline(csv_path: Path) -> pd.DataFrame:
    """Return one row per player: teamTricode, displayName, MIN, PTS, REB, AST,
    STL, BLK, and STOCKS (STL + BLK + AST). PTS/REB/AST/STL/BLK are parsed from
    the cumulative counts the NBA's feed already embeds in play descriptions
    (e.g. "(12 PTS)", "Off:2 Def:5", "(1 STL)"), keyed by personId. MIN comes
    from `compute_stints`."""
    df = _load_full_pbp(csv_path)
    name_to_id = _resolve_player_ids(df)
    id_to_display_name = {v: k for k, v in name_to_id.items()}
    pid_to_player_name = (
        df.dropna(subset=["personId", "playerName"]).drop_duplicates("personId").set_index("personId")["playerName"]
    ).to_dict()
    pid_to_team = (
        df.dropna(subset=["personId", "teamTricode"]).drop_duplicates("personId").set_index("personId")["teamTricode"]
    ).to_dict()
    rotation_names = _rotation_display_names(df)

    def _display(pid: int) -> str:
        return id_to_display_name.get(pid, pid_to_player_name.get(pid, rotation_names.get(pid, str(pid))))

    pts_rows = df[df["actionType"].isin(["Made Shot", "Free Throw"])].dropna(subset=["personId"]).copy()
    pts_rows["val"] = pts_rows["description"].str.extract(_PTS_RE)[0].astype(float)
    pts = pts_rows.groupby("personId")["val"].max()

    reb_rows = df[df["actionType"] == "Rebound"].dropna(subset=["personId"]).copy()
    reb_parsed = reb_rows["description"].str.extract(_REB_RE).astype(float)
    reb_rows["off"], reb_rows["def"] = reb_parsed[0], reb_parsed[1]
    reb_totals = reb_rows.groupby("personId").agg(off=("off", "max"), def_=("def", "max"))
    reb = reb_totals["off"] + reb_totals["def_"]

    stl_rows = df[df["description"].str.contains("STEAL", na=False)].dropna(subset=["personId"]).copy()
    stl_rows["val"] = stl_rows["description"].str.extract(_STL_RE)[0].astype(float)
    stl = stl_rows.groupby("personId")["val"].max()

    blk_rows = df[df["description"].str.contains("BLOCK", na=False)].dropna(subset=["personId"]).copy()
    blk_rows["val"] = blk_rows["description"].str.extract(_BLK_RE)[0].astype(float)
    blk = blk_rows.groupby("personId")["val"].max()

    ast_rows = df[df["actionType"] == "Made Shot"].copy()
    ast_extracted = ast_rows["description"].str.extract(_AST_RE)
    ast_rows["assist_name"], ast_rows["val"] = ast_extracted[0], ast_extracted[1].astype(float)
    ast_rows = ast_rows.dropna(subset=["assist_name"])
    ast_rows["assist_id"] = ast_rows["assist_name"].str.strip().map(name_to_id)
    ast = ast_rows.dropna(subset=["assist_id"]).groupby("assist_id")["val"].max()

    minutes = compute_stints(csv_path).groupby("personId")["duration_minutes"].sum()

    # team-level events (team rebounds, timeouts, etc.) are logged with the
    # team's id in the personId column — exclude those from the player list
    known_player_ids = set(name_to_id.values()) | set(pid_to_player_name.keys())
    all_pids = set(minutes.index) | set(pts.index) | set(reb.index) | set(ast.index) | set(stl.index) | set(blk.index)
    all_pids &= known_player_ids
    result = pd.DataFrame({"personId": sorted(all_pids)})
    result["teamTricode"] = result["personId"].map(pid_to_team)
    result["displayName"] = result["personId"].map(_display)
    result["MIN"] = result["personId"].map(minutes).fillna(0).round().astype(int)
    result["PTS"] = result["personId"].map(pts).fillna(0).astype(int)
    result["REB"] = result["personId"].map(reb).fillna(0).astype(int)
    result["AST"] = result["personId"].map(ast).fillna(0).astype(int)
    result["STL"] = result["personId"].map(stl).fillna(0).astype(int)
    result["BLK"] = result["personId"].map(blk).fillna(0).astype(int)
    result["STOCKS"] = result["STL"] + result["BLK"] + result["AST"]
    result = result.sort_values(["teamTricode", "MIN"], ascending=[True, False]).reset_index(drop=True)
    return result[["teamTricode", "displayName", "MIN", "PTS", "REB", "STOCKS"]]


def compute_event_plus_minus(csv_path: Path) -> pd.DataFrame:
    """Return one row per rebound/assist/steal/block/foul/turnover event:
    teamTricode, displayName, game_minutes, plusMinus (that player's on-court
    point differential at the moment of the event), and event_type
    ('REB'/'AST'/'STL'/'BLK'/'FOUL'/'TOV') — for plotting alongside shots on
    the plus/minus chart."""
    df, home_team, away_team, name_to_id, on_court = _prepare_simulation(csv_path)
    intervals = _resolve_on_court_intervals(df, name_to_id, on_court)
    events = _boundary_events(intervals)
    ev_idx = 0
    live_on_court: dict[str, set[int]] = {}

    id_to_display_name = {v: k for k, v in name_to_id.items()}
    pid_to_player_name = (
        df.dropna(subset=["personId", "playerName"]).drop_duplicates("personId").set_index("personId")["playerName"]
    ).to_dict()
    known_player_ids = set(name_to_id.values()) | set(pid_to_player_name.keys())
    rotation_names = _rotation_display_names(df)

    def _display(pid: int) -> str:
        return id_to_display_name.get(pid, pid_to_player_name.get(pid, rotation_names.get(pid, str(pid))))

    plus_minus: dict[int, float] = {}
    prev_home, prev_away = 0.0, 0.0
    records = []

    for _, row in df.iterrows():
        t = row["game_seconds"]
        while ev_idx < len(events) and events[ev_idx][0] < t:
            _e_t, is_entry, pid, team = events[ev_idx]
            court = live_on_court.setdefault(team, set())
            if is_entry:
                court.add(pid)
            else:
                court.discard(pid)
            ev_idx += 1

        cur_home = row["scoreHome"] if pd.notna(row["scoreHome"]) else prev_home
        cur_away = row["scoreAway"] if pd.notna(row["scoreAway"]) else prev_away
        delta_home = cur_home - prev_home
        delta_away = cur_away - prev_away
        prev_home, prev_away = cur_home, cur_away

        if delta_home > 0:
            for pid in live_on_court.get(home_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) + delta_home
            for pid in live_on_court.get(away_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) - delta_home
        if delta_away > 0:
            for pid in live_on_court.get(away_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) + delta_away
            for pid in live_on_court.get(home_team, ()):
                plus_minus[pid] = plus_minus.get(pid, 0) - delta_away

        description = str(row["description"])
        t_minutes = row["game_seconds"] / 60
        pid = int(row["personId"]) if pd.notna(row["personId"]) else None

        event_type = None
        if row["actionType"] == "Rebound" and pid in known_player_ids:
            event_type = "REB"
        elif pid in known_player_ids and "STEAL" in description:
            event_type = "STL"
        elif pid in known_player_ids and "BLOCK" in description:
            event_type = "BLK"
        elif row["actionType"] == "Foul" and pid in known_player_ids:
            event_type = "FOUL"
        elif row["actionType"] == "Turnover" and pid in known_player_ids:
            event_type = "TOV"
        if event_type:
            records.append(
                {
                    "personId": pid, "teamTricode": row["teamTricode"],
                    "game_minutes": t_minutes, "plusMinus": plus_minus.get(pid, 0),
                    "event_type": event_type,
                }
            )

        if row["actionType"] == "Made Shot":
            ast_match = _AST_RE.search(description)
            if ast_match:
                assist_id = name_to_id.get(ast_match.group(1).strip())
                if assist_id is not None:
                    records.append(
                        {
                            "personId": assist_id, "teamTricode": row["teamTricode"],
                            "game_minutes": t_minutes, "plusMinus": plus_minus.get(assist_id, 0),
                            "event_type": "AST",
                        }
                    )

    result = pd.DataFrame.from_records(records)
    if result.empty:
        return result
    result["displayName"] = result["personId"].map(_display)
    return result


def compute_player_stint_stats(csv_path: Path) -> pd.DataFrame:
    """One row per on-court stint (same stints as `compute_stint_plus_minus`)
    with the player's own counting stats accumulated during that stint, in
    official box-score columns: teamTricode, displayName, personId,
    entry_minutes, exit_minutes, MIN (float minutes), FGM, FGA, FG3M, FG3A,
    FTM, FTA, OREB, DREB, REB, AST, STL, BLK, TO, PF, PTS, and PLUS_MINUS
    (the player's net on-court point differential over the stint).

    Events are attributed to the stint whose [entry, exit) window contains
    them. FG/FT/PTS and the offensive/defensive rebound inference mirror the
    per-lineup attribution in `_lineup_segments_with_stats`; AST/STL/BLK/TO/PF
    reuse `compute_event_plus_minus` so the totals match the event markers
    drawn on the charts."""
    df, _home_team, _away_team, name_to_id, on_court = _prepare_simulation(csv_path)
    intervals = _resolve_on_court_intervals(df, name_to_id, on_court)

    id_to_display_name = {v: k for k, v in name_to_id.items()}
    pid_to_player_name = (
        df.dropna(subset=["personId", "playerName"]).drop_duplicates("personId").set_index("personId")["playerName"]
    ).to_dict()
    known_player_ids = set(name_to_id.values()) | set(pid_to_player_name.keys())
    rotation_names = _rotation_display_names(df)

    def _display(pid: int) -> str:
        return id_to_display_name.get(pid, pid_to_player_name.get(pid, rotation_names.get(pid, str(pid))))

    stat_cols = ("FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB",
                 "REB", "AST", "STL", "BLK", "TO", "PF", "PTS")
    stints_by_pid: dict[int, list[dict]] = {
        pid: [
            {"entry_sec": entry, "exit_sec": exit_t, "teamTricode": team, **{c: 0 for c in stat_cols}}
            for entry, exit_t, team in ivals
        ]
        for pid, ivals in intervals.items()
    }

    def _attribute(pid, t, col, n=1):
        stints = stints_by_pid.get(pid, ())
        for stint in stints:
            if stint["entry_sec"] <= t < stint["exit_sec"]:
                stint[col] += n
                return
        # an event at the exact second the player subbed out (e.g. a made
        # shot followed by an immediate substitution at the same clock stop)
        # lands on no [entry, exit) window — credit it to the stint that
        # just ended rather than dropping it
        for stint in stints:
            if stint["entry_sec"] <= t <= stint["exit_sec"]:
                stint[col] += n
                return

    # field goals, free throws, points, and offensive/defensive rebounds from
    # the raw pbp (same off/def inference as the lineup stats: a rebound by
    # the team that just missed is offensive, otherwise defensive)
    last_miss_team = None
    for _, row in df.iterrows():
        if pd.isna(row.get("game_seconds")):
            continue
        t = row["game_seconds"]
        action = row["actionType"]
        desc = str(row["description"])
        pid = int(row["personId"]) if pd.notna(row["personId"]) else None
        team = row["teamTricode"]
        if action in ("Made Shot", "Missed Shot") and row.get("isFieldGoal", 0) == 1 and pid is not None:
            made = action == "Made Shot"
            _attribute(pid, t, "FGA")
            if made:
                _attribute(pid, t, "FGM")
                _attribute(pid, t, "PTS", int(row["shotValue"]) if pd.notna(row.get("shotValue")) else 2)
            if row.get("shotValue") == 3:
                _attribute(pid, t, "FG3A")
                if made:
                    _attribute(pid, t, "FG3M")
            last_miss_team = None if made else team
        elif action == "Free Throw" and pid is not None:
            made = not desc.startswith("MISS")
            _attribute(pid, t, "FTA")
            if made:
                _attribute(pid, t, "FTM")
                _attribute(pid, t, "PTS")
                last_miss_team = None
            else:
                last_miss_team = team
        elif action == "Rebound":
            if pid in known_player_ids:
                kind = "OREB" if (last_miss_team is not None and team == last_miss_team) else "DREB"
                _attribute(pid, t, kind)
                _attribute(pid, t, "REB")
            last_miss_team = None

    # assists / steals / blocks / turnovers / fouls: reuse the careful
    # description parsing in compute_event_plus_minus
    event_col = {"AST": "AST", "STL": "STL", "BLK": "BLK", "FOUL": "PF", "TOV": "TO"}
    events = compute_event_plus_minus(csv_path)
    if not events.empty:
        for _, r in events.iterrows():
            col = event_col.get(r["event_type"])
            if col is not None:
                _attribute(int(r["personId"]), r["game_minutes"] * 60, col)

    # each stint's net plus/minus, keyed by (personId, entry time)
    pm = compute_stint_plus_minus(csv_path)
    pm_by_key = {
        (int(r["personId"]), round(r["entry_minutes"] * 60, 3)): r["exit_pm"] - r["entry_pm"]
        for _, r in pm.iterrows()
    }

    rows = []
    for pid, stints in stints_by_pid.items():
        for s in stints:
            rows.append({
                "teamTricode": s["teamTricode"], "displayName": _display(pid), "personId": pid,
                "entry_minutes": s["entry_sec"] / 60, "exit_minutes": s["exit_sec"] / 60,
                "MIN": (s["exit_sec"] - s["entry_sec"]) / 60,
                **{c: s[c] for c in stat_cols},
                "PLUS_MINUS": int(pm_by_key.get((pid, round(s["entry_sec"], 3)), 0)),
            })
    result = pd.DataFrame.from_records(rows)
    return result.sort_values(["teamTricode", "displayName", "entry_minutes"]).reset_index(drop=True)


def _lineup_code(display_name: str) -> str:
    """First two characters of a player's last name (e.g. 'Jal. Williams' ->
    'Wi', 'Gilgeous-Alexander' -> 'Gi'), capitalized."""
    parts = str(display_name).split()
    last = parts[-1] if parts else str(display_name)
    return last[:2].capitalize()


def _game_clock_label(game_seconds: float) -> str:
    """Elapsed game seconds -> "P MM:SS" game-clock notation (period label
    plus the clock time remaining in that period), e.g. 2604s -> 'Q4 07:24'."""
    period = _period_of_seconds(game_seconds)
    elapsed_before = sum(_period_length_seconds(p) for p in range(1, period))
    remaining = max(_period_length_seconds(period) - (game_seconds - elapsed_before), 0)
    minutes, seconds = divmod(int(round(remaining)), 60)
    if seconds == 60:
        minutes, seconds = minutes + 1, 0
    return f"{_period_label(period)} {minutes:02d}:{seconds:02d}"


def _mmss(seconds: float) -> str:
    """Seconds -> "MM:SS"."""
    total = int(round(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def _lineup_segments_with_stats(csv_path: Path):
    """Every contiguous 5-man lineup stint (segment), with the team's counting
    stats accumulated during it. Returns (segments, display_fn) where segments
    is a list of dicts: teamTricode, lineup (frozenset of pids), start_sec,
    end_sec, PTS, REB, AST, STL, BLK, TO, PF, PM. Shared by the aggregated
    lineup box score and the per-stint breakdown."""
    import numpy as np

    df, home_team, away_team, name_to_id, on_court = _prepare_simulation(csv_path)
    intervals = _resolve_on_court_intervals(df, name_to_id, on_court)

    id_to_name = {v: k for k, v in name_to_id.items()}
    pid_to_pbp_name = (
        df.dropna(subset=["personId", "playerName"]).drop_duplicates("personId")
        .set_index("personId")["playerName"]
    ).to_dict()

    def _display(pid: int) -> str:
        return id_to_name.get(pid) or pid_to_pbp_name.get(pid) or str(pid)

    # sweep every entry/exit to carve out each contiguous 5-man lineup segment
    boundary = []
    for pid, ivs in intervals.items():
        for entry, exit_t, team in ivs:
            boundary.append((entry, 1, pid, team))
            boundary.append((exit_t, -1, pid, team))
    by_time: dict[float, list] = {}
    for t, delta, pid, team in boundary:
        by_time.setdefault(t, []).append((delta, pid, team))

    teams = [home_team, away_team]
    active: dict[str, set] = {t: set() for t in teams}
    open_seg: dict[str, tuple] = {}  # team -> (lineup frozenset, start_sec)
    segments = []  # dicts, in chronological order

    def _close(team, start, lineup, end):
        if end > start:
            segments.append({
                "teamTricode": team, "lineup": lineup, "start_sec": start, "end_sec": end,
                "FGM": 0, "FGA": 0, "FG3M": 0, "FG3A": 0, "FTM": 0, "FTA": 0,
                "OREB": 0, "DREB": 0, "REB": 0, "AST": 0, "STL": 0, "BLK": 0,
                "TO": 0, "PF": 0, "PTS": 0, "PM": 0,
            })

    for t in sorted(by_time):
        for delta, pid, team in by_time[t]:
            (active[team].add if delta == 1 else active[team].discard)(pid)
        # only start a new segment for a team whose own 5-man set actually
        # changed — so one team's lineup isn't split at the other team's subs
        # (or at a same-instant sub/return), which would create adjacent
        # segments with the same lineup and no gap
        for team in teams:
            new_lineup = frozenset(active[team]) if len(active[team]) == 5 else None
            old = open_seg.get(team)
            old_lineup = old[0] if old else None
            if new_lineup == old_lineup:
                continue
            if old is not None:
                _close(team, old[1], old_lineup, t)
                del open_seg[team]
            if new_lineup is not None:
                open_seg[team] = (new_lineup, t)

    # team score as a step function of game seconds, for per-segment PTS / +/-
    timeline, _, _ = compute_team_margin_timeline(csv_path)
    timeline = timeline.sort_values("game_minutes")
    sec = timeline["game_minutes"].to_numpy() * 60
    home_score = timeline["home_score"].to_numpy()
    away_score = timeline["away_score"].to_numpy()

    def _score_at(t: float) -> tuple[float, float]:
        idx = max(int(np.searchsorted(sec, t, side="right")) - 1, 0)
        return home_score[idx], away_score[idx]

    for seg in segments:
        h0, a0 = _score_at(seg["start_sec"])
        h1, a1 = _score_at(seg["end_sec"])
        for_pts, opp_pts = (h1 - h0, a1 - a0) if seg["teamTricode"] == home_team else (a1 - a0, h1 - h0)
        seg["PTS"] = for_pts
        seg["PM"] = for_pts - opp_pts

    segs_by_team: dict[str, list] = {t: [] for t in teams}
    for seg in segments:
        segs_by_team[seg["teamTricode"]].append(seg)
    for lst in segs_by_team.values():
        lst.sort(key=lambda s: s["start_sec"])

    def _attribute(team, t, col, n=1):
        for seg in segs_by_team.get(team, ()):
            if seg["start_sec"] <= t < seg["end_sec"]:
                seg[col] += n
                return

    # assists / steals / blocks / turnovers / fouls: reuse the careful
    # description parsing in compute_event_plus_minus
    event_col = {"AST": "AST", "STL": "STL", "BLK": "BLK", "FOUL": "PF", "TOV": "TO"}
    events = compute_event_plus_minus(csv_path)
    if not events.empty:
        events = events.assign(game_seconds=events["game_minutes"] * 60)
        for _, r in events.iterrows():
            col = event_col.get(r["event_type"])
            if col is not None:
                _attribute(r["teamTricode"], r["game_seconds"], col)

    # field goals, free throws, and offensive/defensive rebounds straight from
    # the raw pbp. Rebound off/def isn't in the feed (subType is "Unknown"),
    # so it's inferred: a rebound by the team that just missed is offensive,
    # otherwise defensive.
    last_miss_team = None
    for _, row in df.iterrows():
        if pd.isna(row.get("game_seconds")):
            continue
        action, team, t = row["actionType"], row["teamTricode"], row["game_seconds"]
        desc = str(row["description"])
        if action in ("Made Shot", "Missed Shot") and row.get("isFieldGoal", 0) == 1:
            made = action == "Made Shot"
            _attribute(team, t, "FGA")
            if made:
                _attribute(team, t, "FGM")
            if row.get("shotValue") == 3:
                _attribute(team, t, "FG3A")
                if made:
                    _attribute(team, t, "FG3M")
            last_miss_team = None if made else team
        elif action == "Free Throw":
            made = not desc.startswith("MISS")
            _attribute(team, t, "FTA")
            if made:
                _attribute(team, t, "FTM")
                last_miss_team = None
            else:
                last_miss_team = team
        elif action == "Rebound":
            kind = "OREB" if (last_miss_team is not None and team == last_miss_team) else "DREB"
            _attribute(team, t, kind)
            _attribute(team, t, "REB")
            last_miss_team = None

    return segments, _display


_LINEUP_STAT_COLUMNS = ["MIN", "PTS", "REB", "AST", "STL", "BLK", "TO", "PF", "PLUS_MINUS"]


def compute_lineup_box_score(csv_path: Path, min_minutes: float = 1.0) -> pd.DataFrame:
    """One row per 5-man lineup each team used for more than `min_minutes`,
    with the team's counting stats accumulated while that lineup was on the
    floor: MIN, `stints` (how many separate stints the lineup had), PTS, REB,
    AST, STL, BLK, TO, PF, and +/- (net scoring margin
    over the lineup's stints). Lineups are named by concatenating the first
    two letters of each player's last name (sorted); same-name collisions are
    left as-is. Built from the same on-court intervals as the stint charts."""
    segments, _display = _lineup_segments_with_stats(csv_path)

    sum_cols = ("FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB",
                "PTS", "REB", "AST", "STL", "BLK", "TO", "PF", "PM")
    agg: dict[tuple, dict] = {}
    for seg in segments:
        key = (seg["teamTricode"], seg["lineup"])
        s = agg.setdefault(key, {"MIN": 0.0, "stints": 0, **{c: 0 for c in sum_cols}})
        s["MIN"] += (seg["end_sec"] - seg["start_sec"]) / 60
        s["stints"] += 1
        for c in sum_cols:
            s[c] += seg[c]

    rows = []
    for (team, lineup), s in agg.items():
        if s["MIN"] <= min_minutes:
            continue
        names = sorted(_display(p) for p in lineup)  # sort names before building the code
        code = "".join(_lineup_code(n) for n in names)
        rows.append({
            "teamTricode": team, "lineup": code, "players": ", ".join(names),
            "MIN": s["MIN"], "stints": s["stints"],
            "FGM": s["FGM"], "FGA": s["FGA"], "FG3M": s["FG3M"], "FG3A": s["FG3A"],
            "FTM": s["FTM"], "FTA": s["FTA"], "OREB": s["OREB"], "DREB": s["DREB"],
            "PTS": int(s["PTS"]), "REB": s["REB"], "AST": s["AST"],
            "STL": s["STL"], "BLK": s["BLK"], "TO": s["TO"], "PF": s["PF"],
            "PLUS_MINUS": int(s["PM"]),
        })
    cols = ["teamTricode", "lineup", "players", "MIN", "stints",
            "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB",
            "PTS", "REB", "AST", "STL", "BLK", "TO", "PF", "PLUS_MINUS"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows).sort_values(["teamTricode", "lineup"]).reset_index(drop=True)


# the full player-style box-score columns, in official order
_LINEUP_BOX_COLUMNS = [
    "MIN", "FGM", "FGA", "FG%", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%",
    "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "PTS", "+/-",
]


def _pct(made, att):
    return round(made / att * 100) if att else 0


def compute_lineup_stints(csv_path: Path, min_seconds: float = 30.0) -> pd.DataFrame:
    """One row per individual lineup stint (a single contiguous stretch a
    5-man unit was on the floor) lasting longer than `min_seconds`. Columns:
    lineup, players, start/end in "P MM:SS" game-clock notation, MIN as MM:SS,
    then the full player-style box score (MIN/FGM/FGA/FG%/3PM/3PA/3P%/FTM/FTA/
    FT%/OREB/DREB/REB/AST/STL/BLK/TO/PF/PTS/+/-) — the team's totals during
    that stint. Not aggregated across a lineup's separate appearances."""
    segments, _display = _lineup_segments_with_stats(csv_path)

    rows = []
    for seg in segments:
        duration = seg["end_sec"] - seg["start_sec"]
        if duration <= min_seconds:
            continue
        names = sorted(_display(p) for p in seg["lineup"])  # sort names before building the code
        rows.append({
            "teamTricode": seg["teamTricode"],
            "lineup": "".join(_lineup_code(n) for n in names),
            "players": ", ".join(names),
            "start": _game_clock_label(seg["start_sec"]),
            "end": _game_clock_label(seg["end_sec"]),
            "MIN": _mmss(duration),
            "FGM": seg["FGM"], "FGA": seg["FGA"], "FG%": _pct(seg["FGM"], seg["FGA"]),
            "3PM": seg["FG3M"], "3PA": seg["FG3A"], "3P%": _pct(seg["FG3M"], seg["FG3A"]),
            "FTM": seg["FTM"], "FTA": seg["FTA"], "FT%": _pct(seg["FTM"], seg["FTA"]),
            "OREB": seg["OREB"], "DREB": seg["DREB"], "REB": seg["REB"],
            "AST": seg["AST"], "STL": seg["STL"], "BLK": seg["BLK"],
            "TO": seg["TO"], "PF": seg["PF"], "PTS": int(seg["PTS"]),
            "+/-": int(seg["PM"]),
            "_start_sec": seg["start_sec"],
        })
    cols = ["teamTricode", "lineup", "players", "start", "end", *_LINEUP_BOX_COLUMNS]
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame(rows).sort_values(["teamTricode", "lineup", "_start_sec"]).reset_index(drop=True)
    return out[cols]


def compute_lineup_stint_segments(csv_path: Path, min_seconds: float = 30.0) -> pd.DataFrame:
    """Numeric view of each lineup stint longer than `min_seconds` for
    plotting/hover: teamTricode, lineup code, start_min, end_min, MIN (float
    minutes) and MIN_str (MM:SS), the stint's net PLUS_MINUS, and its counting
    stats (PTS, REB, AST, STL, BLK, TO, PF). In chronological order per team."""
    segments, _display = _lineup_segments_with_stats(csv_path)
    rows = []
    for seg in segments:
        duration = seg["end_sec"] - seg["start_sec"]
        if duration <= min_seconds:
            continue
        names = sorted(_display(p) for p in seg["lineup"])
        rows.append({
            "teamTricode": seg["teamTricode"],
            "lineup": "".join(_lineup_code(n) for n in names),
            "players": ", ".join(names),
            "start_min": seg["start_sec"] / 60,
            "end_min": seg["end_sec"] / 60,
            "MIN": duration / 60,
            "MIN_str": _mmss(duration),
            "PLUS_MINUS": int(seg["PM"]),
            "FGM": seg["FGM"], "FGA": seg["FGA"], "FG3M": seg["FG3M"], "FG3A": seg["FG3A"],
            "FTM": seg["FTM"], "FTA": seg["FTA"], "OREB": seg["OREB"], "DREB": seg["DREB"],
            "PTS": int(seg["PTS"]), "REB": seg["REB"], "AST": seg["AST"],
            "STL": seg["STL"], "BLK": seg["BLK"], "TO": seg["TO"], "PF": seg["PF"],
        })
    cols = ["teamTricode", "lineup", "players", "start_min", "end_min", "MIN", "MIN_str", "PLUS_MINUS",
            "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB",
            "PTS", "REB", "AST", "STL", "BLK", "TO", "PF"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows).sort_values(["teamTricode", "start_min"]).reset_index(drop=True)
