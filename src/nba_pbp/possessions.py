"""Split a game's play-by-play into team possessions.

WHAT COUNTS AS A POSSESSION
---------------------------
The standard basketball definition (the one NBA.com and Basketball-
Reference count with): a possession starts when a team gains control of
the ball and ends when it gives that control up. It is NOT the same as a
"play" or a shot attempt — a team that misses and grabs its own rebound
is still in the SAME possession.

A possession ENDS on exactly four things:

  1. a made field goal            (the ball goes to the other team)
  2. a made LAST free throw       (end of a trip to the line)
  3. a defensive rebound          (of a missed field goal, or of a
                                   missed last free throw)
  4. a turnover
  ... and, mechanically, the end of a period.

A possession does NOT end on:

  * an OFFENSIVE rebound — the same team keeps the ball, the possession
    just gets longer (this is the whole reason possessions and shot
    attempts differ)
  * a made free throw that is not the last of its trip (1 of 2)
  * a technical free throw — it is shot by the other team mid-possession
    and hands the ball straight back
  * fouls, timeouts, substitutions, kicked-ball violations, replays

AND-1: a made basket plus the bonus free throw is ONE possession. The
free throw lands on the same game clock as the basket, so the possession
absorbs it and its point.

WHAT THE PLAY-BY-PLAY GIVES US
------------------------------
  * shots      actionType Made Shot / Missed Shot, shotValue 2 or 3,
               teamTricode = the shooting team
  * free throws subType "Free Throw N of M" (or "Free Throw Technical");
               a MISS is flagged in the description text, made ones
               carry the updated score
  * rebounds   subType is useless ("Unknown"), so offensive vs defensive
               is decided the reliable way: by whether the rebounding
               team is the team already in possession. Team rebounds
               carry no tricode at all and are resolved from their
               description ("Rockets Rebound").
  * turnovers  teamTricode = the team that lost the ball

VALIDATING THE RESULT
---------------------
`possession_summary` checks the derived count against the classic
estimator, POSS = FGA - OREB + TOV + 0.44 * FTA, and against the fact
that two teams' possession counts in a real game are within about one of
each other. Both are reported, never assumed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

_CLOCK = re.compile(r"PT(\d+)M([\d.]+)S")
_PERIOD_LEN = {True: 720.0, False: 300.0}   # regulation vs overtime


def _clock_seconds(clock: str) -> float | None:
    """Seconds REMAINING in the period, from the 'PT11M26.00S' form."""
    m = _CLOCK.match(str(clock))
    if not m:
        return None
    return int(m.group(1)) * 60 + float(m.group(2))


def _elapsed(period: int, remaining: float) -> float:
    """Seconds since tip-off (regulation periods 12:00, overtimes 5:00)."""
    full = 720.0 * min(period - 1, 4) + 300.0 * max(0, period - 5)
    return full + _PERIOD_LEN[period <= 4] - remaining


def _mmss(remaining: float) -> str:
    return f"{int(remaining // 60)}:{remaining % 60:04.1f}"


def _last_free_throw(sub_type: str) -> bool:
    """'Free Throw 2 of 2' / '1 of 1' -> True; '1 of 2' -> False."""
    m = re.search(r"(\d+) of (\d+)", str(sub_type))
    return bool(m) and m.group(1) == m.group(2)


def _event_code(atype: str, sub: str, desc: str, made: bool | None) -> str:
    """A short code for one play-by-play row: M2/M3 made, X2/X3 missed,
    FT/XFT, OREB/DREB (the caller decides which), TOV, FOUL, VIOL."""
    if atype == "Made Shot":
        return "M3" if "3PT" in desc else "M2"
    if atype == "Missed Shot":
        return "X3" if "3PT" in desc else "X2"
    if atype == "Free Throw":
        return "FT" if made else "XFT"
    if atype == "Turnover":
        return "TOV"
    if atype == "Foul":
        return "FOUL"
    if atype == "Violation":
        return "VIOL"
    if atype == "Jump Ball":
        return "JUMP"
    return atype[:4].upper()


def compute_possessions(csv_path: str | Path) -> pd.DataFrame:
    """Every possession in one game, in order.

    Columns: gameId, date, period, team, start_clock, end_clock (game
    clock, counting down), start_elapsed, end_elapsed (seconds since
    tip), duration_s, points, scored ("Y"/"N"), end_reason.
    """
    df = pd.read_csv(csv_path, dtype=str)
    game_id = str(df["gameId"].iloc[0])
    try:                       # cached; no network on a warm cache
        from nba_pbp import client
        game_date = client.get_game_info(game_id)["date"]
    except Exception:
        game_date = ""
    teams = [t for t in df["teamTricode"].dropna().unique()]
    if len(teams) != 2:
        raise ValueError(f"expected 2 teams, found {teams}")
    other = {teams[0]: teams[1], teams[1]: teams[0]}

    # team rebounds carry no tricode — resolve them from the text
    # ("Rockets Rebound", "THUNDER Rebound") by matching the nickname
    # against each tricode's own rows
    def _team_from_text(text: str) -> str | None:
        up = str(text).upper()
        for t in teams:
            if up.startswith(t):
                return t
        # nickname: the word before "Rebound"
        w = up.replace(" REBOUND", "").strip()
        for t, name in _NICKNAMES.items():
            if t in teams and name in w:
                return t
        return None

    out: list[dict] = []
    cur_team: str | None = None
    start_el: float | None = None
    start_rem: float | None = None
    points = 0
    last_code = ""       # the last thing that happened inside this one
    desyncs = 0          # shots by the team we did not think had the ball

    def close(period, end_rem, end_el, reason, next_team, detail=""):
        """Emit the running possession and open the next one."""
        nonlocal cur_team, start_el, start_rem, points, last_code
        if cur_team is not None and start_el is not None:
            out.append({
                "gameId": game_id, "date": game_date,
                "period": period, "team": cur_team,
                "start_clock": _mmss(start_rem), "end_clock": _mmss(end_rem),
                "start_elapsed": round(start_el, 1),
                "end_elapsed": round(end_el, 1),
                "duration_s": round(end_el - start_el, 1),
                "points": points, "scored": "Y" if points > 0 else "N",
                "last_event": last_code or "-",
                "end_reason": reason, "end_detail": detail,
            })
        cur_team, points, last_code = next_team, 0, ""
        start_el, start_rem = end_el, end_rem

    rows = df.to_dict("records")
    for idx, r in enumerate(rows):
        period = int(r["period"])
        rem = _clock_seconds(r["clock"])
        if rem is None:
            continue
        el = _elapsed(period, rem)
        atype, sub = str(r["actionType"]), str(r["subType"])
        team = r["teamTricode"] if pd.notna(r["teamTricode"]) else None
        desc = str(r["description"]) if pd.notna(r["description"]) else ""
        # team turnovers and team rebounds carry no tricode — the club
        # name in the text is the only attribution there is
        if team is None and atype in ("Rebound", "Turnover"):
            team = _team_from_text(desc)

        if atype in ("Made Shot", "Missed Shot", "Free Throw", "Turnover",
                     "Rebound", "Foul", "Violation", "Jump Ball"):
            _made = None
            if atype == "Free Throw":
                _made = "MISS" not in desc
            _code = _event_code(atype, sub, desc, _made)
            if atype == "Rebound":
                _code = "OREB" if team == cur_team else "DREB"
            last_code = _code

        if atype == "period":
            if sub == "start":
                cur_team, start_el, start_rem, points = None, el, rem, 0
            else:                                   # period end
                close(period, rem, el, "period end", None)
                cur_team, start_el, start_rem = None, None, None
            continue

        # opening a period (or recovering after one): the first event that
        # actually names who had the ball sets it
        if cur_team is None and team is not None:
            if atype in ("Made Shot", "Missed Shot", "Free Throw",
                         "Turnover", "Rebound"):
                cur_team = team
                if start_el is None:
                    start_el, start_rem = el, rem
            else:
                continue

        if atype in ("Made Shot", "Missed Shot") and team != cur_team:
            # the other team is shooting, so possession changed on
            # something we did not model — close it out and resync rather
            # than mis-credit the points
            desyncs += 1
            close(period, rem, el, "possession change", team)

        if atype == "Made Shot":
            points += int(float(r["shotValue"] or 2))
            # an and-1 free throw rides on the same made basket: absorb it
            # (and its point) before handing the ball over
            j = idx + 1
            while j < len(rows) and _clock_seconds(rows[j]["clock"]) == rem:
                nx = rows[j]
                if (str(nx["actionType"]) == "Free Throw"
                        and nx["teamTricode"] == team
                        and "Technical" not in str(nx["subType"])):
                    if "MISS" not in str(nx["description"]):
                        points += 1
                    rows[j] = {**nx, "actionType": "_absorbed"}
                j += 1
            close(period, rem, el, "made field goal", other[team],
                  "3PT" if "3PT" in desc else "2PT")

        elif atype == "Free Throw":
            if "Technical" in sub:                  # not a possession event
                continue
            if team != cur_team:                    # trip we had not opened
                desyncs += 1
                close(period, rem, el, "possession change", team)
            made = "MISS" not in desc
            if made:
                points += 1
            if _last_free_throw(sub) and made:
                close(period, rem, el, "made last free throw", other[team])
            # a missed last free throw is left to its rebound

        elif atype == "Rebound":
            if team is None:
                continue
            if team != cur_team:                    # defensive rebound
                close(period, rem, el, "defensive rebound", team)
            # offensive rebound: same team, possession continues

        elif atype == "Turnover":
            # whoever lost it, the ball goes to the other side
            loser = team or cur_team
            if loser is None:
                continue
            if loser != cur_team:
                desyncs += 1
            close(period, rem, el, "turnover", other[loser], sub)

    frame = pd.DataFrame(out)
    if len(frame):
        # EVERY possession window concludes TWO possessions at once: the
        # offensive one for the team with the ball and the defensive one
        # for the team without it. The same event decides both, in
        # opposite directions — a basket is an offensive success and a
        # defensive failure; a stop (miss into their rebound, a turnover,
        # a shot-clock expiry) is the reverse.
        # HOW THIS POSSESSION BEGAN. A team gets the ball because the
        # other side scored, turned it over (a live-ball loss, a shot-clock
        # expiry, an offensive foul...), because we rebounded their missed
        # 2P/3P/last free throw, because we won a jump ball we did not
        # already have, or at the start of a period. Anything the data
        # cannot place lands in "other" rather than being guessed at.
        def _gain(prev_reason, prev_detail, prev_team, team):
            if pd.isna(prev_reason) or prev_reason == "period end":
                return "period start"
            if prev_team == team:            # we kept it (period boundary)
                return "retained"
            if prev_reason in ("made field goal", "made last free throw"):
                return "opponent score"
            if prev_reason == "defensive rebound":
                return "defensive rebound"
            if prev_reason == "turnover":
                d = str(prev_detail)
                if "Offensive Foul" in d or "Charge" in d:
                    return "offensive foul"
                if "Shot Clock" in d:
                    return "shot clock"
                if "Out of Bounds" in d or "Backcourt" in d or "Traveling" in d:
                    return "violation"
                return "turnover"
            if prev_reason == "possession change":
                return "other"
            return "other"

        frame["gained"] = [
            _gain(pr, pd_, pt, t) for pr, pd_, pt, t in zip(
                frame["end_reason"].shift(1), frame["end_detail"].shift(1),
                frame["team"].shift(1), frame["team"])]
        frame["off_success"] = ["Y" if p > 0 else "N" for p in frame["points"]]
        frame["def_success"] = ["N" if p > 0 else "Y" for p in frame["points"]]
        # who was defending it
        pair = dict.fromkeys(frame["team"])
        two = list(pair)
        frame["def_team"] = [two[0] if t == two[1] else two[1]
                             for t in frame["team"]]
    frame.attrs["desyncs"] = desyncs
    return frame


# nicknames only needed for team-rebound rows, which name the club
_NICKNAMES = {
    "ATL": "HAWKS", "BOS": "CELTICS", "BKN": "NETS", "CHA": "HORNETS",
    "CHI": "BULLS", "CLE": "CAVALIERS", "DAL": "MAVERICKS", "DEN": "NUGGETS",
    "DET": "PISTONS", "GSW": "WARRIORS", "HOU": "ROCKETS", "IND": "PACERS",
    "LAC": "CLIPPERS", "LAL": "LAKERS", "MEM": "GRIZZLIES", "MIA": "HEAT",
    "MIL": "BUCKS", "MIN": "TIMBERWOLVES", "NOP": "PELICANS", "NYK": "KNICKS",
    "OKC": "THUNDER", "ORL": "MAGIC", "PHI": "76ERS", "PHX": "SUNS",
    "POR": "TRAIL BLAZERS", "SAC": "KINGS", "SAS": "SPURS", "TOR": "RAPTORS",
    "UTA": "JAZZ", "WAS": "WIZARDS",
}


def possession_summary(csv_path: str | Path) -> dict:
    """Derived possessions vs the classic estimator, per team.

    POSS = FGA - OREB + TOV + 0.44 * FTA is the estimate every box-score
    site falls back on; a play-by-play walk should land within a couple
    of possessions of it, and the two teams should be within about one
    of each other.
    """
    poss = compute_possessions(csv_path)
    df = pd.read_csv(csv_path, dtype=str)
    teams = list(poss["team"].dropna().unique())
    est = {}
    for t in teams:
        tr = df[df["teamTricode"] == t]
        fga = int(tr["actionType"].isin(["Made Shot", "Missed Shot"]).sum())
        fta = int(((tr["actionType"] == "Free Throw")
                   & ~tr["subType"].astype(str).str.contains("Technical")).sum())
        tov = int((tr["actionType"] == "Turnover").sum())
        # offensive rebounds: rebounds by the team that just missed
        oreb = 0
        prev_shooter = None
        for _, r in df.iterrows():
            a = str(r["actionType"])
            if a in ("Made Shot", "Missed Shot", "Free Throw"):
                prev_shooter = r["teamTricode"]
            elif a == "Rebound" and pd.notna(r["teamTricode"]):
                if r["teamTricode"] == prev_shooter == t:
                    oreb += 1
        est[t] = round(fga - oreb + tov + 0.44 * fta, 1)
    counts = poss["team"].value_counts().to_dict()
    return {
        "derived": counts,
        "estimator": est,
        "team_gap": abs(counts.get(teams[0], 0) - counts.get(teams[1], 0)),
        "mean_duration_s": round(float(poss["duration_s"].mean()), 1),
        "scored_rate": {t: round(float(
            (poss[poss.team == t]["scored"] == "Y").mean()), 3) for t in teams},
        "total_points_check": int(poss["points"].sum()),
    }
