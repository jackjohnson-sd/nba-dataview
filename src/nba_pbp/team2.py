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
    "BLK": "#9E6FFF", "TOV": "#C13BD4", "FL": "#E6C229",
    "B2B": "#C9A227", "HOM": "#8FD3FF", "W/L": "#2ecc55",
}
# the plot hues sit a notch darker on the black ground (PM stays as
# is); 0.85 keeps every family readable and the trio hierarchy intact
_HEX = {k: (v if k == "+/-" else
            "#" + "".join(f"{int(int(v[i:i + 2], 16) * 0.85):02X}"
                          for i in (1, 3, 5)))
        for k, v in _HEX.items()}


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
        st["MIN"] *= 60          # carried in seconds
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
    PW = f"calc({_tbl_chars * 8.34443:.2f}*var(--u))"
    TW = (f"calc({_tbl_chars * 0.60205 * 0.0154:.5f}"
          " * var(--vw))")
    # lane height follows flag depth, one 13px character per member:
    # n value chips ladder down the line's left from the top, n rank
    # chips ladder up its right with the bottom row centred on the
    # lane's bottom edge — the line ends mid-flag. Opposite sides, so
    # the columns may share heights without colliding
    STAT_H, SHORT_H = 69.0, 26.0
    _SCHED = ("+/-", "B2B", "HOM", "W/L")
    _LH = [SHORT_H if k in _SCHED else 13 * len(_vrows_of(k)) + 19
           for k in _ORDER]

    # default x: each game at its calendar day; sorted views repack
    # uniformly. Bar half-width: half a day, floored so sparse stretches
    # still show a visible bar.
    x_frac = [(0.5 + (g["date"] - d0).days) / (ndays + 1) for g in games]
    hw = 0.25 / (ndays + 1)

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
    # the flag pole: rises two flags plus a pad above the lane top —
    # value flags ladder down its left, rank flags mirror them on the
    # right — and ends flush with the lane bottom (no down pole)
    _CHIP = [k not in ("B2B", "HOM", "W/L") for k in _ORDER]
    _EXTT = [26 + 6 if c else 0 for c in _CHIP]
    _EXTB = [0 for c in _CHIP]
    _PADS = [6] * n
    for _k in range(9):        # a label strip hangs below lanes 1..9
        _PADS[_k] = 26
    _PADS[_ORDER.index("W/L")] = 30
    for _k in range(n - 1):
        # the band below a lane holds its tail flags AND (on stat
        # lanes) the 24px label strip, then the next pole's head —
        # the deeper of the two sets the pad
        _lbl = 29 if _ORDER[_k] not in _SCHED else 0
        _PADS[_k] = max(_PADS[_k],
                        max(_EXTB[_k], _lbl) + 2 + _EXTT[_k + 1])
    # PM's successor is a headless schedule strip, but it keeps the
    # same breathing room the single-label stat lanes get (29+2+32)
    _PADS[_PM] = max(_PADS[_PM], 63)
    _TS = 216  # room for the count, pin and box-excerpt bands above lane 1
    _t2, _T2 = float(_TS), []
    for i in range(n):
        _T2.append(_t2)
        _t2 += _LH[i] + _PADS[i]
    _H2 = _t2

    _DN = {"FL": "PF", "TOV": "TO", "+/-": "PM"}

    def _badge_rows(kind):
        return [_DN.get(k, k) for k in _vrows_of(kind)]

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
    _LFS = 17.1
    _PLFS = 21
    _BW = [round(_text_px(" ".join(_badge_rows(k)), _LFS) + 8 + _LGAP)
           for k in _ORDER]
    _PLW = round(_text_px("PLOTS", _PLFS) + 8 + _LGAP)
    _CFS = _LFS
    _CTW = round(_text_px("CLOSE", _CFS) + 8)
    _ALW = round(_text_px("ALL", _CFS) + 8)
    _DW = _CTW - _ALW   # the control slot shrinks by this when ALL shows

    # ---- radios / forms ----
    srt_radios = ""
    srt_radios += ('<input type="radio" class="srt" name="bx" id="bx-10"'
                   ' checked>'
                   '<input type="radio" class="srt" name="bx" id="bx-25">'
                   '<input type="radio" class="srt" name="bx" id="bx-a">'
                   '<input type="radio" class="srt" name="bx" id="bx-h">')
    srt_radios += ('<input type="radio" class="srt" name="pg" id="pg-g"'
                   ' checked>'
                   '<input type="radio" class="srt" name="pg" id="pg-p">'
                   '<input type="radio" class="srt" name="pg" id="pg-u">'
                   '<input type="radio" class="srt" name="pg" id="pg-t">')
    srt_radios += ('<form autocomplete="off">' + "".join(
            f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-n" checked>'
            f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-u">'
            f'<input type="radio" class="srt" name="ls-{i}" id="ls-{i}-d">'
            f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-n" checked>'
            f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-l">'
            f'<input type="radio" class="srt" name="pk-{i}" id="pk-{i}-r">'
            for i in range(n) if _ORDER[i] not in ("B2B", "HOM", "W/L"))
        + "</form>")
    # open/closed lives in its own form: SHOW is that form's reset
    # (absolute all-open), SHRINK checks the la-1 inverter radio —
    # a radio, not a checkbox, so a second click is a no-op
    srt_radios += ('<form autocomplete="off">' + "".join(
        f'<input type="checkbox" class="srt" id="lc-{i}">'
        for i in range(n))
        + '<input type="checkbox" class="srt" id="lcs">'
        + '<input type="radio" class="srt" name="la" id="la-0" checked>'
        '<input type="radio" class="srt" name="la" id="la-1">'
        '<input type="radio" class="srt" name="la" id="la-S">'
        + "".join(f'<input type="radio" class="srt" name="la" '
                  f'id="la-X{k}">' for k in range(11))
        + '<input type="reset" class="srt" id="lshow"></form>')
    srt_radios += '<input type="radio" class="srt" name="gp" id="gp-none" checked>'
    srt_radios += "".join(
        f'<input type="radio" class="gpin {_gflags(j)}" name="gp" id="gp-{j}">'
        for j in range(N))
    srt_radios += '<input type="checkbox" class="srt" id="lock">'

    seg_checkboxes = ('<form autocomplete="off">' + "".join(
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
    lanes, _mrow = [], []
    lov_css = ""
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
                    f'style="left:var(--x{j});'
                    f'top:{13 * r - _EXTT[i]}px;'
                    f'display:var(--pd{j},none);'
                    f'color:{_HEX.get(k, "#ccc")};">{txt}</div>')
                if k in ranks:
                    fills.append(
                        f'<div class="tv lrk lrk-{j}" '
                        f'style="left:var(--x{j});'
                        f'top:{13 * r - _EXTT[i]}px;'
                        f'display:var(--pd{j},none);'
                        f'color:{_HEX.get(k, "#ccc")};">{ranks[k][j]}</div>')

        # month gridlines along the W/L lane; the tick labels live in
        # their own .mrow so the axis outlives a shrunk group (they
        # always follow the last plot content)
        if kind == "W/L":
            _m = pd.Timestamp(d0.year, d0.month, 1)
            while _m <= d1:
                _at = max(_m, d0)
                _fx = (0.5 + (_at - d0).days) / (ndays + 1) * 100
                fills.append(
                    f'<div class="mg" style="left:{_fx:.2f}%;"></div>')
                _mrow.append(f'<div class="ml" style="left:{_fx:.2f}%;">'
                             f'{_at.strftime("%b")}</div>')
                _m = (_m + pd.offsets.MonthBegin(1)).normalize()

        # hover machinery: line segments + cells
        _cw = 100.0 / (ndays + 1)
        # hover cells tile the whole axis: each game's cell reaches
        # the midpoints toward its neighbours, so the tracking snaps
        # to the closest game with no dead gaps. The Voronoi span
        # rides width/margin so the sorted and packed views' uniform
        # overrides still land exactly
        _xp = [f * 100.0 for f in x_frac]
        _vlo = [0.0] + [(_xp[j - 1] + _xp[j]) / 2 for j in range(1, N)]
        _vhi = [(_xp[j] + _xp[j + 1]) / 2 for j in range(N - 1)] + [100.0]
        for j in range(N):
            _mj = _vlo[j] - (_xp[j] - _cw / 2)
            fills.append(
                f'<div class="ldl ldl-{j}" style="left:var(--x{j});'
                f'display:var(--pd{j},none);'
                f'background:var(--pbg{j},#C0C0C0);'
                f'opacity:var(--po{j},.75);"></div>'
                f'<label class="lwc lwc-{j} {_gflags(j)}" for="gp-{j}" '
                f'style="left:calc(var(--x{j}) - {_cw / 2:.3f}%);'
                f'width:{_vhi[j] - _vlo[j]:.3f}%;'
                f'margin-left:{_mj:.3f}%;"></label>')
        # the lane badge (margin label = close toggle; parked = open)
        _lfor = ("" if kind in ("+/-", "B2B", "HOM", "W/L")
                 else f'for="lc-{i}" ')
        # right-hand value column, team-page style: at rest the active
        # view's averages, while hovering a game (or its box row) that
        # game's values — one row per group member, colours matching
        _val_html = ""
        if kind not in ("B2B", "HOM", "W/L"):
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
                "\u2192</label>"
                f'<label class="lcx" for="lc-{i}" {_cst}>\u2715</label>'
                '<label class="lcx lcx2" for="la-S"></label>')
        _spans = " ".join(f'<span style="color:{_HEX.get(k, "#ccc")};">'
                          f'{_DN.get(k, k)}</span>'
                          for k in _vrows)
        # the shrunk plot's one line: label + open symbol + the primary
        # member's season MAX / MID / MIN in fixed columns (absolute
        # lefts so the figures align down the shrunk stack)
        _lop = ""
        if kind == "B2B":
            # the schedule strips shrink as one group (label W/L)
            _lop = ('<label class="lops" for="lcs">'
                    f'<span style="color:{_HEX["W/L"]};">W/L</span> '
                    '<span class="lplus" style="color:#aaa">＋</span>'
                    "</label>"
                    '<label class="lops2" for="la-X10"></label>')
        elif kind == "W/L":
            # the open group's label line: inert label + close ✕ that
            # shrinks the whole group
            _cs9 = (f'style="border-color:{_HEX["W/L"]};'
                    f'color:{_HEX["W/L"]};"')
            _lop = ('<label class="lzs">'
                    f'<span style="color:{_HEX["W/L"]};">W/L</span>'
                    "</label>"
                    f'<label class="lcx" for="lcs" {_cs9}>✕</label>'
                    '<label class="lcx lcx2" for="la-S"></label>')
        if kind not in ("B2B", "HOM", "W/L"):
            # one MIN/MID/MAX set per member, LIVE over the currently
            # shown games: min()/max() over per-game terms gated by
            # the visibility vars (hidden games park at ±9999) and a
            # pairwise sum tree (log calc depth) over the visible
            # count for MID (the average of shown games). The numbers
            # render through the counter trick (.lovc).
            _lov = ""
            for _m, _k0 in enumerate(_vrows):
                _vals = [gv(j, _k0) for j in range(N)]
                _pid = f"{i}x{_m}"
                _mna = ",".join(
                    f"calc(9999 - var(--v{j},1)*{9999 - v:.1f})"
                    for j, v in enumerate(_vals))
                _mxa = ",".join(
                    f"calc(var(--v{j},1)*{v + 9999:.1f} - 9999)"
                    for j, v in enumerate(_vals))
                _decl = ""
                _names = []
                for _t in range(0, N, 2):
                    _e = (f"calc(var(--v{_t},1)*{_vals[_t]:.1f}"
                          + (f" + var(--v{_t + 1},1)*"
                             f"{_vals[_t + 1]:.1f})"
                             if _t + 1 < N else ")"))
                    _decl += f"--w{_pid}L1x{_t // 2}:{_e};"
                    _names.append(f"var(--w{_pid}L1x{_t // 2})")
                _lv = 1
                while len(_names) > 1:
                    _lv += 1
                    _nx = []
                    for _t in range(0, len(_names), 2):
                        if _t + 1 < len(_names):
                            _decl += (
                                f"--w{_pid}L{_lv}x{_t // 2}:calc("
                                f"{_names[_t]} + {_names[_t + 1]});")
                            _nx.append(f"var(--w{_pid}L{_lv}x{_t // 2})")
                        else:
                            _nx.append(_names[_t])
                    _names = _nx
                lov_css += (
                    ".wrap{" + _decl
                    + f"--lmn{_pid}:min({_mna});"
                    + f"--lmx{_pid}:max({_mxa});"
                    + f"--lav{_pid}:calc({_names[0]}"
                    "/max(1,var(--tn,1)));}")
                _lov += "".join(
                    f'<span class="lov lovc" style="left:calc('
                    f'{170 + 156 * _m + 48 * t}'
                    f'*var(--u));color:{_HEX.get(_k0, "#ccc")};'
                    f'--cv:var(--{_vn}{_pid});"></span>'
                    for t, _vn in enumerate(("lmn", "lav", "lmx")))
            _lop = (f'<label class="lop" for="lc-{i}">{_spans} '
                    '<span class="lplus" style="color:#aaa">＋</span>'
                    f'{_lov}</label>'
                    f'<label class="lop2" for="la-X{i}"></label>')
        lanes.append(
            f'<div class="lane lane-{i}" style="top:0;height:{STAT_H}px;">'
            + "".join(fills)
            + _val_html
            + f'<label class="lzl'
              f'{" lzg" if len(_vrows) > 1 else ""}" {_lfor}>'
            + _spans
            + "</label>" + _lop + "</div>")

    # ---- gsort css (the sort view IS the page) ----
    _GS = ".st"
    _tc0 = _dim_hex(_TEAM_BRAND_COLORS.get(team, "#999"))
    _R = [_LH[i] + _PADS[i] for i in range(n)]
    _call = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in range(n))
    gsort_css = (
        lov_css
        + _GS + " ~ .wrap .lane .lzl{display:block;}"
        + "".join(_GS + f" ~ .wrap .lane-{i} .lzl{{display:none;}}"
                  for i in range(n)
                  if _ORDER[i] in ("B2B", "HOM", "W/L")))
    # hovers over the always-open schedule strips don't flip the
    # right-hand columns — only stat-lane (or box-row) hovers do
    _STL = (":is(" + ",".join(
        f".lane-{k}" for k, kd in enumerate(_ORDER)
        if kd not in _SCHED) + ")")
    # hovering a game's column scrolls the box score to its row, the
    # season page's trick: the blanket rule withdraws every row's snap
    # point and the per-game rule below restores only the hovered
    # game's — the mandatory snap container must re-snap to it
    # every lane steers the box now — with all lanes resting in date
    # order, cross-lane transit points at the same game, so the old
    # stat-lane-only guard is unnecessary
    gsort_css += (".wrap:has(.lwc:hover) ~ .bxwrap .bxs .br"
                  "{scroll-snap-align:none;}")
    for j in range(N):
        oc = _TEAM_BRAND_COLORS.get(games[j]["opp"], "#999")
        _gdt = games[j]["date"].strftime("%m-%d")
        gsort_css += (
            f"body:has(.bxwrap .br-{j}:hover) :is(.ldl-{j},"
            f".lvv-{j},.lrk-{j}){{display:block!important;}}"
            # important: the rows carry the pin's inline background
            # (var(--pb{j})), which outranks plain hover rules
            f".wrap:has(.lwc-{j}:hover) ~ .bxwrap .br-{j}"
            f"{{background:{oc}8C!important;}}"
            f".bxwrap .br-{j}:hover{{background:{oc}8C!important;}}"
            f'.wrap:has(.lwc-{j}:hover){{--gdt:"{_gdt}";}}'
            f'body:has(.bxwrap .br-{j}:hover) .wrap{{--gdt:"{_gdt}";}}'
            f".wrap:has(.lwc-{j}:hover) ~ .bxwrap .bxs .br-{j}"
            "{scroll-snap-align:start;}")
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
    # games rest in DATE order (the wrap's calendar --x defaults and
    # the cells' Voronoi day spans); a lane's own sort arrows override
    # lane by lane
    for i, kind in enumerate(_ORDER):
        if kind in ("B2B", "HOM", "W/L"):
            continue
        _st = f".st:has(#ls-{i}"
        _lwd = _text_px(" ".join(_badge_rows(kind)), 14) * 1.25
        gsort_css += (
            f".lane-{i} .lcr:not(.pcr)"
            f"{{left:calc({_lwd + 5:.1f}*var(--u) + 16px);}}"
            f".lane-{i} .pcr"
            f"{{left:calc({_lwd + 39.3:.1f}*var(--u) + 20px);}}"
            f".lane-{i} .lcx"
            f"{{left:calc({_lwd + 73.5:.1f}*var(--u) + 24px);}}")
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
        _cwp = 100.0 / (ndays + 1)

        def _psel(inner):
            return ",".join(
                f".st{c}{_pk}{sd}:checked) ~ .wrap .lane-{i} {inner}"
                for c in _FC for sd in ("-l", "-r"))
        gsort_css += (
            _psel(".fl.bar") + "{width:calc(.5*var(--psl))!important;"
            f"margin-left:calc({hw * 100:.2f}% - .25*var(--psl))"
            "!important;}"
            + _psel(".flh") + "{width:calc(.25*var(--psl))!important;"
            f"margin-left:calc({hw * 50:.2f}% - .125*var(--psl))"
            "!important;}"
            + _psel(".lwc") + "{width:var(--psl)!important;"
            f"margin-left:calc({_cwp / 2:.3f}% - .5*var(--psl))"
            "!important;}")
    # the pinned game: its line, chips, info line and box row stay
    # lit until the next click; its B2B/HOM/W-L rows rest visible
    _SCHL = (":is(" + ",".join(
        f".lane-{k}" for k, kd in enumerate(_ORDER)
        if kd in ("B2B", "HOM", "W/L")) + ")")
    def _pin_guard(j):
        # the pin's artifacts only show while the pinned game passes
        # every active filter — a hidden game shows nothing
        g = games[j]
        ns = ""
        for m in (1, 2, 4, 7, 8):
            if not (g["seg"] & m):
                ns += f":not(:has(#seg-m{m}:checked))"
        if not g["ot"]:
            ns += ":not(:has(#gt-o:checked))"
        if not g["clutch"]:
            ns += ":not(:has(#gt-c:checked))"
        ns += (":not(:has(#cf-w:checked))" if _conf(j) == "e"
               else ":not(:has(#cf-e:checked))")
        ns += (":not(:has(#wl-l:checked))" if g["win"]
               else ":not(:has(#wl-w:checked))")
        ns += (":not(:has(#ha-v:checked))" if g["home"]
               else ":not(:has(#ha-h:checked))")
        ns += (":not(:has(.opr:checked:not(#op-all)"
               f":not(#op-{g['opp']})))")
        return ns

    for j in range(N):
        _poc = _TEAM_BRAND_COLORS.get(games[j]["opp"], "#999")
        gsort_css += (
            f"body:has(#gp-{j}:checked){_pin_guard(j)}"
            f"{{--pd{j}:block;--pv{j}:visible;--pz{j}:2;"
            f"--pbg{j}:#FFF;--po{j}:1;--pb{j}:{_poc}59;"
            f'--gdt:"{games[j]["date"].strftime("%m-%d")}";}}')
    # while hovering, the hovered game's schedule rows replace the
    # pinned game's (ordered !important pair keeps this cheap)
    # while another column is actually tracked, only the tracking
    # line shows — the pinned line yields (ordered !important pair);
    # a bare mouseover of the plot area leaves the pin alone
    gsort_css += (".wrap:has(.lwc:hover) .ldl{display:none!important;}"
                  ".wrap:has(.lwc:hover) :is(.lvv,.lrk)"
                  "{display:none!important;}")
    for j in range(N):
        gsort_css += (f".wrap:has(.lwc-{j}:hover) .ldl-{j},"
                      f".wrap:has(.lwc-{j}:hover) .lvv-{j},"
                      f".wrap:has(.lwc-{j}:hover) .lrk-{j}"
                      "{display:block!important;}")
    # lane tops/heights: members inside the window (reclaiming
    # closed members above, shifted by the scrub offset); schedule
    # strips pinned below the window
    # the month ticks only tell the truth on an unsorted, unfiltered
    # calendar — any game filter or a sort on the hovered lane mutes
    # them
    _NOFLT = (":not(:has(:is(#seg-m1,#seg-m2,#seg-m4,#seg-m7,#seg-m8,"
              "#gt-o,#gt-c,#cf-e,#cf-w,#wl-w,#wl-l,#ha-h,#ha-v)"
              ":checked)):not(:has(.opr:checked:not(#op-all)))")
    for i in range(n):
        # open lanes pack to the top: a shrunk lane above yields its
        # whole band (its one-line moves below the open block)
        _up = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px"
                      for k in range(i))
        if i < 10:
            _tex = (f"top:calc({_T2[i] - _T2[0] + 34:.0f}px{_up})"
                    "!important;")
            # hovering this plot's AREA (its game cells — not its
            # label line, and never a shrunk line: closed lanes hide
            # their cells) shows the ticks along its top edge
            gsort_css += (_GS + _NOFLT
                          + f":not(:has(#ls-{i}-u:checked))"
                          f":not(:has(#ls-{i}-d:checked))"
                          f" ~ .wrap:has(.lane-{i} .lwc:hover) .mrowh"
                          "{display:block;"
                          f"top:calc({_T2[i] - _T2[0] + 36:.0f}px{_up});}}")
        else:
            # SHOWN strips sort with the open plots: they sit right
            # after the open stat block (closed group lanes get an
            # end-of-stack top override in the collapse rules)
            _suba = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px"
                            for k in range(10))
            _tex = (f"top:calc({_T2[i] - _T2[10] + _T2[0] + sum(_R[:10]) - 140:.0f}px"
                    f"{_suba})!important;")
        gsort_css += (_GS + f" ~ .wrap .lane-{i}"
                      f"{{{_tex}"
                      f"height:{_LH[i]:.1f}px!important;}}")
        if _CHIP[i]:
            # hover cells stop at the lane bottom: the label line
            # below is mouse-quiet (no tracking line, no label dodge)
            gsort_css += (f".lane-{i} .ldl"
                          f"{{top:{-_EXTT[i]}px;"
                          f"bottom:{-_EXTB[i]}px;}}"
                          f".lane-{i} .lwc"
                          f"{{top:{-_EXTT[i]}px;height:calc(100% + "
                          f"{_EXTT[i]}px);}}")
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

    # ---- the plot carousel (season-page technique): the ten member
    # plots (stats + "+/-") live in a clipped window sized by the
    # 1/3/OPEN row; the left-edge zones scrub it (hover previews,
    # click pins); closed members vanish and park their names on the
    # PLOTS row. The schedule strips stay fixed below the window. ----
    _MEMB = list(range(10))
    _PB = _T2[0] - 34            # the window's top inside .plot
    _MB = [_R[i] for i in _MEMB]
    _SCH = _T2[12] + _R[12] - _T2[10]
    gsort_css += (
        f".pwin{{position:absolute;top:{_PB - 140:.0f}px;left:0;right:0;"
        "height:var(--wh,0px);}"
        ".pcar{position:absolute;left:0;right:0;top:0;height:100%;}"
        + _GS + f" ~ .wrap .plot{{height:calc({_PB + _SCH + 8 - 140:.0f}px"
        # a closed W/L group hands its strip band back too, so the
        # box score keeps a constant distance from the last plot
        f" + var(--wh,0px) - var(--cs,0)*{_SCH + 15:.0f}px);}}"
        + ".tabs2{display:flex;justify-content:flex-start;"
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
        ".pcln{display:flex;justify-content:flex-start;align-items:center;"
        "gap:calc(6*var(--u));flex-wrap:wrap;margin:4px 0;"
        f"font-size:calc({_LFS * 1.25:.1f}*var(--u));text-transform:uppercase;}}"
        ".pcard .pnm{display:block;opacity:.45;}"
        ".fgrp{display:flex;align-items:center;"
        "gap:calc(6*var(--u));border-top:1px solid #888;"
        "padding-top:1px;}"
        + "".join(
            f"{_GS}:has(#la-0:checked):has(#lc-{i}:not(:checked))"
            f" ~ .pc-p .pnm-{i},"
            f"{_GS}:has(#la-1:checked):has(#lc-{i}:checked)"
            f" ~ .pc-p .pnm-{i}"
            "{opacity:1;background:rgba(255,255,255,.12);}"
            for i in _MEMB)
        + f"{_GS}:has(#la-0:checked):has(#lcs:not(:checked))"
        " ~ .pc-p .pnm-wl,"
        f"{_GS}:has(#la-1:checked):has(#lcs:checked)"
        " ~ .pc-p .pnm-wl"
        "{opacity:1;background:rgba(255,255,255,.12);}"
        + f".ptg2{{position:absolute;top:2px;left:0;"
        f"width:calc({TW} + 16px);"
        "display:flex;align-items:center;justify-content:center;"
        "gap:calc(6*var(--u));"
        f"font-size:calc({_LFS}*var(--u));text-transform:uppercase;"
        "z-index:200;}"
        ".ptg2 .tg{background:none;}"
        ".ptg2b{top:30px;}"
        ".ptg2c{top:56px;}"
        f".ptgv{{top:0;justify-content:flex-end;"
        f"width:calc({TW} + 3px);}}"
        ".pclr{margin-right:-13px;}"
        # SHOW lights while anything is shrunk; SHRINK lights while
        # anything is open (both can be lit in a mixed state)
        + "".join(
            f"{_GS}:has(#{_la}:checked)"
            f":has(:is({_lcu}){_st}) ~ :is(.wrap,.pc-p) .{_cls}"
            "{color:#ddd;background:rgba(255,255,255,.16);}"
            for _lcu in [",".join([f"#lc-{k}" for k in range(10)]
                                  + ["#lcs"])]
            for _la, _st, _cls in (
                ("la-0", ":checked", "psh"),
                ("la-1", ":not(:checked)", "psh"),
                ("la-0", ":not(:checked)", "pclr"),
                ("la-1", ":checked", "pclr")))
        + '.ptgv::before{content:var(--gdt,"");margin-right:auto;color:#9BA3AD;}'
        f".pinb{{display:none;order:-1;margin-right:10px;"
        "color:#ddd;background:rgba(255,255,255,.16);"
        f"font-size:calc({_LFS}*var(--u));text-transform:uppercase;}}"
        ".st:not(:has(#gp-none:checked)) ~ .wrap .pinb"
        "{display:block;}"
        ".st:has(#gp-none:checked) ~ .wrap .pbx{display:none;}"
        # no pin, no chrome: the game-info + box-excerpt band
        # above the plots hands its 100px back, and the count
        # line, plots and box score all ride up

        ".tglh{margin:14px 0 2px 26px;}"
        ".tgl2{margin:0 0 4px 26px;}"
        ".pnm{display:none;}"
        ".pnm span{margin-right:4px;}")
    # a shrunk plot keeps a single line: the lane collapses to zero
    # height, its content hides, and only the .lop line (label + open
    # symbol) shows; clicking it reopens. Shrunk lines gather BELOW
    # the open block: each takes the open total plus 20px per shrunk
    # lane before it
    # the header row lights up whenever every stat chart is shrunk
    for _acn in (
            _GS + ":has(#la-0:checked)"
            + "".join(f":has(#lc-{k}:checked)" for k in range(10)),
            _GS + ":has(#la-1:checked)"
            + "".join(f":has(#lc-{k}:not(:checked))" for k in range(10)),
            _GS + ":has(#la-S:checked)"):
        gsort_css += _acn + " ~ .wrap .lohd{display:block;}"

    # ---- SHRINK always shuts everything in one click. Clean
    # all-open flips the la inverter (the one-liners' + stays live);
    # a mixed state checks the la-S "all shut" latch, which closes
    # every lane regardless of the per-plot boxes — under it the
    # one-liners go inert and SHOW is the way back. The inert .pcx
    # shows (unlit) when there is nothing left to shrink.
    _oids = [f"lc-{k}" for k in range(10)] + ["lcs"]
    _all_u = ",".join("#" + o for o in _oids)
    _XU = ",".join(f"#la-X{k}" for k in range(11))
    _LAX = f":has(:is({_XU}):checked)"
    _shr_html = ('<span class="tg pclr pcx">SHRINK</span>'
                 '<label class="tg pclr pcs pcs-all" for="la-S">'
                 "SHRINK</label>")
    gsort_css += (
        ".pcs{display:none;}"
        # SHOW is two-stage: under the shut-all latch it returns to
        # normal mode with the manual closes intact (for="la-0");
        # in normal mode it is the full reset that shows everything
        ".psh-0{display:none;}"
        + f"{_GS}:has(:is(#la-S,{_XU}):checked)"
        " ~ :is(.wrap,.pc-p) .psh-0{display:inline-block;}"
        + f"{_GS}:has(:is(#la-S,{_XU}):checked)"
        " ~ :is(.wrap,.pc-p) .psh-r{display:none;}"
        + f"{_GS}:has(#la-0:checked):has(:is({_all_u}):not(:checked))"
        " ~ :is(.wrap,.pc-p) .pcx,"
        f"{_GS}:has(#la-1:checked):has(:is({_all_u}):checked)"
        " ~ :is(.wrap,.pc-p) .pcx"
        "{display:none;}"
        # one SHRINK: the shut-all latch, shown whenever anything is
        # open (the complement of the inert .pcx conditions)
        + f"{_GS}:has(#la-0:checked):has(:is({_all_u}):not(:checked))"
        " ~ :is(.wrap,.pc-p) .pcs-all,"
        f"{_GS}:has(#la-1:checked):has(:is({_all_u}):checked)"
        " ~ :is(.wrap,.pc-p) .pcs-all"
        "{display:inline-block;}"
        # under the latch a shrunk line's click peeks that plot open
        # (transparent overlays retarget the lines to la-X radios; the
        # peeked plot's ✕ overlay re-shuts to la-S)
        + ".lop2,.lops2{display:none;position:absolute;top:0;left:0;"
        "right:0;height:28px;z-index:165;cursor:pointer;}"
        ".lcx2{display:none;z-index:166;cursor:pointer;}"
        + "".join(
            f"{_GS}:has(#la-X{k}:checked) ~ .wrap "
            f".lane-{k if k < 10 else _ORDER.index('W/L')} .lcx2"
            "{display:block;}"
            for k in range(11))
        + f"{_GS}{_LAX} ~ :is(.wrap,.pc-p) .pcs-all"
        "{display:inline-block;}"
        + f"{_GS}{_LAX} ~ :is(.wrap,.pc-p) .pcx{{display:none;}}"
        + f"{_GS}{_LAX} ~ :is(.wrap,.pc-p) .pclr"
        "{color:#ddd;background:rgba(255,255,255,.16);}"
        + f"{_GS}:has(:is(#la-S,{_XU}):checked) ~ :is(.wrap,.pc-p) .psh"
        "{color:#ddd;background:rgba(255,255,255,.16);}"
        # under the latch the PLOTS chips swap to their peek twins
        + ".pcard .pnm.pnmx{display:none;}"
        + f"{_GS}:has(:is(#la-S,{_XU}):checked) ~ .pc-p "
        ".pnm:not(.pnmx){display:none;}"
        + f"{_GS}:has(:is(#la-S,{_XU}):checked) ~ .pc-p "
        ".pnmx{display:block;}"
        + "".join(
            f"{_GS}:has(#la-X{k}:checked) ~ .pc-p .pnmx-{k}"
            "{opacity:1;background:rgba(255,255,255,.12);}"
            for k in range(11))
        + ".pc-p .pclr{margin-right:0;}")

    _SUMR = sum(_MB)
    _sub_all = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in _MEMB)
    # the schedule group's band: shrunk stat lines start below it
    # unless the group itself is shrunk (--cs)
    _S = _T2[12] - _T2[10] + _LH[12] + 34
    for i in _MEMB:
        _lines_above = "".join(f" + var(--c{k},0)*24px"
                               for k in range(i))
        # the latch family: la-S shuts every lane; la-X{k} shuts all
        # but lane k (the "peek" a shrunk line's click opens)
        _lat_i = (":has(:is(" + ",".join(
            ["#la-S"] + [f"#la-X{k}" for k in range(11) if k != i])
            + "):checked)")
        _exc = ":not(.lop):not(.lop2)"
        for _lb, _cnd in (
                (False,
                 _GS + f":has(#la-0:checked):has(#lc-{i}:checked)"),
                (False,
                 _GS + f":has(#la-1:checked):has(#lc-{i}:not(:checked))"),
                (True, _GS + _lat_i)):
            gsort_css += (
                _cnd + f" ~ .wrap{{--c{i}:1;}}"
                + _cnd + f" ~ .wrap .lane-{i}"
                f"{{height:0!important;background:none;"
                # +20: a breath between the open block and the lines
                f"top:calc({_SUMR + 44 + _S:.0f}px{_sub_all}{_lines_above}"
                f" - var(--cs,0)*{_S:.0f}px)"
                "!important;}"
                + _cnd + f" ~ .wrap .lane-{i} > {_exc}"
                "{display:none!important;}"
                + _cnd + f" ~ .wrap .lane-{i} "
                + (":is(.lop,.lop2){display:block;}" if _lb
                   else ".lop{display:block;}"))

    # ---- accordion mode: no scrolling. The plot area is always the
    # full stack (open bands + 20px lines for shrunk plots); the old
    # window/pan/scroll machinery is neutralised, and the schedule
    # strips ride the same --wh so they sit right below the stack ----
    _sub2 = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px"
                    for k in _MEMB)
    gsort_css += (
        _GS + " ~ .wrap{"
        f"--wh:calc({sum(_MB) + 34:.0f}px{_sub2});}}"
        ".lop{display:none;position:absolute;top:0;"
        f"left:calc({(_tbl_chars * 8.34443 - 618) / 2:.0f}*var(--u));"
        # same size as the shown label lines
        "font-size:calc(17.5*var(--u));"
        "line-height:1.15;z-index:160;"
        "cursor:pointer;white-space:nowrap;padding:1px 8px 1px 0;}"
        ":is(.lop,.lops,.lohd) .lov{position:absolute;top:1px;"
        "width:calc(40*var(--u));text-align:right;}"
        # live figures: the counter trick prints round(--cv)
        ".lovc::before{counter-reset:cv calc(round(var(--cv,0)));"
        "content:counter(cv);}"
        # column headers over the shrunk table, shown only when no
        # charts are open
        ".lohd{display:none;position:absolute;right:0;"
        f"left:calc({(_tbl_chars * 8.34443 - 618) / 2:.0f}*var(--u));"
        "font-size:calc(14*var(--u));"
        "line-height:1.15;color:#9BA3AD;z-index:160;"
        f"top:calc({_SUMR + 44 + _S - 22:.0f}px{_sub_all}"
        f" - var(--cs,0)*{_S:.0f}px);}}"
        # the schedule group's one line + its open-state label
        ".lops{display:none;position:absolute;top:0;right:0;"
        f"left:calc({(_tbl_chars * 8.34443 - 618) / 2:.0f}*var(--u));"
        "height:28px;"
        "font-size:calc(17.5*var(--u));"
        "line-height:1.15;z-index:160;cursor:pointer;"
        "white-space:nowrap;padding:1px 8px 1px 0;}"
        ".lops span{position:relative;z-index:2;}"

        ".lzs{position:absolute;top:calc(100% + 2px);left:0;"
        "font-size:calc(17.5*var(--u));line-height:1.15;"
        "z-index:160;pointer-events:none;white-space:nowrap;"
        "padding:1px 8px 1px 0;}"
        f".lane-{_ORDER.index('W/L')} .lcx"
        f"{{left:calc({_text_px('W/L', 14) * 1.25 + 5:.1f}"
        "*var(--u) + 16px);}")
    _SIS = [i for i, k in enumerate(_ORDER) if k in ("B2B", "HOM", "W/L")]
    _slanes = ":is(" + ",".join(f".lane-{i}" for i in _SIS) + ")"
    # the month ticks exist only on hover: on a stat plot's own area,
    # on the W/L strip's area for the open group, or under the
    # shrunk group's one line
    gsort_css += (
        ".mrowh{display:none;position:absolute;left:0;right:0;"
        "height:14px;z-index:150;pointer-events:none;}"
        ".mrowh .ml{top:0;margin-top:0;background:#000;padding:0 2px;}")
    # ONE months line for the whole W/L group: hovering any of its
    # three open strips shows it near the top of the B2B band; the
    # shrunk one-line never shows it
    _subm = "".join(f" - var(--c{k},0)*{_R[k]:.0f}px" for k in _MEMB)
    for _op in (_GS + ":has(#la-0:checked):has(#lcs:not(:checked))",
                _GS + ":has(#la-1:checked):has(#lcs:checked)",
                _GS + ":has(#la-X10:checked)"):
        gsort_css += (
            _op + _NOFLT
            + " ~ .wrap:has(" + _slanes + " .lwc:hover) .mrowh"
            f"{{display:block;top:calc({sum(_MB) + 36:.0f}px{_subm});}}")
    _lat_g = (":has(:is(#la-S," + ",".join(
        f"#la-X{k}" for k in range(10)) + "):checked)")
    for _lbg, _cnds in (
            (False, _GS + ":has(#la-0:checked):has(#lcs:checked)"),
            (False, _GS + ":has(#la-1:checked):has(#lcs:not(:checked))"),
            (True, _GS + _lat_g)):
        gsort_css += (
            _cnds + " ~ .wrap{--cs:1;}"
            + _cnds + f" ~ .wrap {_slanes}"
            "{height:0!important;background:none;"
            # the shrunk group's line sorts last: end of the stack
            f"top:calc({_T2[0] - 174:.0f}px + var(--wh,0px))!important;}}"
            + _cnds + f" ~ .wrap {_slanes} > :not(.lops):not(.lops2)"
            "{display:none!important;}"
            + _cnds + f" ~ .wrap .lane-{_SIS[0]} "
            + (":is(.lops,.lops2){display:block;}" if _lbg
               else ".lops{display:block;}"))
    # shrunk plots are parked for now: a shrunk lane leaves no
    # residual line, headers, or slot — it simply disappears (the
    # PLOTS panel chips and SHOW bring plots back)
    gsort_css += (".lop,.lop2,.lops,.lops2,.lohd"
                  "{display:none!important;}")

    # outputs tree: <season>/<tri>/html/ holds this page; a game's
    # page and csv live under its HOME team's dirs
    def _ghome(g):
        return (team if g["home"] else g["opp"]).lower()

    def _ghref(g):
        return (f'pm_players_{g["gid"]}.html' if g["home"] else
                f'../../{_ghome(g)}/html/pm_players_{g["gid"]}.html')

    def _gcsv(g):
        return (output_path.parent.parent.parent / _ghome(g) / "csv"
                / f'pbp_{g["gid"]}.csv')

    # ---- box table: one row per game ----
    _NAME_W = 24
    col_hi = {key: max(gv(j, key) for j in range(N))
              for _, key, _, c, _ in _BOX_COLS2 if c}
    col_lo = {key: min(gv(j, key) for j in range(N))
              for _, key, _, c, _ in _BOX_COLS2 if c}
    rows_html, pbx_rows = [], []
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
        name = (f'<a href="{_ghref(g)}">'
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
            if key == "MIN":
                v /= 60
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
        rows_html.append(f'<div class="br br-{j} {_gflags(j)}" '
                         f'style="background:var(--pb{j},transparent);">'
                         + "".join(parts) + "</div>")
        pbx_rows.append(f'<div class="pbr pbr-{j}" '
                        f'style="display:var(--pd{j},none);'
                        f'background:var(--pb{j},transparent);">'
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
                if key == "MIN":
                    v /= 60
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
                _cn = []
                if _SEGN[m[0]]:
                    _cn.append(f'<span style="color:#cfa96b">'
                               f'{_SEGN[m[0]]}</span>')
                if cf != "a":
                    _cn.append(f'<span style="color:#7fa6d9">'
                               f'{"EAST" if cf == "e" else "WEST"}</span>')
                if m[1] == "o":
                    _cn.append('<span style="color:#7fc9a6">OT</span>')
                if m[1] == "c":
                    _cn.append('<span style="color:#7fc9a6">CLUTCH</span>')
                if wl != "a":
                    _cn.append('<span style="color:#2ecc55">W</span>'
                               if wl == "w" else
                               '<span style="color:#ff5252">L</span>')
                if ha != "a":
                    _cn.append(
                        f'<span style="color:'
                        f'{_cap(_TEAM_BRAND_COLORS.get(team, "#c0c0c0"))}"'
                        '>H</span>' if ha == "h" else
                        '<span style="color:#9BA3AD">A</span>')
                _plain = f"{lbl} {len(sel)}"
                if len(_plain) <= _NAME_W - 1:
                    cells[0] = (
                        '<span style="color:#666">+</span>'.join(_cn)
                        + f" {len(sel)}"
                        + " " * (_NAME_W - len(_plain)))
                fmsgs.append(f'<div class="fmsg fm-{_fmk}">'
                             + "".join(cells) + "</div>")
                combo_css += (_gate(m, cf, wl, ha)
                              + f" ~ .bxwrap .fm-{_fmk}{{display:block;}}")
            _fmk += 1

    for _tri in _OPPS:
        _osel = [j for j in range(N) if games[j]["opp"] == _tri]
        _oplain = f"vs {_tri} {len(_osel)}"
        _ocells = [
            f'vs <span style="color:'
            f'{_dim_hex(_TEAM_BRAND_COLORS.get(_tri, "#999"))}">{_tri}</span>'
            f' {len(_osel)}' + " " * (_NAME_W - len(_oplain))]
        for lab, key, w, _c2_, _i2_ in _BOX_COLS2:
            v = sum(gv(j, key) for j in _osel) / len(_osel)
            if key == "MIN":
                v /= 60
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
                 + '<div class="bxs">'
                 + "".join(rows_html) + '<div class="bxsp"></div></div>'
                 + "".join(col_stripes) + "</div>")
    def _fpass(g, sm, ot, cl, cf2, wl, ha, op):
        return ((g["seg"] & sm)
                and (not ot or g["ot"]) and (not cl or g["clutch"])
                and (cf2 == "a"
                     or (("e" if g["opp"] in _TEAM_EAST else "w")
                         == cf2))
                and (wl == "a" or (g["win"] if wl == "w"
                                   else not g["win"]))
                and (ha == "a" or (g["home"] if ha == "h"
                                   else not g["home"]))
                and (op == "a" or g["opp"] == op))

    from functools import lru_cache

    @lru_cache(maxsize=None)
    def _fempty(sm, ot, cl, cf2, wl, ha, op):
        return not any(_fpass(g, sm, ot, cl, cf2, wl, ha, op)
                       for g in games)
    _opps = ["a"] + sorted({g["opp"] for g in games})
    _msgr = []
    for _sm, _ in _SEG_BTNS:
        for _ot in (False, True):
            for _cl in (False, True):
                for _cf2 in ("a", "e", "w"):
                    for _wl in ("a", "w", "l"):
                        for _ha in ("a", "h", "v"):
                            for _op in _opps:
                                _st7 = (_sm, _ot, _cl, _cf2,
                                        _wl, _ha, _op)
                                if not _fempty(*_st7):
                                    continue
                                # minimal only: every single-step
                                # relaxation is non-empty
                                if _sm != 15 and _fempty(
                                        15, _ot, _cl, _cf2,
                                        _wl, _ha, _op):
                                    continue
                                if _ot and _fempty(
                                        _sm, False, _cl, _cf2,
                                        _wl, _ha, _op):
                                    continue
                                if _cl and _fempty(
                                        _sm, _ot, False, _cf2,
                                        _wl, _ha, _op):
                                    continue
                                if _cf2 != "a" and _fempty(
                                        _sm, _ot, _cl, "a",
                                        _wl, _ha, _op):
                                    continue
                                if _wl != "a" and _fempty(
                                        _sm, _ot, _cl, _cf2,
                                        "a", _ha, _op):
                                    continue
                                if _ha != "a" and _fempty(
                                        _sm, _ot, _cl, _cf2,
                                        _wl, "a", _op):
                                    continue
                                if _op != "a" and _fempty(
                                        _sm, _ot, _cl, _cf2,
                                        _wl, _ha, "a"):
                                    continue
                                _sel = (".st:has(#seg-m"
                                        f"{_sm}:checked)")
                                if _ot:
                                    _sel += ":has(#gt-o:checked)"
                                if _cl:
                                    _sel += ":has(#gt-c:checked)"
                                if _cf2 != "a":
                                    _sel += (f":has(#cf-{_cf2}"
                                             ":checked)")
                                if _wl != "a":
                                    _sel += (f":has(#wl-{_wl}"
                                             ":checked)")
                                if _ha != "a":
                                    _sel += (f":has(#ha-{_ha}"
                                             ":checked)")
                                if _op != "a":
                                    _sel += (f":has(#op-{_op}"
                                             ":checked)")
                                _msgr.append(
                                    _sel + " ~ .bxwrap .bxmsg"
                                    "{display:block;}")
    gsort_css += "".join(_msgr)
    gsort_css += (
        ".bxmsg{display:none;position:absolute;left:0;right:0;"
        "text-align:center;color:#888;"
        "font-size:calc(var(--vw)*0.0462);"
        "top:calc(40px + var(--vw)*0.0693);}"
        ".bxwrap{position:relative;}"
        ".st:has(#bx-h:checked) ~ .bxwrap .bxmsg"
        "{display:block;}")
    # the scroll box: 10 or 25 lines (a line is 1.5x the responsive
    # font), or MANY = every row
    gsort_css += (
        ".bxs{overflow-y:auto;overflow-x:hidden;"
        "scrollbar-gutter:stable;direction:rtl;margin-left:-24px;"
        "scroll-snap-type:y mandatory;}"
        ".bxs .br{scroll-snap-align:start;direction:ltr;}"
        ".bxs::-webkit-scrollbar{width:24px;}"
        f".bxs::-webkit-scrollbar-thumb{{background:"
        f"linear-gradient({_cap(_TEAM_BRAND_COLORS.get(team, '#999'))},"
        f"{_tc0});"
        "border-radius:5px;border:6px solid #000;}"
        f".bxs::-webkit-scrollbar-thumb:hover{{background:"
        f"linear-gradient(#FFF,{_tc0});box-shadow:0 0 8px {_tc0};}}"
        ".bxs::-webkit-scrollbar-track{background:rgba(255,255,255,.06);}"
        f".btg{{display:flex;align-items:center;"
        f"justify-content:flex-end;width:calc({TW} + 3px);"
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
                 + _tgl("wl-w", "W") + _tgl("wl-l", "L")
                 + "</span>"
                 + '<span class="fgrp">'
                 + _tgl("ha-h", "H") + _tgl("ha-v", "A")
                 + "</span>")

    tname = _TEAM_NAMES.get(team, team)
    try:
        _y0, _y1 = season.split("-")
        full_season = f"{_y0}-{_y0[:2]}{_y1}"
    except Exception:
        full_season = season
    tab_title = f"{tname} {full_season} Games"
    tc = _dim_hex(_TEAM_BRAND_COLORS.get(team, "#999"))

    css = f"""
body{{background:#000;color:#b6b6b6;font-family:'DejaVu Sans',sans-serif;margin:0 auto 24px;width:calc({TW} + 68px);
  --vw:clamp(700px, 100vw, 1200px);--u:calc(var(--vw) / 900);}}
@supports (width: round(1px, 1px)) {{
  body{{--vw:clamp(700px, round(100vw, 32px), 1200px);}}
}}
.wrap{{position:relative;width:{PW};margin:0 0 0 26px;}}
.plot{{position:relative;height:100px;}}
.lane{{position:absolute;left:0;right:0;contain:layout style;background:rgba(255,255,255,.035);}}
.fl{{position:absolute;}}
.bar{{opacity:.85;}}
.tv{{display:none;position:absolute;transform:translateX(-50%);
  font-size:9px;line-height:1;padding:1px 2px;border-radius:3px;
  background:#000;white-space:nowrap;pointer-events:none;
  z-index:150;font-family:'DejaVu Sans Mono',monospace;}}
.seg,.srt{{display:none;}}
.ltx{{display:none;position:absolute;top:100%;margin-top:3px;
  transform:translateX(-50%);writing-mode:vertical-rl;line-height:1;
  font-size:{_LTX_FS};pointer-events:none;z-index:3;
  font-family:'DejaVu Sans Mono',monospace;}}
.ltxa{{pointer-events:auto;cursor:pointer;z-index:121;
  text-decoration:none;}}
.ltxa:hover{{text-decoration:underline;}}
.lwc{{display:block;position:absolute;top:0;height:100%;
  z-index:120;cursor:crosshair;}}
.lwc:hover{{background:rgba(255,255,255,.06);}}
.ldl{{display:none;position:absolute;top:0;bottom:0;
  width:3px;margin-left:-1.5px;background:#C0C0C0;opacity:.75;
  z-index:-1;pointer-events:none;}}

.lvv{{transform:translateX(calc(-100% - 3px));}}
.lrk{{transform:translateX(3px);}}
.lvv-0,.lvv-1,.lvv-2,.lvv-3,.lvv-4,.lvv-5{{transform:translateX(3px);}}
.lrk-0,.lrk-1,.lrk-2,.lrk-3,.lrk-4,.lrk-5{{transform:translateX(calc(-100% - 3px));}}
.lzl{{display:none;position:absolute;top:calc(100% + 2px);left:0;
  right:auto;width:auto;text-align:left;
  font-size:calc(17.5*var(--u));line-height:1.15;z-index:160;pointer-events:none;
  white-space:nowrap;padding:1px 8px 1px 0;}}
.lzl span{{display:inline;}}
.lgv{{display:none;position:absolute;bottom:0;
  left:calc({_tbl_chars * 8.34443 - 27:.2f}*var(--u) + 0px);
  width:calc(27*var(--u));text-align:right;
  font-size:calc(14*var(--u));line-height:1.15;z-index:6;pointer-events:none;
  white-space:nowrap;}}
.lgv span{{display:block;}}
.lcr{{display:none;position:absolute;
  top:calc(100% + 2px);
  left:30px;
  width:calc(29.3*var(--u));
  height:calc(20.1*var(--u));
  box-sizing:border-box;text-align:center;
  line-height:calc(20.1*var(--u));
  font-size:calc(17.5*var(--u));
  z-index:161;cursor:pointer;}}
.lcr:hover{{background:rgba(255,255,255,.12);}}
.lcx{{position:absolute;top:calc(100% + 2px);
  width:calc(20.1*var(--u));height:calc(20.1*var(--u));
  box-sizing:border-box;text-align:center;
  line-height:calc(20.1*var(--u));
  font-size:calc(17.5*var(--u));color:#aaa;
  z-index:161;cursor:pointer;}}
.lcx:hover{{background:rgba(255,255,255,.16);}}
.pcr{{left:60px;}}
.lgvL{{left:calc(100% + 8*var(--u));width:auto;text-align:left;}}
.lgvM{{left:calc({_tbl_chars * 8.34443 - 78:.2f}*var(--u) + 3px);
  width:calc(78*var(--u));text-align:center;}}
.lgvL span,.lgvC span,.lgvM span{{display:inline;}}
.lgvC{{left:calc({_tbl_chars * 8.34443 - 78:.2f}*var(--u) + 3px);
  width:calc(78*var(--u));text-align:center;}}

.lcls,.lals{{display:none;position:absolute;top:13px;transform:translateY(-50%);
  font-size:calc({_CFS}*var(--u));
  line-height:1.15;padding:1px 3px;border-radius:3px;
  background:rgba(0,0,0,.72);color:#aaa;cursor:pointer;z-index:130;
  user-select:none;white-space:nowrap;}}
.lcls:hover,.lals:hover{{color:#ddd;background:rgba(255,255,255,.16);}}
.lpl{{display:none;position:absolute;top:13px;transform:translateY(-50%);
  font-size:calc({_PLFS}*var(--u));
  line-height:1.15;padding:1px 3px;color:#888;z-index:6;
  text-transform:uppercase;pointer-events:none;white-space:nowrap;}}
.toggles{{width:calc({TW} + 16px);margin:16px 0 14px 26px;display:flex;
  align-items:center;justify-content:center;gap:calc(6*var(--u));
  font-size:calc(17.1*var(--u));text-transform:uppercase;}}
.tglabel{{color:#888;padding-right:8px;
  font-size:calc({_PLFS}*var(--u));}}
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
.glns{{position:absolute;top:0;left:0;right:0;
  height:22px;z-index:5;pointer-events:none;}}
.gln{{visibility:hidden;position:absolute;top:0;line-height:22px;
  pointer-events:auto;white-space:nowrap;
  left:calc(({TW} + 16px)/2);transform:translateX(-50%);
  font-size:calc(17.6*var(--u));font-family:'DejaVu Sans Mono',monospace;
  color:#a6a6a6;background:#000;min-width:60%;text-align:center;
  z-index:1;}}
.gln a{{color:#6ca0ff;text-decoration:none;}}
.gln a:hover{{text-decoration:underline;}}
.bxwrap{{margin:40px 0 12px 26px;}}
.fmsg{{display:none;order:-2;color:#8f8f8f;}}
.pbx{{display:none;position:absolute;top:42px;left:0;width:calc({TW} + 16px);
  font-family:'DejaVu Sans Mono',monospace;
  line-height:1.5;font-size:calc(var(--vw) * 0.0154);
  white-space:pre;color:#a6a6a6;}}
.pbx .pbr{{display:none;position:relative;}}
.pbx a{{text-decoration:none;color:inherit;}}
.pbx a:hover{{text-decoration:underline;}}
.pbx label:hover{{text-decoration:underline;}}
.bx{{display:flex;flex-direction:column;position:relative;
  font-family:'DejaVu Sans Mono',monospace;
  line-height:1.5;font-size:calc(var(--vw) * 0.0154);
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
.lgl{{position:absolute;top:12px;left:16px;font-size:13px;
  display:flex;flex-direction:column;gap:2px;}}
.lgl a{{color:#6ca0ff;text-decoration:none;}}
.lgl a:hover{{text-decoration:underline;}}
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
        _gap = (g["date"] - games[j - 1]["date"]).days if j else 0
        if _gap == 1:
            _b2b = (("H" if games[j - 1]["home"] else "A")
                    + " " + ("H" if g["home"] else "A"))
        elif _gap >= 3:
            _b2b = "REST"
        else:
            _b2b = "-"
        _b2c = ("#9BA3AD" if _b2b == "-"
                else "#2ecc55" if _b2b == "REST"
                else "#2ecc55" if g["win"] else "#ff5252")
        _ginner = (
            f'{g["date"].strftime("%Y-%m-%d")}&nbsp; '
            f'<span style="color:{_cap(_TEAM_BRAND_COLORS.get(team, "#c0c0c0"))}">'
            f'{team}</span>{" vs. " if g["home"] else " @ "}'
            f'<span style="color:{_cap(_TEAM_BRAND_COLORS.get(g["opp"], "#c0c0c0"))}">'
            f'{g["opp"]}</span>&nbsp; '
            f'<span style="color:{"#2ecc55" if g["win"] else "#ff5252"}">{res}</span>'
            + (f'&nbsp; <span style="color:{_b2c}">{_b2b}</span>'
               if _b2b != "-" else "")
            + (f'  <a href="{_ghref(g)}" style="color:#6ca0ff">LINK</a>'
               if _gcsv(g).exists() else ""))
        gln_html.append(
            f'<div class="gln gln-{j}" '
            f'style="visibility:var(--pv{j},hidden);'
            f'z-index:var(--pz{j},1);">' + _ginner + "</div>")

    # each chip has a latch twin targeting the peek radio, so the
    # PLOTS tab buttons show/shrink plots in every state; colours key
    # on the raw stat kinds (the display names are not palette keys)
    def _pnm_spans(i):
        return " ".join(f'<span style="color:{_HEX.get(k2, "#ccc")};">'
                        f'{_DN.get(k2, k2)}</span>'
                        for k2 in _vrows_of(_ORDER[i]))
    pnames = [
        f'<label class="tg pnm pnm-{i}" for="lc-{i}">'
        + _pnm_spans(i) + "</label>"
        + f'<label class="tg pnm pnmx pnmx-{i}" for="la-X{i}">'
        + _pnm_spans(i) + "</label>"
        for i in range(10)]
    _wl_span = (f'<span style="color:{_HEX["W/L"]};">W/L</span>')
    _wlchip = (f'<label class="tg pnm pnm-wl" for="lcs">{_wl_span}'
               "</label>"
               f'<label class="tg pnm pnmx pnmx-10" for="la-X10">'
               f"{_wl_span}</label>")
    # upper-left corner nav: season page, then the previous and next
    # team pages in a circle over the alphabetical tricodes
    _tris = sorted(t.lower() for t in _TEAM_BRAND_COLORS)
    _ti = _tris.index(team.lower())
    _pv, _nx = _tris[_ti - 1], _tris[(_ti + 1) % len(_tris)]
    _lgl_html = (
        '<div class="lgl">'
        '<a href="../../html/nba_season.html">'
        '<span style="font-size:75%">^</span> '
        f"{season.split('-')[0][2:]}/{season.split('-')[1]}</a>"
        f'<a href="../../{_pv}/html/team_{_pv}.html">'
        f"‹ {_pv.upper()}</a>"
        f'<a href="../../{_nx}/html/team_{_nx}.html">'
        f"› {_nx.upper()}</a></div>")
    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{tab_title}</title><style>{css}</style></head><body>"
        + _lgl_html +
        f"<div class=\"st\">{seg_checkboxes}{srt_radios}</div>"
        + '<div class="tabs2">'
          '<label class="tb-g" for="pg-g">GAMES</label>'
          '<label class="tb-p" for="pg-p">PLOTS</label>'
        + f'<label class="tb-t" for="pg-t">'
          f'<span style="color:{tc}">{tname}</span> {full_season}</label>'
          '</div>'
        + '<div class="toggles pcard pc-g">'
        + f'<div class="pcln">{seg_line1}</div>'
        + f'<div class="pcln">{seg_line2}</div></div>'
        + '<div class="toggles pcard pc-p">'
        + '<div class="pcln">'
          '<label class="tg psh psh-r" for="lshow">SHOW</label>'
          '<label class="tg psh psh-0" for="la-0">SHOW</label>'
        + _shr_html
        + pnames[9] + _wlchip + "</div>"
        + '<div class="pcln">' + "".join(pnames[0:6]) + "</div>"
        + '<div class="pcln">' + "".join(pnames[6:9]) + "</div></div>"
        + '<div class="toggles pcard pc-t">'
          '<div style="white-space:pre-line;text-transform:none">'
          'thank you\n\n\n....</div></div>'

        + '<div class="wrap">'
        + '<div class="ptg2 ptgv">'
          '<label class="tg pinb" for="gp-none">PINNED</label>'
          '<label class="tg psh psh-r" for="lshow">SHOW</label>'
          '<label class="tg psh psh-0" for="la-0">SHOW</label>'
        + _shr_html + "</div>"
        + '<div class="plot">'
        + '<div class="pwin"><div class="pcar">'
        + "".join(lanes[:10])
        + '<div class="mrowh">' + "".join(_mrow) + "</div>"
        + '<div class="lohd">'
        + "".join(f'<span class="lov" style="left:calc('
                  f'{170 + 156 * _m + 48 * _t}*var(--u));">'
                  + ("MIN", "MID", "MAX")[_t] + "</span>"
                  for _m in range(3) for _t in range(3))
        + "</div>"
        + "</div></div>"
        + "".join(lanes[10:])
        + "</div>"
        + '<div class="glns">' + "".join(gln_html) + "</div>"
        + '<div class="pbx">'
        + f'<div class="pbx-h">{hdr_html}</div>'
        + "".join(pbx_rows) + "</div>"
        + "</div>"
        + '<div class="bxwrap"><div class="btg">'
          '<label class="tg tg-bx-10" for="bx-10">10</label>'
          '<label class="tg tg-bx-25" for="bx-25">25</label>'
          '<label class="tg tg-bx-a" for="bx-a">ALL</label>'
          '<label class="tg tg-bx-h" for="bx-h">HIDE</label></div>'
        + '<div class="bxmsg">No Games</div>'
        + f'{box_table}</div></body></html>'
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
