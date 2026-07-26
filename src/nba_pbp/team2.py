"""team2: one team's season in the league page's visual grammar.

A copy of the league sort-view app (``nba_season.plot_nba_season_2d_html``)
with the 30 team columns replaced by the TEAM'S GAMES: the x-axis runs
over the calendar days between the team's first and last game (each game
at its date), every bar is that game's box-score value, and four extra
schedule-derived lanes (B2B, HOM, W, L) follow the stat lanes. Pure
HTML/CSS, no JavaScript.

Differences from the league page, by design:

* bars exist ONCE per game (not per filter combo) — the GAMES filters
  hide whole game columns instead of re-averaging, so the lane scales
  are fixed across views (auto-fitted to the full season);
* the hover rank stack ranks the game within the WHOLE season;
* the default column order is chronological at true date spacing; a
  sorted lane packs the qualifying games uniformly from the left.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from nba_pbp.edge import league_history
from nba_pbp.plotting import (_TEAM_BRAND_COLORS, _TEAM_EAST,
                              _season_break_dates)
from nba_pbp.nba_season import (_BOX_COLS, _GOLD, _RED, _dim_hex,
                                _game_ot_clutch)

# lane order: the league page's ten, then the four schedule lanes
_ORDER = ["FL", "TOV", "BLK", "STL", "AST", "DR", "FTA", "3PA", "2PA",
          "+/-", "B2B", "HOM", "W/L"]
_COMBO = {"FTA": ("FTM", "FT%"), "3PA": ("3PM", "3P%"),
          "2PA": ("2PM", "2P%"), "DR": ("OR", None)}
_BINARY = {"B2B", "HOM", "W/L"}
_LOWER_BETTER = {"FL", "TOV"}

_HEX = {
    "+/-": "#B0B0B0",
    "2PM": "#FF9F1C", "2PA": "#A65605", "2P%": "#FFE1AE",
    "3PM": "#FF4FA3", "3PA": "#99175E", "3P%": "#FFC6E3",
    "FTA": "#0C6B5B", "FTM": "#22D3B8", "FT%": "#B5F2E6",
    "DR": "#3D7BFF", "OR": "#9CC2FF", "AST": "#6FD9F2", "STL": "#2FD98C",
    "BLK": "#9E6FFF", "TOV": "#C23B3B", "FL": "#FF5555",
    "B2B": "#C9A227", "HOM": "#8FD3FF", "W/L": "#2ecc55",
}


def _team2_games(season: str, team: str) -> list[dict]:
    """One dict per game, chronological: date, opponent, home flag,
    win/loss, season-segment bit, OT/Clutch flags, back-to-back flag,
    and the full box-score stat line straight from the game log."""
    hist = league_history(season)
    tg = hist[hist["TEAM_ABBREVIATION"] == team].sort_values("GAME_DATE")
    breaks = _season_break_dates(season)
    games, prev, reg_k = [], None, 0
    for _, g in tg.iterrows():
        gid = str(g["GAME_ID"]).zfill(10)
        date = pd.Timestamp(g["GAME_DATE"]).normalize()
        if gid.startswith("004"):
            seg = 8
        elif breaks:
            seg = 1 if date <= breaks[0] else 2 if date <= breaks[1] else 4
        else:
            seg = 1 if reg_k < 27 else 2 if reg_k < 54 else 4
        if not gid.startswith("004"):
            reg_k += 1
        home = "vs." in g["MATCHUP"]
        opp = g["MATCHUP"].split()[-1]
        bits = _game_ot_clutch(g["GAME_ID"])
        margin = float(g["PTS"] - g["OPP_PTS"])
        st = {k: float(g[c]) for k, c in [
            ("MIN", "MIN"), ("PTS", "PTS"), ("FGM", "FGM"), ("FGA", "FGA"),
            ("FG3M", "FG3M"), ("FG3A", "FG3A"), ("FTM", "FTM"),
            ("FTA", "FTA"), ("OREB", "OREB"), ("DREB", "DREB"),
            ("REB", "REB"), ("AST", "AST"), ("STL", "STL"), ("BLK", "BLK"),
            ("TO", "TOV"), ("PF", "PF")]}
        st["FG%"] = 100 * st["FGM"] / st["FGA"] if st["FGA"] else 0.0
        st["2PM"], st["2PA"] = st["FGM"] - st["FG3M"], st["FGA"] - st["FG3A"]
        st["2P%"] = 100 * st["2PM"] / st["2PA"] if st["2PA"] else 0.0
        st["3PM"], st["3PA"] = st["FG3M"], st["FG3A"]
        st["3P%"] = 100 * st["FG3M"] / st["FG3A"] if st["FG3A"] else 0.0
        st["FT%"] = 100 * st["FTM"] / st["FTA"] if st["FTA"] else 0.0
        st["FL"], st["TOV"] = st["PF"], st["TO"]
        st["DR"], st["OR"] = st["DREB"], st["OREB"]
        st["+/-"] = margin
        st["B2B"] = 1.0 if (prev is not None
                            and (date - prev).days == 1) else 0.0
        st["HOM"] = 1.0 if home else 0.0
        st["W/L"] = 1.0 if margin > 0 else 0.0
        games.append({"gid": gid, "date": date, "opp": opp, "home": home,
                      "win": margin > 0, "seg": seg,
                      "ot": bool(bits & 16), "clutch": bool(bits & 32),
                      "st": st})
        prev = date
    return games


def plot_team2_html(season: str, team: str, output_path: Path) -> Path:
    import html as _html

    games = _team2_games(season, team)
    if not games:
        raise SystemExit(f"no games for {team} {season}")
    N = len(games)
    d0, d1 = games[0]["date"], games[-1]["date"]
    ndays = max((d1 - d0).days, 1)

    def gv(j, k):
        return games[j]["st"][k]

    # per-team season partitions for the segment buttons
    _c1 = sum(1 for g in games if g["seg"] == 1)
    _c2 = _c1 + sum(1 for g in games if g["seg"] == 2)
    _c3 = _c2 + sum(1 for g in games if g["seg"] == 4)
    SEGS = [1, 2, 4, 7, 8, 15]
    TYPES = ["a", "o", "c"]
    CONFS = ["a", "e", "w"]
    MASKS = [(sg, ty) for sg in SEGS for ty in TYPES]
    _SEG_BTNS = [(1, f"1:{_c1}"), (2, f"{_c1 + 1}:{_c2}"),
                 (4, f"{_c2 + 1}:{_c3}"),
                 (7, "Regular"), (8, "Playoffs"), (15, "All")]

    def _conf(j):
        return "e" if games[j]["opp"] in _TEAM_EAST else "w"

    def _in_view(j, m, cf):
        g = games[j]
        if not (g["seg"] & m[0]):
            return False
        if m[1] == "o" and not g["ot"]:
            return False
        if m[1] == "c" and not g["clutch"]:
            return False
        if cf != "a" and _conf(j) != cf:
            return False
        return True

    # per-game filter flag classes (bars, codes, cells, box rows carry
    # them; a reveal rule per view selects the qualifying combination)
    def _gflags(j):
        g = games[j]
        return (f"gs{g['seg']}"
                + (" go" if g["ot"] else "")
                + (" gc" if g["clutch"] else "")
                + f" g{_conf(j)}")

    n = len(_ORDER)

    # value rows per lane, in label-stack order
    def _vrows_of(kind):
        if kind == "+/-":
            return ["+/-"]
        if kind == "DR":
            return ["DR", "OR"]
        if kind in _COMBO:
            mk, pct = _COMBO[kind]
            return ([pct] if pct else []) + [kind, mk]
        return [kind]

    # ---- geometry (the league page's constants) ----
    _tbl_chars = 17 + sum(w for _, _, w, _, _ in _BOX_COLS)
    # 2.75 scaled px per calendar day (a quarter of the code-row era:
    # with no axis codes the plot compresses back into the window)
    PW = f"calc({(ndays + 1) * 2.75:.2f}*var(--u))"
    TW = (f"calc({_tbl_chars * 0.60205 * 0.0154:.5f}"
          " * clamp(700px, 100vw, 1200px))")
    STAT_H = 34.5
    _SH2 = 2 * STAT_H

    # default x: each game at its calendar day; sorted views repack
    # uniformly. Bar half-width: half a day, floored so sparse stretches
    # still show a visible bar.
    x_frac = [(0.5 + (g["date"] - d0).days) / (ndays + 1) for g in games]
    hw = 0.35 / (ndays + 1)

    def _xvars(pos_of):
        return "".join(f"--x{j}:{pos_of[j] * 100:.3f}%;" for j in range(N))

    sort_css = ".wrap{" + _xvars({j: x_frac[j] for j in range(N)}) + "}"

    def _gate(m, cf):
        return (f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
                f":has(#cf-{cf}:checked)")

    # every lane is chronological on the date axis (no per-lane sorts)
    sort_keys = sorted({k for kind in _ORDER for k in _vrows_of(kind)})

    # season-wide ranks (competition style) per stat
    ranks = {}
    for key in sort_keys:
        if key in _BINARY:
            continue
        vals = sorted((gv(j, key) for j in range(N)),
                      reverse=key not in _LOWER_BETTER)
        ranks[key] = {j: 1 + vals.index(gv(j, key)) for j in range(N)}

    # fixed auto-fitted scales (whole season; filters only hide columns)
    def nice_scale(vmin, vmax, nint=6):
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

    lane_geo = {}
    for kind in _ORDER:
        if kind in _BINARY:
            lane_geo[kind] = (0.0, 1.0, 1.0, None)
        elif kind == "+/-":
            vmax = max(abs(gv(j, "+/-")) for j in range(N)) or 1.0
            lane_geo[kind] = (0.0, vmax, vmax, None)
        elif kind == "DR":
            lo, hi, _ = nice_scale(min(gv(j, "DR") for j in range(N)),
                                   max(gv(j, "REB") for j in range(N)))
            lane_geo[kind] = (lo, hi, hi - lo, None)
        elif kind in _COMBO:
            mk, pct = _COMBO[kind]
            lo, hi, _ = nice_scale(min(gv(j, mk) for j in range(N)),
                                   max(gv(j, kind) for j in range(N)))
            ps = (nice_scale(min(gv(j, pct) for j in range(N)),
                             max(gv(j, pct) for j in range(N)))[:2]
                  if pct else None)
            lane_geo[kind] = (lo, hi, hi - lo, ps)
        else:
            lo, hi, _ = nice_scale(min(gv(j, kind) for j in range(N)),
                                   max(gv(j, kind) for j in range(N)))
            lane_geo[kind] = (lo, hi, hi - lo, None)

    # ---- sort-mode geometry ----
    _LTX_FS = "calc(10*var(--u))"
    _LTX_MAX = 10 * (1200 / 900)
    _PM = _ORDER.index("+/-")
    _PADS = [14] * n
    _PADS[_ORDER.index("W/L")] = 30
    _TS = 32
    _t2, _T2 = float(_TS), []
    for i in range(n):
        _T2.append(_t2)
        _t2 += _SH2 + _PADS[i]
    _H2 = _t2

    def _badge_rows(kind):
        return _vrows_of(kind)

    def _text_px(txt, size=17.1):
        from matplotlib.font_manager import FontProperties
        from matplotlib.textpath import TextPath
        return TextPath((0, 0), txt, size=size,
                        prop=FontProperties(family="DejaVu Sans")
                        ).get_extents().width * 1.25
    _LGAP = 5
    # parked labels carry the FULL flattened group (like the league
    # page); the parked font self-fits: the largest size whose 13
    # labels + controls fit the box span
    _LFS = 17.1   # matches the GAMES line
    _BW = [round(_text_px(" ".join(_badge_rows(k)), _LFS) + 6 + _LGAP)
           for k in _ORDER]
    _PLW = round(_text_px("PLOTS", _LFS) + 10 + _LGAP)
    _CTW = round(_text_px("CLOSE", _LFS) + 6)

    # ---- radios / forms ----
    srt_radios = '<input type="checkbox" class="srt" id="gsort" checked>'
    srt_radios += ("<form>" + "".join(
        f'<input type="checkbox" class="srt" id="lc-{i}"'
        f'{"" if _ORDER[i] in ("+/-", "B2B", "HOM", "W/L") else " checked"}>' for i in range(n))
        + '<input type="checkbox" class="srt" id="lall">'
        + '<input type="reset" class="srt" id="lclose"></form>')
    seg_checkboxes = ("<form>" + "".join(
        f'<input type="radio" class="seg" name="seg" id="seg-m{mask}"'
        f'{" checked" if mask == 15 else ""}>'
        for mask, _ in _SEG_BTNS)
        + '<input type="radio" class="seg" name="gt" id="gt-a" checked>'
        '<input type="radio" class="seg" name="gt" id="gt-o">'
        '<input type="radio" class="seg" name="gt" id="gt-c">'
        '<input type="radio" class="seg" name="cf" id="cf-a" checked>'
        '<input type="radio" class="seg" name="cf" id="cf-e">'
        '<input type="radio" class="seg" name="cf" id="cf-w">'
        '<input type="reset" class="seg" id="gall"></form>')

    # ---- lanes ----
    lanes = []
    for i, kind in enumerate(_ORDER):
        lo, hi, rng, pct_scale = lane_geo[kind]
        _vrows = _vrows_of(kind)
        fills = []
        bar_geo = (f"left:calc(var(--x{{j}}) - {hw * 100:.2f}%);"
                   f"width:{2 * hw * 100:.2f}%;")
        for j in range(N):
            gf = _gflags(j)
            if kind == "B2B":
                # classic team-page colorization: the second night of a
                # back-to-back, colored by the pair's venues (HH yellow,
                # HA/AH pink, AA red); a half-height green mark on any
                # game after 2+ full days off
                _bt, _bc = None, None
                if gv(j, "B2B") > 0:
                    _nh = int(games[j]["home"]) + int(games[j - 1]["home"])
                    _bc = {2: "#FFD54F", 1: "#FF69B4", 0: "#e04545"}[_nh]
                    _bt = 25
                elif (j > 0 and (games[j]["date"]
                                 - games[j - 1]["date"]).days >= 3):
                    _bc, _bt = "#2ecc55", 50
                if _bc:
                    fills.append(
                        f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                        f'top:{_bt}%;bottom:0;'
                        f'background:{_bc};"></div>')
            elif kind == "HOM":
                # away games full height in the OPPONENT's color, home
                # games half height in the team's own color
                if games[j]["home"]:
                    _hc, _ht = _dim_hex(
                        _TEAM_BRAND_COLORS.get(team, "#999")), 50.0
                else:
                    _oc0 = _TEAM_BRAND_COLORS.get(games[j]["opp"], "#999")
                    _h0 = _oc0.lstrip("#")
                    _hc = "#%02X%02X%02X" % tuple(
                        int(int(_h0[k:k + 2], 16) * 0.8) for k in (0, 2, 4))
                    _ht = 0.0
                fills.append(
                    f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                    f'top:{_ht:.0f}%;bottom:0;'
                    f'background:{_hc};"></div>')
            elif kind == "W/L":
                _win = games[j]["win"]
                fills.append(
                    f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                    f'top:{100 / 3 if _win else 0.0:.2f}%;bottom:0;'
                    f'background:{"#2ecc55" if _win else "#e04545"};"></div>')
            elif kind in _BINARY:
                if gv(j, kind) > 0:
                    fills.append(
                        f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                        f'top:25%;bottom:0;'
                        f'background:{_HEX[kind]};"></div>')
            elif kind == "+/-":
                v = gv(j, "+/-")
                fills.append(
                    f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                    f'top:{(1 - abs(v) / hi) * 100:.2f}%;bottom:0;'
                    f'background:{"#2ecc55" if v >= 0 else "#e04545"};"></div>')
            elif kind == "DR":
                vd, vo = gv(j, "DR"), gv(j, "OR")
                fills.append(
                    f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                    f'top:{(1 - (vd - lo) / rng) * 100:.2f}%;bottom:0;'
                    f'background:{_HEX["DR"]};"></div>')
                fills.append(
                    f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                    f'top:{(1 - (vd + vo - lo) / rng) * 100:.2f}%;'
                    f'bottom:{(vd - lo) / rng * 100:.2f}%;'
                    f'background:{_HEX["OR"]};"></div>')
            elif kind in _COMBO:
                mk, pct = _COMBO[kind]

                def _z(frac):
                    return 100 - round(max(0.0, min(1.0, frac)) * 98)
                for v, c in ((gv(j, kind), _HEX[kind]), (gv(j, mk), _HEX[mk])):
                    frac = (v - lo) / rng
                    fills.append(
                        f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                        f'top:{(1 - frac) * 100:.2f}%;bottom:0;'
                        f'z-index:{_z(frac)};background:{c};"></div>')
                if pct:
                    plo, phi = pct_scale
                    frac = (gv(j, pct) - plo) / max(phi - plo, 1e-9)
                    fills.append(
                        f'<div class="fl bar {gf}" style="'
                        f'left:calc(var(--x{j}) - {hw * 50:.2f}%);'
                        f'width:{hw * 100:.2f}%;'
                        f'top:{(1 - frac) * 100:.2f}%;bottom:0;'
                        f'z-index:{_z(frac)};background:{_HEX[pct]};"></div>')
            else:
                v = gv(j, kind)
                fills.append(
                    f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                    f'top:{(1 - (v - lo) / rng) * 100:.2f}%;bottom:0;'
                    f'background:{_HEX[kind]};"></div>')

            # hover value chips (one set per game; values don't vary by
            # view) and, for stat lanes, the season-wide rank stack
            for r, k in enumerate(_vrows):
                v = gv(j, k)
                txt = (f"{v:+.0f}" if k == "+/-"
                       else ("W" if v else "L") if k == "W/L"
                       else ("H" if v else "A") if k == "HOM"
                       else ("Y" if k in _BINARY and v else
                             "-" if k in _BINARY else f"{v:.0f}"))
                fills.append(
                    f'<div class="tv lvv lvv-{j}" '
                    f'style="left:var(--x{j});top:{13 * r}px;'
                    f'color:{_HEX.get(k, "#ccc")};">{txt}</div>')
                if k in ranks:
                    fills.append(
                        f'<div class="tv lrk lrk-{j}" '
                        f'style="left:var(--x{j});'
                        f'bottom:{2 + 13 * (len(_vrows) - 1 - r)}px;'
                        f'color:{_HEX.get(k, "#ccc")};">{ranks[k][j]}</div>')

        # month gridlines + tick labels along the W/L lane, exactly
        # like the classic team page's date axis
        if kind == "W/L":
            _m = pd.Timestamp(d0.year, d0.month, 1)
            while _m <= d1:
                _at = max(_m, d0)
                _fx = (0.5 + (_at - d0).days) / (ndays + 1) * 100
                fills.append(
                    f'<div class="mg" style="left:{_fx:.2f}%;"></div>'
                    f'<div class="ml" style="left:{_fx:.2f}%;">'
                    f'{_at.strftime("%b")}</div>')
                _m = (_m + pd.offsets.MonthBegin(1)).normalize()

        # hover machinery: line segments + cells
        _cw = max(100.0 / (ndays + 1), 55.0 / N)
        for j in range(N):
            fills.append(
                f'<div class="ldl ldl-{j}" style="left:var(--x{j});"></div>'
                f'<label class="lwc lwc-{j} {_gflags(j)}" '
                f'style="left:calc(var(--x{j}) - {_cw / 2:.3f}%);'
                f'width:{_cw:.3f}%;"></label>')
        # the lane badge (margin label = close toggle; parked = open)
        _lfor = ("" if kind in ("+/-", "B2B", "HOM", "W/L")
                 else f'for="lc-{i}" ')
        lanes.append(
            f'<div class="lane lane-{i}" style="top:0;height:{STAT_H}px;">'
            + "".join(fills)
            + f'<label class="lzl'
              f'{" lzlm" if kind == "+/-" else ""}'
              f'{" lzg" if len(_vrows) > 1 else ""}" {_lfor}>'
            + " ".join(f'<span style="color:{_HEX.get(k, "#ccc")};">{k}</span>'
                       for k in _vrows)
            + "</label></div>")

    # ---- gsort css (the sort view IS the page) ----
    _GS = ".st:has(#gsort:checked)"
    _R = [_SH2 + _PADS[i] for i in range(n)]
    _call = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in range(n))
    gsort_css = (
        _GS + f" ~ .wrap .plot{{height:calc({_H2:.0f}px{_call});}}"
        + _GS + " ~ .wrap .lane .ltx{display:block;}"
        + _GS + " ~ .wrap .lane .lwc{display:block;}"
        + _GS + " ~ .wrap .lane .lzl{display:block;}")
    for j in range(N):
        oc = _TEAM_BRAND_COLORS.get(games[j]["opp"], "#999")
        gsort_css += (
            f".wrap:has(.lwc-{j}:hover) .ldl-{j}{{display:block;}}"
            f".wrap:has(.lwc-{j}:hover) .ltx-{j}{{font-weight:bold;}}"
            f".wrap:has(.lwc-{j}:hover) .lvv-{j},"
            f".wrap:has(.lwc-{j}:hover) .lrk-{j},"
            f"body:has(.bxwrap .br-{j}:hover) .lvv-{j},"
            f"body:has(.bxwrap .br-{j}:hover) .lrk-{j}"
            "{display:block;}"
            f"body:has(.bxwrap .br-{j}:hover) .ldl-{j}{{display:block;}}"
            f"body:has(.bxwrap .br-{j}:hover) .ltx-{j}{{font-weight:bold;}}"
            f".wrap:has(.lwc-{j}:hover) ~ .bxwrap .br-{j}"
            f"{{background:{oc}59;}}"
            f".bxwrap .br-{j}:hover{{background:{oc}59;}}"
            f".wrap:has(.lwc-{j}:hover) .gln-{j},"
            f"body:has(.bxwrap .br-{j}:hover) .gln-{j},"
            f".gln-{j}:hover"
            "{visibility:visible;transition-delay:0s;}")
    # lane tops/heights with full space reclamation
    for i in range(n):
        _up = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in range(i))
        gsort_css += (_GS + f" ~ .wrap .lane-{i}"
                      f"{{top:calc({_T2[i]:.0f}px{_up})!important;"
                      f"height:{_SH2:.0f}px!important;}}")
    # per-view game visibility: bars/codes/cells/box rows
    _hide_base = ".gs1,.gs2,.gs4,.gs8{display:none;}"
    reveal = []
    for m in MASKS:
        for cf in CONFS:
            gate = _gate(m, cf)
            segs = [s for s in (1, 2, 4, 8) if s & m[0]]
            ty = "" if m[1] == "a" else (".go" if m[1] == "o" else ".gc")
            cfc = "" if cf == "a" else f".g{cf}"
            sels = []
            for s in segs:
                sels.append(f"{gate} ~ .wrap .gs{s}{ty}{cfc}")
                sels.append(f"{gate} ~ .bxwrap .gs{s}{ty}{cfc}")
            reveal.append(",".join(sels) + "{display:block;}")
    combo_css = _hide_base + "".join(reveal)
    # button highlights
    _hl = "{color:#ccc;background:rgba(255,255,255,.16);}"
    for mask, _ in _SEG_BTNS:
        if mask == 15:
            continue
        combo_css += (f".st:has(#seg-m{mask}:checked) ~ .toggles "
                      f".tg-m{mask}{_hl}")
    for gid_ in ("gt-o", "gt-c", "cf-e", "cf-w"):
        combo_css += (f".st:has(#{gid_}:checked) ~ .toggles .tg-{gid_},"
                      f".st:has(#{gid_}:checked) ~ .toggles .tgu-{gid_}{_hl}")
        combo_css += (f".st:has(#{gid_}:checked) ~ .toggles "
                      f".tgu-{gid_}{{display:block;}}")
    combo_css += ",".join(
        f".st:has(#{x}:checked) ~ .toggles .tg-all"
        for x in ("seg-m1", "seg-m2", "seg-m4", "seg-m7", "seg-m8",
                  "gt-o", "gt-c", "cf-e", "cf-w")) + _hl

    # ---- collapse machinery (lall inversion, CLOSE/ALL, PLOTS) ----
    _closable = [i for i in range(n)
                 if _ORDER[i] not in ("+/-", "B2B", "HOM", "W/L")]
    _sumall = "".join(f" + var(--c{k},0)*{_BW[k]:.0f}*var(--u)"
                      for k in range(n))
    _suball = "".join(f" - var(--c{k},0)*{_BW[k]:.0f}*var(--u)"
                      for k in range(n))
    _endslot = (f"{{left:calc(({TW} - 60px - {_CTW}*var(--u)"
                f" - var(--pl,0)*{_PLW}*var(--u){_suball})/2"
                f" + var(--pl,0)*{_PLW}*var(--u));}}")
    gsort_css += (
        ".wrap .lcls" + _endslot + ".wrap .lals" + _endslot
        + ",".join(
            [f".st:has(#lall:not(:checked)):has(#lc-{i}:not(:checked))"
             " ~ .wrap .lcls" for i in _closable]
            + [f".st:has(#lall:checked):has(#lc-{i}:checked) ~ .wrap .lcls"
               for i in _closable])
        + "{display:block;}"
        + ".st:has(#lall:not(:checked))" + "".join(
            f":has(#lc-{i}:checked)" for i in _closable) + " ~ .wrap .lals,"
        + ".st:has(#lall:checked)" + "".join(
            f":has(#lc-{i}:not(:checked))" for i in _closable)
        + " ~ .wrap .lals{display:block;}")
    _parked = ([f".st:has(#lall:not(:checked)):has(#lc-{i}:checked)"
                for i in _closable]
               + [f".st:has(#lall:checked):has(#lc-{i}:not(:checked))"
                  for i in _closable])
    gsort_css += (
        ",".join(f"{c} ~ .wrap" for c in _parked) + "{--pl:1;}"
        + ",".join(f"{c} ~ .wrap .lpl" for c in _parked)
        + "{display:block;}"
        + f".wrap .lpl{{left:calc(({TW} - 60px - {_CTW}*var(--u)"
        f" - var(--pl,0)*{_PLW}*var(--u)" + _suball + ")/2);}")
    for i in range(n):
        _conds = [_GS + f":has(#lall:not(:checked)):has(#lc-{i}:checked)"]
        if _ORDER[i] not in ("+/-", "B2B", "HOM", "W/L"):
            _conds.append(
                _GS + f":has(#lall:checked):has(#lc-{i}:not(:checked))")
        _tot = _suball
        _slot = "".join(f" + var(--c{k},0)*{_BW[k]:.0f}*var(--u)"
                        for k in range(i))
        for _cnd in _conds:
            _lci = _cnd + f" ~ .wrap .lane-{i}"
            gsort_css += (
                _cnd + f" ~ .wrap{{--c{i}:1;}}"
                + _lci + " > :not(.lzl){display:none!important;}"
                + _lci + "{top:2px!important;height:22px!important;"
                "background:none!important;}"
                + _lci + " .lzl{pointer-events:auto;cursor:pointer;"
                "right:auto;"
                f"left:calc(({TW} - 60px - {_CTW}*var(--u)"
                f" - var(--pl,0)*{_PLW}*var(--u){_tot})/2"
                f" + var(--pl,0)*{_PLW}*var(--u)"
                f" + {_CTW + 4 + _LGAP}*var(--u){_slot});}}"
                + _lci + " .lzl span{display:inline;}"
                + _lci + f" .lzl{{font-size:calc({_LFS}*var(--u));}}"
                + _lci + " .lzg{border-top:1px solid #888;}")

    # ---- box table: one row per game ----
    _NAME_W = 17
    col_hi = {key: max(gv(j, key) for j in range(N))
              for _, key, _, c, _ in _BOX_COLS if c}
    col_lo = {key: min(gv(j, key) for j in range(N))
              for _, key, _, c, _ in _BOX_COLS if c}
    rows_html = []
    for j in range(N):
        g = games[j]
        oc = _dim_hex(_TEAM_BRAND_COLORS.get(g["opp"], "#999"))
        head = (f"{g['date'].strftime('%m-%d')} "
                f"{'v' if g['home'] else '@'}")
        res = "W" if g["win"] else "L"
        name = (_html.escape(head)
                + f'<a href="pm_players_{g["gid"]}.html" '
                f'style="color:{oc}">{g["opp"]}</a> '
                + (f'<span style="color:{_GOLD}">W</span>' if g["win"]
                   else f'<span style="color:{_RED}">L</span>')
                + "      "[:_NAME_W - len(head) - 5])
        parts = [name]
        for _ci, (lab, key, w, colored, invert) in enumerate(_BOX_COLS):
            v = gv(j, key)
            if key == "+/-":
                cell = ('<span style="position:relative;left:.5ch">'
                        + f"{v:+.0f}".rjust(w) + "</span>")
            else:
                cell = f"{v:.0f}".rjust(w)
            if colored:
                best, worst = ((col_lo[key], col_hi[key]) if invert
                               else (col_hi[key], col_lo[key]))
                if v == best:
                    cell = f'<span style="color:{_GOLD}">{cell}</span>'
                elif v == worst:
                    cell = f'<span style="color:{_RED}">{cell}</span>'
            parts.append(f'<span class="bc-{_ci}">{cell}</span>')
        rows_html.append(f'<div class="br br-{j} {_gflags(j)}">'
                         + "".join(parts) + "</div>")
    # column stripes + colored header
    _off, _pos = {}, _NAME_W
    for _lab, _key, _w, _c, _inv in _BOX_COLS:
        _off[_key] = (_pos, _w)
        _pos += _w
    _STAT_BOX_COL = {
        "FL": "PF", "TOV": "TO", "BLK": "BLK", "STL": "STL", "AST": "AST",
        "DR": "DREB", "OR": "OREB",
        "FTA": "FTA", "FTM": "FTM", "FT%": "FT%",
        "3PA": "FG3A", "3PM": "FG3M", "3P%": "3P%",
        "2PA": "FGA", "2PM": "FGM", "2P%": "FG%",
    }
    _COL_STAT = {v: k for k, v in _STAT_BOX_COL.items()}
    _COL_STAT["+/-"] = "+/-"
    col_stripes = []
    _stripe_cls = {}
    for sk, bc in _STAT_BOX_COL.items():
        cstart, cw = _off[bc]
        cls = f"bxs-{len(col_stripes)}"
        _stripe_cls[sk] = cls
        col_stripes.append(f'<div class="bxhl {cls}" '
                           f'style="left:{cstart + 1}ch;width:{cw - 1}ch;'
                           f'background:{_HEX[sk]}59;"></div>')
    _pms, _pmw = _off["+/-"]
    _stripe_cls["+/-"] = "bxhl-pm"
    col_stripes.append(f'<div class="bxhl bxhl-pm" '
                       f'style="left:{_pms + 1}ch;width:{_pmw - 1}ch;'
                       f'background:{_HEX["+/-"]}59;"></div>')
    _BOXCOL_HEX = {bc: _HEX[sk] for sk, bc in _STAT_BOX_COL.items()}
    _BOXCOL_HEX["+/-"] = _HEX["+/-"]
    hdr_html = _html.escape(f"{'Game':<{_NAME_W}}")
    for lab, key, w, _c, _i in _BOX_COLS:
        cell = _html.escape(f"{lab:>{w}}")
        hx = _BOXCOL_HEX.get(key)
        if hx:
            cell = f'<span style="color:{hx}">{cell}</span>'
        hdr_html += cell
    # ---- the view status row: "{filters} {n}" in the box's name
    # field, then that view's AVERAGES aligned to the box columns
    # (team-page style). One row per view, unfiltered "All" included;
    # only the active view's row shows.
    _SEGN = {1: f"1:{_c1}", 2: f"{_c1 + 1}:{_c2}", 4: f"{_c2 + 1}:{_c3}",
             7: "Regular", 8: "Playoffs", 15: None}
    fmsgs, _fmk = [], 0
    for m in MASKS:
        for cf in CONFS:
            parts = []
            if _SEGN[m[0]]:
                parts.append(_SEGN[m[0]])
            if m[1] == "o":
                parts.append("OT")
            if m[1] == "c":
                parts.append("Clutch")
            if cf != "a":
                parts.append("vs" + ("E" if cf == "e" else "W"))
            sel = [j for j in range(N) if _in_view(j, m, cf)]
            lbl = "+".join(parts) if parts else "All"
            name = f"{lbl} {len(sel)}"[:_NAME_W - 1].ljust(_NAME_W)
            cells = [_html.escape(name)]
            for lab, key, w, _c2_, _i2_ in _BOX_COLS:
                if not sel:
                    cells.append(" " * w)
                    continue
                v = sum(gv(j, key) for j in sel) / len(sel)
                if key == "+/-":
                    cells.append('<span style="position:relative;left:.5ch">'
                                 + f"{v:+.1f}".rjust(w) + "</span>")
                else:
                    cells.append(f"{v:.0f}".rjust(w))
            fmsgs.append(f'<div class="fmsg fm-{_fmk}">'
                         + "".join(cells) + "</div>")
            combo_css += (_gate(m, cf)
                          + f" ~ .bxwrap .fm-{_fmk}{{display:block;}}")
            _fmk += 1

    box_table = (f'<div class="bx">' + "".join(fmsgs)
                 + f'<div class="bx-head">{hdr_html}</div>'
                 + "".join(rows_html) + "".join(col_stripes) + "</div>")
    # lane/label hover -> box column accents; box cell -> plot mirror
    for i, kind in enumerate(_ORDER):
        stats_i = [k for k in _vrows_of(kind) if k in _stripe_cls]
        if not stats_i:
            continue
        sels = [f".wrap:has(.lane-{i} .lwc:hover) ~ .bxwrap",
                f".wrap:has(.lane-{i} .lzl:hover) ~ .bxwrap"]
        gsort_css += (",".join(
            f"{s} .{_stripe_cls[k]}" for s in sels for k in stats_i)
            + "{display:block;}")
    for _ci, (_lab, _bkey, _w, _c, _i2) in enumerate(_BOX_COLS):
        sk = _COL_STAT.get(_bkey)
        if not sk:
            continue
        gsort_css += (f".bx:has(.bc-{_ci}:hover) .{_stripe_cls[sk]}"
                      "{display:block;}")
        li = next((i for i, kk in enumerate(_ORDER)
                   if sk in _vrows_of(kk)), None)
        if li is not None:
            gsort_css += "".join(
                f"body:has(.br-{j} .bc-{_ci}:hover) .lane-{li} .lwc-{j}"
                "{background:rgba(255,255,255,.06);}" for j in range(N))

    # ---- toggles ----
    def _tgl(gid_, label):
        _offr = "gt-a" if gid_.startswith("gt") else "cf-a"
        return (f'<span class="tgw"><label class="tg tg-{gid_}"'
                f' for="{gid_}">{label}</label>'
                f'<label class="tg tgu tgu-{gid_}" for="{_offr}">'
                f'{label}</label></span>')
    seg_toggles = '<label class="tg tg-all" for="gall">All</label>'
    seg_toggles += "".join(
        f'<label class="tg tg-m{mask}" for="seg-m{mask}">{label}</label>'
        for mask, label in _SEG_BTNS[:-1])
    seg_toggles += (_tgl("cf-e", "East") + _tgl("cf-w", "West")
                    + _tgl("gt-o", "OT") + _tgl("gt-c", "Clutch"))

    tname = _TEAM_NAMES.get(team, team)
    try:
        _y0, _y1 = season.split("-")
        full_season = f"{_y0}-{_y0[:2]}{_y1}"
    except Exception:
        full_season = season
    tab_title = f"{tname} {full_season} Games"
    tc = _dim_hex(_TEAM_BRAND_COLORS.get(team, "#999"))

    css = f"""
body{{background:#000;color:#b6b6b6;font-family:'DejaVu Sans',sans-serif;margin:0 0 24px;
  --u:calc(clamp(700px, 100vw, 1200px) / 900);}}
h1{{font-size:22px;font-weight:normal;color:#b6b6b6;text-align:center;
  width:{TW};margin:14px 0 10px 26px;}}
h1 b{{color:{tc};font-weight:normal;}}
.wrap{{position:relative;width:{PW};margin:0 0 0 60px;}}
.plot{{position:relative;height:100px;}}
.lane{{position:absolute;left:0;right:0;background:rgba(255,255,255,.035);}}
.fl{{position:absolute;}}
.bar{{opacity:.85;}}
.tv{{display:none;position:absolute;transform:translateX(-50%);
  font-size:11px;line-height:1;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);white-space:nowrap;pointer-events:none;
  z-index:7;font-family:'DejaVu Sans Mono',monospace;}}
.seg,.srt{{display:none;}}
.ltx{{display:none;position:absolute;top:100%;margin-top:3px;
  transform:translateX(-50%);writing-mode:vertical-rl;line-height:1;
  font-size:{_LTX_FS};pointer-events:none;z-index:3;
  font-family:'DejaVu Sans Mono',monospace;}}
.ltxa{{pointer-events:auto;cursor:pointer;z-index:121;
  text-decoration:none;}}
.ltxa:hover{{text-decoration:underline;}}
.lwc{{display:none;position:absolute;top:0;height:100%;
  z-index:120;cursor:crosshair;}}
.lwc:hover{{background:rgba(255,255,255,.06);}}
.ldl{{display:none;position:absolute;top:0;bottom:0;
  width:2px;margin-left:-1px;background:#C0C0C0;opacity:.75;
  z-index:-1;pointer-events:none;}}

.lvv,.lrk{{transform:translateX(calc(-100% - 3px));}}
.lzl{{display:none;position:absolute;top:50%;transform:translateY(-50%);
  left:auto;right:calc(100% + 1ch);text-align:left;
  font-size:calc(17.1*var(--u));line-height:1.15;z-index:6;pointer-events:none;
  white-space:nowrap;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);}}
.lzl span{{display:block;}}
.lzl[for]{{pointer-events:auto;cursor:pointer;}}
.lzl[for]:hover{{background:rgba(255,255,255,.16);}}
.lzlm{{font-size:calc(20*var(--u));}}
.lcls,.lals{{display:none;position:absolute;top:13px;transform:translateY(-50%);
  font-size:calc({_LFS}*var(--u));
  line-height:1.15;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);color:#aaa;cursor:pointer;z-index:6;
  user-select:none;white-space:nowrap;}}
.lcls:hover,.lals:hover{{color:#ddd;background:rgba(255,255,255,.16);}}
.lpl{{display:none;position:absolute;top:13px;transform:translateY(-50%);
  font-size:calc({_LFS}*var(--u));
  line-height:1.15;padding:1px 3px;color:#888;z-index:6;
  text-transform:uppercase;pointer-events:none;white-space:nowrap;}}
.toggles{{width:{TW};margin:30px 0 24px 26px;display:flex;
  align-items:center;justify-content:center;gap:calc(6*var(--u));
  font-size:calc(17.1*var(--u));text-transform:uppercase;}}
.tglabel{{color:#888;padding-right:8px;}}
.tg{{cursor:pointer;color:#888;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);user-select:none;line-height:1.15;}}
.tg:hover{{color:#ddd;}}
.tg-m1,.tg-m2,.tg-m4,.tg-m7,.tg-m8{{color:#cfa96b;}}
.tg-cf-e,.tg-cf-w,.tgu-cf-e,.tgu-cf-w{{color:#7fa6d9;}}
.tg-gt-o,.tg-gt-c,.tgu-gt-o,.tgu-gt-c{{color:#7fc9a6;}}
.tgw{{position:relative;display:inline-block;}}
.tgw .tg{{display:inline-block;}}
.tgw .tgu{{display:none;}}
.tgu{{position:absolute;left:0;top:0;right:0;bottom:0;
  box-sizing:border-box;text-align:center;}}
.mg{{position:absolute;top:0;bottom:0;width:1px;
  background:rgba(255,255,255,.10);pointer-events:none;}}
.ml{{position:absolute;top:100%;margin-top:4px;transform:translateX(-50%);
  font-size:calc(12*var(--u));color:#999;pointer-events:none;}}
.glns{{position:relative;height:calc(24*var(--u));margin-top:6px;}}
.gln{{visibility:hidden;position:absolute;left:0;top:0;white-space:nowrap;
  font-size:calc(16*var(--u));font-family:'DejaVu Sans Mono',monospace;
  color:#a6a6a6;transition:visibility 0s .5s;}}
.gln a{{color:#6ca0ff;text-decoration:none;}}
.gln a:hover{{text-decoration:underline;}}
.bxwrap{{margin:8px 0 12px 26px;}}
.fmsg{{display:none;order:-2;color:#8f8f8f;}}
.bx{{display:flex;flex-direction:column;position:relative;
  font-family:'DejaVu Sans Mono',monospace;
  line-height:1.5;font-size:calc(clamp(700px, 100vw, 1200px) * 0.0154);
  box-sizing:border-box;width:calc({TW} + 16px);
  white-space:pre;color:#a6a6a6;padding:10px 16px 10px 0;}}
.bx-head{{color:#a6a6a6;order:-1;}}
.br{{position:relative;}}
.bxhl{{display:none;position:absolute;top:0;bottom:0;
  pointer-events:none;}}
.bx a{{text-decoration:none;color:inherit;}}
.bx a:hover{{text-decoration:underline;}}
""" + sort_css + combo_css + gsort_css

    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        f"<title>{tab_title}</title><style>{css}</style></head><body>"
        f"<h1><b>{tname}</b> {full_season}<br>Game by Game</h1>"
        f"<div class=\"st\">{seg_checkboxes}{srt_radios}</div>"
        + f'<div class="toggles"><span class="tglabel">Games</span>{seg_toggles}</div>'
        + '<div class="wrap"><div class="plot">'
        + "".join(lanes)
        + '<label class="lcls" for="lclose">CLOSE</label>'
        + '<label class="lals" for="lall">ALL</label>'
        + '<div class="lpl">Plots</div>'
        + "</div>"
        + '<div class="glns">' + "".join(
            f'<div class="gln gln-{j}">'
            + (f'<span style="color:{_GOLD}">W</span>' if games[j]["win"]
               else f'<span style="color:{_RED}">L</span>')
            + f' {"v" if games[j]["home"] else "@"} '
            + f'<span style="color:'
            f'{_dim_hex(_TEAM_BRAND_COLORS.get(games[j]["opp"], "#999"))}">'
            f'{games[j]["opp"]}</span> '
            + f'<a href="pm_players_{games[j]["gid"]}.html">'
            f'{games[j]["date"].strftime("%m-%d")} game page</a></div>'
            for j in range(N)) + "</div>"
        + "</div>"
        + f'<div class="bxwrap">{box_table}</div></body></html>'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


_TEAM_NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets",
    "IND": "Indiana Pacers", "LAC": "LA Clippers", "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies", "MIA": "Miami Heat", "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves", "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs", "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}
