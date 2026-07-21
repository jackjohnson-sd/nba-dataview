"""The league-wide season page: the same visual grammar as the per-team
2-D season page (``plot_season_events_2d_html``), but the columns are the
30 teams instead of one team's games, and every value is that team's
season per-game average. Pure HTML/CSS, no JavaScript, no images.

Dropped versus the team page: the W/L, B2B and HOM schedule lanes (they
have no league-average meaning) and the month zoom (no calendar axis).
Kept: the stacked stat-bar lanes, the combined shooting lanes (attempts
with makes drawn inside and a % line on top), the DR/DO rebound duo, the
signed +/- bars, lane spotlight, the right-hand value column, and a
season-average box table beneath the plot whose row for the
hovered/selected team is highlighted.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from nba_pbp import client
from nba_pbp.edge import league_history
from nba_pbp.plotting import _TEAM_BRAND_COLORS
from nba_pbp.plusminus import compute_official_box_score_for_game


# the season-average box table columns, in the same order and field
# widths as the team-page box score (`_box_score_player_line`), so it
# reads identically. Each entry: (label, key, width, colored, invert) —
# `colored` cells get the team-box highlight (league leader goldenrod,
# worst red); `invert` flips it for TO/PF where lower is better.
_GOLD, _RED, _DIM = "goldenrod", "#ff4d4d", "#ddd"
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


def _team_season_averages(season: str, team: str) -> dict | None:
    """Per-game season averages for one team, from its cached box scores.
    Returns None when the team has no cached games."""
    hist = league_history(season)
    tg = hist[hist["TEAM_ABBREVIATION"] == team].sort_values("GAME_DATE")
    tg = tg[[client.has_cached_play_by_play(g) for g in tg["GAME_ID"]]]
    n = len(tg)
    if not n:
        return None
    frames = []
    for _, g in tg.iterrows():
        box = compute_official_box_score_for_game(g["GAME_ID"], team)
        frames.append(box[(box["teamTricode"] == team) & (box["MIN"] > 0)])
    allb = pd.concat(frames, ignore_index=True)
    tot = allb[["MIN", "PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA",
                "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF"]].sum()
    avg = {c: float(tot[c]) / n for c in tot.index}
    avg["G"] = n
    _2pm, _2pa = tot["FGM"] - tot["FG3M"], tot["FGA"] - tot["FG3A"]
    avg["FG%"] = 100 * tot["FGM"] / tot["FGA"] if tot["FGA"] else 0.0
    avg["2P%"] = 100 * _2pm / _2pa if _2pa else 0.0
    avg["3P%"] = 100 * tot["FG3M"] / tot["FG3A"] if tot["FG3A"] else 0.0
    avg["FT%"] = 100 * tot["FTM"] / tot["FTA"] if tot["FTA"] else 0.0
    avg["+/-"] = float((tg["PTS"] - tg["OPP_PTS"]).mean())
    # the stat lanes, in the team page's own keys
    avg["FL"] = avg["PF"]
    avg["TOV"] = avg["TO"]
    avg["DR"] = avg["DREB"]
    avg["DO"] = avg["OREB"]
    avg["3PM"], avg["3PA"] = avg["FG3M"], avg["FG3A"]
    avg["2PM"] = avg["FGM"] - avg["FG3M"]
    avg["2PA"] = avg["FGA"] - avg["FG3A"]
    return avg


def plot_nba_season_2d_html(season: str, output_path: Path) -> Path:
    import html as _html

    teams = sorted(league_history(season)["TEAM_ABBREVIATION"].unique())
    rows = []
    for t in teams:
        a = _team_season_averages(season, t)
        if a:
            rows.append((t, a))
    rows.sort(key=lambda ta: -ta[1]["+/-"])   # best net rating first
    codes = [t for t, _ in rows]
    avgs = {t: a for t, a in rows}
    N = len(codes)

    def _team_href(t):
        """The team's season page, when it's present in this collection."""
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

    def series(kind):
        return [avgs[t][kind] for t in codes]

    # geometry (mirrors the team page)
    LANE_H, LANE_GAP, TIGHT_GAP, GROUP_GAP = 46, 6, 2, 18
    STAT_H = LANE_H * 0.75
    heights = [LANE_H if k == "+/-" else STAT_H for k in order]
    is_stat = [k != "+/-" for k in order]
    tops, y = [], 0
    gap = LANE_GAP
    for idx, h in enumerate(heights):
        tops.append(y)
        gap = TIGHT_GAP if is_stat[idx] and idx + 1 < n and is_stat[idx + 1] else LANE_GAP
        if idx + 1 < n and order[idx + 1] in COMBO:
            gap = GROUP_GAP
        y += h + gap
    PLOT_H = y - gap
    PW = "min(100vw - 180px, 1152px)"

    x_frac = [(j + 0.5) / N for j in range(N)]
    hw = 0.09 / N   # thin bars: a quarter of the old 0.36/N half-width

    def _pulse_edges(fx):
        c = min(max(fx, hw), 1.0 - hw)
        return (c - hw) * 100, (c + hw) * 100

    def lane_scale(kind):
        vals = series(kind)
        vmin, vmax = min(vals), max(vals)
        span = max(vmax - vmin, 1.0)
        step = next(t for t in (1, 2, 5, 10, 20, 25, 50) if t >= span / 4)
        lo = math.floor(vmin / step) * step
        hi = max(math.ceil(vmax / step) * step, lo + step)
        return lo, hi, step

    sel_idx = [i for i, k in enumerate(order) if k != "+/-"]

    # ---- lanes / bars ----
    lanes = [f'<div class="lane" style="top:{tops[0]}px;'
             f'height:{tops[max(i for i in range(n) if is_stat[i])] + STAT_H - tops[0]}px;"></div>']
    ticks, grow_css = [], []
    for i, kind in enumerate(order):
        h, top = heights[i], tops[i]
        fills = []
        if kind == "+/-":
            z = series("+/-")
            vmax = max((abs(v) for v in z), default=1.0) or 1.0
            for fx, v in zip(x_frac, z):
                lft, rgt = _pulse_edges(fx)
                fills.append(
                    f'<div class="fl bar" style="left:{lft:.2f}%;width:{rgt - lft:.2f}%;'
                    f'top:{(1 - abs(v) / vmax) * 100:.2f}%;bottom:0;'
                    f'background:{"#2ecc55" if v >= 0 else "#e04545"};"></div>')
            lo, hi, step, rng = 0.0, vmax, max(round(vmax / 4), 1), vmax
        elif kind in COMBO:
            _mk, _pct = COMBO[kind]
            za, zm = series(kind), series(_mk)
            vmin, vmax = min(zm), max(za)
            step = next(s for s in (1, 2, 5, 10, 20) if (vmax - vmin) / s <= 6)
            lo = math.floor(vmin / step) * step
            hi = max(math.ceil(vmax / step) * step, lo + step)
            rng = hi - lo
            for fx, va, vm in zip(x_frac, za, zm):
                lft, rgt = _pulse_edges(fx)
                for v, c in ((va, hex_by_kind[kind]), (vm, hex_by_kind[_mk])):
                    fills.append(
                        f'<div class="fl bar" style="left:{lft:.2f}%;width:{rgt - lft:.2f}%;'
                        f'top:{(1 - (v - lo) / rng) * 100:.2f}%;bottom:0;background:{c};"></div>')
            if _pct is not None:
                plo, phi, _ = lane_scale(_pct)
                prng = phi - plo
                pz = series(_pct)
                PHW = 2.0
                ptop = [f"{fx * 100:.2f}% {(1 - (v - plo) / prng) * 100 - PHW:.2f}%"
                        for fx, v in zip(x_frac, pz)]
                pbot = [f"{fx * 100:.2f}% {(1 - (v - plo) / prng) * 100 + PHW:.2f}%"
                        for fx, v in zip(x_frac, pz)]
                fills.append(
                    f'<div class="fl" style="inset:0;clip-path:polygon('
                    f'{", ".join(ptop + pbot[::-1])});background:{hex_by_kind[_pct]};"></div>')
        else:
            z = series(kind)
            vmin, vmax = min(z), max(z)
            step = next(s for s in (1, 2, 5, 10, 20) if (vmax - vmin) / s <= 6)
            lo = math.floor(vmin / step) * step
            hi = max(math.ceil(vmax / step) * step, lo + step)
            rng = hi - lo
            for fx, v in zip(x_frac, z):
                lft, rgt = _pulse_edges(fx)
                fills.append(
                    f'<div class="fl bar" style="left:{lft:.2f}%;width:{rgt - lft:.2f}%;'
                    f'top:{(1 - (v - lo) / rng) * 100:.2f}%;bottom:0;'
                    f'background:{hex_by_kind[kind]};"></div>')

        # spotlight axis: the lane grows to 2x UPWARD, ticks revealed
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

    # ---- per-team columns: hover cells, value column, tricode axis ----
    radios = ['<input type="radio" class="bsel bsel-none" name="bsel" id="g-none">']
    strips, values, tlabels, dl_css = [], [], [], []
    for j, t in enumerate(codes):
        sel = " checked autofocus" if j == 0 else ""
        radios.append(f'<input type="radio" class="bsel" name="bsel" id="g-{j}"{sel}>')
        lft, rgt = _pulse_edges(x_frac[j])
        cell = f'left:{max(x_frac[j] - 0.5 / N, 0) * 100:.3f}%;width:{100 / N:.3f}%;'
        strips.append(f'<label class="wc wc-{j}" style="{cell}" for="g-{j}"></label>')
        strips.append(f'<label class="gu gu-{j}" style="{cell}" for="g-none"></label>')
        strips.append(f'<div class="dl dl-{j}" style="left:{x_frac[j] * 100:.3f}%;"></div>')
        tcol = _TEAM_BRAND_COLORS.get(t, "#999")
        _tag, _end = ("a", "</a>") if _team_href(t) else ("div", "</div>")
        _hattr = f' href="{_team_href(t)}"' if _team_href(t) else ""
        tlabels.append(f'<{_tag} class="tx tx-{j}"{_hattr} '
                       f'style="left:{x_frac[j] * 100:.3f}%;color:{tcol};">{t}{_end}')
        a = avgs[t]
        for gi, gkind in enumerate(order):
            ay = tops[gi] + heights[gi] - 6.4

            def _cell(k, dy, col=None):
                v = a[k]
                txt = f"{v:+.1f}" if k == "+/-" else f"{v:.0f}"
                return (f'<div class="gv gv-{j}" style="top:{ay + dy:.0f}px;'
                        f'color:{col or hex_by_kind[k]};">{txt}</div>')
            if gkind in COMBO:
                _mk, _pct = COMBO[gkind]
                rws = ((_pct, -32), (gkind, -16), (_mk, 0)) if _pct else ((gkind, -16), (_mk, 0))
                for k, dy in rws:
                    values.append(_cell(k, dy))
            else:
                values.append(_cell(gkind, 0))
        # per-team highlight wiring
        dl_css.append(
            f".wrap:has(.wc-{j}:hover) .dl-{j},"
            f".wrap:has(.wc-{j}:hover) .gv-{j},"
            f".st:has(#g-{j}:checked) ~ .wrap:not(:has(.wc:hover)) .dl-{j},"
            f".st:has(#g-{j}:checked) ~ .wrap:not(:has(.wc:hover)) .gv-{j}{{display:block;}}"
            f".wrap:has(.wc-{j}:hover) .tx-{j},"
            f".st:has(#g-{j}:checked) ~ .wrap:not(:has(.wc:hover)) .tx-{j}"
            f"{{text-shadow:0 0 7px currentColor;font-weight:bold;}}"
            f".st:has(#g-{j}:checked) ~ .wrap:not(:has(.wc:hover)) .gu-{j}{{display:block;}}"
            f".st:has(#g-{j}:checked) ~ .bxwrap .br-{j},"
            f".wrap:has(.wc-{j}:hover) ~ .bxwrap .br-{j}"
            f"{{background:rgba(255,255,255,.24);}}")

    # ---- lane labels + trio stacks (baseline anchored) ----
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

    # ---- season-average box table: the game box-score layout (same
    # column order + field widths as _box_score_player_line), with the
    # player-name column replaced by a fixed "TRICODE games" field, and
    # the same per-column highlight (league leader gold, worst red;
    # TO/PF inverted) ----
    _NAME_W = 8   # "OKC 97" fits; the trailing pad keeps MIN off the name
    col_hi = {key: max(avgs[t][key] for t in codes) for _, key, _, c, _ in _BOX_COLS if c}
    col_lo = {key: min(avgs[t][key] for t in codes) for _, key, _, c, _ in _BOX_COLS if c}
    hdr = (f"{'Team':<{_NAME_W}}"
           + "".join(f"{lab:>{w}}" for lab, _, w, _, _ in _BOX_COLS))
    trows = []
    for j, t in enumerate(codes):
        a = avgs[t]
        plain = f"{t} {a['G']:.0f}"
        _tcode = (f'<a href="{_team_href(t)}" style="color:{_TEAM_BRAND_COLORS.get(t, "#999")}">{t}</a>'
                  if _team_href(t)
                  else f'<span style="color:{_TEAM_BRAND_COLORS.get(t, "#999")}">{t}</span>')
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
        trows.append(f'<div class="br br-{j}">' + "".join(parts) + "</div>")
    # each row is its own block div (breaks the line itself); joining with
    # "\n" instead would add a blank text-line between rows under
    # white-space:pre and double the spacing
    box_table = (f'<div class="bx"><div class="bx-head">{_html.escape(hdr)}</div>'
                 + "".join(trows) + "</div>")

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
/* vertical tricodes via writing-mode (not a rotate): the element itself
   becomes ~1 char wide, so translateX(-50%) centers it EXACTLY on the
   team's x — a rotate transform would shift by half the horizontal text
   width instead and miss the bar */
.tx{{position:absolute;top:100%;margin-top:16px;writing-mode:vertical-rl;
  text-orientation:mixed;transform:translateX(-50%);
  font-size:14px;font-family:'DejaVu Sans Mono',monospace;}}
.wc{{position:absolute;top:0;height:{PLOT_H}px;z-index:5;cursor:crosshair;}}
.wc:hover{{background:rgba(255,255,255,.06);}}
.gu{{display:none;position:absolute;top:0;height:{PLOT_H}px;z-index:6;}}
.dl{{display:none;position:absolute;top:0;bottom:0;width:2px;margin-left:-1px;
  background:#fff;box-shadow:0 0 7px rgba(255,255,255,.85);z-index:-1;}}
.gv{{display:none;position:absolute;left:100%;margin-left:64px;
  transform:translateY(calc(-50% - .8px));line-height:1.05;
  font-size:15px;white-space:nowrap;z-index:5;}}
.wrap:has(.lbl:hover) .lane{{opacity:.15;}}
.st:has(.esel-on:checked) ~ .wrap:not(:has(.lbl:hover)) .lane{{opacity:.15;}}
.bsel{{position:fixed;left:-30px;opacity:0;width:2px;height:2px;}}
.bsel-none{{display:none;}}
.esel{{display:none;}}
.bxwrap{{margin:44px 0 12px;overflow-x:auto;}}
.bx{{display:inline-block;font-family:'DejaVu Sans Mono',monospace;
  line-height:1.5;font-size:calc((min(100vw, 1332px) - 34px) / 54.8);
  white-space:pre;color:#a6a6a6;padding:10px 16px;}}
.bx-head{{color:#cfcfcf;}}
.br{{display:block;}}
/* team tricodes (axis + box score) link to that team's season page,
   keeping their brand color; underline only on hover */
a.tx,.bx a{{text-decoration:none;color:inherit;}}
a.tx:hover,.bx a:hover{{text-decoration:underline;}}
""" + spotlight_css + "".join(grow_css) + "".join(dl_css)

    try:
        _y0, _y1 = season.split("-")
        full_season = f"{_y0}-{_y0[:2]}{_y1}"   # 2025-26 -> 2025-2026
    except Exception:
        full_season = season
    title = f"NBA {full_season} Season"
    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        f"<title>{title}</title><style>{css}</style></head><body>"
        f"<h1>{title}</h1>"
        f"<div class=\"st\">{''.join(radios)}{''.join(lane_radios)}</div>"
        '<div class="wrap"><div class="plot">'
        + "".join(lanes) + "".join(strips) + "".join(tlabels) + "".join(ticks)
        + f"</div>{''.join(labels)}{''.join(values)}</div>"
        + f'<div class="bxwrap">{box_table}</div></body></html>'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path
