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
SEG_LABELS = ["1st third", "2nd third", "3rd third", "Playoffs"]


def _team_segments(season: str, team: str) -> list[dict] | None:
    """For one team, a per-segment {sum, n, margin} from its cached box
    scores. Segments: regular games [0:27], [27:54], [54:], then the
    playoffs. None if the team has no cached games."""
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
        margin, nn = 0.0, 0
        for _, g in part.iterrows():
            box = compute_official_box_score_for_game(g["GAME_ID"], team)
            b = box[(box["teamTricode"] == team) & (box["MIN"] > 0)]
            for k in _SUM_KEYS:
                s[k] += float(b[k].sum())
            margin += float(g["PTS"] - g["OPP_PTS"])
            nn += 1
        segs.append({"sum": s, "n": nn, "margin": margin})
    return segs


def _combine(segs: list[dict], mask: int) -> dict | None:
    """Per-game averages over the segments selected by `mask`, or None
    when no game is selected."""
    S = {k: 0.0 for k in _SUM_KEYS}
    n, margin = 0, 0.0
    for bit in range(4):
        if mask & (1 << bit):
            seg = segs[bit]
            for k in _SUM_KEYS:
                S[k] += seg["sum"][k]
            n += seg["n"]
            margin += seg["margin"]
    if n == 0:
        return None
    a = {k: S[k] / n for k in _SUM_KEYS}
    a["G"] = n
    _2pm, _2pa = S["FGM"] - S["FG3M"], S["FGA"] - S["FG3A"]
    a["FG%"] = 100 * S["FGM"] / S["FGA"] if S["FGA"] else 0.0
    a["2P%"] = 100 * _2pm / _2pa if _2pa else 0.0
    a["3P%"] = 100 * S["FG3M"] / S["FG3A"] if S["FG3A"] else 0.0
    a["FT%"] = 100 * S["FTM"] / S["FTA"] if S["FTA"] else 0.0
    a["+/-"] = margin / n
    a["FL"], a["TOV"], a["DR"], a["DO"] = a["PF"], a["TO"], a["DREB"], a["OREB"]
    a["3PM"], a["3PA"] = a["FG3M"], a["FG3A"]
    a["2PM"], a["2PA"] = _2pm / n, _2pa / n
    return a


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
    MASKS = range(1, 16)   # 0 = nothing selected, never rendered

    def _team_href(t):
        href = f"season_events_2d_{t.lower()}.html"
        return href if (output_path.parent / href).exists() else None

    order = ["FL", "TOV", "BLK", "STL", "AST", "DR", "FTA", "3PA", "2PA", "+/-"]
    COMBO = {"FTA": ("FTM", "FT%"), "3PA": ("3PM", "3P%"),
             "2PA": ("2PM", "2P%"), "DR": ("DO", None)}
    n = len(order)
    hex_by_kind = {
        "+/-": "#F2F2F2",
        "2PM": "#FF9F1C", "2PA": "#C96A0A", "2P%": "#FFD08A",
        "3PM": "#FF4FA3", "3PA": "#B01E6E", "3P%": "#FFA9D4",
        "FTA": "#B7A214", "FTM": "#E8DC3E", "FT%": "#FFF3A0",
        "DR": "#3D7BFF", "DO": "#9CC2FF", "AST": "#6FD9F2", "STL": "#2FD98C",
        "BLK": "#9E6FFF", "TOV": "#C23B3B", "FL": "#FF5555",
    }

    def all_vals(kind):
        return [avgs[m][t][kind] for m in MASKS for t in codes
                if avgs[m][t] is not None]

    # geometry (mirrors the team page)
    LANE_H, LANE_GAP, TIGHT_GAP, GROUP_GAP = 46, 6, 2, 18
    STAT_H = LANE_H * 0.75
    heights = [LANE_H if k == "+/-" else STAT_H for k in order]
    is_stat = [k != "+/-" for k in order]
    tops, y, gap = [], 0, LANE_GAP
    for idx, h in enumerate(heights):
        tops.append(y)
        gap = TIGHT_GAP if is_stat[idx] and idx + 1 < n and is_stat[idx + 1] else LANE_GAP
        if idx + 1 < n and order[idx + 1] in COMBO:
            gap = GROUP_GAP
        y += h + gap
    PLOT_H = y - gap
    PW = "min(100vw - 180px, 1152px)"
    x_frac = [(j + 0.5) / N for j in range(N)]
    hw = 0.09 / N

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
            if kind == "+/-":
                for fx, t in zip(x_frac, codes):
                    v = val(t, "+/-")
                    if v is None:
                        continue
                    lft, rgt = _pulse_edges(fx)
                    fills.append(
                        f'<div class="fl bar cmb-{m}" style="left:{lft:.2f}%;width:{rgt - lft:.2f}%;'
                        f'top:{(1 - abs(v) / hi) * 100:.2f}%;bottom:0;'
                        f'background:{"#2ecc55" if v >= 0 else "#e04545"};"></div>')
            elif kind in COMBO:
                _mk, _pct = COMBO[kind]
                for fx, t in zip(x_frac, codes):
                    va, vm = val(t, kind), val(t, _mk)
                    if va is None:
                        continue
                    lft, rgt = _pulse_edges(fx)
                    for v, c in ((va, hex_by_kind[kind]), (vm, hex_by_kind[_mk])):
                        fills.append(
                            f'<div class="fl bar cmb-{m}" style="left:{lft:.2f}%;width:{rgt - lft:.2f}%;'
                            f'top:{(1 - (v - lo) / rng) * 100:.2f}%;bottom:0;background:{c};"></div>')
                if _pct is not None:
                    plo, phi = pct_scale
                    prng = phi - plo
                    pts = [(fx, val(t, _pct)) for fx, t in zip(x_frac, codes) if val(t, _pct) is not None]
                    if len(pts) >= 2:
                        PHW = 2.0
                        ptop = [f"{fx * 100:.2f}% {(1 - (v - plo) / prng) * 100 - PHW:.2f}%" for fx, v in pts]
                        pbot = [f"{fx * 100:.2f}% {(1 - (v - plo) / prng) * 100 + PHW:.2f}%" for fx, v in pts]
                        fills.append(
                            f'<div class="fl cmb-{m}" style="inset:0;clip-path:polygon('
                            f'{", ".join(ptop + pbot[::-1])});background:{hex_by_kind[_pct]};"></div>')
            else:
                for fx, t in zip(x_frac, codes):
                    v = val(t, kind)
                    if v is None:
                        continue
                    lft, rgt = _pulse_edges(fx)
                    fills.append(
                        f'<div class="fl bar cmb-{m}" style="left:{lft:.2f}%;width:{rgt - lft:.2f}%;'
                        f'top:{(1 - (v - lo) / rng) * 100:.2f}%;bottom:0;'
                        f'background:{hex_by_kind[kind]};"></div>')

        ax_top, ax_h = top - h, 2 * h
        grow_css.append(
            f".wrap:has(.lbl-{i}:hover) .lane-{i},"
            f".st:has(#e-{i}:checked) ~ .wrap:not(:has(.lbl:hover)) .lane-{i}"
            f"{{top:{ax_top:.1f}px!important;height:{ax_h:.1f}px!important;z-index:2;}}")
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
        cell = f'left:{max(x_frac[j] - 0.5 / N, 0) * 100:.3f}%;width:{100 / N:.3f}%;'
        strips.append(f'<label class="wc wc-{j}" style="{cell}" for="g-{j}"></label>')
        strips.append(f'<label class="gu gu-{j}" style="{cell}" for="g-none"></label>')
        strips.append(f'<div class="dl dl-{j}" style="left:{x_frac[j] * 100:.3f}%;"></div>')
        tcol = _TEAM_BRAND_COLORS.get(t, "#999")
        _tag, _end = ("a", "</a>") if _team_href(t) else ("div", "</div>")
        _hattr = f' href="{_team_href(t)}"' if _team_href(t) else ""
        tlabels.append(f'<{_tag} class="tx tx-{j}"{_hattr} '
                       f'style="left:{x_frac[j] * 100:.3f}%;color:{tcol};">{t}{_end}')
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
                for k, dy in rows_:
                    v = a[k]
                    txt = f"{v:+.1f}" if k == "+/-" else f"{v:.0f}"
                    gvs.append(f'<div class="gv cmb-{m}" style="top:{ay + dy:.0f}px;'
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

    # ---- lane labels + trio stacks ----
    lane_radios = ['<input type="radio" class="esel esel-none" name="esel" id="e-none" checked>']
    labels = []
    for i, kind in enumerate(order):
        ay = tops[i] + heights[i] - 6.4
        if kind == "+/-":
            labels.append(f'<div class="lbln" style="top:{ay:.0f}px;'
                          f'color:{hex_by_kind[kind]};font-size:22px;">{kind}</div>')
            continue
        lane_radios.append(f'<input type="radio" class="esel esel-on" name="esel" id="e-{i}">')
        geo = f'style="top:{(ay - 16 if kind in COMBO else ay):.0f}px;color:{hex_by_kind[kind]};"'
        if kind in COMBO:
            _mk, _pct = COMBO[kind]
            if _pct is not None:
                labels.append(f'<div class="lbln" style="top:{ay - 32:.0f}px;'
                              f'color:{hex_by_kind[_pct]};">{_pct}</div>')
            labels.append(f'<div class="lbln" style="top:{ay:.0f}px;'
                          f'color:{hex_by_kind[_mk]};">{_mk}</div>')
        labels.append(f'<label class="lbl lbl-{i}" for="e-{i}" {geo}>{kind}</label>')
        labels.append(f'<label class="lbl lbl-{i} lblu lblu-{i}" for="e-none" {geo}>{kind}</label>')

    spotlight_css = "".join(
        f".wrap:has(.lbl-{i}:hover) .lane-{i},"
        f".st:has(#e-{i}:checked) ~ .wrap:not(:has(.lbl:hover)) .lane-{i}{{opacity:1;}}"
        f".wrap:has(.lbl-{i}:hover) .zt-{i},.wrap:has(.lbl-{i}:hover) .zg-{i},"
        f".st:has(#e-{i}:checked) ~ .wrap:not(:has(.lbl:hover)) .zt-{i},"
        f".st:has(#e-{i}:checked) ~ .wrap:not(:has(.lbl:hover)) .zg-{i}{{display:block;}}"
        f".st:has(#e-{i}:checked) ~ .wrap .lblu-{i}{{display:block;}}"
        f".st:has(#e-{i}:checked) ~ .wrap .lbl-{i}"
        f"{{text-shadow:0 0 7px currentColor;background:rgba(255,255,255,.16);border-radius:4px;}}"
        for i in sel_idx)

    # ---- season-average box table (a 30-row block per mask) ----
    _NAME_W = 8
    hdr = (f"{'Team':<{_NAME_W}}"
           + "".join(f"{lab:>{w}}" for lab, _, w, _, _ in _BOX_COLS))
    mask_blocks = []
    for m in MASKS:
        am = avgs[m]
        present = [t for t in codes if am[t] is not None]
        col_hi = {key: max(am[t][key] for t in present) for _, key, _, c, _ in _BOX_COLS if c and present}
        col_lo = {key: min(am[t][key] for t in present) for _, key, _, c, _ in _BOX_COLS if c and present}
        for j, t in enumerate(codes):
            a = am[t]
            tcol = _TEAM_BRAND_COLORS.get(t, "#999")
            _tcode = (f'<a href="{_team_href(t)}" style="color:{tcol}">{t}</a>'
                      if _team_href(t) else f'<span style="color:{tcol}">{t}</span>')
            if a is None:   # team played no game in this combination
                pad = " " * max(_NAME_W - len(t) - 1, 1)
                cells = "".join(("-".rjust(w)) for _, _, w, _, _ in _BOX_COLS)
                mask_blocks.append(f'<div class="br br-{j} cmb-{m}">{_tcode} {pad}{cells}</div>')
                continue
            plain = f"{t} {a['G']:.0f}"
            name = _tcode + f" {a['G']:.0f}" + " " * max(_NAME_W - len(plain), 1)
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
    box_table = (f'<div class="bx"><div class="bx-head">{_html.escape(hdr)}</div>'
                 + "".join(mask_blocks) + "</div>")

    # ---- segment toggles (default ON) + the show-the-right-combo rules ----
    seg_checkboxes = "".join(
        f'<input type="checkbox" class="seg" id="seg{b}" checked>' for b in range(4))
    # every combination element (bars, % lines, box rows) is hidden by
    # default; the matching combination's toggle-state rule reveals it
    combo_css = '[class*="cmb-"]{display:none;}'
    for m in MASKS:
        st = ".st"
        for b in range(4):
            st += f":has(#seg{b}:checked)" if (m >> b) & 1 else f":not(:has(#seg{b}:checked))"
        combo_css += f"{st} ~ .wrap .cmb-{m},{st} ~ .bxwrap .cmb-{m}{{display:block;}}"
        # a segment's toggle lights up while it is on
    for b in range(4):
        combo_css += (f".st:has(#seg{b}:checked) ~ .toggles .tg-{b}"
                      f"{{color:#eee;background:rgba(255,255,255,.16);}}")
    seg_toggles = "".join(
        f'<label class="tg tg-{b}" for="seg{b}">{SEG_LABELS[b]}</label>' for b in range(4))

    css = f"""
body{{background:#000;color:#ddd;font-family:'DejaVu Sans',sans-serif;margin:0 0 24px;}}
h1{{font-size:22px;font-weight:normal;color:#eee;text-align:center;margin:14px 0 10px;}}
.wrap{{position:relative;width:{PW};
  margin:0 0 0 calc((100vw - {PW} - 180px) / 2 + 48px);}}
.plot{{position:relative;height:{PLOT_H}px;}}
.lane{{position:absolute;left:0;right:0;background:rgba(255,255,255,.035);}}
.fl{{position:absolute;}}
.lbl{{position:absolute;left:100%;margin-left:18px;transform:translateY(-50%);
  cursor:pointer;white-space:nowrap;padding:1px 6px;font-size:15px;line-height:1.05;z-index:5;}}
.lbl:hover{{text-shadow:0 0 6px currentColor;background:rgba(255,255,255,.14);border-radius:4px;}}
.lblu{{display:none;z-index:6;}}
.lbln{{position:absolute;left:100%;margin-left:18px;transform:translateY(-50%);
  white-space:nowrap;padding:1px 6px;font-size:15px;line-height:1.05;z-index:5;}}
.zt{{display:none;position:absolute;right:100%;margin-right:8px;transform:translateY(-50%);
  font-size:11px;color:#ccc;z-index:5;}}
.zg{{display:none;position:absolute;left:0;right:0;height:1px;background:rgba(255,255,255,.18);z-index:1;}}
.tx{{position:absolute;top:100%;margin-top:16px;writing-mode:vertical-rl;
  text-orientation:mixed;transform:translateX(-50%);
  font-size:14px;font-family:'DejaVu Sans Mono',monospace;}}
.wc{{position:absolute;top:0;height:{PLOT_H}px;z-index:5;cursor:crosshair;}}
.wc:hover{{background:rgba(255,255,255,.06);}}
.gu{{display:none;position:absolute;top:0;height:{PLOT_H}px;z-index:6;}}
.dl{{display:none;position:absolute;top:0;bottom:0;width:2px;margin-left:-1px;
  background:#fff;box-shadow:0 0 7px rgba(255,255,255,.85);z-index:-1;}}
/* the value column: .gvcol is the team gate (hidden until selected),
   the .gv inside are the combination gate ([class*=cmb-] hides them,
   the active toggle rule reveals) — both must open for a value to show */
.gvcol{{display:none;}}
.gv{{position:absolute;left:100%;margin-left:64px;
  transform:translateY(calc(-50% - .8px));line-height:1.05;
  font-size:15px;white-space:nowrap;z-index:5;}}
.wrap:has(.lbl:hover) .lane{{opacity:.15;}}
.st:has(.esel-on:checked) ~ .wrap:not(:has(.lbl:hover)) .lane{{opacity:.15;}}
.bsel{{position:fixed;left:-30px;opacity:0;width:2px;height:2px;}}
.bsel-none{{display:none;}}
.esel,.seg{{display:none;}}
/* the segment toggles sit in the middle band between chart and table */
.toggles{{margin:80px 0 8px calc((100vw - {PW} - 180px) / 2 + 48px);
  display:flex;gap:12px;font-family:'DejaVu Sans Mono',monospace;font-size:14px;}}
.tg{{cursor:pointer;color:#888;padding:4px 12px;border-radius:6px;
  border:1px solid rgba(255,255,255,.18);user-select:none;}}
.tg:hover{{color:#ddd;}}
.bxwrap{{margin:8px 0 12px;overflow-x:auto;}}
.bx{{display:inline-block;font-family:'DejaVu Sans Mono',monospace;
  /* same size as the game and team box scores: 1.54% of a 1200px-max
     container (matches the game page's 1.54cqw box scores) */
  line-height:1.5;font-size:calc(min(100vw, 1200px) * 0.0154);
  white-space:pre;color:#c0c0c0;padding:10px 16px;}}
.bx-head{{color:#e0e0e0;}}
.br{{display:block;}}
a.tx,.bx a{{text-decoration:none;color:inherit;}}
a.tx:hover,.bx a:hover{{text-decoration:underline;}}
""" + combo_css + spotlight_css + "".join(grow_css) + "".join(dl_css)

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
        f"<div class=\"st\">{''.join(radios)}{''.join(lane_radios)}{seg_checkboxes}</div>"
        '<div class="wrap"><div class="plot">'
        + "".join(lanes) + "".join(strips) + "".join(tlabels) + "".join(ticks)
        + f"</div>{''.join(labels)}{''.join(gvcols)}</div>"
        + f'<div class="toggles">{seg_toggles}</div>'
        + f'<div class="bxwrap">{box_table}</div></body></html>'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path
