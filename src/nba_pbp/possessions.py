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

import math
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


def _offsets(start_rem, clocks) -> list[str]:
    """Whole seconds from a possession's start to each of its events."""
    if start_rem is None:
        return ["0"] * len(clocks)
    out = []
    for c in clocks:
        try:
            m, sec = c.split(":")
            out.append(f"{max(0, int(round(start_rem - (int(m) * 60 + int(sec))))):d}")
        except ValueError:
            out.append("0")
    return out


def _mmss(remaining: float) -> str:
    return f"{int(remaining // 60)}:{remaining % 60:04.1f}"


def _last_free_throw(sub_type: str) -> bool:
    """'Free Throw 2 of 2' / '1 of 1' -> True; '1 of 2' -> False."""
    m = re.search(r"(\d+) of (\d+)", str(sub_type))
    return bool(m) and m.group(1) == m.group(2)


# NBA "legacy" shot coordinates: tenths of a foot, origin at the basket,
# +y out toward half court. The five sectors below are the 45-degree split
# NBA's own SHOT_ZONE_AREA uses (boundaries at 22.5 / 67.5 / 112.5 / 157.5
# degrees), which is also how a broadcast talks: corner, wing, top. Their
# labelling has LOC_X > 0 as the RIGHT side, so that is what "right" means
# here. Checked against the arc, which is the geometry's own witness: the
# corner sectors come out 22.3-23.5 ft (the corner line is 22 ft) and the
# top sector 24.2-27.8 ft (23.75 ft up top).
_SECTORS = ((22.5, "right corner"), (67.5, "right wing"),
            (112.5, "straight on"), (157.5, "left wing"), (181.0, "left corner"))
# two letters per area, so a shot fits the table as "RW25" — the long name
# rides along in the hover, the way a player's does behind their initials
_AREA_CODE = {"at the rim": "RM", "right corner": "RC", "right wing": "RW",
              "straight on": "SO", "left wing": "LW", "left corner": "LC"}


def shot_area(x: float, y: float) -> str:
    """A named area for one shot, from its coordinates. Distance is the
    caller's business — see shot_note()."""
    if math.hypot(x, y) / 10.0 < 4.0:
        return "at the rim"           # angle is meaningless under the hoop
    ang = math.degrees(math.atan2(y, x))
    for limit, name in _SECTORS:
        if ang < limit:
            return name
    return "left corner"


def shot_code(x: float, y: float) -> str:
    """"RW 27" — two letters for the area, two digits for the feet. Fixed
    five-character width so the column stacks, and the distance is
    right-aligned rather than zero-padded because "RM  1" reads as one
    foot where "RM 01" reads as a serial number.

    Distance comes from the COORDINATES, not the feed's shotDistance: the
    two agree to 0.26 ft where both exist, but shotDistance is 0 on ~9% of
    attempts including threes, which the coordinates still locate. Checked
    against the NBA's own prose, which embeds the distance ("25' 3PT Jump
    Shot"): 4,117 of 4,117 shots over 25 games matched within a foot."""
    return (f"{_AREA_CODE[shot_area(x, y)]} "
            f"{min(99, round(math.hypot(x, y) / 10.0)):>2d}")


def _event_code(atype: str, sub: str, desc: str, made: bool | None) -> str:
    """A short code for one play-by-play row: M2/M3 made, X2/X3 missed,
    FT made / X1 missed free throw, OREB/DREB (the caller decides
    which), TOV, FOUL, VIOL."""
    if atype == "Made Shot":
        return "M3" if "3PT" in desc else "M2"
    if atype == "Missed Shot":
        return "X3" if "3PT" in desc else "X2"
    if atype == "Free Throw":
        return "FT" if made else "X1"
    if atype == "Turnover":
        return "TO"
    if atype == "Foul":
        # an offensive foul is its own thing: it ENDS the possession
        return "OF" if "Offensive" in str(sub) else "FL"
    if atype == "Timeout":
        return "TM"
    if atype == "Violation":
        return "VIOL"
    if atype == "Jump Ball":
        return "JUMP"
    if atype == "Heave":
        return "HE"           # a buzzer heave, filed as a TEAM attempt
    if atype == "Instant Replay":
        return "IR"           # a review; the feed never says who called it
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

    # who plays for whom, straight out of this game's own rows — needed
    # because a jump ball is filed under the JUMPER's tricode, not the
    # team that actually came away with the tip
    player_team: dict[str, str] = {}
    for _n, _t in zip(df["playerName"], df["teamTricode"]):
        if pd.notna(_n) and pd.notna(_t):
            player_team.setdefault(str(_n), str(_t))
    # surname -> "C. Holmgren". Shot text names the assister by surname
    # only, so this is how that credit reaches the initialled form.
    name_i: dict[str, str] = {}
    for _n, _i in zip(df["playerName"], df["playerNameI"]):
        if pd.notna(_n) and pd.notna(_i):
            name_i.setdefault(str(_n).strip(), str(_i).strip())

    out: list[dict] = []
    cur_team: str | None = None
    start_el: float | None = None
    start_rem: float | None = None
    points = 0
    last_code = ""       # the last thing that happened inside this one
    away_ft = False      # an away-from-play foul: the shooter KEEPS the ball
    by_team: dict[str, list] = {t: [] for t in teams}
    tm_team: dict[str, list] = {t: [] for t in teams}   # each event's clock
    pl_team: dict[str, list] = {t: [] for t in teams}   # ...and its player
    sh_team: dict[str, list] = {t: [] for t in teams}   # ...and, for a
                                                       # shot, where from
    # an event by the team WITHOUT the ball (a kicked ball, a foul, a
    # block) is that team's doing, so it is held here and recorded on
    # THEIR next possession rather than on the one it happened during
    pend: dict[str, list] = {t: [] for t in teams}
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
                "off_events": " ".join(by_team.get(cur_team, [])) or "-",
                "def_events": " ".join(
                    by_team.get(other.get(cur_team, ""), [])) or "-",
                "off_times": " ".join(tm_team.get(cur_team, [])) or "",
                "def_times": " ".join(
                    tm_team.get(other.get(cur_team, ""), [])) or "",
                # one name per event code, same order, so a box score can
                # print them as columns beside the codes. Pipe-joined, not
                # space-joined: surnames carry spaces ("Smith Jr.") and a
                # space-joined list cannot be split back into names.
                "off_players": "|".join(pl_team.get(cur_team, [])) or "",
                "def_players": "|".join(
                    pl_team.get(other.get(cur_team, ""), [])) or "",
                "off_shots": "|".join(sh_team.get(cur_team, [])) or "",
                "def_shots": "|".join(
                    sh_team.get(other.get(cur_team, ""), [])) or "",
                # seconds from the possession's START to each event, in the
                # same order as the codes. The clock counts DOWN, so the
                # offset is start-minus-event. The first event is measured
                # from the possession start — which IS the end of the one
                # before — so it reads 0 whenever the ball changed hands and
                # the event that follows is what took it.
                "off_offsets": " ".join(
                    _offsets(start_rem, tm_team.get(cur_team, []))),
                "def_offsets": " ".join(
                    _offsets(start_rem,
                             tm_team.get(other.get(cur_team, ""), []))),
                "end_reason": reason, "end_detail": detail,
            })
        cur_team, points, last_code = next_team, 0, ""
        for _t in by_team:
            by_team[_t] = []
            tm_team[_t] = []
            pl_team[_t] = []
            sh_team[_t] = []
        if next_team in pend and pend[next_team]:     # their held events
            for _c, _k, _p, _s in pend[next_team]:    # open their line
                by_team[next_team].append(_c)
                tm_team[next_team].append(_k)
                pl_team[next_team].append(_p)
                sh_team[next_team].append(_s)
            pend[next_team] = []
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
        if team is None and atype in ("Rebound", "Turnover", "Timeout",
                                      "Heave"):
            team = _team_from_text(desc)
        # a review names nobody at all — not a tricode, not a nickname in
        # the text — so it can only be placed on the possession it
        # interrupted. That is "this happened here", NOT "this team did
        # it", and the player column says so by staying blank.
        if team is None and atype == "Instant Replay":
            team = cur_team
        # "Jump Ball Holmgren vs. Adams: Tip to Thompson" is filed under
        # Holmgren's team, but Thompson's team is the one that won it
        _tip = ""
        if atype == "Jump Ball" and "Tip to " in desc:
            _won = desc.split("Tip to ", 1)[1].strip()
            team = player_team.get(_won, team)
            _tip = _won
        # The player the row is filed under. Computed HERE, after the team
        # is settled, because the fallback IS the team: a timeout, a team
        # rebound and a shot-clock turnover are the club's doing, not any
        # player's, so they carry the tricode rather than a blank. Only a
        # review, which names no team either, stays "-".
        _pl = (str(r["playerNameI"]).strip()
               if pd.notna(r.get("playerNameI")) else "") or team or "-"
        # where the shot came from, for the codes that ARE shots
        _sh = "-"
        if atype in ("Made Shot", "Missed Shot"):
            _x, _y = float(r["xLegacy"] or 0), float(r["yLegacy"] or 0)
            if _x or _y:
                _sh = shot_code(_x, _y)
        # A jump ball is FILED under a jumper but WON by whoever the tip
        # went to, and the possession follows the tip — so the row would
        # otherwise print an opponent's name, in the possessing team's
        # colour, on the winning team's line. Credit the tip's receiver,
        # the same player the team attribution already keys off.
        if _tip:
            _pl = name_i.get(_tip, _pl)
        if atype == "Instant Replay":
            _pl = "-"        # placed on the possession it interrupted, but
                             # attributed to nobody: the feed does not say
                             # which bench called for the review

        if atype in ("nan", "None") and team in by_team:
            _clk = f"{int(rem // 60)}:{int(rem % 60):02d}"
            if "STEAL" in desc:
                by_team[team].append("STL")
                tm_team[team].append(_clk)
                pl_team[team].append(_pl)
                sh_team[team].append("-")
                last_code = "STL"
            elif "BLOCK" in desc:
                if cur_team is not None and team != cur_team:
                    pend[team].append(("BLK", _clk, _pl, "-"))
                else:
                    by_team[team].append("BLK")
                    tm_team[team].append(_clk)
                    pl_team[team].append(_pl)
                    sh_team[team].append("-")
                last_code = "BLK"
            continue

        if atype in ("Made Shot", "Missed Shot") and team != cur_team \
                and cur_team is not None:
            desyncs += 1
            close(period, rem, el, "possession change", team)

        if atype in ("Made Shot", "Missed Shot", "Free Throw", "Turnover",
                     "Rebound", "Foul", "Violation", "Jump Ball", "Timeout",
                     "Heave", "Instant Replay"):
            _made = None
            if atype == "Free Throw":
                _made = "MISS" not in desc
            _code = _event_code(atype, sub, desc, _made)
            if atype == "Foul":
                away_ft = "Away From Play" in sub
            if atype == "Rebound":
                # OR when the team that shot it gets it back, DR otherwise
                _code = "OR" if team == cur_team else "DR"
            # the offensive-foul turnover is the SAME event as the OF
            # foul row beside it — record it once, not twice
            if atype == "Turnover" and "Offensive Foul" in sub:
                _code = None
            if _code:
                last_code = _code
            _clk = f"{int(rem // 60)}:{int(rem % 60):02d}"
            if atype == "Rebound" and _code == "DR":
                pass          # recorded below, AFTER the possession closes
            elif (_code and team in pend and cur_team is not None
                    and team != cur_team and atype not in ("Turnover",)):
                pend[team].append((_code, _clk, _pl, _sh))  # hold for them
            elif _code and team in by_team:
                # the assist is credited to the shooter's own team and
                # happens just before the basket
                if atype == "Made Shot" and "AST)" in desc:
                    _a = re.search(r"\(([^()]+?)\s+\d+\s+AST\)", desc)
                    by_team[team].append("AST")
                    tm_team[team].append(_clk)
                    _an = _a.group(1).strip() if _a else ""
                    pl_team[team].append(name_i.get(_an, _an) or "-")
                    sh_team[team].append("-")
                by_team[team].append(_code)
                tm_team[team].append(_clk)
                pl_team[team].append(_pl)
                sh_team[team].append(_sh)
            if atype == "Timeout":
                continue          # a timeout does not end the possession

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
                # an away-from-play foul hands over a free throw but NOT
                # the ball: the shooting team keeps its possession
                if away_ft:
                    away_ft = False
                else:
                    close(period, rem, el, "made last free throw",
                          other[team])
            # a missed last free throw is left to its rebound

        elif atype == "Rebound":
            if team is None:
                continue
            if team != cur_team:                    # defensive rebound
                close(period, rem, el, "defensive rebound", team)
                # ... and it is the first event of the possession it just
                # started, not a footnote on the one it ended
                by_team[team].append("DR")
                tm_team[team].append(f"{int(rem // 60)}:{int(rem % 60):02d}")
                pl_team[team].append(_pl)
                sh_team[team].append("-")
                last_code = "DR"
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
