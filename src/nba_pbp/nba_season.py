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
from pathlib import Path

import pandas as pd

from nba_pbp import client
from nba_pbp.edge import league_history
from nba_pbp.plotting import _TEAM_BRAND_COLORS
from nba_pbp.plusminus import compute_official_box_score_for_game


# box table columns, same order and field widths as the game box score
# (`_box_score_player_line`). (label, key, width, colored, invert) —
# colored cells get the league-leader-gold / worst-red highlight; invert
# flips it for TO/PF where lower is better.
_GOLD, _RED = "goldenrod", "#ff4d4d"
_BOX_COLS = [
    ("MIN", "MIN", 3, False, False), ("PTS", "PTS", 4, True, False),
    ("+/-", "+/-", 6, True, False), ("FGM", "FGM", 4, True, False),
    ("FGA", "FGA", 4, True, False), ("FG%", "FG%", 5, True, False),
    ("3PM", "FG3M", 4, True, False), ("3PA", "FG3A", 4, True, False),
    ("3P%", "3P%", 5, True, False), ("FTM", "FTM", 4, True, False),
    ("FTA", "FTA", 4, True, False), ("FT%", "FT%", 5, True, False),
    ("OREB", "OREB", 5, True, False), ("DREB", "DREB", 5, True, False),
    ("REB", "REB", 4, True, False), ("AST", "AST", 4, True, False),
    ("STL", "STL", 4, True, False), ("BLK", "BLK", 4, True, False),
    ("TO", "TO", 3, True, True), ("PF", "PF", 3, True, True),
]
_SUM_KEYS = ["MIN", "PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
             "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF"]

# the four season segments, in bit order (bit i = 1 << i). The regular
# season splits at fixed game numbers 27 and 54.
SEG_LABELS = ["1:27", "28:54", "55:82", "Playoffs"]


def _team_segments(season: str, team: str) -> list[dict] | None:
    """For one team, a per-segment {sum, n, margin} from its cached box
    scores. Segments match the button labels: regular games 1-27, 28-54,
    55-82 (slices [0:27], [27:54], [54:]), then the playoffs. None if the
    team has no cached games."""
    hist = league_history(season)
    tg = hist[hist["TEAM_ABBREVIATION"] == team].sort_values("GAME_DATE")
    tg = tg[[client.has_cached_play_by_play(g) for g in tg["GAME_ID"]]]
    if tg.empty:
        return None
    ids = tg["GAME_ID"].astype(str)
    reg = tg[ids.str.startswith("002")]
    ply = tg[ids.str.startswith("004")]
    parts = [reg.iloc[0:27], reg.iloc[27:54], reg.iloc[54:], ply]
    segs = []
    for part in parts:
        s = {k: 0.0 for k in _SUM_KEYS}
        margin, nn, wins = 0.0, 0, 0
        for _, g in part.iterrows():
            box = compute_official_box_score_for_game(g["GAME_ID"], team)
            b = box[(box["teamTricode"] == team) & (box["MIN"] > 0)]
            for k in _SUM_KEYS:
                s[k] += float(b[k].sum())
            diff = float(g["PTS"] - g["OPP_PTS"])
            margin += diff
            wins += 1 if diff > 0 else 0
            nn += 1
        segs.append({"sum": s, "n": nn, "margin": margin, "wins": wins})
    return segs


def _combine(segs: list[dict], mask: int) -> dict | None:
    """Per-game averages over the segments selected by `mask`, or None
    when no game is selected."""
    S = {k: 0.0 for k in _SUM_KEYS}
    n, margin, wins = 0, 0.0, 0
    for bit in range(4):
        if mask & (1 << bit):
            seg = segs[bit]
            for k in _SUM_KEYS:
                S[k] += seg["sum"][k]
            n += seg["n"]
            margin += seg["margin"]
            wins += seg["wins"]
    if n == 0:
        return None
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
    seg_data = {}
    for t in teams:
        s = _team_segments(season, t)
        if s and sum(x["n"] for x in s) > 0:
            seg_data[t] = s
    # per-mask averages; mask 15 = all segments (full season) drives the
    # fixed team order and lane scales
    avgs = {m: {t: _combine(seg_data[t], m) for t in seg_data}
            for m in range(16)}
    codes = sorted(seg_data, key=lambda t: -avgs[15][t]["+/-"])
    N = len(codes)
    # the six selectable views, each a single precomputed segment mask:
    # the three regular-season thirds (1/2/4), the playoffs (8), the whole
    # regular season (7 = 1+2+4 = games 1-82), and everything (15)
    MASKS = [1, 2, 4, 7, 8, 15]

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
    # the game filter applies BEFORE the sort: each view mask gets its own
    # ranking from that view's averages. Teams with no games in a view
    # (non-playoff teams in the Playoffs view) sort after everyone,
    # keeping their resting order.
    sort_pos = {}   # (mask, stat key) -> {team: column position}
    for m in MASKS:
        for _i, key in sort_stats:
            def _key(t, _m=m, _s=key):
                a = avgs[_m][t]
                if a is None:
                    return (1, codes.index(t))
                return (0, a[_s] if _s in _LOWER_BETTER else -a[_s])
            ranked = sorted(codes, key=_key)
            sort_pos[(m, key)] = {t: p for p, t in enumerate(ranked)}
    # one radio per sortable stat; +/- (srt-{_PM_S}) is the checked default
    # (= the page's resting order). Non-default sorts carry .srt-on so
    # rules can test "some sort is active".
    srt_radios = "".join(
        f'<input type="radio" class="srt{"" if s == _PM_S else " srt-on"}"'
        f' name="sel" id="srt-{s}"'
        f'{" checked" if s == _PM_S else ""}>' for s in range(len(sort_stats)))
    srt_radios += '<input type="checkbox" class="srt" id="rank">'

    def _xvars(pos_of):
        return "".join(f"--x{j}:{(pos_of[codes[j]] + 0.5) / N * 100:.3f}%;"
                       for j in range(N))

    # default vars on .wrap (the DOM/+/- order); each other sort state
    # overrides them and re-orders the box table's rows via flex order.
    # While a sort is active, an invisible .gvu overlay sits on its value
    # cell targeting the +/- radio — so a second click turns the sort off
    # (radios can't untoggle themselves).
    sort_css = ".wrap{" + _xvars({t: j for j, t in enumerate(codes)}) + "}"
    undo_sorts = []
    for s, (i, key) in enumerate(sort_stats):
        if s == _PM_S:
            continue
        # one rule set per view mask: the ordering follows the ACTIVE
        # game filter's ranking, not the full-season one
        for m in MASKS:
            st = f".st:has(#seg-m{m}:checked):has(#srt-{s}:checked)"
            sort_css += st + " ~ .wrap{" + _xvars(sort_pos[(m, key)]) + "}"
            sort_css += "".join(
                f"{st} ~ .bxwrap .br-{j}"
                f"{{order:{sort_pos[(m, key)][codes[j]]};}}" for j in range(N))
        sort_css += f".st:has(#srt-{s}:checked) ~ .wrap .gvu-{s}{{display:block;}}"
        # a translucent circle in the stat's color around its event VALUE
        # (that value's own sort button) while this sort is active
        _c = hex_by_kind[key]
        sort_css += (f'.st:has(#srt-{s}:checked) ~ .wrap .gvs[for="srt-{s}"] .gvt'
                     f"{{background:{_c}30;box-shadow:0 0 0 2px {_c}66;}}")
        undo_sorts.append(
            f'<label class="gvu gvu-{s}" for="srt-{_PM_S}" '
            f'style="top:{tops[i] + heights[i] - 6.4 + sort_dy[(i, key)]:.0f}px;">'
            "</label>")
    # while ANY non-default sort is active (.srt-on), dim every lane and
    # hide the bottom-axis tricodes; each active sort's own rule (grow_css)
    # then un-dims and grows its lane and shows the under-lane tricodes
    sort_css += (".st:has(.srt-on:checked) ~ .wrap .lane{opacity:.15;}"
                 ".st:has(.srt-on:checked) ~ .wrap .tx{display:none;}")

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
        ranks[m] = {}
        for k in _rank_keys:
            vals = {t: am[t][k] for t in codes if am[t] is not None}
            ranks[m][k] = {
                t: 1 + sum(1 for vu in vals.values()
                           if (vu < v if k in _LOWER_BETTER else vu > v))
                for t, v in vals.items()}

    # ---- lanes / bars (every mask, tagged .cmb-{m}) ----
    lanes = [f'<div class="lane" style="top:{tops[0]}px;'
             f'height:{tops[max(i for i in range(n) if is_stat[i])] + STAT_H - tops[0]}px;"></div>']
    ticks, grow_css = [], []
    for i, kind in enumerate(order):
        h, top = heights[i], tops[i]
        lo, hi, rng, step, pct_scale = lane_geo[kind]
        fills = []
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
                        f'<div class="fl bar cmb-{m}" style="{bar_geo.format(j=j)}'
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
                        f'<div class="fl bar cmb-{m}" style="{bar_geo.format(j=j)}'
                        f'top:{(1 - vd / hi) * 100:.2f}%;bottom:0;'
                        f'background:{hex_by_kind["DR"]};"></div>')
                    fills.append(
                        f'<div class="fl bar cmb-{m}" style="{bar_geo.format(j=j)}'
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
                            f'<div class="fl bar cmb-{m}" style="{bar_geo.format(j=j)}'
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
                            f'<div class="fl bar cmb-{m}" style="'
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
                        f'<div class="fl bar cmb-{m}" style="{bar_geo.format(j=j)}'
                        f'top:{(1 - (v - lo) / rng) * 100:.2f}%;bottom:0;'
                        f'background:{hex_by_kind[kind]};"></div>')

            # Rank overlay: each team's league rank for this lane's sort
            # stat, on the team's own column (follows the sort vars), shown
            # while the Rank button is on and the mask matches
            _rk_key = ("REB" if kind == "DR" else
                       COMBO[kind][1] if kind in COMBO and COMBO[kind][1]
                       else kind)
            for j, t in enumerate(codes):
                rk = ranks[m][_rk_key].get(t)
                if rk is None:
                    continue
                # the rank number alone, in the team's color, placed AT the
                # team's value on this lane's scale (the bar top; the %
                # line for shooting lanes; |v| for +/-) so the magnified
                # lane reads rank-vs-value
                v = val(t, _rk_key)
                if kind == "+/-":
                    y = (1 - abs(v) / hi) * 100
                elif _rk_key != kind and pct_scale:
                    _plo, _phi = pct_scale
                    y = (1 - (v - _plo) / (_phi - _plo)) * 100
                else:
                    y = (1 - (v - lo) / rng) * 100
                _tc = _dim_hex(_TEAM_BRAND_COLORS.get(t, "#999"))
                fills.append(
                    f'<div class="rkv rkm-{m}" style="left:var(--x{j});'
                    f'top:{y:.1f}%;color:{_tc};">{rk}</div>')

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
        t = lo
        while t <= hi + 1e-9:
            fy = ax_top + (1 - (t - lo) / rng) * ax_h
            ticks.append(f'<div class="zt zt-{i}" style="top:{fy:.1f}px;">{int(t)}</div>')
            ticks.append(f'<div class="zg zg-{i}" style="top:{fy:.1f}px;"></div>')
            t += step
        bg = "background:none;" if is_stat[i] else ""
        lanes.append(f'<div class="lane lane-{i}" style="top:{top}px;height:{h}px;{bg}">'
                     + "".join(fills) + "</div>")

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
                # EVERY value is its own sort button: clicking it re-sorts
                # the teams by that exact stat (the +/- one restores the
                # default order). The .gvt span hugs the digits so the
                # active-sort circle centres on the numeric text.
                for k, dy in rows_:
                    v = a[k]
                    txt = f"{v:+.1f}" if k == "+/-" else f"{v:.0f}"
                    s = sort_idx[(gi, k)]
                    if k == "+/-":
                        # combined "+/- <value>" (single space), left edge
                        # on the label column, vertically centred (+2px) in
                        # the +/- lane. Still the sort button that toggles
                        # the +/- default order.
                        gvs.append(
                            f'<label class="gv gvs cmb-{m}" for="srt-{s}" '
                            f'style="top:{tops[gi] + heights[gi] / 2 + 2:.0f}px;'
                            f'left:calc(100% + 4px);right:auto;margin-left:0;'
                            f'width:auto;text-align:left;font-size:15px;'
                            f'color:{hex_by_kind[k]};">'
                            f'+/-&nbsp;<span class="gvt">{txt}</span></label>')
                    else:
                        gvs.append(
                            f'<label class="gv gvs cmb-{m}" for="srt-{s}" '
                            f'style="top:{ay + dy:.0f}px;'
                            f'color:{hex_by_kind[k]};">'
                            f'<span class="gvt">{txt}</span></label>')
        gvcols.append(f'<div class="gvcol gvcol-{j}">' + "".join(gvs) + "</div>")
        dl_css.append(
            # hovering anywhere in this team's value column highlights its
            # tricode on the team-name row
            f".wrap:has(.gvcol-{j} .gv:hover) .tx-{j}"
            f"{{text-shadow:0 0 7px currentColor;font-weight:bold;}}"
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
        return (f'<label class="lbl lbl-{i}" for="srt-{sort_idx[(i, key)]}" '
                f'style="top:{top:.0f}px;color:{hex_by_kind[key]};">{key}</label>')

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
            if a is None:   # team played no game in this combination —
                # the whole dash row dims (tricode included) so filtered-
                # out teams recede behind the ones with games
                cells = "".join(("-".rjust(w)) for _, _, w, _, _ in _BOX_COLS)
                mask_blocks.append(
                    f'<div class="br br-{j} cmb-{m}" style="opacity:.22;">'
                    f'{_tcode}{"-":>{_NAME_W - 10}}{"-":>3}{"-":>3} {cells}</div>')
                continue
            name = (_tcode + f"{a['G']:{_NAME_W - 10}.0f}"
                    + f"{a['W']:>3.0f}{a['L']:>3.0f} ")
            parts = [name]
            for lab, key, w, colored, invert in _BOX_COLS:
                v = a[key]
                cell = (f"{v:+.1f}" if key == "+/-" else f"{v:.0f}").rjust(w)
                if colored:
                    best, worst = (col_lo[key], col_hi[key]) if invert else (col_hi[key], col_lo[key])
                    if v == best:
                        cell = f'<span style="color:{_GOLD}">{cell}</span>'
                    elif v == worst:
                        cell = f'<span style="color:{_RED}">{cell}</span>'
                parts.append(cell)
            mask_blocks.append(f'<div class="br br-{j} cmb-{m}">' + "".join(parts) + "</div>")
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
    box_table = (f'<div class="bx"><div class="bx-head">{_html.escape(hdr)}</div>'
                 + "".join(mask_blocks) + "".join(col_stripes) + "</div>")

    # ---- segment views: one radio per view, each revealing a single
    # precomputed mask. The three thirds and the playoffs are single
    # segments; 'regular' is the whole regular season (mask 7 = games
    # 1-82); All is everything (mask 15). ----
    _SEG_VIEWS = [(1, "1:27"), (2, "28:54"), (4, "55:82"),
                  (7, "Regular"), (8, "Playoffs"), (15, "All")]
    seg_checkboxes = "".join(
        f'<input type="radio" class="seg" name="seg" id="seg-m{mask}"'
        f'{" checked" if mask == 15 else ""}>'
        for mask, _ in _SEG_VIEWS)
    # every mask-tagged element (bars, box rows, rank chips) is hidden by
    # default; the checked view reveals just its own mask and lights its
    # button
    combo_css = '[class*="cmb-"]{display:none;}'
    for mask, _ in _SEG_VIEWS:
        st = f".st:has(#seg-m{mask}:checked)"
        combo_css += (f"{st} ~ .wrap .cmb-{mask},"
                      f"{st} ~ .bxwrap .cmb-{mask}{{display:block;}}")
        combo_css += f"{st}:has(#rank:checked) ~ .wrap .rkm-{mask}{{display:block;}}"
        combo_css += (f"{st} ~ .toggles .tg-m{mask}"
                      f"{{color:#ccc;background:rgba(255,255,255,.16);}}")
    # rank mode shows a clean grid: the bars hide while the chips are up
    combo_css += ".st:has(#rank:checked) ~ .wrap .bar{display:none!important;}"
    seg_toggles = "".join(
        f'<label class="tg tg-m{mask}" for="seg-m{mask}">{label}</label>'
        for mask, label in _SEG_VIEWS)

    css = f"""
body{{background:#000;color:#b6b6b6;font-family:'DejaVu Sans',sans-serif;margin:0 0 24px;}}
/* the title centres on the box score's span (26px + table width), not
   the viewport */
h1{{font-size:22px;font-weight:normal;color:#b6b6b6;text-align:center;
  width:{TW};margin:14px 0 10px 26px;}}
.wrap{{position:relative;width:{PW};
  margin:0 0 0 26px;}}
.plot{{position:relative;height:{PLOT_H}px;}}
.lane{{position:absolute;left:0;right:0;background:rgba(255,255,255,.035);}}
.fl{{position:absolute;}}
/* a touch of transparency so stacked/overlapping bars read as layers */
.bar{{opacity:.85;}}
/* labels are hover-only (no click): hovering displays the magnified
   lane and squares the label */
.lbl{{position:absolute;right:-48px;transform:translateY(-50%);cursor:pointer;
  white-space:nowrap;padding:1px 6px;font-size:15px;line-height:1.05;z-index:5;}}
.lbl:hover{{box-shadow:0 0 0 1px currentColor;}}
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
/* main-lane values are sort buttons; .gvt hugs the digits so the
   active-sort circle centers on the number (negative margins cancel the
   padding so the right-aligned column stays put) */
.gvs{{cursor:pointer;}}
.gvs:hover{{text-shadow:0 0 6px currentColor;}}
.gvt{{display:inline-block;padding:1px 5px;margin:-1px -5px;
  border-radius:50%;}}
/* the active sort's invisible unsort overlay: sits on that lane's value
   cell (same geometry as .gv), a second click reverts to the +/- order.
   No hover outline — the sort circle already marks the value; the
   overlay stays invisible so no extra rectangle shows over the label */
.gvu{{display:none;position:absolute;left:100%;margin-left:30px;
  width:38px;height:18px;transform:translateY(-50%);
  cursor:pointer;z-index:6;}}
/* the Rank button: on the team-name line, centered under the two right
   columns. When on, each value row wears its league rank on a dim
   backdrop (.rkv, same cell geometry as .gv, clicks pass through) */
.rkbtn{{position:absolute;top:100%;margin-top:16px;left:100%;
  margin-left:36px;transform:translateX(-50%);cursor:pointer;
  color:#888;padding:4px 12px;border-radius:6px;
  border:1px solid rgba(255,255,255,.18);user-select:none;
  font-family:'DejaVu Sans Mono',monospace;font-size:14px;}}
.rkbtn:hover{{color:#ddd;}}
.st:has(#rank:checked) ~ .wrap .rkbtn
  {{color:#ccc;background:rgba(255,255,255,.16);}}
/* rank chip: the rank number in the team's color, top set inline at the
   team's value on the lane scale */
.rkv{{display:none;position:absolute;
  transform:translate(-50%,-50%);line-height:1;font-size:11px;
  text-align:center;padding:1px 3px;background:rgba(0,0,0,.72);
  border-radius:3px;white-space:nowrap;pointer-events:none;z-index:7;
  font-family:'DejaVu Sans Mono',monospace;}}
/* the segment toggles sit in the middle band between chart and table */
.toggles{{margin:80px 0 8px 26px;display:flex;align-items:center;gap:12px;
  font-family:'DejaVu Sans Mono',monospace;font-size:14px;}}
.tglabel{{color:#888;padding-right:8px;}}
.tg{{cursor:pointer;color:#888;padding:4px 12px;border-radius:6px;
  border:1px solid rgba(255,255,255,.18);user-select:none;}}
.tg:hover{{color:#ddd;}}
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
""" + sort_css + combo_css + spotlight_css + "".join(grow_css) + "".join(dl_css)

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
        + f"</div>{''.join(labels)}{''.join(gvcols)}{''.join(undo_sorts)}"
        + '<label class="rkbtn" for="rank">Rank</label></div>'
        + f'<div class="toggles"><span class="tglabel">Games</span>{seg_toggles}</div>'
        + f'<div class="bxwrap">{box_table}</div></body></html>'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path
