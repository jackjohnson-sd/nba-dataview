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
                or (ty == "c" and r["clutch"]))]
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
    TYPES = ["a", "o", "c"]
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
        href = f"season_events_2d_{t.lower()}.html"
        return href if (output_path.parent / href).exists() else None

    order = ["FL", "TOV", "BLK", "STL", "AST", "DR", "FTA", "3PA", "2PA", "+/-"]
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
          " * clamp(900px, 100vw, 1200px) - 68px)")
    # the box table's full text width — the title centres on this span
    TW = (f"calc({_tbl_chars * 0.60205 * 0.0154:.5f}"
          " * clamp(900px, 100vw, 1200px))")
    x_frac = [(j + 0.5) / N for j in range(N)]
    hw = 0.135 / N

    def _pulse_edges(fx):
        c = min(max(fx, hw), 1.0 - hw)
        return (c - hw) * 100, (c + hw) * 100

    def nice_scale(vmin, vmax):
        span = max(vmax - vmin, 1.0)
        step = next(t for t in (1, 2, 5, 10, 20, 25, 50) if t >= span / 4)
        lo = math.floor(vmin / step) * step
        hi = max(math.ceil(vmax / step) * step, lo + step)
        return lo, hi, step

    sel_idx = [i for i, k in enumerate(order) if k != "+/-"]

    # fixed lane scales, from the union of every combination's values so
    # no bar clips when segments are toggled
    lane_geo = {}
    for kind in order:
        if kind == "+/-":
            vmax = max((abs(v) for v in all_vals("+/-")), default=1.0) or 1.0
            lane_geo[kind] = (0.0, vmax, vmax, max(round(vmax / 4), 1), None)
        elif kind == "DR":
            # stacked DR+OR bars: the scale runs 0..max total rebounds
            _, hi, step = nice_scale(0.0, max(all_vals("REB")))
            lane_geo[kind] = (0.0, hi, hi, step, None)
        elif kind in COMBO:
            _mk, _pct = COMBO[kind]
            lo = math.floor(min(all_vals(_mk)))
            hi = math.ceil(max(all_vals(kind)))
            step = next(s for s in (1, 2, 5, 10, 20) if (hi - lo) / s <= 6)
            lo = math.floor(lo / step) * step
            hi = max(math.ceil(hi / step) * step, lo + step)
            plo, phi, _ = nice_scale(min(all_vals(_pct)), max(all_vals(_pct))) if _pct else (0, 1, 1)
            lane_geo[kind] = (lo, hi, hi - lo, step, (plo, phi) if _pct else None)
        else:
            lo, hi, step = nice_scale(min(all_vals(kind)), max(all_vals(kind)))
            lane_geo[kind] = (lo, hi, hi - lo, step, None)

    # ---- click-to-sort: clicking a main lane's value in the right-hand
    # column re-sorts the 30 team columns by that stat (full-season
    # values, best first — FL/TOV invert since lower is better there).
    # Pure CSS: a sort radio per lane sets per-team x CSS variables
    # (--x{j} = team j's column center), and every team-positioned
    # element reads its var instead of a baked left. "+/-" IS the
    # default order, so its radio restores the page's normal sort. ----
    _LOWER_BETTER = {"FL", "TOV"}
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
    # one radio per sortable stat; +/- (srt-{_PM_S}) is the checked default
    # (= the page's resting order). Non-default sorts carry .srt-on so
    # rules can test "some sort is active".
    srt_radios = "".join(
        f'<input type="radio" class="srt{"" if s == _PM_S else " srt-on"}"'
        f' name="sel" id="srt-{s}"'
        f'{" checked" if s == _PM_S else ""}>' for s in range(len(sort_stats)))
    # one SPOTLIGHT radio per MEMBER label (the label cycle's first
    # state: 2x plot in the default order, no sort). Same radio group;
    # sp-{i} keys the lane's shared 2x, the square marks only the member.
    srt_radios += "".join(
        f'<input type="radio" class="srt spot sp-{i}" name="sel" id="e-s{s}">'
        for s, (i, _k) in enumerate(sort_stats) if s != _PM_S)
    # Sort is the page's INITIAL mode (gsort starts checked)
    srt_radios += '<input type="checkbox" class="srt" id="gsort" checked>'
    # Sort mode's per-lane collapse state: clicking a lane's bar area
    # checks it (lane content hides), clicking the lane's badge
    # unchecks. The page STARTS with every lane closed except +/-,
    # which can't be closed at all (its click controls are omitted).
    # The lc boxes live in their OWN form whose reset input is the
    # "Close" control: resetting restores every default = all closed,
    # without touching the filters outside the form.
    srt_radios += ("<form>" + "".join(
        f'<input type="checkbox" class="srt" id="lc-{i}"'
        f'{"" if order[i] == "+/-" else " checked"}>' for i in range(n))
        + '<input type="reset" class="srt" id="lclose"></form>')

    def _xvars(pos_of):
        return "".join(f"--x{j}:{(pos_of[codes[j]] + 0.5) / N * 100:.3f}%;"
                       for j in range(N))

    # default vars on .wrap (the DOM/+/- order); each other sort state
    # overrides them and re-orders the box table's rows via flex order.
    # Unsorting: click the "+/-" prefix of the combined phrase (the +/-
    # lane's label) — the value cells themselves take no mouse events.
    sort_css = ".wrap{" + _xvars({t: j for j, t in enumerate(codes)}) + "}"

    def _gate(m, cf):
        # the three filter groups' combined state selector
        return (f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
                f":has(#cf-{cf}:checked)")
    for s, (i, key) in enumerate(sort_stats):
        if s == _PM_S:
            continue
        # one rule set per (data combo, conference): the ordering follows
        # the ACTIVE filters' ranking, not the full-season one
        for m in MASKS:
            for cf in CONFS:
                st = _gate(m, cf) + f":has(#srt-{s}:checked)"
                sort_css += st + " ~ .wrap{" + _xvars(sort_pos[(m, cf, key)]) + "}"
                sort_css += "".join(
                    f"{st} ~ .bxwrap .br-{j}"
                    f"{{order:{sort_pos[(m, cf, key)][codes[j]]};}}"
                    for j in range(N))
        # the on-plot value chips: shown per active data combo while any
        # of the LANE's states is up (plain or sorted) — a grouped lane
        # reveals every member's chip; the team gate is the chips' own
        # .gvcol parent (hovered/pinned team only)
        for m in MASKS:
            _mm = f"{m[0]}{m[1]}"
            sort_css += (
                f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
                f":has(#e-s{s}:checked) ~ .wrap .tvl-{i}.tvm-{_mm},"
                f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
                f":has(#srt-{s}:checked) ~ .wrap .tvl-{i}.tvm-{_mm}"
                f"{{display:block;}}")
    # while ANY non-default sort is active (.srt-on), dim every lane and
    # hide the bottom-axis tricodes; each active sort's own rule (grow_css)
    # then un-dims and grows its lane and shows the under-lane tricodes
    sort_css += (".st:has(.srt-on:checked) ~ .wrap .lane{opacity:.15;}"
                 ".st:has(.srt-on:checked) ~ .wrap .tx{display:none;}"
                 # the plain-2x spotlight state dims the other lanes too
                 # (its own lane un-dims via the per-lane grow rule)
                 ".st:has(.spot:checked) ~ .wrap .lane{opacity:.15;}")

    def _union(sorts, suffix):
        # ".st:has(#srt-a) ~ SUFFIX, .st:has(#srt-b) ~ SUFFIX" — a rule that
        # fires if ANY of a lane's stats is the active sort
        return ",".join(f".st:has(#srt-{s}:checked) ~ {suffix}" for s in sorts)

    # ---- Rank overlay: per mask and stat, each team's league rank
    # (competition ranking — ties share; FL/TOV rank 1 = fewest). The
    # Rank button overlays these on the value column. ----
    _rank_keys = set(order) | {"REB"}
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
    _LTX_FS = (f"calc({_tbl_chars * 0.60205 * 0.0154 * _BARW:.6f}"
               f" * clamp(900px, 100vw, 1200px) - {68 * _BARW:.3f}px)")
    _LTX_MAX = (_tbl_chars * 0.60205 * 0.0154 * 1200 - 68) * _BARW
    _PAD2 = int(3 * _LTX_MAX + 8)

    # ---- lanes / bars (every mask, tagged .cmb-{m}) ----
    lanes = [f'<div class="lane" style="top:{tops[0]}px;'
             f'height:{tops[max(i for i in range(n) if is_stat[i])] + STAT_H - tops[0]}px;"></div>']
    ticks, grow_css = [], []
    for i, kind in enumerate(order):
        h, top = heights[i], tops[i]
        lo, hi, rng, step, pct_scale = lane_geo[kind]
        fills = []
        # the lane's members in value-column (label-stack) order — drives
        # the Sort-mode hover chips, the line's start, and the lane badge
        if kind == "+/-":
            _vrows = ["+/-"]
        elif kind == "DR":
            _vrows = ["DR", "OR"]
        elif kind in COMBO:
            _vmk, _vpct = COMBO[kind]
            _vrows = ([_vpct] if _vpct else []) + [kind, _vmk]
        else:
            _vrows = [kind]
        for m in MASKS:
            am = avgs[m]

            def val(t, k):
                return am[t][k] if am[t] is not None else None
            # every bar's left comes from its team's --x{j} variable, so
            # the sort states move whole columns with a handful of rules
            bar_geo = (f"left:calc(var(--x{{j}}) - {hw * 100:.2f}%);"
                       f"width:{2 * hw * 100:.2f}%;")
            if kind == "+/-":
                for j, t in enumerate(codes):
                    v = val(t, "+/-")
                    if v is None:
                        continue
                    fills.append(
                        f'<div class="fl bar {_cmb_cls(m, t)}" style="{bar_geo.format(j=j)}'
                        f'top:{(1 - abs(v) / hi) * 100:.2f}%;bottom:0;'
                        f'background:{"#2ecc55" if v >= 0 else "#e04545"};"></div>')
            elif kind == "DR":
                # DR from the baseline with OR stacked on top: the bar's
                # total height is DR+OR = total rebounds (the lane's sort)
                for j, t in enumerate(codes):
                    vd, vo = val(t, "DR"), val(t, "OR")
                    if vd is None:
                        continue
                    fills.append(
                        f'<div class="fl bar {_cmb_cls(m, t)}" style="{bar_geo.format(j=j)}'
                        f'top:{(1 - vd / hi) * 100:.2f}%;bottom:0;'
                        f'background:{hex_by_kind["DR"]};"></div>')
                    fills.append(
                        f'<div class="fl bar {_cmb_cls(m, t)}" style="{bar_geo.format(j=j)}'
                        f'top:{(1 - (vd + vo) / hi) * 100:.2f}%;'
                        f'bottom:{vd / hi * 100:.2f}%;'
                        f'background:{hex_by_kind["OR"]};"></div>')
            elif kind in COMBO:
                _mk, _pct = COMBO[kind]

                # the trio's bars overlap at each x, so the z-stack follows
                # VALUE: the taller a bar renders, the further back it sits
                # — the shortest is always fully visible in front
                def _z(frac):
                    return 100 - round(max(0.0, min(1.0, frac)) * 98)
                for j, t in enumerate(codes):
                    va, vm = val(t, kind), val(t, _mk)
                    if va is None:
                        continue
                    for v, c in ((va, hex_by_kind[kind]), (vm, hex_by_kind[_mk])):
                        frac = (v - lo) / rng
                        fills.append(
                            f'<div class="fl bar {_cmb_cls(m, t)}" style="{bar_geo.format(j=j)}'
                            f'top:{(1 - frac) * 100:.2f}%;bottom:0;'
                            f'z-index:{_z(frac)};background:{c};"></div>')
                if _pct is not None:
                    # the % as half-width bars on the pct scale — per-team
                    # elements follow the sort vars natively, and their z
                    # comes from the same value rule as the counts' bars
                    plo, phi = pct_scale
                    prng = phi - plo
                    for j, t in enumerate(codes):
                        v = val(t, _pct)
                        if v is None:
                            continue
                        frac = (v - plo) / prng
                        fills.append(
                            f'<div class="fl bar {_cmb_cls(m, t)}" style="'
                            f'left:calc(var(--x{j}) - {hw * 50:.2f}%);'
                            f'width:{hw * 100:.2f}%;'
                            f'top:{(1 - frac) * 100:.2f}%;bottom:0;'
                            f'z-index:{_z(frac)};'
                            f'background:{hex_by_kind[_pct]};"></div>')
            else:
                for j, t in enumerate(codes):
                    v = val(t, kind)
                    if v is None:
                        continue
                    fills.append(
                        f'<div class="fl bar {_cmb_cls(m, t)}" style="{bar_geo.format(j=j)}'
                        f'top:{(1 - (v - lo) / rng) * 100:.2f}%;bottom:0;'
                        f'background:{hex_by_kind[kind]};"></div>')

            # Sort mode's hover chips: the hovered team's values ride at
            # its column in this lane (group members stacked in value-
            # column order, like the single-lane 2x view's chips). Lane
            # children, so they follow the LANE's own sort; revealed per
            # (active combo, hovered team) in gsort_css.
            for j, t in enumerate(codes):
                if am[t] is None:
                    continue
                for _r, _k in enumerate(_vrows):
                    _v = am[t][_k]
                    _vt = f"{_v:+.1f}" if _k == "+/-" else f"{_v:.0f}"
                    fills.append(
                        f'<div class="tv lvv lvv-{j} lvm-{m[0]}{m[1]}" '
                        f'style="left:var(--x{j});top:{13 * _r}px;'
                        f'color:{hex_by_kind[_k]};">{_vt}</div>')
            # ... and the matching RANK stack at the base of the line
            # (below the lane, where the line ends), same member order
            # and colors. Ranks are per view, so per (mask, conference).
            _nvr = len(_vrows)
            for _cf in CONFS:
                _rkv = ranks[(m, _cf)]
                for j, t in enumerate(codes):
                    if am[t] is None or (_cf != "a" and _conf(t) != _cf):
                        continue
                    for _r, _k in enumerate(_vrows):
                        rk = _rkv[_k].get(t)
                        if rk is None:
                            continue
                        fills.append(
                            f'<div class="tv lrk lrk-{j} '
                            f'lrkm-{m[0]}{m[1]}{_cf}" '
                            f'style="left:var(--x{j});'
                            f'bottom:{13 * (_nvr - 1 - _r) - (_PAD2 - 6)}px;'
                            f'color:{hex_by_kind[_k]};">{rk}</div>')

        ax_top, ax_h = top - h, 2 * h
        grow_css.append(
            f".wrap:has(.lbl-{i}:hover) .lane-{i}"
            f"{{top:{ax_top:.1f}px!important;height:{ax_h:.1f}px!important;z-index:2;}}")
        _srts = [s for s in lane_sorts[i] if s != _PM_S]
        if _srts:
            # sorting by ANY of this lane's stats pops the lane into the 2x
            # spotlight (grown lane, ticks shown; the under-lane tricodes
            # sit at the grown lane's baseline = ax_top + ax_h)
            grow_css.append(
                _union(_srts, f".wrap .lane-{i}")
                + f"{{opacity:1;top:{ax_top:.1f}px!important;"
                f"height:{ax_h:.1f}px!important;z-index:2;}}"
                + _union(_srts, f".wrap .zt-{i}") + ","
                + _union(_srts, f".wrap .zg-{i}") + "{display:block;}"
                + _union(_srts, ".wrap .txs")
                + f"{{display:block;top:{ax_top + ax_h + 5:.0f}px;}}")
            # the label cycle's FIRST state (any member's e-s radio, via
            # the lane's sp-{i} class): the same 2x spotlight in the
            # default column order — grown lane, ticks, others dim (the
            # .spot global rule), bottom tricodes stay put
            grow_css.append(
                f".st:has(.sp-{i}:checked) ~ .wrap .lane-{i}"
                f"{{opacity:1;top:{ax_top:.1f}px!important;"
                f"height:{ax_h:.1f}px!important;z-index:2;}}"
                f".st:has(.sp-{i}:checked) ~ .wrap .zt-{i},"
                f".st:has(.sp-{i}:checked) ~ .wrap .zg-{i}{{display:block;}}")
            # per member: its own cycle's twins, and the square on only
            # the active member's label stack (both active states)
            for _s2 in _srts:
                grow_css.append(
                    f".st:has(#e-s{_s2}:checked) ~ .wrap .lbls-{_s2}{{display:block;}}"
                    f".st:has(#srt-{_s2}:checked) ~ .wrap .lblu-{_s2}{{display:block;}}"
                    f".st:has(#e-s{_s2}:checked) ~ .wrap .lm-{_s2},"
                    f".st:has(#srt-{_s2}:checked) ~ .wrap .lm-{_s2}"
                    "{box-shadow:0 0 0 1px currentColor;}"
                    f".st:has(#e-s{_s2}:checked) ~ .wrap .zl-{_s2},"
                    f".st:has(#srt-{_s2}:checked) ~ .wrap .zl-{_s2}"
                    "{display:block;}")
        t = lo
        while t <= hi + 1e-9:
            fy = ax_top + (1 - (t - lo) / rng) * ax_h
            ticks.append(f'<div class="zt zt-{i}" style="top:{fy:.1f}px;">{int(t)}</div>')
            ticks.append(f'<div class="zg zg-{i}" style="top:{fy:.1f}px;"></div>')
            t += step
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
        # +/- can't be closed: its cells and badge carry no lc target
        _lfor = "" if kind == "+/-" else f'for="lc-{i}" '
        for j, t in enumerate(codes):
            fills.append(
                f'<div class="ldl ldl-{j}" style="left:var(--x{j});"></div>'
                f'<label class="lwc lwc-{j} lwcc-{"e" if t in _TEAM_EAST else "w"}" '
                f'{_lfor}'
                f'style="left:calc(var(--x{j}) - {50 / N:.3f}%);'
                f'width:{100 / N:.3f}%;"></label>')
        # the lane's stat name(s) as its Sort-mode badge at the upper
        # LEFT of the lane (the label column itself is hidden there);
        # a group's labels flatten onto one line, single-space
        # separated. The badge is also the collapsed lane's SHOW control
        fills.append(f'<label class="lzl" {_lfor}>' + " ".join(
            f'<span style="color:{hex_by_kind[_k]};">{_k}</span>'
            for _k in _vrows) + "</label>")
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
    _SH2 = 2 * STAT_H
    _TS = 32
    _t2, _T2 = float(_TS), []
    for i in range(n):
        _T2.append(_t2)
        _t2 += _SH2 + _PAD2
    _H2 = _t2
    _GS = ".st:has(#gsort:checked)"
    # collapsing a lane reclaims its vertical space IN FULL: every
    # lane's top (and the plot height) subtracts the whole slots of the
    # collapsed lanes above it via per-lane --c{i} flags (0/1), so any
    # combination of collapsed lanes lays out right. The collapsed
    # lane's label parks on the top label line instead.
    _R = [_SH2 + _PAD2 for _ in range(n)]
    _call = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in range(n))
    gsort_css = (
        _GS + f" ~ .wrap .plot{{height:calc({_H2:.0f}px{_call});}}"
        # a flat reading layout: no dimming, no member-state furniture,
        # no value column, and the labels/hover cells go inert
        + _GS + " ~ .wrap .lane{opacity:1!important;transition-delay:0s;}"
        + _GS + " ~ .wrap .gvcol{display:none!important;}"
        + _GS + " ~ .wrap .zt," + _GS + " ~ .wrap .zg,"
        + _GS + " ~ .wrap .txs," + _GS + " ~ .wrap .zl,"
        + _GS + " ~ .wrap .dl," + _GS + " ~ .wrap .gu"
        "{display:none!important;}"
        + _GS + " ~ .wrap .tx{display:none;}"
        + _GS + " ~ .wrap .wc{pointer-events:none;}"
        # the label column is hidden outright — each lane wears its
        # stat name(s) as a badge at its upper right instead
        + _GS + " ~ .wrap .lbl{display:none!important;}"
        + _GS + " ~ .wrap .lane .ltx{display:block;}"
        + _GS + " ~ .wrap .lane .lwc{display:block;}"
        + _GS + " ~ .wrap .lane .lzl{display:block;}"
        + _GS + f" ~ .wrap .lane .bar{{transform:scaleX({_BARSX:.4f});}}")
    # hovering a team's column (or its tricode) in ANY lane lights the
    # team up everywhere: line segments at its position in every lane,
    # glowing tricodes, and its box score row tinted
    for j in range(N):
        gsort_css += (
            f".wrap:has(.lwc-{j}:hover) .ldl-{j}{{display:block;}}"
            f".wrap:has(.lwc-{j}:hover) .ltx-{j}"
            "{font-weight:bold;}"
            f".wrap:has(.lwc-{j}:hover) ~ .bxwrap .br-{j}"
            "{background:rgba(255,255,255,.24);}")
    for i in range(n):
        _up = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in range(i))
        gsort_css += (_GS + f" ~ .wrap .lane-{i}"
                      f"{{top:calc({_T2[i]:.0f}px{_up})!important;"
                      f"height:{_SH2:.0f}px!important;}}")
    # which head columns sit under each lane's badge: estimated badge
    # pixel span vs the narrowest responsive pitch (the 900px clamp)
    _pitch_min = (_tbl_chars * 0.60205 * 0.0154 * 900 - 68) / N

    def _badge_rows(kind):
        if kind == "+/-":
            return ["+/-"]
        if kind == "DR":
            return ["DR", "OR"]
        if kind in COMBO:
            _bmk, _bpct = COMBO[kind]
            return ([_bpct] if _bpct else []) + [kind, _bmk]
        return [kind]
    # estimated badge pixel widths (also the top label line's slots);
    # +27px: the value stack hangs left of the line, so the badge also
    # yields when the chips (not just the line) would land on it
    _BW = [16 + len(" ".join(_badge_rows(k))) * 7.8 for k in order]
    _ncov = [max(1, int((_BW[_i2] + 27) / _pitch_min + 0.5))
             for _i2 in range(n)]
    _dodge: dict[int, list[str]] = {}
    for m in MASKS:
        for cf in CONFS:
            _pre = _gate(m, cf) + ":has(#gsort:checked)"
            for i, kind in enumerate(order):
                _k0 = ((COMBO[kind][1] or kind) if kind in COMBO else kind)
                _pos = sort_pos[(m, cf, _k0)]
                gsort_css += (_pre + f" ~ .wrap .lane-{i}{{"
                              + _xvars(_pos) + "}")
                # a hovered team whose line/stack lands on this lane's
                # badge hides the badge (this lane only — and not when
                # the lane is collapsed, since no line shows there)
                for j, t in enumerate(codes):
                    if _pos[t] < _ncov[i]:
                        _dodge.setdefault(j, []).append(
                            f"{_pre}:not(:has(#lc-{i}:checked))"
                            f" ~ .wrap:has(.lwc-{j}:hover)"
                            f" .lane-{i} .lzl")
            # the rank stacks at the line's base: this view's ranks only
            gsort_css += "".join(
                f"{_pre} ~ .wrap:has(.lwc-{j}:hover)"
                f" .lrk-{j}.lrkm-{m[0]}{m[1]}{cf}{{display:block;}}"
                for j in range(N))
        # teams with no games in this combo are suppressed entirely:
        # no bars (no cmb nodes), no tricode, and no hover cell
        _g = f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
        _hid = [j for j, t in enumerate(codes) if avgs[m][t] is None]
        if _hid:
            gsort_css += (",".join(f"{_g} ~ .wrap .ltx-{j},{_g} ~ .wrap .lwc-{j}"
                                   for j in _hid)
                          + "{display:none!important;}")
        # the hover chips: shown for the active combo's values only,
        # on the hovered team's columns
        gsort_css += "".join(
            f"{_g} ~ .wrap:has(.lwc-{j}:hover) .lvv-{j}.lvm-{m[0]}{m[1]}"
            "{display:block;}" for j in range(N))
    # the badge-hide bodies
    for j, _sels in _dodge.items():
        gsort_css += ",".join(_sels) + "{display:none;}"
    # "Close": sits in the next slot after the parked labels, appears
    # whenever at least one closable lane is open
    gsort_css += (
        ".wrap .lcls{left:calc(6px" + "".join(
            f" + var(--c{k},0)*{_BW[k] + 10:.0f}px" for k in range(n))
        + ");}"
        + ",".join(f".st:has(#lc-{i}:not(:checked)) ~ .wrap .lcls"
                   for i in range(n) if order[i] != "+/-")
        + "{display:block;}")
    # per-lane collapse (Sort mode only): a checked lane hides all its
    # content but keeps the badge, which turns clickable to restore it
    for i in range(n):
        _lci = _GS + f":has(#lc-{i}:checked) ~ .wrap .lane-{i}"
        # the collapsed lane parks on the top label line; its badge
        # takes the next open slot (after lower-index collapsed lanes)
        _slot = "".join(f" + var(--c{k},0)*{_BW[k] + 10:.0f}px"
                        for k in range(i))
        gsort_css += (
            _GS + f":has(#lc-{i}:checked) ~ .wrap{{--c{i}:1;}}"
            + _lci + " > :not(.lzl){display:none!important;}"
            + _lci + "{top:2px!important;height:22px!important;"
            "background:none!important;}"
            + _lci + " .lzl{pointer-events:auto;cursor:pointer;"
            f"left:calc(6px{_slot});}}")

    # ---- per-team columns: hover cells, tricode axis, and the
    # right-hand value column. Each team's values live in a .gvcol-{j}
    # wrapper (shown only when that team is selected/hovered); inside,
    # every combination's values are tagged .cmb-{m} (shown only for the
    # active toggle state) — so a value shows only when BOTH gates open. ----
    radios = ['<input type="radio" class="bsel bsel-none" name="bsel" id="g-none">']
    strips, tlabels, dl_css, gvcols = [], [], [], []
    for j, t in enumerate(codes):
        sel = " checked autofocus" if j == 0 else ""
        radios.append(f'<input type="radio" class="bsel" name="bsel" id="g-{j}"{sel}>')
        cell = (f'left:calc(var(--x{j}) - {50 / N:.3f}%);'
                f'width:{100 / N:.3f}%;')
        strips.append(f'<label class="wc wc-{j}" style="{cell}" for="g-{j}"></label>')
        strips.append(f'<label class="gu gu-{j}" style="{cell}" for="g-none"></label>')
        strips.append(f'<div class="dl dl-{j}" style="left:var(--x{j});"></div>')
        tcol = _dim_hex(_TEAM_BRAND_COLORS.get(t, "#999"))
        _tag, _end = ("a", "</a>") if _team_href(t) else ("div", "</div>")
        _hattr = f' href="{_team_href(t)}"' if _team_href(t) else ""
        tlabels.append(f'<{_tag} class="tx tx-{j}"{_hattr} '
                       f'style="left:var(--x{j});color:{tcol};">{t}{_end}')
        # the same tricode repeated just under the magnified sorted lane
        # (its top is set, and it is revealed, per active sort in grow_css)
        # so a sorted lane reads its ranking right at the bars
        tlabels.append(f'<div class="txs" style="left:var(--x{j});'
                       f'color:{tcol};">{t}</div>')
        # value column: one set of values per combination
        gvs = []
        for m in MASKS:
            a = avgs[m][t]
            if a is None:
                continue
            for gi, gkind in enumerate(order):
                ay = tops[gi] + heights[gi] - 6.4
                rows_ = (((COMBO[gkind][1], -32), (gkind, -16), (COMBO[gkind][0], 0))
                         if gkind in COMBO and COMBO[gkind][1]
                         else ((gkind, -16), (COMBO[gkind][0], 0)) if gkind in COMBO
                         else ((gkind, 0),))
                # values are DISPLAY-ONLY (sorting lives on the labels, like
                # the team page); the .gvt span hugs the digits so the
                # active-sort circle centres on the numeric text. Only the
                # "+/-" text prefix stays clickable: it is that lane's label,
                # and restores the default order.
                for k, dy in rows_:
                    v = a[k]
                    txt = f"{v:+.1f}" if k == "+/-" else f"{v:.0f}"
                    s = sort_idx[(gi, k)]
                    if k == "+/-":
                        # combined "+/- <value>" (single space), left edge
                        # on the label column, vertically centred (+2px) in
                        # the +/- lane
                        gvs.append(
                            f'<div class="gv vk-{s} {_cmb_cls(m, t)}" '
                            f'style="top:{tops[gi] + heights[gi] / 2 + 2:.0f}px;'
                            f'left:calc(100% + 4px);right:auto;margin-left:0;'
                            f'width:auto;text-align:left;font-size:15px;'
                            f'color:{hex_by_kind[k]};">'
                            f'<label class="pml" for="srt-{s}">+/-</label>'
                            f'&nbsp;<span class="gvt">{txt}</span></div>')
                    else:
                        gvs.append(
                            f'<div class="gv vk-{s} {_cmb_cls(m, t)}" '
                            f'style="top:{ay + dy:.0f}px;'
                            f'color:{hex_by_kind[k]};">'
                            f'<span class="gvt">{txt}</span></div>')
                        # while the lane's 2x is up, the hovered team's
                        # values ride ON the big plot at the team's column
                        # (left follows the sort vars, so they drag across
                        # as the pointer moves team to team). A grouped
                        # lane shows ALL its members, stacked in value-
                        # column order. Team gating is free: the chips
                        # live in this team's .gvcol.
                        _row = lane_sorts[gi].index(s)
                        gvs.append(
                            f'<div class="tv tvl-{gi} tvm-{m[0]}{m[1]}" '
                            f'style="left:var(--x{j});'
                            f'top:{tops[gi] - heights[gi] + 3 + 13 * _row:.0f}px;'
                            f'color:{hex_by_kind[k]};">{txt}</div>')
        gvcols.append(f'<div class="gvcol gvcol-{j}">' + "".join(gvs) + "</div>")
        dl_css.append(
            f".wrap:has(.wc-{j}:hover) .dl-{j},"
            f".st:has(#g-{j}:checked) ~ .wrap:not(:has(.wc:hover)) .dl-{j},"
            f".wrap:has(.wc-{j}:hover) .gvcol-{j},"
            f".st:has(#g-{j}:checked) ~ .wrap:not(:has(.wc:hover)) .gvcol-{j}{{display:block;}}"
            f".wrap:has(.wc-{j}:hover) .tx-{j},"
            f".st:has(#g-{j}:checked) ~ .wrap:not(:has(.wc:hover)) .tx-{j}"
            f"{{text-shadow:0 0 7px currentColor;font-weight:bold;}}"
            f".st:has(#g-{j}:checked) ~ .wrap:not(:has(.wc:hover)) .gu-{j}{{display:block;}}"
            f".st:has(#g-{j}:checked) ~ .bxwrap .br-{j},"
            f".wrap:has(.wc-{j}:hover) ~ .bxwrap .br-{j}{{background:rgba(255,255,255,.24);}}")

    # ---- lane labels + trio stacks. EVERY label is a control: clicking
    # it sorts by that exact stat (its value's own srt radio), hovering it
    # displays the magnified (2x) lane and squares the label. A trio's
    # three labels all carry .lbl-{i}, so hovering any of them magnifies
    # the whole group's lane. ----
    lane_radios = []
    labels = []

    def _lbl(i, key, top):
        # the label cycle, like the team page — PER MEMBER: rest -> 2x
        # (e-s{s}, square on this member only) -> sorted by this member
        # (srt-{s}) -> rest, via stacked twins revealed per state. The
        # .zl badge rides above the 2x plot's upper right in both states.
        s = sort_idx[(i, key)]
        g = f'style="top:{top:.0f}px;color:{hex_by_kind[key]};"'
        return (f'<div class="zl zl-{s}" style="top:'
                f'{tops[i] - heights[i] - 20:.0f}px;'
                f'color:{hex_by_kind[key]};">{key}</div>'
                f'<label class="lbl lbl-{i} lm-{s}" for="e-s{s}" {g}>{key}</label>'
                f'<label class="lbl lbl-{i} lm-{s} lbls lbls-{s}" for="srt-{s}" {g}>{key}</label>'
                f'<label class="lbl lbl-{i} lm-{s} lblu lblu-{s}" for="srt-{_PM_S}" {g}>{key}</label>')

    for i, kind in enumerate(order):
        ay = tops[i] + heights[i] - 6.4
        if kind == "+/-":
            # no separate label — the value cell carries the combined
            # "+/-<value>" text, itself the +/- sort button
            continue
        if kind in COMBO:
            _mk, _pct = COMBO[kind]
            if _pct is not None:
                labels.append(_lbl(i, _pct, ay - 32))
            labels.append(_lbl(i, kind, ay - 16))
            labels.append(_lbl(i, _mk, ay))
        else:
            labels.append(_lbl(i, kind, ay))

    # hovering any of a lane's labels magnifies that lane; the active-sort
    # circle marks the value column, not the label
    spotlight_css = "".join(
        f".wrap:has(.lbl-{i}:hover) .lane-{i}{{opacity:1;}}"
        f".wrap:has(.lbl-{i}:hover) .zt-{i},"
        f".wrap:has(.lbl-{i}:hover) .zg-{i}{{display:block;}}"
        for i in sel_idx)

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
            for lab, key, w, colored, invert in _BOX_COLS:
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
                parts.append(cell)
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
        # its leading gap, so the shading hugs the digits
        _cstart, _cw = _off[_col]
        _left = _cstart + 1
        _right = _cstart + _cw
        col_stripes.append(f'<div class="bxhl srt-{_sidx}" '
                           f'style="left:{_left}ch;width:{_right - _left}ch;"></div>')
        sort_css += (f".st:has(#srt-{_sidx}:checked) ~ .bxwrap"
                     f" .bxhl.srt-{_sidx}{{display:block;}}")
    # the +/- HEADER stays at its natural right-aligned spot (half a
    # character left of the shifted values)
    box_table = (f'<div class="bx"><div class="bx-head">{_html.escape(hdr)}</div>'
                 + "".join(mask_blocks) + "".join(col_stripes) + "</div>")

    # ---- the filter buttons: three combinable groups ----
    # the league buttons can't show per-team game numbers, so the thirds
    # are named by the breaks that bound them (fixed ranges as fallback)
    if _breaks:
        _SEG_BTNS = [(1, "to Cup"), (2, "to ASB"), (4, "post ASB"),
                     (7, "Regular"), (8, "Playoffs"), (15, "All")]
    else:
        _SEG_BTNS = [(1, "1:27"), (2, "28:54"), (4, "55:82"),
                     (7, "Regular"), (8, "Playoffs"), (15, "All")]
    # three radio groups: the season segment (exactly one), the game type
    # (none or one of OT/Clutch) and the conference (none or one of
    # East/West) — the filters COMBINE (e.g. Regular + Clutch + East)
    seg_checkboxes = "".join(
        f'<input type="radio" class="seg" name="seg" id="seg-m{mask}"'
        f'{" checked" if mask == 15 else ""}>'
        for mask, _ in _SEG_BTNS)
    seg_checkboxes += (
        '<input type="radio" class="seg" name="gt" id="gt-a" checked>'
        '<input type="radio" class="seg" name="gt" id="gt-o">'
        '<input type="radio" class="seg" name="gt" id="gt-c">'
        '<input type="radio" class="seg" name="cf" id="cf-a" checked>'
        '<input type="radio" class="seg" name="cf" id="cf-e">'
        '<input type="radio" class="seg" name="cf" id="cf-w">')
    # every combo-tagged element is hidden by default; the checked TRIPLE
    # of filter states reveals just its own combo's nodes
    combo_css = '[class*="cmb-"]{display:none;}'
    for m in MASKS:
        for cf in CONFS:
            st = _gate(m, cf)
            _c = f"cmb-{m[0]}{m[1]}{cf}"
            combo_css += (f"{st} ~ .wrap .{_c},"
                          f"{st} ~ .bxwrap .{_c}{{display:block;}}")
    # active-button highlights, one per group
    _hl = "{color:#ccc;background:rgba(255,255,255,.16);}"
    for mask, _ in _SEG_BTNS:
        combo_css += (f".st:has(#seg-m{mask}:checked) ~ .toggles "
                      f".tg-m{mask}{_hl}")
    for gid in ("gt-o", "gt-c", "cf-e", "cf-w"):
        combo_css += (f".st:has(#{gid}:checked) ~ .toggles .tg-{gid},"
                      f".st:has(#{gid}:checked) ~ .toggles .tgu-{gid}{_hl}")
        # the toggle-off twin sits over its button while it is active,
        # so a second click releases the filter (back to the group's
        # neutral radio)
        combo_css += (f".st:has(#{gid}:checked) ~ .toggles "
                      f".tgu-{gid}{{display:block;}}")
    # a conference filter makes the hidden teams' hover cells inert and
    # dims their tricodes (their bars/rows/values are combo-hidden)
    for j, t in enumerate(codes):
        _other = "cf-w" if t in _TEAM_EAST else "cf-e"
        combo_css += (f".st:has(#{_other}:checked) ~ .wrap .wc-{j}"
                      f"{{pointer-events:none;}}"
                      f".st:has(#{_other}:checked) ~ .wrap .tx-{j}"
                      f"{{opacity:.25;}}")

    def _tgl(gid, label):
        # a toggling button: the base label turns the filter on; its
        # absolutely-stacked twin (revealed while on) turns it off
        _off = "gt-a" if gid.startswith("gt") else "cf-a"
        return (f'<span class="tgw"><label class="tg tg-{gid}"'
                f' for="{gid}">{label}</label>'
                f'<label class="tg tgu tgu-{gid}" for="{_off}">'
                f'{label}</label></span>')
    seg_toggles = "".join(
        f'<label class="tg tg-m{mask}" for="seg-m{mask}">{label}</label>'
        for mask, label in _SEG_BTNS[:-1])
    seg_toggles += (_tgl("cf-e", "East") + _tgl("cf-w", "West")
                    + _tgl("gt-o", "OT") + _tgl("gt-c", "Clutch"))
    seg_toggles += '<label class="tg tg-m15" for="seg-m15">All</label>'

    css = f"""
body{{background:#000;color:#b6b6b6;font-family:'DejaVu Sans',sans-serif;margin:0 0 24px;}}
/* the title centres on the box score's span (26px + table width), not
   the viewport */
h1{{font-size:22px;font-weight:normal;color:#b6b6b6;text-align:center;
  width:{TW};margin:14px 0 10px 26px;}}
.wrap{{position:relative;width:{PW};
  margin:0 0 0 26px;}}
.plot{{position:relative;height:{PLOT_H}px;}}
.lane{{position:absolute;left:0;right:0;background:rgba(255,255,255,.035);
  /* the 2x spotlight closes on a one-second grace after mouse-out
     (the delayed 0s transitions fire late); opening is instant — any
     hover or active state zeroes the delay below */
  transition:top 0s 1s,height 0s 1s,opacity 0s 1s,z-index 0s 1s;}}
.wrap:has(.lbl:hover) .lane,
.st:has(.srt-on:checked) ~ .wrap .lane,
.st:has(.spot:checked) ~ .wrap .lane{{transition-delay:0s;}}
.fl{{position:absolute;}}
/* a touch of transparency so stacked/overlapping bars read as layers */
.bar{{opacity:.85;}}
/* labels cycle rest -> 2x -> sorted -> rest via stacked twins;
   hovering previews the magnified lane and squares the label */
.lbl{{position:absolute;right:-48px;transform:translateY(-50%);cursor:pointer;
  white-space:nowrap;padding:1px 6px;font-size:15px;line-height:1.05;z-index:5;}}
.lbl:hover{{box-shadow:0 0 0 1px currentColor;}}
.lbls,.lblu{{display:none;z-index:6;}}
/* the active member's name above the 2x plot's upper left */
.zl{{display:none;position:absolute;left:6px;font-size:14px;
  line-height:1;z-index:6;pointer-events:none;}}
/* the hovered/pinned team's value ON the 2x plot at the team's column
   (a .rkv-style chip; left follows the sort vars) */
.tv{{display:none;position:absolute;transform:translateX(-50%);
  font-size:11px;line-height:1;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);white-space:nowrap;pointer-events:none;
  z-index:7;font-family:'DejaVu Sans Mono',monospace;}}
.lbln{{position:absolute;right:-48px;transform:translateY(-50%);
  white-space:nowrap;padding:1px 6px;font-size:15px;line-height:1.05;z-index:5;}}
.zt{{display:none;position:absolute;right:100%;margin-right:8px;transform:translateY(-50%);
  font-size:11px;color:#ccc;z-index:5;}}
.zg{{display:none;position:absolute;left:0;right:0;height:1px;background:rgba(255,255,255,.18);z-index:1;}}
.tx{{position:absolute;top:100%;margin-top:16px;writing-mode:vertical-rl;
  text-orientation:mixed;transform:translateX(-50%);
  font-size:15.4px;font-family:'DejaVu Sans Mono',monospace;}}
/* per-team tricode shown just under the magnified sorted lane */
.txs{{display:none;position:absolute;writing-mode:vertical-rl;
  text-orientation:mixed;transform:translateX(-50%);
  font-size:13px;font-family:'DejaVu Sans Mono',monospace;z-index:3;}}
.wc{{position:absolute;top:0;height:{PLOT_H}px;z-index:5;cursor:crosshair;}}
.wc:hover{{background:rgba(255,255,255,.06);}}
.gu{{display:none;position:absolute;top:0;height:{PLOT_H}px;z-index:6;}}
.dl{{display:none;position:absolute;top:0;bottom:0;width:2px;margin-left:-1px;
  background:#C0C0C0;box-shadow:0 0 7px rgba(192,192,192,.85);z-index:-1;}}
/* the value column: .gvcol is the team gate (hidden until selected),
   the .gv inside are the combination gate ([class*=cmb-] hides them,
   the active toggle rule reveals) — both must open for a value to show */
.gvcol{{display:none;}}
.gv{{position:absolute;left:100%;margin-left:30px;
  transform:translateY(calc(-50% - .8px));line-height:1.05;
  font-size:15px;white-space:nowrap;z-index:5;
  /* fixed-width, right-aligned numeric column: every value (including
     the signed, decimal +/-) shares the same left AND right edges */
  width:38px;text-align:right;}}
.wrap:has(.lbl:hover) .lane{{opacity:.15;}}
.bsel{{position:fixed;left:-30px;opacity:0;width:2px;height:2px;}}
.bsel-none{{display:none;}}
.seg,.srt{{display:none;}}
/* values are display-only (sorting lives on the labels); .gvt hugs the
   digits so the active-sort circle centers on the number (negative
   margins cancel the padding so the right-aligned column stays put).
   Only the "+/-" prefix (.pml) is clickable — the +/- lane's label,
   restoring the default order */
.gv{{pointer-events:none;}}
.gvt{{display:inline-block;padding:1px 5px;margin:-1px -5px;
  border-radius:50%;}}
.pml{{pointer-events:auto;cursor:pointer;}}
.pml:hover{{box-shadow:0 0 0 1px currentColor;}}
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
.lwc{{display:none;position:absolute;top:0;height:calc(100% + {_PAD2}px);
  z-index:120;cursor:crosshair;}}
.lwc:hover{{background:rgba(255,255,255,.06);}}
/* the line runs the lane's full height, breaks for the team name at
   the baseline, then CONTINUES below it through the rest of the
   padding; painted on the BOTTOM layer (behind the bars); the hovered
   team's value stack hangs on its LEFT side, from the lane's top */
.ldl{{display:none;position:absolute;top:0;bottom:0;
  width:2px;margin-left:-1px;background:#C0C0C0;opacity:.75;
  z-index:-1;pointer-events:none;}}
.ldl::after{{content:"";position:absolute;left:0;width:2px;
  background:#C0C0C0;
  top:calc(100% + {3 - 1.9 * 68 * _BARW:.2f}px
    + {1.9 * _tbl_chars * 0.60205 * 0.0154 * _BARW:.6f}*clamp(900px,100vw,1200px));
  height:calc({_PAD2 - 5 + 1.9 * 68 * _BARW:.2f}px
    - {1.9 * _tbl_chars * 0.60205 * 0.0154 * _BARW:.6f}*clamp(900px,100vw,1200px));}}
.lvv,.lrk{{transform:translateX(calc(-100% - 3px));}}
/* Sort mode's per-lane stat badge, left-justified at the lane's upper
   left; a group's labels sit flattened on one line */
.lzl{{display:none;position:absolute;top:2px;left:6px;text-align:left;
  font-size:14px;line-height:1.15;z-index:6;pointer-events:none;
  white-space:nowrap;padding:1px 4px;border-radius:3px;
  background:rgba(0,0,0,.72);}}
/* "Close" on the top label line, after the parked labels: shown while
   any closable lane is open; clicking resets the lc form = all closed */
.lcls{{display:none;position:absolute;top:4px;font-size:14px;
  line-height:1.15;padding:1px 4px;border-radius:3px;
  background:rgba(0,0,0,.72);color:#aaa;cursor:pointer;z-index:6;
  user-select:none;white-space:nowrap;}}
.lcls:hover{{color:#ddd;}}
.st:has(#cf-e:checked) ~ .wrap .ltxc-w,
.st:has(#cf-e:checked) ~ .wrap .lwcc-w,
.st:has(#cf-w:checked) ~ .wrap .ltxc-e,
.st:has(#cf-w:checked) ~ .wrap .lwcc-e{{display:none!important;}}
/* the segment toggles sit in the middle band between chart and table */
.toggles{{margin:80px 0 8px 26px;display:flex;align-items:center;gap:12px;
  font-family:'DejaVu Sans Mono',monospace;font-size:14px;}}
.tglabel{{color:#888;padding-right:8px;}}
.tg{{cursor:pointer;color:#888;padding:4px 12px;border-radius:6px;
  border:1px solid rgba(255,255,255,.18);user-select:none;}}
.tg:hover{{color:#ddd;}}
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
  line-height:1.5;font-size:calc(clamp(900px, 100vw, 1200px) * 0.0154);
  /* no left padding: the text's left edge lands exactly at .bxwrap's
     own left (26px), matching the plot's lane edge above it */
  /* same width formula as the team season page's box card, so both
     pages' box scores render at the same width at any viewport */
  box-sizing:border-box;width:clamp(848px, 100vw - 52px, 1332px);
  white-space:pre;color:#a6a6a6;padding:10px 16px 10px 0;}}
/* same as the game/team pages' column-header rows, which render in the
   body text color — not the brighter game-title #e0e0e0 */
.bx-head{{color:#a6a6a6;order:-1;}}
.br{{display:block;}}
/* the sorted stat's column stripe over the box table */
.bxhl{{display:none;position:absolute;top:0;bottom:0;
  background:rgba(255,255,255,.22);pointer-events:none;}}
a.tx,.bx a{{text-decoration:none;color:inherit;}}
a.tx:hover,.bx a:hover{{text-decoration:underline;}}
""" + sort_css + combo_css + spotlight_css + "".join(grow_css) + "".join(dl_css) + gsort_css

    try:
        _y0, _y1 = season.split("-")
        full_season = f"{_y0}-{_y0[:2]}{_y1}"
    except Exception:
        full_season = season
    tab_title = f"NBA {full_season} Season Averages"
    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        f"<title>{tab_title}</title><style>{css}</style></head><body>"
        f"<h1>NBA {full_season}<br>Season Averages</h1>"
        f"<div class=\"st\">{''.join(radios)}{''.join(lane_radios)}"
        f"{seg_checkboxes}{srt_radios}</div>"
        '<div class="wrap"><div class="plot">'
        + "".join(lanes) + "".join(strips) + "".join(tlabels) + "".join(ticks)
        + '<label class="lcls" for="lclose">Close</label>'
        + f"</div>{''.join(labels)}{''.join(gvcols)}"
        + '</div>'
        + f'<div class="toggles"><span class="tglabel">Games</span>{seg_toggles}</div>'
        + f'<div class="bxwrap">{box_table}</div></body></html>'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path
