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

# the team page's box layout: 24-char name field, +/- 4 wide
_BOX_COLS2 = [(lab, key, (4 if key == "+/-" else w), c, i)
              for lab, key, w, c, i in _BOX_COLS]
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


def _cap(hexc: str, m: int = 215) -> str:
    # scale a colour down so its brightest channel is <= m, keeping the
    # hue — pulls a pure-white tricode (BKN) off full white
    hexc = hexc.lstrip("#")
    r, g, b = (int(hexc[k:k + 2], 16) for k in (0, 2, 4))
    mx = max(r, g, b)
    if mx <= m:
        return "#" + hexc.upper()
    f = m / mx
    return "#%02X%02X%02X" % tuple(int(c * f) for c in (r, g, b))


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
    _OPPS = sorted({g["opp"] for g in games})
    MASKS = [(sg, ty) for sg in SEGS for ty in TYPES]
    _SEG_BTNS = [(1, f"1:{_c1}"), (2, f"{_c1 + 1}:{_c2}"),
                 (4, f"{_c2 + 1}:{_c3}"),
                 (7, "Regular"), (8, "Playoffs"), (15, "All")]

    def _conf(j):
        return "e" if games[j]["opp"] in _TEAM_EAST else "w"

    WLS = ["a", "w", "l"]
    HAS = ["a", "h", "v"]

    def _in_view(j, m, cf, wl="a", ha="a"):
        g = games[j]
        if not (g["seg"] & m[0]):
            return False
        if m[1] == "o" and not g["ot"]:
            return False
        if m[1] == "c" and not g["clutch"]:
            return False
        if cf != "a" and _conf(j) != cf:
            return False
        if wl != "a" and g["win"] != (wl == "w"):
            return False
        if ha != "a" and g["home"] != (ha == "h"):
            return False
        return True

    # per-game filter flag classes (bars, codes, cells, box rows carry
    # them; a reveal rule per view selects the qualifying combination)
    def _gflags(j):
        g = games[j]
        return (f"gs{g['seg']}"
                + (" go" if g["ot"] else "")
                + (" gc" if g["clutch"] else "")
                + f" g{_conf(j)}"
                + (" gwin" if g["win"] else " glos")
                + (" ghm" if g["home"] else " gaw")
                + f" op{g['opp']}")

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
    # 24-char name field + the stat columns = the real row length
    _tbl_chars = 24 + sum(w for _, _, w, _, _ in _BOX_COLS2)
    # 2.75 scaled px per calendar day (a quarter of the code-row era:
    # with no axis codes the plot compresses back into the window)
    PW = f"calc({(ndays + 1) * 2.75:.2f}*var(--u) + 65px)"
    TW = (f"calc({_tbl_chars * 0.60205 * 0.0154:.5f}"
          " * clamp(700px, 100vw, 1200px))")
    # the team page's flat geometry: stat lanes 34.5px, the four
    # schedule lanes 26px, 6px between lanes
    STAT_H, SHORT_H = 69.0, 26.0
    _SCHED = ("+/-", "B2B", "HOM", "W/L")
    _LH = [SHORT_H if k in _SCHED else STAT_H for k in _ORDER]

    # default x: each game at its calendar day; sorted views repack
    # uniformly. Bar half-width: half a day, floored so sparse stretches
    # still show a visible bar.
    x_frac = [(0.5 + (g["date"] - d0).days) / (ndays + 1) for g in games]
    hw = 0.35 / (ndays + 1)

    def _xvars(pos_of):
        return "".join(f"--x{j}:{pos_of[j] * 100:.3f}%;" for j in range(N))

    sort_css = ".wrap{" + _xvars({j: x_frac[j] for j in range(N)}) + "}"

    def _gate(m, cf, wl=None, ha=None):
        # wl/ha clauses only when a caller pins them: the per-view
        # game reveals stay wl/ha-agnostic (independent hides apply),
        # while the status row and averages gate on the full state
        g = (f".st:has(#seg-m{m[0]}:checked):has(#gt-{m[1]}:checked)"
             f":has(#cf-{cf}:checked)")
        if wl is not None:
            g += f":has(#wl-{wl}:checked):has(#ha-{ha}:checked)"
        return g

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
    _PADS = [6] * n
    _PADS[_ORDER.index("W/L")] = 30
    _TS = 56   # an extra blank line between the PLOTS line and lane 1
    _t2, _T2 = float(_TS), []
    for i in range(n):
        _T2.append(_t2)
        _t2 += _LH[i] + _PADS[i]
    _H2 = _t2

    def _badge_rows(kind):
        return _vrows_of(kind)

    # Helvetica advance widths (per-em/1000) — what the browser's
    # sans fallback actually renders, so the slots come out exact and
    # the gaps equal
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
    _LGAP = 5
    # parked labels carry the FULL flattened group (like the league
    # page); the parked font self-fits: the largest size whose 13
    # labels + controls fit the box span
    # the plots line self-fits: the largest font whose labels and
    # controls fit the box span with one uniform gap between blocks
    for _LFS in (17.1, 16, 15, 14, 13, 12, 11, 10):
        _BW = [round(_text_px(" ".join(_badge_rows(k)), _LFS) + 8 + _LGAP)
               for k in _ORDER]
        _PLW = round(_text_px("PLOTS", _LFS) + 8 + _LGAP)
        _CTW = round(_text_px("CLOSE", _LFS) + 8)
        _ALW = round(_text_px("ALL", _LFS) + 8)
        _line = (sum(_BW[i] for i in range(n)
                     if _ORDER[i] not in ("+/-", "B2B", "HOM", "W/L"))
                 + _PLW + _CTW + 10)
        if _line <= 700:
            break
    _DW = _CTW - _ALW   # the control slot shrinks by this when ALL shows

    # ---- radios / forms ----
    srt_radios = '<input type="checkbox" class="srt" id="gsort" checked>'
    srt_radios += ("<form>" + "".join(
        f'<input type="checkbox" class="srt" id="lc-{i}"'
        f'{"" if _ORDER[i] in ("+/-", "B2B", "HOM", "W/L") else " checked"}>' for i in range(n))
        + "".join(
            f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-n" checked>'
            f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-u">'
            f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-d">'
            f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-n" checked>'
            f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-l">'
            f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-r">'
            for i in range(n) if _ORDER[i] not in _SCHED)
        + '<input type="checkbox" class="srt" id="lall">'
        + '<input type="reset" class="srt" id="lclose"></form>')
    srt_radios += "".join(
        f'<input type="radio" class="gpin {_gflags(j)}" name="gp" id="gp-{j}"'
        f'{" checked" if j == 0 else ""}>' for j in range(N))
    srt_radios += '<input type="checkbox" class="srt" id="lock">'

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
        '<input type="radio" class="seg" name="wl" id="wl-a" checked>'
        '<input type="radio" class="seg" name="wl" id="wl-w">'
        '<input type="radio" class="seg" name="wl" id="wl-l">'
        '<input type="radio" class="seg" name="ha" id="ha-a" checked>'
        '<input type="radio" class="seg" name="ha" id="ha-h">'
        '<input type="radio" class="seg" name="ha" id="ha-v">'
        '<input type="radio" class="seg opr" name="op" id="op-all" checked>'
        + "".join(f'<input type="radio" class="seg opr" name="op" '
                  f'id="op-{t}">' for t in _OPPS)
        + '<input type="reset" class="seg" id="gall"></form>')

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
                    _bc, _bt = "#2ecc55", 60
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
                        _TEAM_BRAND_COLORS.get(team, "#999")), 60.0
                else:
                    _oc0 = _TEAM_BRAND_COLORS.get(games[j]["opp"], "#999")
                    _h0 = _oc0.lstrip("#")
                    _hc = "#%02X%02X%02X" % tuple(
                        int(int(_h0[k:k + 2], 16) * 0.8) for k in (0, 2, 4))
                    _ht = 20.0
                fills.append(
                    f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                    f'top:{_ht:.0f}%;bottom:0;'
                    f'background:{_hc};"></div>')
            elif kind == "W/L":
                _win = games[j]["win"]
                fills.append(
                    f'<div class="fl bar {gf}" style="{bar_geo.format(j=j)}'
                    f'top:{100 / 3 if _win else 20.0:.2f}%;bottom:0;'
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
                        f'<div class="fl bar flh {gf}" style="'
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
            # view) and, for stat lanes, the season-wide rank stack.
            # The bottom three strips stay bare — their info lives in
            # the right-hand column rows
            for r, k in enumerate(_vrows if kind not in
                                  ("B2B", "HOM", "W/L") else ()):
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
        _cw = 100.0 / (ndays + 1)
        for j in range(N):
            fills.append(
                f'<div class="ldl ldl-{j}" style="left:var(--x{j});"></div>'
                f'<label class="lwc lwc-{j} {_gflags(j)}" for="gp-{j}" '
                f'style="left:calc(var(--x{j}) - {_cw / 2:.3f}%);'
                f'width:{_cw:.3f}%;"></label>')
        # the lane badge (margin label = close toggle; parked = open)
        _lfor = ("" if kind in ("+/-", "B2B", "HOM", "W/L")
                 else f'for="lc-{i}" ')
        # right-hand value column, team-page style: at rest the active
        # view's averages, while hovering a game (or its box row) that
        # game's values — one row per group member, colours matching
        _val_html = ""
        if kind not in _SCHED:
            # the circle off the plot's left edge, centred on the lane
            # sort toggle: no sort shows both arrows, a click walks
            # none -> up -> down -> none (each face targets the next
            # state's radio)
            _cst = f'style="border-color:{_HEX[kind]};color:{_HEX[kind]};"'
            _val_html += (
                f'<label class="lcr lcr-n" for="ls-{i}-u" {_cst}>'
                "\u2191\u2193</label>"
                f'<label class="lcr lcr-u" for="ls-{i}-d" {_cst}>'
                "\u2191</label>"
                f'<label class="lcr lcr-d" for="ls-{i}-n" {_cst}>'
                "\u2193</label>"
                f'<label class="lcr pcr pcr-n" for="pk-{i}-l" {_cst}>'
                "\u2190\u2192</label>"
                f'<label class="lcr pcr pcr-l" for="pk-{i}-r" {_cst}>'
                "\u2190</label>"
                f'<label class="lcr pcr pcr-r" for="pk-{i}-n" {_cst}>'
                "\u2192</label>")
            for j in range(N):
                _val_html += (f'<div class="lgv lgv-{j}">' + "".join(
                    f'<span style="color:{_HEX.get(k, "#ccc")};">'
                    f'{gv(j, k):.0f}</span>' for k in _vrows) + "</div>")
            _kc = 0
            for m in MASKS:
                for cf in CONFS:
                    for wl in WLS:
                        for ha in HAS:
                            sel = [j for j in range(N)
                                   if _in_view(j, m, cf, wl, ha)]
                            if sel:
                                _val_html += (
                                    f'<div class="lgv lav lav-{_kc}">'
                                    + "".join(
                                        f'<span style="color:'
                                        f'{_HEX.get(k, "#ccc")};">'
                                        f'{sum(gv(j, k) for j in sel) / len(sel):.0f}'
                                        "</span>" for k in _vrows)
                                    + "</div>")
                            _kc += 1
            for _tri in _OPPS:
                _osel = [j for j in range(N)
                         if games[j]["opp"] == _tri]
                _val_html += (
                    f'<div class="lgv lav lavo lavo-{_tri}">' + "".join(
                        f'<span style="color:{_HEX.get(k, "#ccc")};">'
                        f'{sum(gv(j, k) for j in _osel) / len(_osel):.0f}'
                        "</span>" for k in _vrows) + "</div>")
        elif kind == "+/-":
            # like the team page: the game's signed margin in its
            # win/loss colour; the view's average margin at rest
            for j in range(N):
                _c = "#2ecc55" if games[j]["win"] else "#ff5252"
                _val_html += (f'<div class="lgv lgvM lgv-{j}" '
                              f'style="color:{_c};">'
                              f'{gv(j, "+/-"):+.0f}</div>')
            _kc = 0
            for m in MASKS:
                for cf in CONFS:
                    for wl in WLS:
                        for ha in HAS:
                            sel = [j for j in range(N)
                                   if _in_view(j, m, cf, wl, ha)]
                            if sel:
                                _avg = (sum(gv(j, "+/-") for j in sel)
                                        / len(sel))
                                _val_html += (
                                    f'<div class="lgv lgvM lav lav-{_kc}" '
                                    f'style="color:{_HEX["+/-"]};">'
                                    f'{_avg:+.1f}</div>')
                            _kc += 1
            for _tri in _OPPS:
                _osel = [j for j in range(N)
                         if games[j]["opp"] == _tri]
                _oavg = sum(gv(j, "+/-") for j in _osel) / len(_osel)
                _val_html += (
                    f'<div class="lgv lgvM lav lavo lavo-{_tri}" '
                    f'style="color:{_HEX["+/-"]};">{_oavg:+.1f}</div>')
        elif kind == "B2B":
            # venue-coded pair (HH/HA/AH/AA), OFF after 2+ full days
            # off; nothing when neither
            for j in range(N):
                _gap = ((games[j]["date"] - games[j - 1]["date"]).days
                        if j else 0)
                if _gap == 1:
                    _pair = (("H" if games[j - 1]["home"] else "A")
                             + ("H" if games[j]["home"] else "A"))
                elif _gap >= 3:
                    _pair = "OFF"
                else:
                    _pair = "-"
                _c = ("#9BA3AD" if _pair == "-"
                      else "#2ecc55" if games[j]["win"] else "#ff5252")
                _val_html += (
                    f'<div class="lgv lgvC lgv-{j}">'
                    f'<span style="color:{_c}">{_pair}</span></div>')
        elif kind == "HOM":
            # the matchup with vertical tricodes, centred across the
            # label+value span, like the team page's LOC row
            _rot = ("display:inline-block;writing-mode:vertical-rl;"
                    "text-orientation:mixed;vertical-align:middle;"
                    "line-height:1;font-size:calc(12*var(--u));")
            for j in range(N):
                _c = "#2ecc55" if games[j]["win"] else "#ff5252"
                _conn = "vs" if games[j]["home"] else "@"
                _val_html += (
                    f'<div class="lgv lgvC lgv-{j}">'
                    f'<span style="color:'
                    f'{_cap(_TEAM_BRAND_COLORS.get(team, "#c0c0c0"))};'
                    f'{_rot}">{team}</span>&nbsp;'
                    f'<span style="color:{_c}">{_conn}</span>&nbsp;'
                    f'<span style="color:{_c};{_rot}">{games[j]["opp"]}</span>'
                    "</div>")
        elif kind == "W/L":
            # the result — W/L in its colour then the score
            for j in range(N):
                _c = "#2ecc55" if games[j]["win"] else "#ff5252"
                _pts = int(games[j]["st"]["PTS"])
                _opts = int(games[j]["st"]["PTS"] - games[j]["st"]["+/-"])
                _oc2 = _dim_hex(
                    _TEAM_BRAND_COLORS.get(games[j]["opp"], "#999"))
                _val_html += (
                    f'<div class="lgv lgvM lgv-{j}">'
                    f'<span style="color:{_c}">'
                    f'{"W" if games[j]["win"] else "L"} {_pts}-</span>'
                    f'<span style="color:{_oc2}">{_opts}</span></div>')
        lanes.append(
            f'<div class="lane lane-{i}" style="top:0;height:{STAT_H}px;">'
            + "".join(fills)
            + _val_html
            + f'<label class="lzl'
              f'{" lzlm" if kind == "+/-" else ""}'
              f'{" lzg" if len(_vrows) > 1 else ""}" {_lfor}>'
            + " ".join(f'<span style="color:{_HEX.get(k, "#ccc")};">{k}</span>'
                       for k in _vrows)
            + "</label></div>")

    # ---- gsort css (the sort view IS the page) ----
    _GS = ".st:has(#gsort:checked)"
    _R = [_LH[i] + _PADS[i] for i in range(n)]
    _call = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in range(n))
    gsort_css = (
        _GS + f" ~ .wrap .plot{{height:calc({_H2:.0f}px{_call});}}"
        + _GS + " ~ .wrap .lane .ltx{display:block;}"
        + _GS + " ~ .wrap .lane .lwc{display:block;}"
        + _GS + " ~ .wrap .lane .lzl{display:block;}"
        + "".join(_GS + f" ~ .wrap .lane-{i} .lzl{{display:none;}}"
                  for i in range(n) if _ORDER[i] in _SCHED))
    # hovers over the always-open schedule strips don't flip the
    # right-hand columns — only stat-lane (or box-row) hovers do
    _STL = (":is(" + ",".join(
        f".lane-{k}" for k, kd in enumerate(_ORDER)
        if kd not in _SCHED) + ")")
    for j in range(N):
        oc = _TEAM_BRAND_COLORS.get(games[j]["opp"], "#999")
        gsort_css += (
            f".wrap:has(.lwc-{j}:hover) .ldl-{j}{{display:block;}}"
            f".wrap:has(.lwc-{j}:hover) .lvv-{j},"
            f".wrap:has(.lwc-{j}:hover) .lrk-{j},"
            f".wrap:has({_STL} .lwc-{j}:hover) .lgv-{j},"
            f"body:has(.bxwrap .br-{j}:hover) .lvv-{j},"
            f"body:has(.bxwrap .br-{j}:hover) .lrk-{j},"
            f"body:has(.bxwrap .br-{j}:hover) .lgv-{j}"
            "{display:block;}"
            f"body:has(.bxwrap .br-{j}:hover) .ldl-{j}{{display:block;}}"
            f".wrap:has(.lwc-{j}:hover) ~ .bxwrap .br-{j}"
            f"{{background:{oc}59;}}"
            f".bxwrap .br-{j}:hover{{background:{oc}59;}}"
            f".wrap:has(.lwc-{j}:hover) .gln-{j},"
            f"body:has(.bxwrap .br-{j}:hover) .gln-{j},"
            f".gln-{j}:hover"
            "{visibility:visible;transition-delay:0s;z-index:3;}")
    # pack machinery: a 0/1 visibility var per game (product of the
    # filter dimensions), plus prefix-sum chains that count visible
    # games — packed positions derive from the counts, so a packed
    # lane closes filtering gaps no matter which filters are active
    def _sumtree(order, pref):
        # binary block sums over the games' 0/1 visibility vars, in
        # the given order — prefix counts then need only ~log2(N)
        # terms, keeping calc() nesting far under the browser's depth
        # limit (a 97-long linear chain blows it)
        decls = "".join(f"--{pref}0x{k}:var(--v{j});"
                        for k, j in enumerate(order))
        width, level, count = 2, 1, len(order)
        while width < 2 * count:
            up = (count + width - 1) // width
            for k in range(up):
                lo, hi = 2 * k, 2 * k + 1
                if hi * (width // 2) < count:
                    decls += (f"--{pref}{level}x{k}:calc("
                              f"var(--{pref}{level - 1}x{lo}) + "
                              f"var(--{pref}{level - 1}x{hi}));")
                else:
                    decls += (f"--{pref}{level}x{k}:"
                              f"var(--{pref}{level - 1}x{lo});")
            width, level = width * 2, level + 1
        top = f"var(--{pref}{level - 1}x0)"

        def _prefix(r):
            pos, parts = 0, []
            while pos < r:
                lv = 0
                while (pos % (2 ** (lv + 1)) == 0
                       and pos + 2 ** (lv + 1) <= r):
                    lv += 1
                parts.append(f"var(--{pref}{lv}x{pos // (2 ** lv)})")
                pos += 2 ** lv
            return "(" + " + ".join(parts) + ")" if parts else "0"
        return decls, _prefix, top

    for _tri in _OPPS:
        _bad = [j for j in range(N) if games[j]["opp"] != _tri]
        gsort_css += (f".st:has(#op-{_tri}:checked) ~ .wrap{{"
                      + "".join(f"--vo{j}:0;" for j in _bad) + "}")
    _nd, _npre, _ntop = _sumtree(list(range(N)), "nb")
    gsort_css += (".wrap{" + "".join(
        f"--v{j}:calc(var(--vm{j},1)*var(--vc{j},1)"
        f"*var(--vw{j},1)*var(--vh{j},1)*var(--vo{j},1));"
        for j in range(N))
        + _nd
        + "".join(f"--kn{j}:calc({_npre(j)});" for j in range(N))
        + f"--tn:calc({_ntop});" + "}")
    for _mk in SEGS:
        for _t in TYPES:
            if _mk == 15 and _t == "a":
                continue
            _bad = [j for j in range(N)
                    if not _in_view(j, (_mk, _t), "a")]
            if _bad:
                gsort_css += (
                    f".st:has(#seg-m{_mk}:checked):has(#gt-{_t}:checked)"
                    " ~ .wrap{"
                    + "".join(f"--vm{j}:0;" for j in _bad) + "}")
    for _gid, _dim, _badf in (
            ("cf-e", "vc", lambda j: _conf(j) != "e"),
            ("cf-w", "vc", lambda j: _conf(j) != "w"),
            ("wl-w", "vw", lambda j: not games[j]["win"]),
            ("wl-l", "vw", lambda j: games[j]["win"]),
            ("ha-h", "vh", lambda j: not games[j]["home"]),
            ("ha-v", "vh", lambda j: games[j]["home"])):
        _bad = [j for j in range(N) if _badf(j)]
        if _bad:
            gsort_css += (f".st:has(#{_gid}:checked) ~ .wrap{{"
                          + "".join(f"--{_dim}{j}:0;" for j in _bad) + "}")

    # per-lane sort: show the active state's face; when sorting, the
    # lane's games re-pack into rank order via lane-scoped --x vars
    _SL = 100.0 / N
    for i, kind in enumerate(_ORDER):
        if kind in _SCHED:
            continue
        _st = f".st:has(#ls-{i}"
        gsort_css += (
            f"{_st}-n:checked) ~ .wrap .lane-{i} .lcr-n{{display:block;}}"
            f"{_st}-u:checked) ~ .wrap .lane-{i} .lcr-u{{display:block;}}"
            f"{_st}-d:checked) ~ .wrap .lane-{i} .lcr-d{{display:block;}}")
        _asc = sorted(range(N), key=lambda j, _k=kind: (gv(j, _k), j))
        _up = "".join(f"--x{j}:{(r + 0.5) / N * 100:.3f}%;"
                      for r, j in enumerate(_asc))
        _dn = "".join(f"--x{j}:{(N - 0.5 - r) / N * 100:.3f}%;"
                      for r, j in enumerate(_asc))
        gsort_css += (f"{_st}-u:checked) ~ .wrap .lane-{i}{{{_up}}}"
                      f"{_st}-d:checked) ~ .wrap .lane-{i}{{{_dn}}}")
        # this lane's visible-count tree in ascending-sort order
        _ad, _apre, _atop = _sumtree(_asc, f"a{i}b")
        _rk = {j: r for r, j in enumerate(_asc)}
        gsort_css += (".wrap{" + _ad + "".join(
            f"--ka{i}x{j}:calc({_apre(_rk[j])});" for j in range(N))
            + f"--ta{i}:calc({_atop});" + "}")
        _pk = f":has(#pk-{i}"
        _FC = ([f":has(#{x}:checked)" for x in
                ("seg-m1", "seg-m2", "seg-m4", "seg-m7", "seg-m8",
                 "gt-o", "gt-c", "cf-e", "cf-w",
                 "wl-w", "wl-l", "ha-h", "ha-v")]
               + [":has(.opr:checked:not(#op-all))"])
        for _pst, _fc in (("-n", "pcr-n"), ("-l", "pcr-l"),
                          ("-r", "pcr-r")):
            gsort_css += (",".join(
                f".st{c}{_pk}{_pst}:checked) ~ .wrap .lane-{i} .{_fc}"
                for c in _FC) + "{display:block;}")
        _dw = 100.0 / (ndays + 1)
        gsort_css += (
            f"{_st}-u:checked) ~ .wrap .lane-{i} .lwc,"
            f"{_st}-d:checked) ~ .wrap .lane-{i} .lwc"
            f"{{width:{100.0 / N:.3f}%!important;"
            f"margin-left:{(_dw - 100.0 / N) / 2:.3f}%!important;}}")

        def _xs(expr):
            return "".join(f"--x{j}:{expr(j)};" for j in range(N))
        for _sst, _side, _e in (
                ("-n", "-l", lambda j:
                 f"calc((var(--kn{j}) + 0.5)*var(--psl))"),
                ("-n", "-r", lambda j:
                 f"calc(100% - (var(--tn) - var(--kn{j}) - 0.5)"
                 f"*var(--psl))"),
                ("-u", "-l", lambda j:
                 f"calc((var(--ka{i}x{j}) + 0.5)*var(--psl))"),
                ("-u", "-r", lambda j:
                 f"calc(100% - (var(--ta{i}) - var(--ka{i}x{j}) - 0.5)"
                 f"*var(--psl))"),
                ("-d", "-l", lambda j:
                 f"calc((var(--ta{i}) - var(--ka{i}x{j}) - 0.5)"
                 f"*var(--psl))"),
                ("-d", "-r", lambda j:
                 f"calc(100% - (var(--ka{i}x{j}) + 0.5)*var(--psl))")):
            gsort_css += (",".join(
                f".st{c}:has(#ls-{i}{_sst}:checked)"
                f"{_pk}{_side}:checked) ~ .wrap .lane-{i}"
                for c in _FC)
                + "{--psl:calc(80%/var(--tn));" + _xs(_e) + "}")
        # packed geometry: game lines and hover cells widen with the
        # dynamic slot so the packed set fills 80% of the plot
        _cwp = max(100.0 / (ndays + 1), 100.0 / N)

        def _psel(inner):
            return ",".join(
                f".st{c}{_pk}{sd}:checked) ~ .wrap .lane-{i} {inner}"
                for c in _FC for sd in ("-l", "-r"))
        gsort_css += (
            _psel(".fl.bar") + "{width:calc(.7*var(--psl))!important;"
            f"margin-left:calc({hw * 100:.2f}% - .35*var(--psl))"
            "!important;}"
            + _psel(".flh") + "{width:calc(.35*var(--psl))!important;"
            f"margin-left:calc({hw * 50:.2f}% - .175*var(--psl))"
            "!important;}"
            + _psel(".lwc") + "{width:var(--psl)!important;"
            f"margin-left:calc({_cwp / 2:.3f}% - .5*var(--psl))"
            "!important;}")
    # the pinned game: its line, chips, info line and box row stay
    # lit until the next click; its B2B/HOM/W-L rows rest visible
    _SCHL = (":is(" + ",".join(
        f".lane-{k}" for k, kd in enumerate(_ORDER)
        if kd in ("B2B", "HOM", "W/L")) + ")")
    for j in range(N):
        _poc = _TEAM_BRAND_COLORS.get(games[j]["opp"], "#999")
        gsort_css += (
            f".st:has(#gp-{j}:checked) ~ .wrap "
            + _SCHL + f" .lgv-{j}{{display:block;}}")
        gsort_css += (
            f".st:has(#gp-{j}:checked) ~ .wrap .lvv-{j},"
            f".st:has(#gp-{j}:checked) ~ .wrap .lrk-{j}"
            "{display:block;}"
            f".st:has(#gp-{j}:checked) ~ .wrap .ldl-{j}"
            "{display:block;background:#FFF;opacity:1;}"
            f".st:has(#gp-{j}:checked) ~ .wrap .gln-{j}"
            "{visibility:visible;transition-delay:0s;z-index:2;}"
            f".st:has(#gp-{j}:checked) ~ .bxwrap .br-{j}"
            f"{{background:{_poc}59;}}")
    # while hovering, the hovered game's schedule rows replace the
    # pinned game's (ordered !important pair keeps this cheap)
    gsort_css += (
        ".wrap:has(" + _STL + " .lwc:hover) " + _SCHL + " .lgv"
        "{display:none!important;}"
        "body:has(.bxwrap .br:hover) .wrap " + _SCHL + " .lgv"
        "{display:none!important;}")
    for j in range(N):
        gsort_css += (
            ".wrap:has(" + _STL + f" .lwc-{j}:hover) " + _SCHL
            + f" .lgv-{j},"
            f"body:has(.bxwrap .br-{j}:hover) .wrap " + _SCHL
            + f" .lgv-{j}"
            "{display:block!important;}")
    # lane tops/heights with full space reclamation
    for i in range(n):
        _up = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in range(i))
        gsort_css += (_GS + f" ~ .wrap .lane-{i}"
                      f"{{top:calc({_T2[i]:.0f}px{_up})!important;"
                      f"height:{_LH[i]:.1f}px!important;}}")
    # per-view game visibility: bars/codes/cells/box rows
    _hide_base = (".gs1,.gs2,.gs4,.gs8{display:none;}"
                  ".st .gpin:is(.gs1,.gs2,.gs4,.gs8){display:none;}")
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
                sels.append(f"{gate} .gpin.gs{s}{ty}{cfc}")
            reveal.append(",".join(sels) + "{display:block;}")
    combo_css = _hide_base + "".join(reveal)
    for _gid, _cls in (("wl-w", "glos"), ("wl-l", "gwin"),
                       ("ha-h", "gaw"), ("ha-v", "ghm")):
        combo_css += (f".st:has(#{_gid}:checked) ~ .wrap .{_cls},"
                      f".st:has(#{_gid}:checked) ~ .bxwrap .{_cls},"
                      f".st:has(#{_gid}:checked) .gpin.{_cls}"
                      "{display:none!important;}")
    # opponent filter: keep only that opponent's games
    _GSANY = ":is(.gs1,.gs2,.gs4,.gs8)"
    for _tri in _OPPS:
        combo_css += (
            f".st:has(#op-{_tri}:checked) ~ .wrap {_GSANY}:not(.op{_tri}),"
            f".st:has(#op-{_tri}:checked) ~ .bxwrap {_GSANY}:not(.op{_tri}),"
            f".st:has(#op-{_tri}:checked) .gpin{_GSANY}:not(.op{_tri})"
            "{display:none!important;}")
    combo_css += (".st:has(.opr:checked:not(#op-all)) ~ .toggles .tg-all"
                  "{color:#ccc;background:rgba(255,255,255,.16);}"
                  ".opu{display:none;}")
    for _tri in _OPPS:
        combo_css += (
            f".st:has(#op-{_tri}:checked) ~ .bxwrap .opl-{_tri}"
            "{display:none;}"
            f".st:has(#op-{_tri}:checked) ~ .bxwrap .opu-{_tri}"
            "{display:inline;}")
    # button highlights
    _hl = "{color:#ccc;background:rgba(255,255,255,.16);}"
    for mask, _ in _SEG_BTNS:
        if mask == 15:
            continue
        combo_css += (f".st:has(#seg-m{mask}:checked) ~ .toggles "
                      f".tg-m{mask}{_hl}")
    for gid_ in ("gt-o", "gt-c", "cf-e", "cf-w",
                 "wl-w", "wl-l", "ha-h", "ha-v"):
        combo_css += (f".st:has(#{gid_}:checked) ~ .toggles .tg-{gid_},"
                      f".st:has(#{gid_}:checked) ~ .toggles .tgu-{gid_}{_hl}")
        combo_css += (f".st:has(#{gid_}:checked) ~ .toggles "
                      f".tgu-{gid_}{{display:block;}}")
    combo_css += ",".join(
        f".st:has(#{x}:checked) ~ .toggles .tg-all"
        for x in ("seg-m1", "seg-m2", "seg-m4", "seg-m7", "seg-m8",
                  "gt-o", "gt-c", "cf-e", "cf-w",
                  "wl-w", "wl-l", "ha-h", "ha-v")) + _hl

    # ---- collapse machinery (lall inversion, CLOSE/ALL, PLOTS) ----
    _closable = [i for i in range(n)
                 if _ORDER[i] not in ("+/-", "B2B", "HOM", "W/L")]
    _sumall = "".join(f" + var(--c{k},0)*{_BW[k]:.0f}*var(--u)"
                      for k in range(n))
    _suball = "".join(f" - var(--c{k},0)*{_BW[k]:.0f}*var(--u)"
                      for k in range(n))
    _endslot = (f"{{left:calc(({TW} - 60px - ({_CTW} - {_DW}*var(--cw,0))*var(--u)"
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
        + " ~ .wrap .lals{display:block;}"
        + ".st:has(#lall:not(:checked))" + "".join(
            f":has(#lc-{i}:checked)" for i in _closable) + " ~ .wrap,"
        + ".st:has(#lall:checked)" + "".join(
            f":has(#lc-{i}:not(:checked))" for i in _closable)
        + " ~ .wrap{--cw:1;}")
    _parked = ([f".st:has(#lall:not(:checked)):has(#lc-{i}:checked)"
                for i in _closable]
               + [f".st:has(#lall:checked):has(#lc-{i}:not(:checked))"
                  for i in _closable])
    gsort_css += (
        ",".join(f"{c} ~ .wrap" for c in _parked) + "{--pl:1;}"
        + ",".join(f"{c} ~ .wrap .lpl" for c in _parked)
        + "{display:block;}"
        + f".wrap .lpl{{left:calc(({TW} - 60px - ({_CTW} - {_DW}*var(--cw,0))*var(--u)"
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
                "right:auto;width:auto;text-align:left;"
                f"left:calc(({TW} - 60px - ({_CTW} - {_DW}*var(--cw,0))*var(--u)"
                f" - var(--pl,0)*{_PLW}*var(--u){_tot})/2"
                f" + var(--pl,0)*{_PLW}*var(--u)"
                f" + ({_CTW + _LGAP} - {_DW}*var(--cw,0))*var(--u){_slot});}}"
                + _lci + " .lzl span{display:inline;}"
                + _lci + f" .lzl{{font-size:calc({_LFS}*var(--u));}}"
                + _lci + " .lzg{border-top:1px solid #888;}")

    # ---- box table: one row per game ----
    _NAME_W = 24
    col_hi = {key: max(gv(j, key) for j in range(N))
              for _, key, _, c, _ in _BOX_COLS2 if c}
    col_lo = {key: min(gv(j, key) for j in range(N))
              for _, key, _, c, _ in _BOX_COLS2 if c}
    rows_html = []
    for j in range(N):
        g = games[j]
        oc = _dim_hex(_TEAM_BRAND_COLORS.get(g["opp"], "#999"))
        head = f"{g['date'].strftime('%m-%d')} "
        # leading columns: W/L (green/red), H/A (team colour/grey),
        # then the game and the full score, own points first and
        # coloured by the result
        _wl = ('<span style="color:#2ecc55">W</span>' if g["win"]
               else '<span style="color:#ff5252">L</span>')
        _ha = (f'<span style="color:'
               f'{_cap(_TEAM_BRAND_COLORS.get(team, "#c0c0c0"))}">H</span>'
               if g["home"] else '<span style="color:#9BA3AD">A</span>')
        _pts = int(g["st"]["PTS"])
        _opts = int(g["st"]["PTS"] - g["st"]["+/-"])
        if g["win"]:
            _sc = (f'<span style="color:#2ecc55">{_pts:>3}</span>-'
                   f'<span style="color:{oc}">{_opts:<3}</span>')
        else:
            _sc = (f'<span style="color:'
                   f'{_dim_hex(_TEAM_BRAND_COLORS.get(team, "#999"))}">'
                   f'{_pts:>3}</span>'
                   f"-{_opts:<3}")
        name = (f'<a href="pm_players_{g["gid"]}.html">'
                + _html.escape(head.rstrip()) + "</a>   "
                + _wl + " " + _ha + " "
                + f'<label class="opl opl-{g["opp"]}" for="op-{g["opp"]}" '
                f'style="color:{oc};cursor:pointer">{g["opp"]}</label>'
                f'<label class="opu opu-{g["opp"]}" for="op-all" '
                f'style="color:{oc};cursor:pointer">{g["opp"]}</label> '
                + _sc
                + " " * max(_NAME_W - len(head) - 17, 0))
        parts = [name]
        for _ci, (lab, key, w, colored, invert) in enumerate(_BOX_COLS2):
            v = gv(j, key)
            if key == "+/-":
                cell = f"{v:+.0f}".rjust(w)
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
    for _lab, _key, _w, _c, _inv in _BOX_COLS2:
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
    # name-field headers over the leading columns:
    # (date: none) W  H  OPP  SCORE
    hdr_html = _html.escape(
        f"{'Date':<8}" + "W " + "H " + "OPP " + f"{'SCORE':^7}"
        + " " * (_NAME_W - 23))
    for lab, key, w, _c, _i in _BOX_COLS2:
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
        for wl in WLS:
          for ha in HAS:
            parts = []
            # named and ordered like the GAMES-line buttons, so a
            # combined view reads e.g. "EAST+OT"
            if _SEGN[m[0]]:
                parts.append(_SEGN[m[0]])
            if cf != "a":
                parts.append("EAST" if cf == "e" else "WEST")
            if m[1] == "o":
                parts.append("OT")
            if m[1] == "c":
                parts.append("Clutch")
            if wl != "a":
                parts.append("W" if wl == "w" else "L")
            if ha != "a":
                parts.append("H" if ha == "h" else "A")
            sel = [j for j in range(N) if _in_view(j, m, cf, wl, ha)]
            lbl = "+".join(parts) if parts else "All"
            name = f"{lbl} {len(sel)}"[:_NAME_W - 1].ljust(_NAME_W)
            cells = [_html.escape(name)]
            for lab, key, w, _c2_, _i2_ in _BOX_COLS2:
                if not sel:
                    cells.append(" " * w)
                    continue
                v = sum(gv(j, key) for j in sel) / len(sel)
                if key == "+/-":
                    _pm = f"{v:+.1f}"
                    if len(_pm) > w:
                        _pm = f"{v:+.0f}"
                    cells.append(_pm.rjust(w))
                else:
                    cells.append(f"{v:.0f}".rjust(w))
            combo_css += (_gate(m, cf, wl, ha)
                          + f" ~ .wrap .lav-{_fmk}{{display:block;}}")
            if parts:
                fmsgs.append(f'<div class="fmsg fm-{_fmk}">'
                             + "".join(cells) + "</div>")
                combo_css += (_gate(m, cf, wl, ha)
                              + f" ~ .bxwrap .fm-{_fmk}{{display:block;}}")
            _fmk += 1

    for _tri in _OPPS:
        _osel = [j for j in range(N) if games[j]["opp"] == _tri]
        _oname = f"vs {_tri} {len(_osel)}"[:_NAME_W - 1].ljust(_NAME_W)
        _ocells = [_html.escape(_oname)]
        for lab, key, w, _c2_, _i2_ in _BOX_COLS2:
            v = sum(gv(j, key) for j in _osel) / len(_osel)
            if key == "+/-":
                _pm = f"{v:+.1f}"
                if len(_pm) > w:
                    _pm = f"{v:+.0f}"
                _ocells.append(_pm.rjust(w))
            else:
                _ocells.append(f"{v:.0f}".rjust(w))
        fmsgs.append(f'<div class="fmsg fmo fmo-{_tri}">'
                     + "".join(_ocells) + "</div>")
        combo_css += (f".st:has(#op-{_tri}:checked) ~ .bxwrap "
                      f".fmo-{_tri}{{display:block;}}"
                      f".st:has(#op-{_tri}:checked)"
                      f" ~ .wrap .lavo-{_tri}{{display:block;}}")
    combo_css += (
        ".wrap:has(" + _STL + " .lwc:hover) .lav{display:none!important;}"
        "body:has(.bxwrap .br:hover) .wrap .lav{display:none!important;}"
        ".st:has(.opr:checked:not(#op-all)) ~ .bxwrap "
        ".fmsg:not(.fmo){display:none!important;}"
        ".st:has(.opr:checked:not(#op-all)) ~ .wrap "
        ".lav:not(.lavo){display:none!important;}")

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
    for _ci, (_lab, _bkey, _w, _c, _i2) in enumerate(_BOX_COLS2):
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
        _offr = (gid_[:2] + "-a") if gid_[:2] in ("gt", "cf", "wl", "ha") \
            else "cf-a"
        return (f'<span class="tgw"><label class="tg tg-{gid_}"'
                f' for="{gid_}">{label}</label>'
                f'<label class="tg tgu tgu-{gid_}" for="{_offr}">'
                f'{label}</label></span>')
    seg_toggles = '<label class="tg tg-all" for="gall">All</label>'
    seg_toggles += "".join(
        f'<label class="tg tg-m{mask}" for="seg-m{mask}">{label}</label>'
        for mask, label in _SEG_BTNS[:-1])
    seg_toggles += (_tgl("cf-e", "East") + _tgl("cf-w", "West")
                    + _tgl("gt-o", "OT") + _tgl("gt-c", "Clutch")
                    + _tgl("wl-w", "W") + _tgl("wl-l", "L")
                    + _tgl("ha-h", "H") + _tgl("ha-v", "A"))

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
.lvv-0,.lrk-0,.lvv-1,.lrk-1,.lvv-2,.lrk-2,.lvv-3,.lrk-3,.lvv-4,.lrk-4,.lvv-5,.lrk-5{{transform:translateX(3px);}}
.lzl{{display:none;position:absolute;bottom:0;
  left:calc({_tbl_chars * 8.34443 - 78:.2f}*var(--u) - 28px);right:auto;
  width:calc(47*var(--u));
  text-align:left;
  font-size:calc(14*var(--u));line-height:1.15;z-index:6;pointer-events:none;
  white-space:nowrap;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);}}
.lzl span{{display:block;}}
.lgv{{display:none;position:absolute;bottom:0;
  left:calc({_tbl_chars * 8.34443 - 27:.2f}*var(--u) - 34px);
  width:calc(27*var(--u));text-align:right;
  font-size:calc(14*var(--u));line-height:1.15;z-index:6;pointer-events:none;
  white-space:nowrap;}}
.lgv span{{display:block;}}
.lcr{{display:none;position:absolute;top:calc(50% - 12px);
  right:calc(100% + 10px);
  transform:translateY(-50%);width:{STAT_H * 2 / 3 * .364:.0f}px;
  height:{STAT_H * 2 / 3 * .364:.0f}px;border-radius:50%;
  box-sizing:border-box;border:1.5px solid;text-align:center;
  line-height:{STAT_H * 2 / 3 * .364 - 3:.0f}px;
  font-size:{STAT_H * 2 / 3 * .364 * .55:.0f}px;
  cursor:pointer;}}
.lcr:hover{{background:rgba(255,255,255,.12);}}
.lcr-n,.pcr-n{{font-size:{STAT_H * 2 / 3 * .364 * .42:.0f}px;}}
.pcr{{top:calc(50% + 12px);}}
.lgvL{{left:calc(100% + 8*var(--u));width:auto;text-align:left;}}
.lgvM{{left:calc({_tbl_chars * 8.34443 - 78:.2f}*var(--u) - 31px);
  width:calc(78*var(--u));text-align:center;}}
.lgvL span,.lgvC span,.lgvM span{{display:inline;}}
.lgvC{{left:calc({_tbl_chars * 8.34443 - 78:.2f}*var(--u) - 31px);
  width:calc(78*var(--u));text-align:center;}}
.lzl[for]{{pointer-events:auto;cursor:pointer;}}
.lzl[for]:hover{{background:rgba(255,255,255,.16);}}
.lzlm{{font-size:calc(16.4*var(--u));}}
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
.tg-wl-w,.tgu-wl-w{{color:#2ecc55;}}
.tg-wl-l,.tgu-wl-l{{color:#ff5252;}}
.tg-ha-h,.tgu-ha-h{{color:{_cap(_TEAM_BRAND_COLORS.get(team, "#c0c0c0"))};}}
.tg-ha-v,.tgu-ha-v{{color:#9BA3AD;}}
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
  color:#a6a6a6;transition:visibility 0s .25s;background:#000;min-width:100%;z-index:1;}}
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
.br label:hover{{text-decoration:underline;}}
.lwc{{cursor:pointer;}}
.gpin{{position:fixed;left:-40px;top:10px;width:8px;height:8px;
  opacity:0;}}
.lkb{{cursor:pointer;font-size:18.75px;vertical-align:middle;
  margin-right:11px;}}
.lkb::after{{content:"\\01F513";}}
body:has(#lock:checked) .lkb::after{{content:"\\01F512";}}
body:has(#lock:checked) .toggles{{opacity:.45;}}
body:has(#lock:checked) .toggles label{{pointer-events:none;}}
body:has(#lock:checked) .wrap .lzl,
body:has(#lock:checked) .wrap .lcls,
body:has(#lock:checked) .wrap .lals{{pointer-events:none;opacity:.45;}}
body:has(#lock:checked) .wrap .lwc{{pointer-events:none;}}
body:has(#lock:checked) .br label{{pointer-events:none;}}
""" + sort_css + combo_css + gsort_css

    # hovered-game info line, formatted like the team page's game head:
    # "2025-10-21  OKC vs. HOU  W 125-109  detail"
    gln_html = []
    for j in range(N):
        g = games[j]
        pts = int(g["st"]["PTS"])
        opp_pts = int(g["st"]["PTS"] - g["st"]["+/-"])
        res = f'{"W" if g["win"] else "L"}  {pts}-{opp_pts}'
        gln_html.append(
            f'<div class="gln gln-{j}">{g["date"].strftime("%Y-%m-%d")}&nbsp; '
            f'<span style="color:{_cap(_TEAM_BRAND_COLORS.get(team, "#c0c0c0"))}">'
            f'{team}</span>{" vs. " if g["home"] else " @ "}'
            f'<span style="color:{_cap(_TEAM_BRAND_COLORS.get(g["opp"], "#c0c0c0"))}">'
            f'{g["opp"]}</span>&nbsp; '
            f'<span style="color:{"#2ecc55" if g["win"] else "#ff5252"}">{res}</span>'
            + (f'  <a href="pm_players_{g["gid"]}.html" style="color:#6ca0ff">detail</a>'
               if (output_path.parent / f'pbp_{g["gid"]}.csv').exists() else "")
            + "</div>")

    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        f"<title>{tab_title}</title><style>{css}</style></head><body>"
        f'<h1><label class="lkb" for="lock"></label>'
        f"<b>{tname}</b> {full_season}<br>&nbsp;</h1>"
        f"<div class=\"st\">{seg_checkboxes}{srt_radios}</div>"
        + f'<div class="toggles"><span class="tglabel">Games</span>{seg_toggles}</div>'
        + '<div class="wrap"><div class="plot">'
        + "".join(lanes)
        + '<label class="lcls" for="lclose">CLOSE</label>'
        + '<label class="lals" for="lall">ALL</label>'
        + '<div class="lpl">Plots</div>'
        + "</div>"
        + '<div class="glns">' + "".join(gln_html) + "</div>"
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
