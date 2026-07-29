"""The league-wide season page: the same visual grammar as the per-team
2-D season page (``plot_season_events_2d_html``), but the columns are the
30 teams and every value is that team's per-game average. Pure HTML/CSS,
no JavaScript, no images.

The season is split into four segments — first third of the regular
season (games 1-27), second third (28-54), last third (55-82), and the
playoffs — each with a toggle in the middle band that defaults to ON.
Turning a segment off drops its games from every average. Because pure
CSS cannot re-average, all 16 on/off combinations are precomputed and
the toggles simply reveal the matching one (team order and lane scales
are fixed across combinations so only the bar heights and the box
numbers change).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd

from nba_pbp import client
from nba_pbp.edge import league_history
from nba_pbp.plotting import (_TEAM_BRAND_COLORS, _TEAM_EAST,
                              _season_break_dates)
from nba_pbp.plusminus import compute_official_box_score_for_game

_CLOCK_RE = re.compile(r"PT(\d+)M([\d.]+)S")


def _game_ot_clutch(game_id) -> int:
    """OT/Clutch bits for one game, from its cached play-by-play (same
    rules as the team pages): 16 = the game went past regulation;
    32 = the NBA clutch-game rule, the score within 5 at any point past
    43:00 (the margin standing AT 43:00 counts, so every OT game is
    clutch too). 0 on any parsing trouble."""
    try:
        df = client.get_play_by_play_cached(game_id)
        bits = 16 if int(df["period"].max()) > 4 else 0
        sc = df[df["scoreHome"].notna() & (df["scoreHome"].astype(str) != "")]
        pre, checks = None, []
        for p, c, sh, sa in zip(sc["period"], sc["clock"],
                                sc["scoreHome"], sc["scoreAway"]):
            m = _CLOCK_RE.match(str(c))
            if not m:
                continue
            p = int(p)
            remaining = int(m.group(1)) * 60 + float(m.group(2))
            plen = 720.0 if p <= 4 else 300.0
            elapsed = (720.0 * min(p - 1, 4) + 300.0 * max(0, p - 5)
                       + plen - remaining)
            margin = float(sh) - float(sa)
            if elapsed <= 2580.0:
                pre = margin
            else:
                checks.append(margin)
        if any(abs(v) <= 5 for v in
               ([pre if pre is not None else 0.0] + checks)):
            bits |= 32
        return bits
    except Exception:
        return 0


# box table columns, same order and field widths as the game box score
# (`_box_score_player_line`). (label, key, width, colored, invert) —
# colored cells get the league-leader-gold / worst-red highlight; invert
# flips it for TO/PF where lower is better.
_GOLD, _RED = "goldenrod", "#ff4d4d"
_BOX_COLS = [
    ("MIN", "MIN", 3, False, False), ("PTS", "PTS", 4, True, False),
    ("+/-", "+/-", 5, True, False), ("FGM", "FGM", 4, True, False),
    ("FGA", "FGA", 4, True, False), ("FG%", "FG%", 4, True, False),
    ("3PM", "FG3M", 4, True, False), ("3PA", "FG3A", 4, True, False),
    ("3P%", "3P%", 4, True, False), ("FTM", "FTM", 4, True, False),
    ("FTA", "FTA", 4, True, False), ("FT%", "FT%", 4, True, False),
    ("OR", "OREB", 3, True, False), ("DR", "DREB", 3, True, False),
    ("REB", "REB", 4, True, False), ("AST", "AST", 4, True, False),
    ("STL", "STL", 4, True, False), ("BLK", "BLK", 4, True, False),
    ("TO", "TO", 3, True, True), ("PF", "PF", 3, True, True),
]
_SUM_KEYS = ["MIN", "PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
             "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF"]

# the four season segments, in bit order (bit i = 1 << i). The regular
# season splits at fixed game numbers 27 and 54.
SEG_LABELS = ["1:27", "28:54", "55:82", "Playoffs"]


def _team_game_rows(season: str, team: str,
                    breaks: tuple | None = None) -> list[dict] | None:
    """For one team, one row per cached game: its box-score sums, margin,
    win flag, season-segment bit (thirds cut at the two detected league
    `breaks`, else fixed games 1-27/28-54/55-82; 8 = playoffs) and
    OT/Clutch flags. Per-game granularity lets the filter views be
    INTERSECTED (e.g. Regular AND Clutch). None if no cached games."""
    hist = league_history(season)
    tg = hist[hist["TEAM_ABBREVIATION"] == team].sort_values("GAME_DATE")
    tg = tg[[client.has_cached_play_by_play(g) for g in tg["GAME_ID"]]]
    if tg.empty:
        return None
    ids = tg["GAME_ID"].astype(str)
    reg = tg[ids.str.startswith("002")]
    ply = tg[ids.str.startswith("004")]

    def _sb(k, g):
        if breaks:
            d = pd.Timestamp(g["GAME_DATE"]).normalize()
            return 1 if d <= breaks[0] else 2 if d <= breaks[1] else 4
        return 1 if k < 27 else 2 if k < 54 else 4
    tagged = ([(g, _sb(k, g)) for k, (_, g) in enumerate(reg.iterrows())]
              + [(g, 8) for _, g in ply.iterrows()])
    rows = []
    for g, sb in tagged:
        box = compute_official_box_score_for_game(g["GAME_ID"], team)
        b = box[(box["teamTricode"] == team) & (box["MIN"] > 0)]
        diff = float(g["PTS"] - g["OPP_PTS"])
        bits = _game_ot_clutch(g["GAME_ID"])
        rows.append({"sums": {k: float(b[k].sum()) for k in _SUM_KEYS},
                     "margin": diff, "win": diff > 0, "seg": sb,
                     "home": "vs." in str(g["MATCHUP"]),
                     "ot": bool(bits & 16), "clutch": bool(bits & 32)})
    return rows


def _avg_rows(rows: list[dict], segm: int, ty: str) -> dict | None:
    """Per-game averages over the games matching a view: season-segment
    mask `segm` (1/2/4/8 bits; 7 = Regular, 15 = All) intersected with
    the game type `ty` — "a" all, "o" OT games, "c" Clutch games. None
    when no game matches."""
    sel = [r for r in rows
           if (r["seg"] & segm)
           and (ty == "a" or (ty == "o" and r["ot"])
                or (ty == "c" and r["clutch"])
                or (ty == "w" and r["win"])
                or (ty == "l" and not r["win"])
                or (ty == "h" and r.get("home"))
                or (ty == "v" and not r.get("home")))]
    if not sel:
        return None
    n = len(sel)
    S = {k: sum(r["sums"][k] for r in sel) for k in _SUM_KEYS}
    margin = sum(r["margin"] for r in sel)
    wins = sum(1 for r in sel if r["win"])
    a = {k: S[k] / n for k in _SUM_KEYS}
    a["G"], a["W"], a["L"] = n, wins, n - wins
    _2pm, _2pa = S["FGM"] - S["FG3M"], S["FGA"] - S["FG3A"]
    a["FG%"] = 100 * S["FGM"] / S["FGA"] if S["FGA"] else 0.0
    a["2P%"] = 100 * _2pm / _2pa if _2pa else 0.0
    a["3P%"] = 100 * S["FG3M"] / S["FG3A"] if S["FG3A"] else 0.0
    a["FT%"] = 100 * S["FTM"] / S["FTA"] if S["FTA"] else 0.0
    a["+/-"] = margin / n
    a["FL"], a["TOV"], a["DR"], a["OR"] = a["PF"], a["TO"], a["DREB"], a["OREB"]
    a["3PM"], a["3PA"] = a["FG3M"], a["FG3A"]
    a["2PM"], a["2PA"] = _2pm / n, _2pa / n
    return a


def _dim_hex(hexcol: str, cap: int = 215) -> str:
    """Scale a hex colour down so its brightest channel is at most `cap`,
    keeping the hue — tones a pure-white tricode (BKN) off full white
    without touching the already-muted team colours."""
    h = hexcol.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    m = max(r, g, b)
    if m <= cap:
        return hexcol
    f = cap / m
    return f"#{int(r * f):02X}{int(g * f):02X}{int(b * f):02X}"


def plot_nba_season_2d_html(season: str, output_path: Path) -> Path:
    import html as _html

    teams = sorted(league_history(season)["TEAM_ABBREVIATION"].unique())
    # the two detected league breaks (Cup final week / All-Star break)
    # cut every team's regular season into its own real thirds
    _breaks = _season_break_dates(season)
    seg_data = {}
    for t in teams:
        s = _team_game_rows(season, t, _breaks)
        if s:
            seg_data[t] = s
    # ---- COMBINABLE views: three independent filter groups ----
    # season segment (radio, one of): thirds 1/2/4, Regular 7, Playoffs
    #   8, All 15
    # game type (none-or-one): "a" all games, "o" OT, "c" Clutch
    # conference (none-or-one): "a" all teams, "e" East, "w" West
    # The DATA differs only per (segment, type) — 18 combos, averaged
    # from the per-game rows; the conference just picks which TEAMS show.
    # Every element for (combo, team) carries cmb-{seg}{ty}a plus
    # cmb-{seg}{ty}{team's conference}, so the 54 selectable states reuse
    # the same nodes.
    SEGS = [1, 2, 4, 7, 8, 15]
    TYPES = ["a", "o", "c", "w", "l", "h", "v"]
    CONFS = ["a", "e", "w"]
    MASKS = [(sg, ty) for sg in SEGS for ty in TYPES]   # the 18 data combos
    avgs = {m: {t: _avg_rows(seg_data[t], m[0], m[1]) for t in seg_data}
            for m in MASKS}
    _ALL = (15, "a")   # the full-season view drives order and lane scales

    def _conf(t):
        return "e" if t in _TEAM_EAST else "w"

    def _cmb_cls(m, t):
        return f"cmb-{m[0]}{m[1]}a cmb-{m[0]}{m[1]}{_conf(t)}"
    codes = sorted(seg_data, key=lambda t: -avgs[_ALL][t]["+/-"])
    N = len(codes)

    def _team_href(t):
        href = f"team_{t.lower()}.html"
        return href if (output_path.parent / href).exists() else None

    order = ["FL", "TOV", "BLK", "STL", "AST", "DR", "FTA",
             "3PA", "2PA", "+/-", "G"]
    COMBO = {"FTA": ("FTM", "FT%"), "3PA": ("3PM", "3P%"),
             "2PA": ("2PM", "2P%"), "DR": ("OR", None)}
    n = len(order)

    # every event value in the value column sorts independently: a
    # shooting trio's %/attempts/makes and the DR/OR pair each get their
    # own sort (17 in all), instead of one sort per lane. sort_stats lists
    # (lane index, stat key) in the value column's top-to-bottom stacking
    # order; each maps to a radio srt-{s}. sort_dy is that stat's row
    # offset inside the lane (px, matching where its value/label sits).
    sort_stats: list[tuple[int, str]] = []
    sort_dy: dict[tuple[int, str], int] = {}
    for _i, _k in enumerate(order):
        if _k in COMBO:
            _mk2, _pct2 = COMBO[_k]
            _rows = ([(_pct2, -32)] if _pct2 else []) + [(_k, -16), (_mk2, 0)]
        elif _k == "G":
            _rows = [("G", -32), ("W", -16), ("L", 0)]
        else:
            _rows = [(_k, 0)]
        for _key, _d in _rows:
            sort_dy[(_i, _key)] = _d
            sort_stats.append((_i, _key))
    sort_idx = {(i, k): s for s, (i, k) in enumerate(sort_stats)}
    _PM_S = sort_idx[(order.index("+/-"), "+/-")]
    lane_sorts: dict[int, list[int]] = {}
    for _s, (_i, _k) in enumerate(sort_stats):
        lane_sorts.setdefault(_i, []).append(_s)
    hex_by_kind = {
        "+/-": "#B0B0B0",   # soft grey, matching the team page's +/-
        # games grey, wins green, losses red (the games line's colours)
        "G": "#B8BEC7", "W": "#2ecc55", "L": "#ff5252",
        # each shooting trio spans one hue in three well-separated steps
        # (dark attempts, vivid makes, near-white %): the family reads as
        # a group, the members stay clearly distinguishable
        "2PM": "#FF9F1C", "2PA": "#A65605", "2P%": "#FFE1AE",
        "3PM": "#FF4FA3", "3PA": "#99175E", "3P%": "#FFC6E3",
        "FTA": "#0C6B5B", "FTM": "#22D3B8", "FT%": "#B5F2E6",
        "DR": "#3D7BFF", "OR": "#9CC2FF", "AST": "#6FD9F2", "STL": "#2FD98C",
        "BLK": "#9E6FFF", "TOV": "#C23B3B", "FL": "#FF5555",
    }

    def all_vals(kind):
        return [avgs[m][t][kind] for m in MASKS for t in codes
                if avgs[m][t] is not None]

    # geometry (mirrors the team page). GROUP_GAP = 40: the gap between
    # the multi-member label groups (DR/OR, FT, 3P, 2P) sits a touch
    # wider (GROUP_GAP + 2.5) than the ungrouped labels' 36.5px pitch
    LANE_H, LANE_GAP, TIGHT_GAP, GROUP_GAP = 46, 6, 2, 40
    STAT_H = LANE_H * 0.75
    heights = [LANE_H if k == "+/-" else STAT_H for k in order]
    is_stat = [k != "+/-" for k in order]
    tops, y, gap = [], 0, LANE_GAP
    for idx, h in enumerate(heights):
        tops.append(y)
        gap = TIGHT_GAP if is_stat[idx] and idx + 1 < n and is_stat[idx + 1] else LANE_GAP
        # DR sits closer to AST than the other combo groups, but 16px
        # lower than the tight stat spacing so its two-row label block's
        # top row keeps the uniform 36.5px label pitch (its labels sit
        # 16px higher inside the lane than a single lane's label)
        if idx + 1 < n and order[idx + 1] == "DR":
            gap = TIGHT_GAP + 16
        elif idx + 1 < n and order[idx + 1] in COMBO:
            gap = GROUP_GAP
        y += h + gap
    PLOT_H = y - gap
    # plot width is set so the label/value columns' RIGHT edge lands on
    # the box table's right edge: the table text spans (17 + column
    # widths) monospace chars from the shared 26px left edge (1ch =
    # 0.60205em of the table's 0.0154*min(100vw,1200px) font), and the
    # value column ends 68px (30px offset + 38px value box) right of
    # the plot
    _tbl_chars = 17 + sum(w for _, _, w, _, _ in _BOX_COLS)
    PW = (f"calc({_tbl_chars * 0.60205 * 0.0154:.5f}"
          " * var(--vw) - 68px)")
    # the box table's full text width — the title centres on this span
    TW = (f"calc({_tbl_chars * 0.60205 * 0.0154:.5f}"
          " * var(--vw))")
    x_frac = [(j + 0.5) / N for j in range(N)]
    hw = 0.135 / N

    def _pulse_edges(fx):
        c = min(max(fx, hw), 1.0 - hw)
        return (c - hw) * 100, (c + hw) * 100

    def nice_scale(vmin, vmax, nint=6):
        # Heckbert's auto-axis (Graphics Gems, the locator matplotlib
        # approximates): a 1/2/2.5/5 x 10^k step sized for ~nint
        # intervals, limits snapped to the nearest step — the scale
        # hugs the data range instead of padding around it
        span = max(vmax - vmin, 1e-9)
        raw = span / max(nint, 1)
        exp = math.floor(math.log10(raw))
        f = raw / 10 ** exp
        nf = 1 if f <= 1 else 2 if f <= 2 else 2.5 if f <= 2.5 else \
            5 if f <= 5 else 10
        step = nf * 10 ** exp
        lo = math.floor(vmin / step) * step
        hi = max(math.ceil(vmax / step) * step, lo + step)
        return lo, hi, step

    sel_idx = [i for i, k in enumerate(order) if k != "+/-"]

    # PER-COMBO lane scales: every filter view's bars are their own
    # nodes, so each (lane, combo) auto-fits its own data range and the
    # bars always use the full lane height — no cross-combo padding,
    # and no clipping either, since each view is scaled to itself
    def mask_vals(kind, m):
        return [avgs[m][t][kind] for t in codes if avgs[m][t] is not None]

    lane_geo = {}
    for kind in order:
        for m in MASKS:
            if not mask_vals(kind if kind not in COMBO else COMBO[kind][0], m):
                lane_geo[(kind, m)] = (0.0, 1.0, 1.0, 1, None)
                continue
            if kind == "+/-":
                vmax = max((abs(v) for v in mask_vals("+/-", m)),
                           default=1.0) or 1.0
                lane_geo[(kind, m)] = (0.0, vmax, vmax, 1, None)
            elif kind == "DR":
                # stacked DR+OR bars, auto-ranged: the scale floors at
                # the smallest DR (both stack segments stay visible)
                # and tops at the largest DR+OR total
                lo, hi, step = nice_scale(min(mask_vals("DR", m)),
                                          max(mask_vals("REB", m)))
                lane_geo[(kind, m)] = (lo, hi, hi - lo, step, None)
            elif kind in COMBO:
                _mk, _pct = COMBO[kind]
                # the trio shares one scale: makes' min to attempts' max
                lo, hi, step = nice_scale(min(mask_vals(_mk, m)),
                                          max(mask_vals(kind, m)))
                plo, phi, _ = (nice_scale(min(mask_vals(_pct, m)),
                                          max(mask_vals(_pct, m)))
                               if _pct else (0, 1, 1))
                lane_geo[(kind, m)] = (lo, hi, hi - lo, step,
                                       (plo, phi) if _pct else None)
            elif kind == "G":
                # games, wins and losses share a zero-floored scale
                lo, hi, step = nice_scale(0, max(mask_vals("G", m)))
                lane_geo[(kind, m)] = (lo, hi, hi - lo, step, None)
            else:
                lo, hi, step = nice_scale(min(mask_vals(kind, m)),
                                          max(mask_vals(kind, m)))
                lane_geo[(kind, m)] = (lo, hi, hi - lo, step, None)

    # ---- click-to-sort: clicking a main lane's value in the right-hand
    # column re-sorts the 30 team columns by that stat (full-season
    # values, best first — FL/TOV invert since lower is better there).
    # Pure CSS: a sort radio per lane sets per-team x CSS variables
    # (--x{j} = team j's column center), and every team-positioned
    # element reads its var instead of a baked left. "+/-" IS the
    # default order, so its radio restores the page's normal sort. ----
    _LOWER_BETTER = {"FL", "TOV", "L"}
    # the filters apply BEFORE the sort: each (data combo, conference)
    # gets its own ranking from that view's averages. Teams outside the
    # view (no games, or the other conference) sort after everyone,
    # keeping their resting order.
    sort_pos = {}   # (combo, conf, stat key) -> {team: column position}
    for m in MASKS:
        for cf in CONFS:
            for _i, key in sort_stats:
                def _key(t, _m=m, _cf=cf, _s=key):
                    a = avgs[_m][t]
                    if a is None or (_cf != "a" and _conf(t) != _cf):
                        return (1, codes.index(t))
                    return (0, a[_s] if _s in _LOWER_BETTER else -a[_s])
                ranked = sorted(codes, key=_key)
                sort_pos[(m, cf, key)] = {t: p for p, t in enumerate(ranked)}
    # Sort is the page's INITIAL (and only) mode — gsort starts checked;
    # the old resting page's member-sort/spotlight radios are gone
    srt_radios = ('<input type="radio" class="srt" name="pg" id="pg-g"'
                  ' checked>'
                  '<input type="radio" class="srt" name="pg" id="pg-p">'
                  '<input type="radio" class="srt" name="pg" id="pg-u">'
                  '<input type="radio" class="srt" name="pg" id="pg-t">')
    srt_radios += ('<input type="radio" class="srt" name="bx" id="bx-10"'
                  ' checked>'
                  '<input type="radio" class="srt" name="bx" id="bx-25">'
                  '<input type="radio" class="srt" name="bx" id="bx-a">'
                   '<input type="radio" class="srt" name="bx" id="bx-h">'
                  '<input type="checkbox" class="srt" id="gsort" checked>'
                  '<input type="radio" class="srt" name="vw" id="vw-1">'
                  '<input type="radio" class="srt" name="vw" id="vw-3" checked>'
                  '<input type="radio" class="srt" name="vw" id="vw-a">'
                  )
    # Sort mode's per-lane collapse state: clicking a lane's bar area
    # checks it (lane content hides), clicking the lane's badge
    # unchecks. The page STARTS with every lane closed except +/-,
    # which can't be closed at all (its click controls are omitted).
    # The lc boxes live in their OWN form whose reset input is the
    # "Close" control: resetting restores every default = all closed,
    # without touching the filters outside the form.
    # lall is the ALL mode flag: while checked, the lc reading INVERTS
    # (unchecked = closed) — so the instant ALL flips it, every lane
    # opens, and the usual bar/badge clicks keep toggling lanes one by
    # one. It resets with the form, so Close restores the landing state.
    srt_radios += ("<form>" + "".join(
        f'<input type="checkbox" class="srt" id="lc-{i}">' for i in range(n))
        + '<input type="checkbox" class="srt" id="lall">'
        + "".join(
            f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-n" checked>'
            + "".join(
                f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-u{mi}">'
                f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-d{mi}">'
                for mi in range(
                    3 if order[i] == "G" else
                    2 if order[i] == "DR" else
                    (3 if COMBO[order[i]][1] else 2)
                    if order[i] in COMBO else 1))
            + f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-n" checked>'
            f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-l">'
            f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-r">'
            for i in range(n))
        + '<input type="reset" class="srt" id="lclose"></form>')

    def _xvars(pos_of):
        return "".join(f"--x{j}:{(pos_of[codes[j]] + 0.5) / N * 100:.3f}%;"
                       for j in range(N))

    # default vars on .wrap (the DOM/+/- order); the sort view's
    # per-lane rules override them lane by lane
    sort_css = ".wrap{" + _xvars({t: j for j, t in enumerate(codes)}) + "}"

    def _gate(m, cf):
        # the three filter groups' combined state selector
        return (f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
                f":has(#cf-{cf}:checked)")

    # ---- Rank overlay: per mask and stat, each team's league rank
    # (competition ranking — ties share; FL/TOV rank 1 = fewest). The
    # Rank button overlays these on the value column. ----
    _rank_keys = set(order) | {"REB", "W", "L"}
    for _k, (_mk, _pct) in COMBO.items():
        _rank_keys.add(_mk)
        if _pct:
            _rank_keys.add(_pct)
    ranks = {}
    for m in MASKS:
        am = avgs[m]
        for cf in CONFS:
            ranks[(m, cf)] = {}
            for k in _rank_keys:
                vals = {t: am[t][k] for t in codes
                        if am[t] is not None
                        and (cf == "a" or _conf(t) == cf)}
                ranks[(m, cf)][k] = {
                    t: 1 + sum(1 for vu in vals.values()
                               if (vu < v if k in _LOWER_BETTER else vu > v))
                    for t, v in vals.items()}

    # ---- Sort mode geometry (used inside the lanes loop and by the
    # gsort CSS below): bars occupy 50% of the column pitch (scaleX);
    # the vertical tricode under each bar fills exactly that width —
    # rotated text at line-height 1 spans its font-size, so the font
    # tracks the bar width through PW's responsive calc(). The
    # inter-lane padding fits the tallest responsive tricode. ----
    _BARW = 0.50 / N
    _BARSX = _BARW / (2 * hw)
    # the tricode renders a third larger than the bar width, so the
    # names overhang the bars a bit
    _LTXW = _BARW * 1.35 * 0.75
    _LTX_FS = (f"calc({_tbl_chars * 0.60205 * 0.0154 * _LTXW:.6f}"
               f" * var(--vw) - {68 * _LTXW:.3f}px)")
    _LTX_MAX = (_tbl_chars * 0.60205 * 0.0154 * 1200 - 68) * _LTXW
    _PAD2 = int(3 * _LTX_MAX + 8)
    # the flag pole's head above each lane (two flags plus a pad);
    # below, the pole and its rank flags resume AFTER the vertical
    # team name: _TRB is the tricode row's tallest extent plus a pad,
    # the n flags ladder from there, and the label line seats below
    # the flag zone (per-lane, set with the lane geometry)
    _EXTT = 32
    _TRB = 1.9 * _LTX_MAX + 6   # static worst case, sizes the pads
    # the name band's true (responsive) bottom: the flags start here
    _TRE = (f"{3 - 1.9 * 68 * _LTXW:.2f}px + "
            f"{1.9 * _tbl_chars * 0.60205 * 0.0154 * _LTXW:.6f}"
            "*var(--vw)")
    _LBL = _TRB + 21   # base-rule fallback; per-lane overrides win

    _HELV = {" ": 278, "%": 889, "+": 584, "/": 278, "-": 333, ":": 278,
             "0": 556, "1": 556, "2": 556, "3": 556, "4": 556, "5": 556,
             "6": 556, "7": 556, "8": 556, "9": 556,
             "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611,
             "G": 778, "H": 722, "I": 278, "J": 500, "K": 667, "L": 556,
             "M": 833, "N": 722, "O": 778, "P": 667, "Q": 778, "R": 722,
             "S": 667, "T": 611, "U": 722, "V": 667, "W": 944, "X": 667,
             "Y": 667, "Z": 611}

    def _text_px(txt, size=17.1):
        return sum(_HELV.get(ch, 600) for ch in txt) / 1000 * size

    # ---- lanes / bars (every mask, tagged .cmb-{m}) ----
    lanes = [f'<div class="lane" style="top:{tops[0]}px;'
             f'height:{tops[max(i for i in range(n) if is_stat[i])] + STAT_H - tops[0]}px;"></div>']
    ticks, grow_css = [], []
    pnames = []
    var_blocks = {m: [] for m in MASKS}
    content_css = []
    _DN2 = {"FL": "PF", "TOV": "TO", "G": "#"}
    for i, kind in enumerate(order):
        h, top = heights[i], tops[i]
        fills = []
        # the lane's members in value-column (label-stack) order — drives
        # the Sort-mode hover chips, the line's start, and the lane badge
        if kind == "+/-":
            _vrows = ["+/-"]
        elif kind == "DR":
            _vrows = ["DR", "OR"]
        elif kind == "G":
            _vrows = ["G", "W", "L"]
        elif kind in COMBO:
            _vmk, _vpct = COMBO[kind]
            _vrows = ([_vpct] if _vpct else []) + [kind, _vmk]
        else:
            _vrows = [kind]
        for m in MASKS:
            am = avgs[m]
            lo, hi, rng, step, pct_scale = lane_geo[(kind, m)]

            def val(t, k):
                return am[t][k] if am[t] is not None else None

            # the trio's bars overlap at each x, so the z-stack follows
            # VALUE: the taller a bar renders, the further back it sits
            def _z(frac):
                return 100 - round(max(0.0, min(1.0, frac)) * 98)
            # this view's numbers go into its variable block; the lane
            # keeps ONE element set below that reads whichever block
            # the checked filters activate
            _vb = var_blocks[m]
            if kind == "+/-":
                for j, t in enumerate(codes):
                    v = val(t, "+/-")
                    if v is None:
                        _vb.append(f"--q{i}m0x{j}:100%;")
                        continue
                    _vb.append(
                        f"--q{i}m0x{j}:{(1 - abs(v) / hi) * 100:.2f}%;"
                        f"--qp{j}:"
                        f"{'#2ecc55' if v >= 0 else '#e04545'};")
            elif kind == "DR":
                for j, t in enumerate(codes):
                    vd, vo = val(t, "DR"), val(t, "OR")
                    if vd is None:
                        _vb.append(f"--q{i}m0x{j}:100%;"
                                   f"--q{i}m1x{j}:100%;"
                                   f"--qb{i}m1x{j}:0%;")
                        continue
                    _vb.append(
                        f"--q{i}m0x{j}:"
                        f"{(1 - (vd - lo) / rng) * 100:.2f}%;"
                        f"--q{i}m1x{j}:"
                        f"{(1 - (vd + vo - lo) / rng) * 100:.2f}%;"
                        f"--qb{i}m1x{j}:"
                        f"{(vd - lo) / rng * 100:.2f}%;")
            elif kind == "G":
                for j, t in enumerate(codes):
                    vg = val(t, "G")
                    if vg is None:
                        _vb.append(f"--q{i}m0x{j}:100%;"
                                   f"--q{i}m1x{j}:100%;"
                                   f"--q{i}m2x{j}:100%;")
                        continue
                    for _mi, v in ((0, vg), (1, val(t, "W")),
                                   (2, val(t, "L"))):
                        frac = (v - lo) / rng
                        _vb.append(
                            f"--q{i}m{_mi}x{j}:"
                            f"{(1 - frac) * 100:.2f}%;"
                            f"--qz{i}m{_mi}x{j}:{_z(frac)};")
            elif kind in COMBO:
                _mk, _pct = COMBO[kind]
                for j, t in enumerate(codes):
                    va, vm = val(t, kind), val(t, _mk)
                    if va is None:
                        _vb.append(
                            f"--q{i}m0x{j}:100%;--q{i}m1x{j}:100%;"
                            + (f"--q{i}m2x{j}:100%;" if _pct else ""))
                        continue
                    for _mi, v in ((0, va), (1, vm)):
                        frac = (v - lo) / rng
                        _vb.append(
                            f"--q{i}m{_mi}x{j}:"
                            f"{(1 - frac) * 100:.2f}%;"
                            f"--qz{i}m{_mi}x{j}:{_z(frac)};")
                    if _pct is not None:
                        plo, phi = pct_scale
                        v = val(t, _pct)
                        if v is None:
                            _vb.append(f"--q{i}m2x{j}:100%;")
                        else:
                            frac = (v - plo) / (phi - plo)
                            _vb.append(
                                f"--q{i}m2x{j}:"
                                f"{(1 - frac) * 100:.2f}%;"
                                f"--qz{i}m2x{j}:{_z(frac)};")
            else:
                for j, t in enumerate(codes):
                    v = val(t, kind)
                    _vb.append(
                        f"--q{i}m0x{j}:100%;" if v is None else
                        f"--q{i}m0x{j}:"
                        f"{(1 - (v - lo) / rng) * 100:.2f}%;")
            # the hover chips' texts ride the same block (ranks are
            # league-wide)
            _rka = ranks[(m, "a")]
            for j, t in enumerate(codes):
                for _r, _k in enumerate(_vrows):
                    if am[t] is None:
                        _vb.append(f'--qv{i}m{_r}x{j}:"";'
                                   f'--qr{i}m{_r}x{j}:"";')
                        continue
                    _v = am[t][_k]
                    _vt = (f"{_v:+.1f}" if _k == "+/-"
                           else f"{_v:.0f}")
                    rk = _rka[_k].get(t)
                    _vb.append(
                        f'--qv{i}m{_r}x{j}:"{_vt}";'
                        f'--qr{i}m{_r}x{j}:'
                        f'"{"" if rk is None else rk}";')

        # ---- the lane's single element set: bar tops, z-orders and
        # chip texts all come from the active view's variable block —
        # switching views swaps one declaration block instead of
        # re-displaying thousands of nodes ----
        bar_geo = (f"left:calc(var(--x{{j}}) - {hw * 100:.2f}%);"
                   f"width:{2 * hw * 100:.2f}%;")
        _half = (f"left:calc(var(--x{{j}}) - {hw * 50:.2f}%);"
                 f"width:{hw * 100:.2f}%;")
        for j, t in enumerate(codes):
            _cf2 = f"bcf-{_conf(t)}"
            if kind == "+/-":
                fills.append(
                    f'<div class="fl bar {_cf2}" '
                    f'style="{bar_geo.format(j=j)}'
                    f'top:var(--q{i}m0x{j},100%);bottom:0;'
                    f'background:var(--qp{j},#2ecc55);"></div>')
            elif kind == "DR":
                fills.append(
                    f'<div class="fl bar {_cf2}" '
                    f'style="{bar_geo.format(j=j)}'
                    f'top:var(--q{i}m0x{j},100%);bottom:0;'
                    f'background:{hex_by_kind["DR"]};"></div>'
                    f'<div class="fl bar {_cf2}" '
                    f'style="{bar_geo.format(j=j)}'
                    f'top:var(--q{i}m1x{j},100%);'
                    f'bottom:var(--qb{i}m1x{j},0%);'
                    f'background:{hex_by_kind["OR"]};"></div>')
            elif kind == "G":
                for _mi, _c in ((0, hex_by_kind["G"]),
                                (1, hex_by_kind["W"]),
                                (2, hex_by_kind["L"])):
                    fills.append(
                        f'<div class="fl bar {_cf2}" '
                        f'style="{bar_geo.format(j=j)}'
                        f'top:var(--q{i}m{_mi}x{j},100%);bottom:0;'
                        f'z-index:var(--qz{i}m{_mi}x{j},1);'
                        f'background:{_c};"></div>')
            elif kind in COMBO:
                _mk, _pct = COMBO[kind]
                for _mi, _c in ((0, hex_by_kind[kind]),
                                (1, hex_by_kind[_mk])):
                    fills.append(
                        f'<div class="fl bar {_cf2}" '
                        f'style="{bar_geo.format(j=j)}'
                        f'top:var(--q{i}m{_mi}x{j},100%);bottom:0;'
                        f'z-index:var(--qz{i}m{_mi}x{j},1);'
                        f'background:{_c};"></div>')
                if _pct is not None:
                    fills.append(
                        f'<div class="fl bar {_cf2}" '
                        f'style="{_half.format(j=j)}'
                        f'top:var(--q{i}m2x{j},100%);bottom:0;'
                        f'z-index:var(--qz{i}m2x{j},1);'
                        f'background:{hex_by_kind[_pct]};"></div>')
            else:
                fills.append(
                    f'<div class="fl bar {_cf2}" '
                    f'style="{bar_geo.format(j=j)}'
                    f'top:var(--q{i}m0x{j},100%);bottom:0;'
                    f'background:{hex_by_kind[kind]};"></div>')
            for _r, _k in enumerate(_vrows):
                fills.append(
                    f'<div class="tv lvv lvv-{j} lq{i}m{_r}" '
                    f'style="left:var(--x{j});'
                    f'top:{13 * _r - _EXTT}px;'
                    f'color:{hex_by_kind[_k]};"></div>'
                    f'<div class="tv lrk lrk-{j} lq{i}m{_r}" '
                    f'style="left:var(--x{j});'
                    f'bottom:calc({-13 - 13 * _r}px - ({_TRE}));'
                    f'color:{hex_by_kind[_k]};"></div>')
                content_css.append(
                    f".lane-{i} .lvv-{j}.lq{i}m{_r}::after"
                    f'{{content:var(--qv{i}m{_r}x{j},"");}}'
                    f".lane-{i} .lrk-{j}.lq{i}m{_r}::after"
                    f'{{content:var(--qr{i}m{_r}x{j},"");}}')

        bg = "background:none;" if is_stat[i] else ""
        # Sort mode's per-lane tricode row: lane children read the LANE's
        # own --x{j} overrides, so each lane's codes follow its own order
        for j, t in enumerate(codes):
            _ltc = _dim_hex(_TEAM_BRAND_COLORS.get(t, "#999"))
            _lcls = f"ltx ltx-{j} ltxc-{'e' if t in _TEAM_EAST else 'w'}"
            _lsty = f'style="left:var(--x{j});color:{_ltc};"'
            if kind == "+/-" and _team_href(t):
                # under the +/- lane the tricode is a link to the
                # team's own page (like the resting bottom axis)
                fills.append(f'<a class="{_lcls} ltxa" '
                             f'href="{_team_href(t)}" {_lsty}>{t}</a>')
            else:
                fills.append(f'<div class="{_lcls}" {_lsty}>{t}</div>')
        # Sort mode's hover machinery, per lane so it reads the lane's
        # own order: a dimmed white line segment at each team's column
        # (the segments join up across lanes into the team's trajectory)
        # and a hover cell covering the column plus the tricode row.
        # The value stack rides the line's left side, descending from
        # the lane's top.
        # the cells are hover-only (plot-area clicks do nothing); the
        # LABEL is the open/close toggle. +/- can't be closed: its
        # badge carries no lc target.
        _lfor = f'for="lc-{i}" '
        for j, t in enumerate(codes):
            fills.append(
                f'<div class="ldl ldl-{j}" style="left:var(--x{j});"></div>'
                f'<label class="lwc lwc-{j} lwcc-{"e" if t in _TEAM_EAST else "w"}" '
                f'style="left:calc(var(--x{j}) - {50 / N:.3f}%);'
                f'width:{100 / N:.3f}%;"></label>')
        # the lane's stat name(s) as its badge in the left margin:
        # clicking it CLOSES the open lane, and the parked copy on the
        # top line re-opens it
        fills.append(
            f'<label class="lzl'
            f'{" lzg" if len(_vrows) > 1 else ""}" {_lfor}>'
            + " ".join(f'<span style="color:{hex_by_kind[_k]};">'
                       f'{_DN2.get(_k, _k)}</span>'
                       for _k in _vrows) + "</label>")
        pnames.append(
            f'<label class="tg pnm pnm-{i}" for="lc-{i}">'
            + " ".join(f'<span style="color:{hex_by_kind[_k]};">'
                       f'{_DN2.get(_k, _k)}</span>'
                       for _k in _vrows) + "</label>")
        _cum = 0.0
        for _mi, _mk in enumerate(_vrows):
            _cum += _text_px(_DN2.get(_mk, _mk), 14)
            _fx = f"calc(8px + {_cum + _mi * 29.9 + 2:.1f}*var(--u))"
            _cm = f'style="color:{hex_by_kind[_mk]};left:{_fx};"'
            fills.append(
                f'<label class="lcr lcr-n{_mi}" for="ls-{i}-u{_mi}" '
                f'{_cm}>\u2191\u2193</label>'
                f'<label class="lcr lcr-u{_mi}" for="ls-{i}-d{_mi}" '
                f'{_cm}>\u2191</label>'
                f'<label class="lcr lcr-d{_mi}" for="ls-{i}-n" '
                f'{_cm}>\u2193</label>')
        if kind != "+/-":
            _px = (f"calc(8px + "
                   f"{_cum + (len(_vrows) - 1) * 29.9 + 32:.1f}*var(--u))")
            _cp = f'style="color:{hex_by_kind[kind]};left:{_px};"'
            fills.append(
                f'<label class="lcr pcr pcr-n" for="pk-{i}-l" {_cp}>'
                "\u2190\u2192</label>"
                f'<label class="lcr pcr pcr-l" for="pk-{i}-r" {_cp}>'
                "\u2190</label>"
                f'<label class="lcr pcr pcr-r" for="pk-{i}-n" {_cp}>'
                "\u2192</label>")
        _cxx = (f"calc(8px + "
                f"{_cum + (len(_vrows) - 1) * 29.9 + 64:.1f}"
                "*var(--u))")
        fills.append(
            f'<label class="lcx" for="lc-{i}" '
            f'style="left:{_cxx};color:{hex_by_kind[kind]};">'
            "\u2715</label>")
        lanes.append(f'<div class="lane lane-{i}" style="top:{top}px;height:{h}px;{bg}">'
                     + "".join(fills) + "</div>")

    # ---- Sort mode (the button under Rank): EVERY lane sorts by its
    # label group's FIRST member, all at once. The lanes open to 2x with
    # vertical padding (a taller plot layout), each lane's columns
    # re-order via LANE-SCOPED --x{j} overrides (bars, rank chips and
    # the per-lane tricode row all inherit them), and the labels ride
    # down to their lane's new baseline. A second click restores the
    # short layout. Respects the active filter combination. ----
    # every sorted lane opens to the SAME height — the +/- lane matches
    # the stat lanes instead of keeping its taller resting height.
    # A top label line (_TS) is reserved above the lanes: collapsed
    # lanes park their labels there.
    # team-page lane geometry: one 13px character of height per label
    # member (singles 32, DR/OR 45, shooting trios 58); the pole rises
    # _EXTT above the lane with the value flags at its tip, and its
    # tail ends flush with the last rank flag below. The pad stacks
    # the tricode row, the label line under it, and the next pole's
    # head.
    _nmem = [3 if k == "G" else 2 if k == "DR" else
             ((3 if COMBO[k][1] else 2) if k in COMBO else 1)
             for k in order]
    _LH2 = [13 * _m + 19 for _m in _nmem]
    # pad: tricode row, the flag zone (13 a member), the label line
    # seated 8px under it, then the next pole's head
    _PAD2B = [round(_TRB + 13 * _m + 8 + _EXTT)
              for _m in _nmem]
    _TS = 34   # the first pole's head
    _t2, _T2 = float(_TS), []
    for i in range(n):
        _T2.append(_t2)
        _t2 += _LH2[i] + _PAD2B[i]
    _H2 = _t2
    _GS = ".st:has(#gsort:checked)"
    # collapsing a lane reclaims its vertical space IN FULL: every
    # lane's top (and the plot height) subtracts the whole slots of the
    # collapsed lanes above it via per-lane --c{i} flags (0/1), so any
    # combination of collapsed lanes lays out right. The collapsed
    # lane's label parks on the top label line instead.
    _BANDS = [_LH2[i] + _PAD2B[i] for i in range(n)]

    def _wh(w, k):
        s_ = min(k, n - w)
        # crop the next plot's chip zone off the window bottom (its
        # hover chips reach _EXTT above its lane top)
        _crop = _EXTT + 2 if s_ + w < n else 22
        return _TS + sum(_BANDS[s_:s_ + w]) - _crop

    def _kf(w):
        # snap position k sizes the window to exactly the w plots in
        # view; the pan itself is the linear ppan below, whose live
        # endpoint keeps it exact at every rest even with closures
        hgt = []
        _last = -1.0
        whk = 0
        for k in range(n - w + 1):
            S_k = sum(_BANDS[:k])
            whk = _wh(w, k)
            rng = _H2 - whk
            pct = 0.0 if k == 0 else min(100.0, 100.0 * S_k / rng)
            if pct <= _last:
                pct = _last + 0.001
            _last = pct
            hgt.append(f"{pct:.3f}%{{--wh:{whk:.0f}px;}}")
        hgt.append(f"100%{{--wh:{whk:.0f}px;}}")
        return ("@keyframes phgt" + str(w) + "{" + "".join(hgt) + "}")
    _kf_css = (_kf(1) + _kf(3)
               + "@keyframes ppan{from{transform:translateY(0px);}"
               "to{transform:translateY("
               "calc(0px - var(--rng,0px)));}}")
    gsort_css = (
        '@property --wh{syntax:"<length>";inherits:true;'
        "initial-value:0px;}"
        + _GS + " ~ .wrap .plot{overflow:hidden;"
        "contain:layout paint;height:var(--wh,0px);}"
        + ".pcar{position:absolute;left:0;right:0;top:0;height:100%;"
        "animation:ppan linear both;animation-timeline:--psb;"
        "will-change:transform;}"
        + _GS + " ~ .wrap{timeline-scope:--psb;"
        f"--rng:max(0px,calc({_H2:.0f}px"
        + "".join(f" - var(--c{j},0)*{_BANDS[j]:.0f}px"
                  for j in range(n))
        + " - var(--wh,0px)));"
        "animation:phgt3 linear both;animation-timeline:--psb;}"
        + _kf_css
        + "".join(
            f".st:has(#vw-{v}:checked) ~ .wrap"
            f"{{animation-name:phgt{v};}}"
            for v in ("1", "3"))
        + ".st:has(#vw-a:checked) ~ .wrap .pcar{animation:none;}"
        + ".st:has(#vw-a:checked) ~ .wrap"
        "{animation:none;"
        f"--wh:calc({_H2:.0f}px"
        + "".join(f" - var(--c{j},0)*{_BANDS[j]:.0f}px"
                  for j in range(n)) + ");}"
        + "".join(
            f".st:has(#vw-{v}:checked) ~ .wrap .tg-vw-{v}"
            "{color:#ddd;background:rgba(255,255,255,.16);}"
            for v in ("1", "3", "a"))
        + ".st:has(#vw-a:checked) ~ .wrap .sroll{display:none;}"
        + (_GS + ":has(#lall:not(:checked))"
           + "".join(f":has(#lc-{i}:checked)" for i in range(n))
           + " ~ .wrap .plmsg,"
           + _GS + ":has(#lall:checked)"
           + "".join(f":not(:has(#lc-{i}:checked))" for i in range(n))
           + " ~ .wrap .plmsg{display:block;}")
        + (_GS + ":has(#lall:not(:checked))"
           + "".join(f":has(#lc-{i}:checked)" for i in range(n))
           + " ~ .wrap .plot,"
           + _GS + ":has(#lall:checked)"
           + "".join(f":not(:has(#lc-{i}:checked))" for i in range(n))
           + " ~ .wrap{--wh:140px!important;"
           "animation:none!important;}")
        + ".plmsg{display:none;position:absolute;left:0;right:0;"
        "text-align:center;color:#888;z-index:50;"
        "font-size:calc(var(--vw)*0.0462);"
        "top:calc(var(--vw)*0.0231);}"
        + "".join(
            f"{_GS}:has(#lall:not(:checked)):has(#lc-{i}:checked)"
            f" ~ .wrap{{--c{i}:1;}}"
            f"{_GS}:has(#lall:checked):has(#lc-{i}:not(:checked))"
            f" ~ .wrap{{--c{i}:1;}}"
            f"{_GS}:has(#lall:not(:checked)):has(#lc-{i}:checked)"
            f" ~ .wrap .lane-{i},"
            f"{_GS}:has(#lall:checked):has(#lc-{i}:not(:checked))"
            f" ~ .wrap .lane-{i}"
            "{display:none!important;}"
            for i in range(n))

        + _GS + " ~ .wrap .lane .ltx{display:block;}"
        + _GS + " ~ .wrap .lane .lwc{display:block;}"
        + _GS + " ~ .wrap .lane .lzl{display:block;"
        "pointer-events:auto;cursor:pointer;}"
        + _GS + f" ~ .wrap .lane .bar{{transform:scaleX({_BARSX:.4f});}}")
    # hovering a team's column (or its tricode) in ANY lane lights the
    # team up everywhere: line segments at its position in every lane,
    # bold tricodes, and its box score row tinted in the TEAM's color
    # hovering a plot column scrolls the box score to that team: the
    # blanket rule withdraws every row's snap point, the per-team rule
    # below restores only the hovered team's — and a mandatory snap
    # container must re-snap to the one snap position left. On unhover
    # every row snaps again and the box rests where it is.
    gsort_css += (".wrap:has(.lwc:hover) ~ .bxwrap .bxs .br"
                  "{scroll-snap-align:none;}")
    for j in range(N):
        gsort_css += (
            f".wrap:has(.lwc-{j}:hover) .ldl-{j}{{display:block;}}"
            f".wrap:has(.lwc-{j}:hover) .ltx-{j}"
            "{font-weight:bold;}"
            f".wrap:has(.lwc-{j}:hover) ~ .bxwrap .br-{j}"
            f"{{background:{_TEAM_BRAND_COLORS.get(codes[j], '#999')}59;}}"
            f".wrap:has(.lwc-{j}:hover) ~ .bxwrap .bxs .br-{j}"
            "{scroll-snap-align:start;}")
    # ... and the box score highlights the hovered LANE's stat
    # column(s) alongside the team's row — hovering a lane's column OR
    # its label on the plots line (parked labels are hoverable)
    for i in range(n):
        _sels = [f".wrap:has(.lane-{i} .lwc:hover) ~ .bxwrap",
                 f".wrap:has(.lane-{i} .lzl:hover) ~ .bxwrap"]
        if order[i] == "+/-":
            gsort_css += (",".join(f"{s} .bxhl-pm" for s in _sels)
                          + "{display:block;}")
        else:
            gsort_css += (",".join(
                f"{s} .bxhl.srt-{st}" for s in _sels
                for st in lane_sorts[i]) + "{display:block;}")
    for i in range(n):
        gsort_css += (_GS + f" ~ .wrap .lane-{i}"
                      f"{{top:calc({_T2[i]:.0f}px"
                      + "".join(
                          f" - var(--c{k},0)*{_BANDS[k]:.0f}px"
                          for k in range(i))
                      + ")!important;"
                      f"height:{_LH2[i]:.0f}px!important;}}"
                      f".lane-{i} .ldl{{top:{-_EXTT}px;}}"
                      f".lane-{i} .ldl::after"
                      f"{{height:{13 * _nmem[i] + 4}px;}}"
                      f".lane-{i} .lwc{{height:calc(100% + "
                      f"{_EXTT + 13 * _nmem[i] + 6}px + ({_TRE}));}}"
"")
    # which head columns sit under each lane's badge: estimated badge
    # pixel span vs the narrowest responsive pitch (the 900px clamp)
    _DN = {"FL": "PF", "TOV": "TO"}

    def _badge_rows(kind):
        if kind == "G":
            return ["G", "W", "L"]
        if kind == "+/-":
            return ["+/-"]
        if kind == "DR":
            return ["DR", "OR"]
        if kind in COMBO:
            _bmk, _bpct = COMBO[kind]
            return ([_bpct] if _bpct else []) + [kind, _bmk]
        return [_DN.get(kind, kind)]
    # Helvetica advance widths (per-em/1000) — what the browser's
    # sans fallback actually renders; the parked font then self-fits:
    # the largest size whose labels + controls fit the wrap width
    _LGAP = 6
    for _LFS in (17.1, 16, 15, 14, 13, 12, 11, 10):
        _BW = [round(_text_px(" ".join(_badge_rows(k)), _LFS) + 6 + _LGAP)
               for k in order]
        _PLW = round(_text_px("PLOTS", _LFS) + 10 + _LGAP)
        _CTW = round(_text_px("CLOSE", _LFS) + 6)
        if sum(_BW) + _PLW + _CTW + 10 <= _tbl_chars * 8.34443:
            break
    # per-lane sort/pack toggles on the label line: faces trail the
    # badge; up/down overrides with the ALL-view ascending/descending
    # order, pack-right shifts the active conference to the right —
    # !important vars so the per-view defaults yield
    def _xvars_imp(pos_of):
        return "".join(
            f"--x{j}:{(pos_of[codes[j]] + 0.5) / N * 100:.3f}%!important;"
            for j in range(N))
    _ALLM = (15, "a")
    gsort_css += (".lzl span{margin-right:calc(26*var(--u));}"
                  ".lzl span:last-child{margin-right:calc(28*var(--u));}")
    for i, kind in enumerate(order):
        _mrows = [(_DN2.get(k, k), k) for k in _badge_rows(kind)]
        _mkeys = (["G", "W", "L"] if kind == "G" else
                  ["DR", "OR"] if kind == "DR" else
                  (([COMBO[kind][1]] if COMBO[kind][1] else [])
                   + [kind, COMBO[kind][0]]) if kind in COMBO else [kind])
        _k0 = ((COMBO[kind][1] or kind) if kind in COMBO else kind)
        _st = f".st:has(#ls-{i}"
        _pk = f".st:has(#pk-{i}"
        _nm = len(_mkeys)
        for _mi, _mk in enumerate(_mkeys):
            # this member's up/down faces + the neutral face whenever
            # the member isn't the active sort
            gsort_css += (
                f"{_st}-u{_mi}:checked) ~ .wrap .lane-{i} "
                f".lcr-u{_mi}{{display:block;}}"
                f"{_st}-d{_mi}:checked) ~ .wrap .lane-{i} "
                f".lcr-d{_mi}{{display:block;}}")
            _others = (["n"] + [f"u{o}" for o in range(_nm) if o != _mi]
                       + [f"d{o}" for o in range(_nm) if o != _mi])
            gsort_css += (",".join(
                f"{_st}-{_s}:checked) ~ .wrap .lane-{i} .lcr-n{_mi}"
                for _s in _others) + "{display:block;}")
            _dsc = sort_pos.get((_ALLM, "a", _mk))
            if _dsc is None:
                continue
            _as = {t: (N - 1 - p) for t, p in _dsc.items()}
            gsort_css += (
                f"{_st}-u{_mi}:checked) ~ .wrap .lane-{i}"
                f"{{{_xvars_imp(_as)}}}"
                f"{_st}-d{_mi}:checked) ~ .wrap .lane-{i}"
                f"{{{_xvars_imp(_dsc)}}}")
        if kind == "+/-":
            continue
        for _pst, _fc in (("-n", "pcr-n"), ("-l", "pcr-l"),
                          ("-r", "pcr-r")):
            gsort_css += (",".join(
                f".st:has(#cf-{c}:checked){_pk[3:]}{_pst}:checked)"
                f" ~ .wrap .lane-{i} .{_fc}" for c in ("e", "w"))
                + "{display:block;}")
        _desc = sort_pos[(_ALLM, "a", _k0)]
        for _c in ("e", "w"):
            _in = [t for t in sorted(codes, key=lambda t: _desc[t])
                   if (t in _TEAM_EAST) == (_c == "e")]
            _out = [t for t in sorted(codes, key=lambda t: _desc[t])
                    if (t in _TEAM_EAST) != (_c == "e")]
            _pr = {t: len(_out) + k for k, t in enumerate(_in)}
            _pr.update({t: k for k, t in enumerate(_out)})
            gsort_css += (
                f".st:has(#cf-{_c}:checked):has(#pk-{i}-r:checked)"
                f" ~ .wrap .lane-{i}{{{_xvars_imp(_pr)}}}")

    # chips reveal per hovered TEAM alone — their texts already track
    # the active view through the variable blocks
    for j in range(N):
        gsort_css += (
            f".wrap:has(.lwc-{j}:hover) :is(.lvv-{j},.lrk-{j}),"
            f"body:has(.bxwrap .br-{j}:hover) :is(.lvv-{j},.lrk-{j})"
            "{display:block;}")
    gsort_css += "".join(
        f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
        " ~ .wrap{" + "".join(var_blocks[m]) + "}"
        for m in MASKS) + "".join(content_css)
    gsort_css += (".st:has(#cf-e:checked) ~ .wrap .bcf-w,"
                  ".st:has(#cf-w:checked) ~ .wrap .bcf-e"
                  "{display:none!important;}")
    # (no line-over-label hiding: the labels live in the left margin
    # outside the plot, so the hover line never touches them)
    for m in MASKS:
        for cf in CONFS:
            # every lane rests in the view's +/- ranking (one wrap-level
            # rule; a lane's own sort radios still override lane-scoped)
            _pre = _gate(m, cf) + ":has(#gsort:checked)"
            _pos = sort_pos[(m, cf, "+/-")]
            gsort_css += _pre + " ~ .wrap{" + _xvars(_pos) + "}"

        # teams with no games in this combo are suppressed entirely:
        # no bars (no cmb nodes), no tricode, and no hover cell
        _g = f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
        _hid = [j for j, t in enumerate(codes) if avgs[m][t] is None]
        if _hid:
            gsort_css += (",".join(f"{_g} ~ .wrap .ltx-{j},{_g} ~ .wrap .lwc-{j}"
                                   for j in _hid)
                          + "{display:none!important;}")

    # "Close" and "All": both sit in the next slot after the parked
    # labels. Close appears whenever at least one closable lane is
    # open; All appears only when NONE are (they never overlap).
    # Openness reads per the lall mode.
    _closable = [i for i in range(n) if order[i] != "+/-"]
    _sumall = "".join(f" + var(--c{k},0)*{_BW[k]:.0f}*var(--u)"
                      for k in range(n))
    _suball = "".join(f" - var(--c{k},0)*{_BW[k]:.0f}*var(--u)"
                      for k in range(n))
    _endslot = (f"{{left:calc((100% - {_CTW}*var(--u) - var(--pl,0)*{_PLW}*var(--u){_suball})/2"
                f" + var(--pl,0)*{_PLW}*var(--u));}}")
    _acs = (_GS + ":has(#lall:not(:checked))"
            + "".join(f":has(#lc-{i}:checked)" for i in range(n)))
    _acs2 = (_GS + ":has(#lall:checked)"
             + "".join(f":not(:has(#lc-{i}:checked))"
                       for i in range(n)))
    gsort_css += (
        ".pcard .tg.pal{color:#ddd;"
        "background:rgba(255,255,255,.16);}"
        ".tabs2{display:flex;justify-content:flex-start;"
        "width:70%;margin:14px auto;"
        "gap:calc(12*var(--u));"
        "font-size:calc(19*var(--u));text-transform:uppercase;}"
        ".tabs2 label{color:#888;cursor:pointer;padding:2px 10px;"
        "border-radius:3px;line-height:1.15;}"
        ".tabs2 label:hover{color:#ddd;}"
        ".st:has(#pg-g:checked) ~ .tabs2 .tb-g,"
        ".st:has(#pg-p:checked) ~ .tabs2 .tb-p,"
        ".st:has(#pg-u:checked) ~ .tabs2 .tb-u,"
        ".st:has(#pg-t:checked) ~ .tabs2 .tb-t"
        "{color:#ddd;background:rgba(255,255,255,.16);}"
        ".pcard{display:none;width:70%;margin:0 auto 18px;"
        "position:relative;z-index:210;"
        "background:#0d0d0d;border:1px solid #333;border-radius:8px;"
        "padding:12px 14px;box-sizing:border-box;"
        "flex-direction:column;align-items:stretch;}"
        ".st:has(#pg-g:checked) ~ .pc-g,"
        ".st:has(#pg-p:checked) ~ .pc-p,"
        ".st:has(#pg-u:checked) ~ .pc-u,"
        ".st:has(#pg-t:checked) ~ .pc-t{display:flex;}"
        ".tabs2 .tb-t{margin-left:auto;}"
        ".pcln{display:flex;justify-content:flex-start;"
        "align-items:center;gap:calc(6*var(--u));flex-wrap:wrap;"
        "margin:4px 0;"
        f"font-size:calc({_LFS}*var(--u));text-transform:uppercase;}}"
        ".pcard .pnm{display:block;opacity:.45;}"
        ".fgrp{display:flex;align-items:center;"
        "gap:calc(6*var(--u));border-top:1px solid #888;"
        "padding-top:1px;}"
        + "".join(
            f"{_GS}:has(#lall:not(:checked)):has(#lc-{i}:not(:checked))"
            f" ~ .pc-p .pnm-{i},"
            f"{_GS}:has(#lall:checked):has(#lc-{i}:checked)"
            f" ~ .pc-p .pnm-{i}"
            "{opacity:1;background:rgba(255,255,255,.12);}"
            for i in range(n))
        + f"{_acs} ~ .wrap .pcl,{_acs2} ~ .wrap .pcl,"
        f"{_acs} ~ .toggles .pcl,{_acs2} ~ .toggles .pcl"
        "{color:#ddd;background:rgba(255,255,255,.16);}"
        + f"{_acs} ~ .wrap .pal,{_acs2} ~ .wrap .pal,"
        f"{_acs} ~ .toggles .pal,{_acs2} ~ .toggles .pal"
        "{color:#888;background:none;}")
    gsort_css += (f".ptg{{margin:6px 0 2px 0;"
                  f"width:calc({TW} + 16px);flex-wrap:wrap;}}"
                  ".ptg2n{margin:0 0 2px 0;}"
                  f".ptgv{{display:flex;align-items:center;"
                  "justify-content:flex-end;gap:calc(6*var(--u));"
                  f"font-size:calc({_LFS}*var(--u));"
                  "text-transform:uppercase;margin:10px 0 4px;}"
                  ".ptgv .tg{background:none;}"
                  ""
                  ".pnm{display:none;}"
                  ".pnm span{margin-right:4px;}"
                  ".ptg .tg{background:none;}")

    # (the resting page's per-team columns — hover cells, pinned-team
    # radios, bottom tricode axis, and the right-hand value column with
    # its traveling chips — are gone: the sort view is the only mode,
    # and its own lane-scoped machinery replaces them all)

    # ---- season-average box table (a 30-row block per mask) ----
    # the name field is 17 chars — the same width as the game and team box
    # scores' Player/name column — so every stat column lands at the same
    # character position on all three pages: 3-char tricode, then the
    # after the tricode: games (#), then wins (W) and losses (L), each a
    # 3-wide column. The tricode+games span shrank by 6 (games field
    # 13->7) to make room for W+L (3+3) so the box still ends at the same
    # column — _NAME_W stays the full pre-stat width (17)
    _NAME_W = 17
    hdr = (f"{'Team':<4}{'#':>{_NAME_W - 11}}{'W':>3}{'L':>3} "
           + "".join(f"{lab:>{w}}" for lab, _, w, _, _ in _BOX_COLS))
    mask_blocks = []
    for m in MASKS:
        am = avgs[m]
        present = [t for t in codes if am[t] is not None]
        col_hi = {key: max(am[t][key] for t in present) for _, key, _, c, _ in _BOX_COLS if c and present}
        col_lo = {key: min(am[t][key] for t in present) for _, key, _, c, _ in _BOX_COLS if c and present}
        for j, t in enumerate(codes):
            a = am[t]
            tcol = _dim_hex(_TEAM_BRAND_COLORS.get(t, "#999"))
            _tcode = (f'<a href="{_team_href(t)}" style="color:{tcol}">{t}</a>'
                      if _team_href(t) else f'<span style="color:{tcol}">{t}</span>')
            if a is None:
                # team has no games in this view — it simply drops out of
                # the box table (no dash row), so a filtered view shows
                # only its own teams
                continue
            name = (_tcode + f"{a['G']:{_NAME_W - 10}.0f}"
                    + f"{a['W']:>3.0f}{a['L']:>3.0f} ")
            parts = [name]
            for _ci, (lab, key, w, colored, invert) in enumerate(_BOX_COLS):
                v = a[key]
                if key == "+/-":
                    # every +/- value sits half a character right of its
                    # right-aligned spot (visual shift only): full-width
                    # values (|v| > 9.9) split their crowding against PTS
                    # evenly, and the shorter ones keep the decimal points
                    # aligned with them
                    cell = ('<span style="position:relative;left:.5ch">'
                            + f"{v:+.1f}".rjust(w) + "</span>")
                else:
                    cell = f"{v:.0f}".rjust(w)
                if colored:
                    best, worst = (col_lo[key], col_hi[key]) if invert else (col_hi[key], col_lo[key])
                    if v == best:
                        cell = f'<span style="color:{_GOLD}">{cell}</span>'
                    elif v == worst:
                        cell = f'<span style="color:{_RED}">{cell}</span>'
                # each data cell is a hover target for the box->plot
                # reverse crosshair (bc-{column index})
                parts.append(f'<span class="bc-{_ci}">{cell}</span>')
            mask_blocks.append(f'<div class="br br-{j} {_cmb_cls(m, t)}">' + "".join(parts) + "</div>")
    # while a sort is active, a translucent stripe highlights the sorted
    # stat's column(s) in the box table — header name included — to pair
    # with the selected team's row highlight. Char offsets in the
    # monospace table map 1:1 to ch units.
    _off, _pos = {}, _NAME_W
    for _lab, _key, _w, _c, _inv in _BOX_COLS:
        _off[_key] = (_pos, _w)
        _pos += _w
    # every sortable stat (each combo member included) highlights its own
    # box column. Keyed by the sort-stat key, valued by the _BOX_COLS key,
    # so DR->DREB, OR->OREB, and the FT/3P/2P trios each hit their own
    # made/attempt/pct column. Indexed by the flattened sort index srt-{s},
    # not the lane index, so it stays in step with the sort radios.
    _STAT_BOX_COL = {
        "FL": "PF", "TOV": "TO", "BLK": "BLK", "STL": "STL", "AST": "AST",
        "DR": "DREB", "OR": "OREB",
        "FTA": "FTA", "FTM": "FTM", "FT%": "FT%",
        "3PA": "FG3A", "3PM": "FG3M", "3P%": "3P%",
        "2PA": "FGA", "2PM": "FGM", "2P%": "FG%",
    }
    col_stripes = []
    for _sidx, (_li, _key) in enumerate(sort_stats):
        _col = _STAT_BOX_COL.get(_key)
        if not _col:
            continue
        # the stripe starts one character in: each field's width includes
        # its leading gap, so the shading hugs the digits. It carries
        # the stat label's color at low alpha.
        _cstart, _cw = _off[_col]
        _left = _cstart + 1
        _right = _cstart + _cw
        col_stripes.append(f'<div class="bxhl srt-{_sidx}" '
                           f'style="left:{_left}ch;width:{_right - _left}ch;'
                           f'background:{hex_by_kind[_key]}59;"></div>')
    # a +/- column stripe of its own (no sort radio ties to it — the
    # default sort IS +/-): shown only by the lane-hover rules
    _pms, _pmw = _off["+/-"]
    col_stripes.append(f'<div class="bxhl bxhl-pm" '
                       f'style="left:{_pms + 1}ch;width:{_pmw - 1}ch;'
                       f'background:{hex_by_kind["+/-"]}59;"></div>')
    # the header: each stat column's name wears its label's color (the
    # spans keep the monospace alignment intact). The +/- HEADER stays
    # at its natural right-aligned spot (half a character left of the
    # shifted values).
    _BOXCOL_HEX = {bc: hex_by_kind[sk] for sk, bc in _STAT_BOX_COL.items()}
    _BOXCOL_HEX["+/-"] = hex_by_kind["+/-"]
    hdr_html = _html.escape(f"{'Team':<4}{'#':>{_NAME_W - 11}}{'W':>3}{'L':>3} ")
    for lab, key, w, _c, _i in _BOX_COLS:
        _cell = _html.escape(f"{lab:>{w}}")
        _hx = _BOXCOL_HEX.get(key)
        if _hx:
            _cell = f'<span style="color:{_hx}">{_cell}</span>'
        hdr_html += _cell
    box_table = (f'<div class="bx"><div class="bx-head">{hdr_html}</div>'
                 + '<div class="bxs">'
                 + "".join(mask_blocks) + '<div class="bxsp"></div></div>'
                 + "".join(col_stripes) + "</div>")
    # views with no qualifying team reveal the message
    gsort_css += "".join(
        _gate(m, cf) + " ~ .bxwrap .bxmsg{display:block;}"
        for m in MASKS for cf in CONFS
        if not any(avgs[m][t] is not None
                   and (cf == "a" or _conf(t) == cf)
                   for t in codes))
    gsort_css += (
        ".bxmsg{display:none;position:absolute;left:0;right:0;"
        "text-align:center;color:#888;"
        "font-size:calc(var(--vw)*0.0462);"
        "top:calc(40px + var(--vw)*0.0693);}"
        ".bxwrap{position:relative;}"
        ".st:has(#bx-h:checked) ~ .bxwrap .bxmsg"
        "{display:block;}")
    gsort_css += (
        ".bxs{overflow-y:auto;overflow-x:hidden;"
        "scrollbar-gutter:stable;direction:rtl;margin-left:-24px;"
        "scroll-snap-type:y mandatory;}"
        ".bxs .br{scroll-snap-align:start;direction:ltr;}"
        ".bxs::-webkit-scrollbar{width:24px;}"
        ".bxs::-webkit-scrollbar-thumb{background:#333;"
        "border-radius:5px;border:6px solid #000;}"
        ".bxs::-webkit-scrollbar-thumb:hover{background:#666;}"
        ".bxs::-webkit-scrollbar-track{background:rgba(255,255,255,.06);}"
        f".btg{{display:flex;align-items:center;"
        f"justify-content:flex-end;width:calc({TW} + 16px);"
        "gap:calc(6*var(--u));"
        f"font-size:calc({_LFS}*var(--u));text-transform:uppercase;"
        "margin:calc(var(--vw)*0.0231) 0 8px 0;}"
        ".btg .tg{background:none;}"
        + "".join(
            f".st:has(#bx-{b}:checked) ~ .bxwrap .bxs"
            f"{{height:calc(var(--vw)*{r_:.4f});}}"
            f".st:has(#bx-{b}:checked) ~ .bxwrap .bxs .bxsp"
            f"{{height:calc(var(--vw)*{r_ - 1.5 * 0.0154:.4f});}}"
            f".st:has(#bx-{b}:checked) ~ .bxwrap .tg-bx-{b}"
            "{color:#ddd;background:rgba(255,255,255,.16);}"
            for b, r_ in (("10", 10 * 1.5 * 0.0154),
                          ("25", 25 * 1.5 * 0.0154)))
        + ".bxsp{height:0;}"
        + ".st:has(#bx-a:checked) ~ .bxwrap .tg-bx-a,"
        ".st:has(#bx-h:checked) ~ .bxwrap .tg-bx-h"
        "{color:#ddd;background:rgba(255,255,255,.16);}"
        + ".st:has(#bx-h:checked) ~ .bxwrap .bx"
        "{display:none;}")

    # ---- box -> plot reverse hover: hovering a box data cell tints
    # its ROW in the team's color and its COLUMN in the stat's color,
    # and the plot reacts as if the pointer were on that team's column
    # (line, bold tricode, and — via body:has, which can reach the
    # earlier sibling — the hovered lane's cell tint) ----
    _COL_STAT = {v: k for k, v in _STAT_BOX_COL.items()}
    _COL_STAT["+/-"] = "+/-"
    _STAT_LANE = {key: li for li, key in sort_stats}
    _STAT_SIDX = {key: s for s, (_li3, key) in enumerate(sort_stats)}
    for j in range(N):
        _tc3 = _TEAM_BRAND_COLORS.get(codes[j], "#999")
        gsort_css += (
            f".bxwrap .br-{j}:hover{{background:{_tc3}59;}}"
            f"body:has(.bxwrap .br-{j}:hover) .ldl-{j}{{display:block;}}"
            f"body:has(.bxwrap .br-{j}:hover) .ltx-{j}{{font-weight:bold;}}")
    for _ci, (_lab3, _bkey, _w3, _c3, _i3) in enumerate(_BOX_COLS):
        _sk = _COL_STAT.get(_bkey)
        if not _sk:
            continue
        if _sk == "+/-":
            gsort_css += f".bx:has(.bc-{_ci}:hover) .bxhl-pm{{display:block;}}"
        else:
            gsort_css += (f".bx:has(.bc-{_ci}:hover) "
                          f".bxhl.srt-{_STAT_SIDX[_sk]}{{display:block;}}")
        _li = _STAT_LANE[_sk]
        gsort_css += "".join(
            f"body:has(.br-{j} .bc-{_ci}:hover) .lane-{_li} .lwc-{j}"
            "{background:rgba(255,255,255,.06);}" for j in range(N))

    # ---- the filter buttons: three combinable groups ----
    # the thirds are labelled with the season partition numbers: the
    # median per-team game count in each detected partition (teams
    # differ by a game or two around the league-wide break dates)
    def _medseg(sb):
        cnts = sorted(sum(1 for r in s if r["seg"] == sb)
                      for s in seg_data.values())
        return cnts[len(cnts) // 2]
    _n1 = _medseg(1)
    _n2 = _n1 + _medseg(2)
    _n3 = _n2 + _medseg(4)
    _SEG_BTNS = [(1, f"1:{_n1}"), (2, f"{_n1 + 1}:{_n2}"),
                 (4, f"{_n2 + 1}:{_n3}"),
                 (7, "Regular"), (8, "Playoffs"), (15, "All")]
    # three radio groups: the season segment (exactly one), the game type
    # (none or one of OT/Clutch) and the conference (none or one of
    # East/West) — the filters COMBINE (e.g. Regular + Clutch + East)
    # the filter radios live in their own form: its defaults ARE the
    # unfiltered state, and the ALL button is the form's reset — one
    # click re-includes every game AND clears East/West.
    seg_checkboxes = ("<form>" + "".join(
        f'<input type="radio" class="seg" name="seg" id="seg-m{mask}"'
        f'{" checked" if mask == 15 else ""}>'
        for mask, _ in _SEG_BTNS)
        + '<input type="radio" class="seg" name="gt" id="gt-a" checked>'
        '<input type="radio" class="seg" name="gt" id="gt-w">'
        '<input type="radio" class="seg" name="gt" id="gt-l">'
        '<input type="radio" class="seg" name="gt" id="gt-h">'
        '<input type="radio" class="seg" name="gt" id="gt-v">'
        '<input type="radio" class="seg" name="gt" id="gt-o">'
        '<input type="radio" class="seg" name="gt" id="gt-c">'
        '<input type="radio" class="seg" name="cf" id="cf-a" checked>'
        '<input type="radio" class="seg" name="cf" id="cf-e">'
        '<input type="radio" class="seg" name="cf" id="cf-w">'
        '<input type="reset" class="seg" id="gall"></form>')
    # every combo-tagged element is hidden by default; the checked TRIPLE
    # of filter states reveals just its own combo's nodes
    combo_css = '[class*="cmb-"]{display:none;}'
    for m in MASKS:
        for cf in CONFS:
            st = _gate(m, cf)
            _c = f"cmb-{m[0]}{m[1]}{cf}"
            combo_css += (f"{st} ~ .wrap .{_c},"
                          f"{st} ~ .bxwrap .{_c}{{display:block;}}")
    # active-button highlights, one per group. ALL is different: it
    # lights up only while some game filter EXCLUDES games, and its
    # click resets the game-filter form (see seg_checkboxes)
    _hl = "{color:#ccc;background:rgba(255,255,255,.16);}"
    for mask, _ in _SEG_BTNS:
        if mask == 15:
            continue
        combo_css += (f".st:has(#seg-m{mask}:checked) ~ .toggles "
                      f".tg-m{mask}{_hl}")
    combo_css += ",".join(
        f".st:has(#{x}:checked) ~ .toggles .tg-all"
        for x in ("seg-m1", "seg-m2", "seg-m4", "seg-m7", "seg-m8",
                  "gt-o", "gt-c", "cf-e", "cf-w",
                  "gt-w", "gt-l", "gt-h", "gt-v")) + _hl
    for gid in ("gt-o", "gt-c", "cf-e", "cf-w",
                "gt-w", "gt-l", "gt-h", "gt-v"):
        combo_css += (f".st:has(#{gid}:checked) ~ .toggles .tg-{gid},"
                      f".st:has(#{gid}:checked) ~ .toggles .tgu-{gid}{_hl}")
        # the toggle-off twin sits over its button while it is active,
        # so a second click releases the filter (back to the group's
        # neutral radio)
        combo_css += (f".st:has(#{gid}:checked) ~ .toggles "
                      f".tgu-{gid}{{display:block;}}")
    def _tgl(gid, label):
        # a toggling button: the base label turns the filter on; its
        # absolutely-stacked twin (revealed while on) turns it off
        _off = "gt-a" if gid.startswith("gt") else "cf-a"
        return (f'<span class="tgw"><label class="tg tg-{gid}"'
                f' for="{gid}">{label}</label>'
                f'<label class="tg tgu tgu-{gid}" for="{_off}">'
                f'{label}</label></span>')
    seg_line1 = ('<label class="tg tg-all" for="gall">All</label>'
                 + "".join(
                     f'<label class="tg tg-m{mask}" for="seg-m{mask}">'
                     f'{label}</label>'
                     for mask, label in _SEG_BTNS[:-1]))
    seg_line2 = (_tgl("cf-e", "East") + _tgl("cf-w", "West")
                 + '<span class="fgrp">'
                 + _tgl("gt-o", "OT") + _tgl("gt-c", "Clutch")
                 + "</span>"
                 + '<span class="fgrp">'
                 + _tgl("gt-w", "W") + _tgl("gt-l", "L")
                 + "</span>"
                 + '<span class="fgrp">'
                 + _tgl("gt-h", "H") + _tgl("gt-v", "A")
                 + "</span>")

    css = f"""
body{{background:#000;color:#b6b6b6;font-family:'DejaVu Sans',sans-serif;margin:0 auto 24px;width:calc({TW} + 68px);
  /* the responsive unit: 1px at the 900px clamp, 1.33px at 1200 —
     the GAMES/PLOTS lines' fonts and slots all scale by it */
  --vw:clamp(700px, 100vw, 1200px);--u:calc(var(--vw) / 900);}}
@supports (width: round(1px, 1px)) {{
  body{{--vw:clamp(700px, round(100vw, 32px), 1200px);}}
}}
/* the plot spans the box table edge to edge */
.wrap{{position:relative;width:calc({TW} + 16px);
  margin:0 0 0 26px;}}
.plot{{position:relative;height:{PLOT_H}px;}}
.lane{{position:absolute;left:0;right:0;contain:layout style;background:rgba(255,255,255,.035);}}
.fl{{position:absolute;}}
/* a touch of transparency so stacked/overlapping bars read as layers */
.bar{{opacity:.85;}}
/* the hover chips (values and ranks) at the hovered team's columns */
.tv{{display:none;position:absolute;transform:translateX(-50%);
  font-size:11px;line-height:1;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);white-space:nowrap;pointer-events:none;
  z-index:7;font-family:'DejaVu Sans Mono',monospace;}}
.seg,.srt{{display:none;}}
/* Sort mode's per-lane tricode row: vertical codes under each lane's
   baseline, following the LANE's own --x order. Teams outside the
   active view (other conference, or no games in the combo) show no
   label at all */
.ltx{{display:none;position:absolute;top:100%;margin-top:3px;
  transform:translateX(-50%);writing-mode:vertical-rl;line-height:1;
  font-size:{_LTX_FS};pointer-events:none;z-index:3;
  font-family:'DejaVu Sans Mono',monospace;}}
/* the +/- lane's tricodes link to the team pages: clickable above the
   hover cells (z 120), everything else about them unchanged */
.ltxa{{pointer-events:auto;cursor:pointer;z-index:121;
  text-decoration:none;}}
.ltxa:hover{{text-decoration:underline;}}
/* Sort mode's per-lane hover cell (covers the column plus the tricode
   row below) and the dimmed white line segment at the team's column */
.lwc{{display:none;position:absolute;top:{-_EXTT}px;
  height:calc(100% + {_EXTT + _LBL + 20}px);
  z-index:120;cursor:crosshair;}}
.lwc:hover{{background:rgba(255,255,255,.06);}}
/* the flag pole: rises above the lane with the value flags at its
   tip, runs the lane, crosses the tricode row and ends at the last
   rank flag (per-lane top/bottom set with the lane geometry);
   painted on the BOTTOM layer (behind the bars) */
.ldl{{display:none;position:absolute;top:0;bottom:0;
  width:3px;margin-left:-1.5px;background:#C0C0C0;opacity:.75;
  z-index:-1;pointer-events:none;}}
.ldl::after{{content:"";position:absolute;left:0;width:3px;
  background:#C0C0C0;top:calc(100% + 2px + ({_TRE}));}}
.lvv{{transform:translateX(calc(-100% - 3px));}}
.lrk{{transform:translateX(3px);}}
/* Sort mode's per-lane stat badge: vertically centred on its lane,
   right edge one character left of the plot edge; a group's labels
   sit flattened on one line */
.lzl{{display:none;position:absolute;
  bottom:100%;left:0;
  right:auto;width:auto;text-align:left;
  font-size:calc(14*var(--u));line-height:1.15;z-index:160;
  pointer-events:none;
  white-space:nowrap;padding:1px 8px;border-radius:3px;
  background:rgba(0,0,0,.72);}}
.lcr{{display:none;position:absolute;
  bottom:100%;
  width:calc(23.4*var(--u));height:calc(16.1*var(--u));
  box-sizing:border-box;text-align:center;
  line-height:calc(16.1*var(--u));font-size:calc(14*var(--u));
  z-index:161;cursor:pointer;background:rgba(0,0,0,.72);
  border-radius:3px;}}
.lcr:hover{{background:rgba(255,255,255,.16);}}
.lcx{{position:absolute;bottom:100%;
  width:calc(16.1*var(--u));height:calc(16.1*var(--u));
  box-sizing:border-box;text-align:center;
  line-height:calc(16.1*var(--u));font-size:calc(14*var(--u));
  color:#aaa;background:rgba(0,0,0,.72);border-radius:3px;
  z-index:161;cursor:pointer;}}
.lcx:hover{{background:rgba(255,255,255,.16);}}
/* a group's members stack vertically while the lane is open (the
   parked one-line form re-inlines them) */
.lzl span{{display:inline;}}
/* any badge with an lc target is a click toggle (open badge closes
   its lane; the parked copy opens it); the +/- badge has none */

/* the +/- lane's badge is just larger */
/* "Close" / "All" on the top label line, after the parked labels:
   Close shows while any closable lane is open (resets the lc form =
   all closed); All shows when none are (flips lall = all open) */
.lcls,.lals{{display:none;position:absolute;top:13px;transform:translateY(-50%);
  font-size:calc({_LFS}*var(--u));
  line-height:1.15;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);color:#aaa;cursor:pointer;z-index:6;
  user-select:none;white-space:nowrap;}}
.lcls:hover,.lals:hover{{color:#ddd;background:rgba(255,255,255,.16);}}
.pvp{{position:relative;}}
.sroll{{position:absolute;top:0;bottom:0;left:-28px;width:28px;
  overflow-y:scroll;scroll-timeline:--psb y;
  scroll-snap-type:y mandatory;z-index:170;}}
.sroll::-webkit-scrollbar{{width:24px;}}
.sroll::-webkit-scrollbar-thumb{{background:#333;border-radius:5px;
  border:6px solid #000;}}
.sroll::-webkit-scrollbar-thumb:hover{{background:#666;}}
.sroll::-webkit-scrollbar-track{{background:rgba(255,255,255,.06);}}
.ssn{{scroll-snap-align:start;}}
/* the label line's "PLOTS --" heading, shown while any plot is parked */
.lpl{{display:none;position:absolute;top:13px;transform:translateY(-50%);
  font-size:calc({_LFS}*var(--u));
  line-height:1.15;padding:1px 3px;color:#888;z-index:6;
  text-transform:uppercase;pointer-events:none;white-space:nowrap;}}
.st:has(#cf-e:checked) ~ .wrap .ltxc-w,
.st:has(#cf-e:checked) ~ .wrap .lwcc-w,
.st:has(#cf-w:checked) ~ .wrap .ltxc-e,
.st:has(#cf-w:checked) ~ .wrap .lwcc-e{{display:none!important;}}
/* the segment toggles sit in the middle band between chart and table */
.toggles{{width:calc({TW} + 16px);margin:30px 0 24px 26px;display:flex;
  align-items:center;justify-content:center;gap:calc(6*var(--u));
  font-size:calc(17.1*var(--u));text-transform:uppercase;}}
.tglabel{{color:#888;padding-right:8px;}}
.tg{{cursor:pointer;color:#888;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);user-select:none;line-height:1.15;}}
.tg:hover{{color:#ddd;}}
/* the games line's filter groups wear their own colors: season
   segments / East-West / OT-Clutch; All keeps the neutral grey */
.tg-m1,.tg-m2,.tg-m4,.tg-m7,.tg-m8{{color:#cfa96b;}}
.tg-cf-e,.tg-cf-w,.tgu-cf-e,.tgu-cf-w{{color:#7fa6d9;}}
.tg-gt-o,.tg-gt-c,.tgu-gt-o,.tgu-gt-c{{color:#7fc9a6;}}
.tg-gt-w,.tgu-gt-w{{color:#2ecc55;}}
.tg-gt-l,.tgu-gt-l{{color:#ff5252;}}
.tg-gt-h,.tgu-gt-h{{color:#8FD3FF;}}
.tg-gt-v,.tgu-gt-v{{color:#9BA3AD;}}
/* toggling buttons (OT/Clutch, East/West): while on, an off-twin sits
   exactly over the button so a second click releases the filter. The
   base label must be inline-block so its padding sizes the wrapper —
   otherwise the twin overlays a shorter box and the two misalign */
.tgw{{position:relative;display:inline-block;}}
.tgw .tg{{display:inline-block;}}
/* the off-twin hides at equal-or-higher specificity than the
   inline-block above, or it would cover the button and eat every
   click; the per-state reveal rules outrank both */
.tgw .tgu{{display:none;}}
.tgu{{position:absolute;left:0;top:0;right:0;bottom:0;
  box-sizing:border-box;text-align:center;}}
/* left edge on the same line as the plot (and the segment toggles).
   No overflow-x here: the box score scrolls with the page rather than
   in its own independent horizontal scrollbar */
.bxwrap{{margin:8px 0 12px 26px;}}
.bx{{display:flex;flex-direction:column;position:relative;
  font-family:'DejaVu Sans Mono',monospace;
  /* same size as the game and team box scores: 1.54% of a 1200px-max
     container (matches the game page's 1.54cqw box scores) */
  line-height:1.5;font-size:calc(var(--vw) * 0.0154);
  /* no left padding: the text's left edge lands exactly at .bxwrap's
     own left (26px), matching the plot's lane edge above it */
  /* the box hugs its own text span (TW = char count x mono advance)
     so the row highlights end with the table instead of running on;
     +16px covers the right padding under border-box */
  box-sizing:border-box;width:calc({TW} + 16px);
  white-space:pre;color:#a6a6a6;padding:10px 16px 10px 0;}}
/* same as the game/team pages' column-header rows, which render in the
   body text color — not the brighter game-title #e0e0e0 */
.bx-head{{color:#a6a6a6;order:-1;}}
.br{{display:block;}}
/* the sorted stat's column stripe over the box table */
.bxhl{{display:none;position:absolute;top:0;bottom:0;
  background:rgba(255,255,255,.22);pointer-events:none;}}
.bx a{{text-decoration:none;color:inherit;}}
.bx a:hover{{text-decoration:underline;}}
""" + sort_css + combo_css + gsort_css

    try:
        _y0, _y1 = season.split("-")
        full_season = f"{_y0}-{_y0[:2]}{_y1}"
    except Exception:
        full_season = season
    tab_title = f"NBA {full_season} Season Averages"
    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{tab_title}</title><style>{css}</style></head><body>"
        f"<div class=\"st\">{seg_checkboxes}{srt_radios}</div>"
        + '<div class="tabs2">'
          '<label class="tb-g" for="pg-g">GAMES</label>'
          '<label class="tb-p" for="pg-p">PLOTS</label>'
        + f'<label class="tb-t" for="pg-t">'
          f'NBA {full_season} Season Averages</label>'
          '</div>'
        + '<div class="toggles pcard pc-g">'
        + f'<div class="pcln">{seg_line1}</div>'
        + f'<div class="pcln">{seg_line2}</div></div>'
        + '<div class="toggles pcard pc-p">'
        + '<div class="pcln">'
          '<label class="tg pal" for="lclose">ALL</label>'
        + pnames[9] + pnames[10] + "</div>"
        + '<div class="pcln">' + "".join(pnames[0:6]) + "</div>"
        + '<div class="pcln">' + "".join(pnames[6:9]) + "</div></div>"
        + '<div class="toggles pcard pc-t"></div>'

        + '<div class="wrap">'
        + '<div class="ptgv">'
          '<label class="tg tg-vw-1" for="vw-1">1</label>'
          '<label class="tg tg-vw-3" for="vw-3">3</label>'
          '<label class="tg tg-vw-a" for="vw-a">ALL</label>'
          '<label class="tg pcl" for="lall">HIDE</label></div>'
        + '<div class="pvp">'
        + '<div class="sroll"><div class="ssp">'
        + "".join(
            f'<div class="ssn" style="height:calc({_BANDS[k]:.0f}px'
            f' - var(--c{k},0)*{_BANDS[k]:.0f}px)"></div>'
            for k in range(n))
        + f'<div style="height:{_TS:.0f}px"></div></div></div>'
        + '<div class="plot">'
          '<div class="plmsg">No one home</div><div class="pcar">'
        + "".join(lanes)
        + "</div></div></div></div>"
        + '<div class="bxwrap"><div class="btg">'
          '<label class="tg tg-bx-10" for="bx-10">10</label>'
          '<label class="tg tg-bx-25" for="bx-25">25</label>'
          '<label class="tg tg-bx-a" for="bx-a">ALL</label>'
          '<label class="tg tg-bx-h" for="bx-h">HIDE</label></div>'
        + '<div class="bxmsg">No TEAMS selected</div>'
        + f'{box_table}</div></body></html>'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path
