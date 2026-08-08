"""The shot chart — one half court, every field goal drawn as the line it
travelled from its launch point to the rim.

Free throws are not shots in this sense and are excluded; the feed agrees,
marking every one of them isFieldGoal=0, so the filter is that flag and
nothing hand-rolled.

Coordinates are the NBA's own legacy pair, in TENTHS OF A FOOT with the
origin at the basket, which is why both teams' attempts land on one half
court: the feed has already reflected each team onto the rim it attacked.
That also means the court can be drawn to the rule book in the SAME units
as the data — every dimension below is the published one, converted once.

Geometry is written in `cqw` throughout rather than percent. A rotated
line's width resolves against the container's INLINE size, so a diagonal
drawn with a percentage length comes out wrong by the container's aspect
ratio — one unit has to mean the same distance on both axes, and cqw is
the unit on this page that does.

Borrowed from the page it lands on: `.chart-wrap`, `.lu-fold`, `.bx`,
`.bx-title`, `.bx-head`, and `.bx-fold` — that last one is what draws the
blue disclosure arrow every other foldable section shows, so the class is
claimed rather than the arrow re-styled here. Everything else is private
to `.scbox`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from nba_pbp.plotting import (_BOX_HEAD_COLOR, _BOX_SCORE_LEFT_MARGIN,
                              _TEAM_BRAND_COLORS, _TITLE_FONT_CQW)
from nba_pbp.possessions import _AREA_CODE, shot_area
from nba_pbp.possessions_section import _initials

# ---- the court, to the rule book, in legacy units (tenths of a foot,
# origin at the CENTRE OF THE RIM) ----
X_MIN, X_MAX = -250.0, 250.0        # 50 ft between the sidelines
BASELINE = -52.5                    # rim centre is 5 ft 3 in off the baseline
HALFCOURT = 417.5                   # 47 ft from the baseline
Y_MIN, Y_MAX = BASELINE, HALFCOURT
W_U, H_U = X_MAX - X_MIN, Y_MAX - Y_MIN
R3 = 237.5                          # arc, 23 ft 9 in from the rim
CORNER_X = 220.0                    # corner three, 22 ft from the rim
ARC_Y = math.sqrt(R3 * R3 - CORNER_X * CORNER_X)   # where the two meet
PAINT_X = 80.0                      # lane 16 ft wide
FT_Y = BASELINE + 190.0             # foul line 19 ft off the baseline
FT_R = 60.0                         # foul circle 6 ft
RIM_R = 7.5                         # hoop 18 in across
RESTRICT_R = 40.0                   # restricted area 4 ft
BACKBOARD_Y = -12.5                 # face 4 ft off the baseline
BACKBOARD_X = 30.0                  # 6 ft wide
CENTRE_R = 60.0                     # centre circle 6 ft
COACH_Y = BASELINE + 280.0          # coaching box, 28 ft off the baseline
COACH_LEN = 30.0                    # a 3 ft mark in from each sideline

ZOOM = 1.75                         # what the "2x" control actually scales
                                    # by. Doubling overshot the page; the
                                    # label stays 2x for now, deliberately
COURT_CQW = 52.0                    # the court's width on the page
S = COURT_CQW / W_U                 # cqw per court unit
COURT_H_CQW = H_U * S

FURN = "#3a4048"                    # court lines: present, never loud
LAB_CQW = _TITLE_FONT_CQW * 0.62    # the hover readout


@dataclass
class ShotSection:
    html: str
    css: str
    stats: dict


def _cx(x: float) -> float:
    """Court x -> cqw from the court's left edge."""
    return (x - X_MIN) * S


def _cy(y: float) -> float:
    """Court y -> cqw from the court's top edge (the rim is near the foot)."""
    return (Y_MAX - y) * S


def _pname(p: int) -> str:
    return f"Q{p}" if p <= 4 else f"OT{p - 4}"


# Distance bands over the TWOS, and a column of its own for every three.
# `16+` therefore means a long two and nothing else — a 16+ that swept up
# the threes would be answering a different question, since almost every
# three is 16+ by distance. The four are mutually exclusive and cover
# every field goal, so a row still adds to the same number across the
# bands as it does across the court segments.
BANDS = ("0-4", "5-15", "16+", "3")


def _band(ft: float, val: int) -> str:
    if val == 3:
        return "3"
    return "0-4" if ft < 5 else ("5-15" if ft < 16 else "16+")


def _aid(name: str) -> str:
    """A column head's id. Segment codes are already safe; a band name is
    not (`0-4`, `16+`), so bands go by their index."""
    return f"z{name}" if name in _AREA_CODE.values() else f"b{BANDS.index(name)}"


def _line(x0: float, y0: float, x1: float, y1: float) -> str:
    return (f'<div class="scf-line" style="left:{_cx(x0):.3f}cqw;'
            f'top:{_cy(y1):.3f}cqw;width:{(x1 - x0) * S:.3f}cqw;'
            f'height:{(y1 - y0) * S:.3f}cqw;"></div>')


def _circ(cx: float, cy: float, r: float, extra: str = "") -> str:
    return (f'<div class="scf-circ" style="left:{_cx(cx - r):.3f}cqw;'
            f'top:{_cy(cy + r):.3f}cqw;width:{2 * r * S:.3f}cqw;'
            f'height:{2 * r * S:.3f}cqw;{extra}"></div>')


def _arc(cx: float, cy: float, r: float, top_y: float, bot_y: float,
         extra: str = "") -> str:
    """A circle shown only between two court-y bounds.

    Every arc on a basketball court is part of a circle that stops
    somewhere — the three-point arc at the corner lines, the restricted
    area at the backboard, the centre circle at half court. Drawing the
    whole circle and clipping it to the band that belongs is exact, and
    needs no path.
    """
    wtop = _cy(top_y)
    return (f'<div class="scf-arcwrap" style="left:0;top:{wtop:.3f}cqw;'
            f'width:{COURT_CQW:.3f}cqw;height:{_cy(bot_y) - wtop:.3f}cqw;">'
            f'<div class="scf-circ" style="left:{_cx(cx - r):.3f}cqw;'
            f'top:{_cy(cy + r) - wtop:.3f}cqw;width:{2 * r * S:.3f}cqw;'
            f'height:{2 * r * S:.3f}cqw;{extra}"></div></div>')


# The six named areas a shot code carries — the RM/RC/RW/SO/LW/LC in
# `M3.LW.25`. The boundaries are not invented here: they are the angles
# possessions.shot_area() cuts the floor at, and the 4ft radius it calls
# "at the rim", so the chart draws exactly what the code names.
ZONE_CUTS = (22.5, 67.5, 112.5, 157.5)      # degrees from the +x axis
ZONE_LABELS = (("RM", 0.0, -32.0), ("RC", 11.25, 235.0), ("RW", 45.0, 300.0),
               ("SO", 90.0, 330.0), ("LW", 135.0, 300.0), ("LC", 168.75, 235.0))


def _zones() -> str:
    """Rays from the rim at the sector cuts, plus each area's code.

    Clipped to the court: a ray long enough to reach the far corner runs
    off three sides of it otherwise.
    """
    ax, ay = _cx(0.0), _cy(0.0)
    rays = ""
    for a in ZONE_CUTS:
        r = 520.0                            # past the furthest corner
        bx, by = _cx(r * math.cos(math.radians(a))), _cy(r * math.sin(math.radians(a)))
        rays += (f'<i class="sczl" style="left:{ax:.3f}cqw;top:{ay:.3f}cqw;'
                 f'width:{math.hypot(bx - ax, by - ay):.3f}cqw;'
                 f'transform:rotate('
                 f'{math.degrees(math.atan2(by - ay, bx - ax)):.2f}deg);"></i>')
    labs = "".join(
        f'<b class="sczt" style="left:{_cx(r * math.cos(math.radians(a))):.3f}cqw;'
        f'top:{_cy(r * math.sin(math.radians(a))):.3f}cqw;">{code}</b>'
        for code, a, r in ZONE_LABELS)
    return (f'<div class="sczone"><div class="sczclip" '
            f'style="width:{COURT_CQW:.3f}cqw;height:{COURT_H_CQW:.3f}cqw;">'
            f'{rays}</div>{labs}</div>')


def _court() -> str:
    """The floor, drawn once, to the dimensions at the top of this file."""
    return (
        # the lane, and the foul line across its head
        _line(-PAINT_X, BASELINE, PAINT_X, FT_Y)
        # foul circle: solid on the court side, dashed inside the lane,
        # which is how it is painted
        + _arc(0.0, FT_Y, FT_R, Y_MAX, FT_Y)
        + _arc(0.0, FT_Y, FT_R, FT_Y, Y_MIN, "border-style:dashed;")
        # restricted area: a semicircle that stops at the backboard
        + _arc(0.0, 0.0, RESTRICT_R, Y_MAX, BACKBOARD_Y)
        + _line(-BACKBOARD_X, BACKBOARD_Y, BACKBOARD_X, BACKBOARD_Y)
        + _circ(0.0, 0.0, RIM_R, "border-color:#6b7280;")
        # three-point line: two corner straights, and the arc between them
        + _line(-CORNER_X, BASELINE, -CORNER_X, ARC_Y)
        + _line(CORNER_X, BASELINE, CORNER_X, ARC_Y)
        + _arc(0.0, 0.0, R3, Y_MAX, ARC_Y)
        # half court: the top edge is the line, the circle straddles it
        + _arc(0.0, HALFCOURT, CENTRE_R, Y_MAX, HALFCOURT - CENTRE_R)
        # the coaching box: a mark on each sideline 28 ft off the baseline,
        # running 3 ft onto the floor — where the bench area begins
        + _line(X_MIN, COACH_Y, X_MIN + COACH_LEN, COACH_Y)
        + _line(X_MAX - COACH_LEN, COACH_Y, X_MAX, COACH_Y))


def build_section(csv_path: str | Path, game_id: str) -> ShotSection:
    df = pd.read_csv(csv_path, dtype=str)
    fg = df[df["isFieldGoal"].astype(str) == "1"].copy()
    fg["period"] = pd.to_numeric(fg["period"], errors="coerce")
    fg["x"] = pd.to_numeric(fg["xLegacy"], errors="coerce")
    fg["y"] = pd.to_numeric(fg["yLegacy"], errors="coerce")
    fg["v"] = pd.to_numeric(fg["shotValue"], errors="coerce")
    fg["an"] = pd.to_numeric(fg["actionNumber"], errors="coerce")
    fg = fg.dropna(subset=["period", "x", "y", "v"])
    fg = fg.sort_values(["period", "an"])
    if fg.empty:
        raise ValueError("no field goals in this game")

    teams = [t for t in df["teamTricode"].dropna().unique()][:2]
    periods = sorted({int(p) for p in fg["period"]})

    # who is home comes from the feed's own location flag ("h" / "v"), which
    # agrees with the canonical csv path the possessions title reads and is
    # still right when the path is not canonical
    def _tri(t: str) -> str:
        return (f'<span style="color:'
                f'{_TEAM_BRAND_COLORS.get(t, "lightgray")};">{t}</span>')
    _loc = df.dropna(subset=["location", "teamTricode"])
    _h = _loc[_loc["location"].astype(str).str.lower() == "h"]["teamTricode"]
    _home = str(_h.iloc[0]) if len(_h) else ""
    if len(teams) == 2 and _home in teams:
        _away = teams[0] if teams[1] == _home else teams[1]
        teams = [_away, _home]                     # away first, as it reads
        matchup = f'{_tri(_away)} @ {_tri(_home)} '
    elif len(teams) == 2:
        matchup = f'{_tri(teams[0])} vs {_tri(teams[1])} '
    else:
        matchup = ""
    tslot = {t: i for i, t in enumerate(teams)}

    # counts[period][team][(value, made)] — and period 0 stands for ALL, so
    # the tally under the court is a lookup rather than a second pass
    counts: dict[int, dict[str, dict[tuple[int, bool], int]]] = {}
    # the same tallies cut one level finer, by (zone, band) PAIR. Every
    # number in the box is a counter summed from one marker per pair,
    # each tagged with its areas — which is what lets the box re-count
    # itself when the floor is filtered.
    cross: dict[int, dict[str, dict[int, dict[tuple[str, int],
                                              list[int]]]]] = {}
    marks, made, missed = [], 0, 0
    for _, r in fg.iterrows():
        pd_ = int(r["period"])
        tri = str(r["teamTricode"])
        col = _TEAM_BRAND_COLORS.get(tri, "#999999")
        hit = str(r["shotResult"]) == "Made"
        made += hit
        missed += not hit
        val = int(r["v"])
        # the zone comes from shot_area(), the same call that writes the LL
        # in a possession's M3.LW.25 — the table cannot disagree with the
        # code beside it, or with the rays drawn on the floor
        zone = _AREA_CODE[shot_area(float(r["x"]), float(r["y"]))]
        _ft = math.hypot(min(max(float(r["x"]), X_MIN), X_MAX),
                         min(max(float(r["y"]), Y_MIN), Y_MAX)) / 10.0
        band = _band(_ft, val)
        for _p in (pd_, 0):
            d = counts.setdefault(_p, {}).setdefault(tri, {})
            # every column keeps its twos and threes apart, because the
            # question is how each fared in that lane / at that range
            for bucket, key in (("z", zone), ("b", band), ("t", "tot")):
                cell = d.setdefault(bucket, {}).setdefault(key, {}) \
                        .setdefault(val, [0, 0])
                cell[0] += 1
                cell[1] += hit
            pair = cross.setdefault(_p, {}).setdefault(tri, {}) \
                        .setdefault(val, {}) \
                        .setdefault((zone, BANDS.index(band)), [0, 0])
            pair[0] += 1
            pair[1] += hit
        # a backcourt heave sits outside the half court; hold it at the edge
        # rather than letting it draw off the plot
        x = min(max(float(r["x"]), X_MIN), X_MAX)
        y = min(max(float(r["y"]), Y_MIN), Y_MAX)
        ax, ay = _cx(x), _cy(y)
        dx, dy = _cx(0.0) - ax, _cy(0.0) - ay
        ln = math.hypot(dx, dy)
        ang = math.degrees(math.atan2(dy, dx))
        who = _initials(str(r["playerNameI"]))
        ft = math.hypot(x, y) / 10.0
        # the possessions table's own vocabulary: initials, then the shot
        # code M/X plus its value, then the distance in feet. No tricode —
        # the dot is already the team's colour — and no "ft", the way the
        # box score writes a distance as a bare number.
        lab = f'{who} {"M" if hit else "X"}{val} {ft:.0f}'
        marks.append(
            f'<div class="scq sp{pd_} t{tslot.get(tri, 0)}'
            f' {"mk" if hit else "ms"} v{val} z{zone} b{BANDS.index(band)}"'
            f' style="left:{ax:.3f}cqw;top:{ay:.3f}cqw;--c:{col};">'
            f'<i class="scl" style="width:{ln:.3f}cqw;'
            f'transform:rotate({ang:.2f}deg);"></i>'
            f'<b class="scf">{lab}</b></div>')

    # ---- free throws, stacked in the court's upper corners ----
    # Not field goals, so they have no place ON the floor — but they are
    # points, and the corners above the arc are empty. One stack per
    # team: away upper-left, home upper-right growing inward, each
    # throw a circle in the order it was taken, wrapping every 7 — the
    # dots' own vocabulary: solid for a make, an open ring for a miss.
    # A MISS is flagged in the description text (shotResult is empty
    # for free throws); made ones carry no flag — possessions.py reads
    # them the same way.
    FTS_D = 1.05                        # circle, the size of a 2pt dot
    FTS_PITCH = 1.6                     # grid step
    FTS_PAD = 1.5                       # inset from the court's corner
    FTS_WRAP = 7                        # stack width, as asked
    ftr = df[df["actionType"].astype(str) == "Free Throw"].copy()
    ftr["period"] = pd.to_numeric(ftr["period"], errors="coerce")
    ftr["an"] = pd.to_numeric(ftr["actionNumber"], errors="coerce")
    ftr = ftr.dropna(subset=["period", "an", "teamTricode"])
    ftr = ftr.sort_values(["period", "an"])
    ftl: dict[tuple[int, str], list[tuple[bool, str]]] = {}
    for _, r in ftr.iterrows():
        tri = str(r["teamTricode"])
        if tri not in tslot:
            continue
        hit = "MISS" not in str(r["description"])
        who = _initials(str(r["playerNameI"]))
        for _p in (int(r["period"]), 0):
            ftl.setdefault((_p, tri), []).append((hit, who))

    def _ftstack(p: int) -> str:
        sides = []
        for t in teams:
            s = tslot[t]
            col = _TEAM_BRAND_COLORS.get(t, "#999999")
            dots = []
            for i, (hit, who) in enumerate(ftl.get((p, t), [])):
                cx = FTS_PAD + (i % FTS_WRAP) * FTS_PITCH
                if s:
                    cx = COURT_CQW - FTS_D - cx
                cy = FTS_PAD + (i // FTS_WRAP) * FTS_PITCH
                dots.append(
                    f'<div class="scfm {"mk" if hit else "ms"}" '
                    f'style="left:{cx:.3f}cqw;top:{cy:.3f}cqw;--c:{col};">'
                    f'<b class="scf">{who} {"M1" if hit else "X1"}</b></div>')
            sides.append(f'<div class="scfts t{s}">' + "".join(dots)
                         + '</div>')
        cls = "ftkall" if p == 0 else f"ftk{p}"
        return f'<div class="scftk {cls}">' + "".join(sides) + '</div>'

    ftstacks = "".join(_ftstack(p) for p in periods) + _ftstack(0)

    # ---- period, one at a time or all ----
    radios = "".join(
        f'<input type="radio" class="scsel scsel-{p}" name="scsel-{game_id}"'
        f' id="sc-{game_id}-{p}"{" checked" if p == periods[0] else ""}>'
        for p in periods)
    radios += (f'<input type="radio" class="scsel scsel-all"'
               f' name="scsel-{game_id}" id="sc-{game_id}-all">')
    tabs = "".join(
        f'<label class="sctab sct-{p}" for="sc-{game_id}-{p}">'
        f'{_pname(p)}</label>' for p in periods)
    tabs += f'<label class="sctab sct-all" for="sc-{game_id}-all">ALL</label>'
    period_css = "".join(
        f'.scbox:has(.scsel-{p}:checked) .sp{p}{{display:block;}}'
        f'.scbox:has(.scsel-{p}:checked) .sct-{p}{{color:#c9ced4;'
        f'border-bottom-color:#4da3ff;}}' for p in periods)
    period_css += "".join(
        f'.scbox:has(.scsel-all:checked) .sp{p}{{display:block;}}'
        for p in periods)
    period_css += ('.scbox:has(.scsel-all:checked) .sct-all{color:#c9ced4;'
                   'border-bottom-color:#4da3ff;}')

    # ---- the filters: each one subtracts, and they combine ----
    # A shot is shown by its period rule at .scbox:has(...) .spN — four
    # class-level pieces. Every hide rule below carries a `div` as well, one
    # type selector heavier, so a filter always beats the period that put
    # the shot on screen rather than depending on source order.
    FILTERS = ([(f"t{i}", t, _TEAM_BRAND_COLORS.get(t, "#999999"))
                for i, t in enumerate(teams)]
               + [("mk", "Made", ""), ("ms", "Miss", "")]
               + [("v2", "2", ""), ("v3", "3", "")])
    boxes = "".join(
        f'<input type="checkbox" class="scfil scfil-{k}"'
        f' id="scf-{game_id}-{k}" checked>' for k, _, _ in FILTERS)
    boxes += (f'<input type="checkbox" class="scfil scfil-ln"'
              f' id="scf-{game_id}-ln" checked>'
              f'<input type="checkbox" class="scfil scfil-2x"'
              f' id="scf-{game_id}-2x">'
              f'<input type="checkbox" class="scfil scfil-zn"'
              f' id="scf-{game_id}-zn" checked>')

    def _tog(k, lbl, col):
        style = f' style="color:{col};"' if col else ""
        return (f'<label class="sctog tog-{k}" for="scf-{game_id}-{k}"'
                f'{style}>{lbl}</label>')
    sep = '<span class="scsep">|</span>'
    controls = (
        "".join(_tog(k, l, c) for k, l, c in FILTERS[:len(teams)]) + sep
        + "".join(_tog(k, l, c) for k, l, c in FILTERS[len(teams):len(teams) + 2])
        + sep
        + "".join(_tog(k, l, c) for k, l, c in FILTERS[len(teams) + 2:]) + sep
        + _tog("ln", "Lines", "") + _tog("zn", "Zones", "")
        + sep + _tog("2x", "2x", "")
        # every filter back on at once. A form reset restores each control
        # in its form to the state it was written with, which is exactly
        # "on" — no script, and nothing to keep in step by hand as filters
        # are added. The period tabs are outside the form on purpose: this
        # recovers the filters, it does not send you back to Q1.
        + sep + '<input type="reset" class="sctog tog-all" value="ALL">')
    filter_css = "".join(
        f'.scbox:has(.scfil-{k}:not(:checked)) div.{k}{{display:none;}}'
        f'.scbox:has(.scfil-{k}:checked) .tog-{k}{{opacity:1;}}'
        for k, _, _ in FILTERS)
    # Lines is a drawing control, not a filter: it leaves every shot in place
    # and takes away only the flight line, which is the whole point of it
    filter_css += ('.scbox:has(.scfil-ln:not(:checked)) i.scl{display:none;}'
                   '.scbox:has(.scfil-ln:checked) .tog-ln{opacity:1;}'
                   '.scbox:has(.scfil-zn:not(:checked)) .sczone{display:none;}'
                   '.scbox:has(.scfil-zn:checked) .tog-zn{opacity:1;}')
    # 2x is a SCALE, not a resize. Every shot is placed in cqw against the
    # section, not against the court, so making the court box bigger would
    # leave the shots exactly where they were — the whole floor has to be
    # transformed together. transform-origin at the top-left is what makes
    # it grow down and to the right rather than out from the middle.
    # A transform does not take part in layout, so the wrapper takes the
    # doubled height too; otherwise the big court would print straight over
    # the HELP / INDEX block that closes the page.
    filter_css += (
        f'.scbox:has(.scfil-2x:checked) .scourt{{transform:scale({ZOOM});}}'
        f'.scbox:has(.scfil-2x:checked) .scwrap'
        f'{{height:{ZOOM * COURT_H_CQW:.3f}cqw;}}'
        '.scbox:has(.scfil-2x:checked) .tog-2x{opacity:1;}')

    # ---- the tally under the court ----
    # One block per period plus one for ALL, each shown by the same radio
    # that shows its shots, so the numbers always describe what is drawn.
    # M/X and the value are the codes the possessions Events column uses.
    # 2M / 2X / 3M / 3X down the side — makes and misses, nothing else,
    # deliberately: attempts and percentages were rows once, and came out
    # BECAUSE they cannot re-count (a percentage is a division). Every
    # number left is a count, so the whole box can follow the filters.
    # The court segments run across the top, and the team's tricode is at
    # BOTH ends of that top line — the right-hand one heads the totals
    # column, so the block is bracketed by the team it belongs to.
    _KEYS = (("2M", 2, "M"), ("2X", 2, "X"),
             ("3M", 3, "M"), ("3X", 3, "X"))

    def _tally(p: int) -> str:
        blocks = []
        for i, t in enumerate(teams):
            c = counts.get(p, {}).get(t, {})
            col = _TEAM_BRAND_COLORS.get(t, "lightgray")
            # a segment earns a column only if a shot came from it, in the
            # order shot_area() names them: rim first, then right to left.
            # The distance bands always show — a band with no shots is
            # itself worth seeing, and they are only four.
            zs = [z for z in _AREA_CODE.values() if c.get("z", {}).get(z)]
            cols = ([(z, c["z"][z]) for z in zs]
                    + [("|", None)]
                    + [(bd, c.get("b", {}).get(bd, {})) for bd in BANDS])
            # ONLY the tricode carries the team's colour. The row labels are
            # headings like the segment codes across the top, and read as
            # them — colouring them made half the block look team-coloured.
            # every column head FILTERS the shots in that area. Both teams'
            # heads point at the SAME control: an area is a place on the
            # floor, not one side's, so RW means RW for the whole chart.
            # The heads are NOT inside the c- column spans the cells get:
            # a filtered area blanks its cells, but its head has to stay
            # on screen, because the head is the control that turns the
            # area back on.
            head = (f'<span style="color:{col};">{t:<5}</span>'
                    + "".join(
                        f'{name:>5}' if name == "|" else
                        # the column's padding sits OUTSIDE the label, so the
                        # rule under a head hugs its own code instead of
                        # trailing back across the whitespace before it
                        f'{"":>{5 - len(name)}}'
                        f'<label class="schd h{_aid(name)}" '
                        f'for="sca-{game_id}-{_aid(name)}">{name}</label>'
                        for name, _ in cols)
                    + f'<span style="color:{col};">{t:>7}</span>')
            live = cross.get(p, {}).get(t, {})

            def _lcell(colkey: str, v: int, kind: str, w: int = 5) -> str:
                """A count that counts ITSELF: one marker element per
                (zone, band) pair, incrementing the cell's counter by
                that pair's share. Filtering an area display:nones its
                markers, and a marker that is not rendered does not
                increment — so the number falls by exactly the hidden
                share. The markers are ELEMENTS, not a variable fed to
                counter-reset, because WebKit paints that variant stale
                when the variable flips; removing boxes repaints."""
                cis = []
                for (z, bi), (att, mk) in sorted(live.get(v, {}).items()):
                    n = mk if kind == "M" else att - mk
                    if not n:
                        continue
                    if colkey == "tot":
                        cls = f"az{z} ab{bi}"
                    elif colkey == f"z{z}":
                        cls = f"ab{bi}"
                    elif colkey == f"b{bi}":
                        cls = f"az{z}"
                    else:
                        continue
                    cis.append(f'<i class="{cls}" '
                               f'style="counter-increment:c {n}"></i>')
                return (f'<span class="c-{colkey} cc'
                        f'{" cw7" if w == 7 else ""}">'
                        + "".join(cis) + '</span>')

            rows = []
            # the row is one element INCLUDING its newline, so hiding it
            # takes the line away rather than leaving a blank one
            for lab, val, kind in _KEYS:
                cells = "".join(
                    f'{"|":>5}' if cc is None
                    else _lcell(_aid(name), val, kind)
                    for name, cc in cols)
                cells += _lcell("tot", val, kind, 7)
                rows.append(
                    f'<span class="scr r{val} '
                    f'{"rmk" if kind == "M" else "rms"}">'
                    f' {lab:<4}' + cells + "\n</span>")
            # NOT tagged with the team's t0/t1 class, deliberately. Letting
            # the team switches hide a block meant turning one team off
            # deleted the lower half and slid the other one up, so the top
            # half changed which team it was under the reader. The tally is
            # the period's record and stays whole; the switches are for the
            # floor.
            blocks.append(f'<div class="sctb">' + head + "\n"
                          + "".join(rows) + '</div>')
        cls = "totall" if p == 0 else f"tot{p}"
        return f'<div class="sctot {cls}">' + "".join(blocks) + '</div>'

    # one checkbox per area — the six segments and the four bands
    _AREAS = [f"z{z}" for z in _AREA_CODE.values()] + [
        f"b{i}" for i in range(len(BANDS))]
    areaboxes = "".join(
        f'<input type="checkbox" class="scfa scfa-{a}"'
        f' id="sca-{game_id}-{a}" checked>' for a in _AREAS)
    # The box reflects the CURRENT VIEW of the floor, in full. Every
    # number in it is a count, and every count re-counts itself, so
    # nothing in the box ever goes stale: filter SO out and every cell
    # that held an SO shot — bands, totals — falls by exactly SO's
    # share, then comes back.
    #
    # An area filtered out also takes its own column (cells blanked in
    # place so nothing shifts, head standing dimmed, because the head
    # is the control that turns the area back on). A value filtered out
    # takes its own two rows, and Made / Miss take THEIR own two rows —
    # every strip filter owns a slice of the box except the teams:
    # the blocks are one team's each on purpose, and the team switches
    # shape the floor, not the record.
    area_css = (
        '.scbox:has(.scfil-v2:not(:checked)) .sctb .r2{display:none;}'
        '.scbox:has(.scfil-v3:not(:checked)) .sctb .r3{display:none;}'
        '.scbox:has(.scfil-mk:not(:checked)) .sctb .rmk{display:none;}'
        '.scbox:has(.scfil-ms:not(:checked)) .sctb .rms{display:none;}')
    area_css += "".join(
        f'.scbox:has(.scfa-{a}:not(:checked)) div.{a}{{display:none;}}'
        f'.scbox:has(.scfa-{a}:not(:checked)) .scr .c-{a}{{visibility:hidden;}}'
        f'.scbox:has(.scfa-{a}:not(:checked)) .sctb i.a{a}{{display:none;}}'
        f'.scbox:has(.scfa-{a}:not(:checked)) .h{a}{{opacity:.3;}}'
        for a in _AREAS)
    tally = "".join(_tally(p) for p in periods) + _tally(0)
    tally_css = "".join(
        f'.scbox:has(.scsel-{p}:checked) .tot{p}{{display:block;}}'
        for p in periods)
    tally_css += '.scbox:has(.scsel-all:checked) .totall{display:block;}'
    # the free-throw stacks ride the same period radios as the tally
    tally_css += "".join(
        f'.scbox:has(.scsel-{p}:checked) .ftk{p}{{display:block;}}'
        for p in periods)
    tally_css += '.scbox:has(.scsel-all:checked) .ftkall{display:block;}'

    css = f"""
.scbox{{position:relative;}}
.scsel,.scfil,.scfa{{position:absolute;opacity:0;pointer-events:none;}}
/* a count that counts itself: markers inside the cell increment its
   counter, a filtered area's markers stop rendering and stop counting.
   ::after, not ::before — the counter is read AFTER the markers in
   tree order; before them it is still zero */
.cc{{display:inline-block;width:5ch;text-align:right;counter-reset:c;}}
.cw7{{width:7ch;}}
.cc::after{{content:counter(c);}}
/* A column head is a filter, and says so: a dotted rule under the code
   marks it as something you can press, the way nothing else in this
   table is. It firms up and brightens under the pointer, and the head
   dims while its area is filtered out. */
.schd{{cursor:pointer;border-bottom:1px dotted #545c66;}}
.schd:hover{{color:#c9ced4;border-bottom-style:solid;
  border-bottom-color:#4da3ff;}}
/* the period strip, one line, on the section's own left margin */
.scside{{position:relative;display:flex;gap:1.1cqw;
  margin-left:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;
  margin-top:{_TITLE_FONT_CQW * 1.5:.2f}cqw;padding:0 0 0.5cqw 0;
  font-family:'DejaVu Sans',sans-serif;font-size:{_TITLE_FONT_CQW:.2f}cqw;}}
.sctab{{color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;
  padding:0 0.2cqw 0.15cqw;}}
.sctab:hover{{color:#9BA3AD;}}
/* the filter strip below it: dim means subtracted */
.scfils{{position:relative;display:flex;gap:0.9cqw;align-items:baseline;
  margin-left:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;padding:0 0 0.7cqw 0;
  font-family:'DejaVu Sans',sans-serif;font-size:{_TITLE_FONT_CQW:.2f}cqw;}}
.sctog{{cursor:pointer;color:#9BA3AD;opacity:.35;}}
/* the reset is an <input>; strip the widget so it reads as a
   label like the rest of the strip, and keep it lit — it is
   always available, never 'off' */
.tog-all{{appearance:none;-webkit-appearance:none;background:none;
  border:0;padding:0;font:inherit;opacity:1;color:#9BA3AD;}}
.sctog:hover{{text-decoration:underline;}}
.scsep{{color:#3a4048;}}
/* the court. both sizes are explicit, so the floor keeps its proportions
   whatever the window does */
/* the wrapper holds the floor's place in the flow — the court itself is
   taken out of it so 2x can scale without the layout arguing */
.scwrap{{position:relative;margin-left:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;
  height:{COURT_H_CQW:.3f}cqw;}}
.scourt{{position:absolute;left:0;top:0;transform-origin:0 0;
  width:{COURT_CQW:.3f}cqw;height:{COURT_H_CQW:.3f}cqw;
  border:1px solid {FURN};box-sizing:border-box;}}
.scf-line{{position:absolute;box-sizing:border-box;
  border:1px solid {FURN};pointer-events:none;}}
.scf-circ{{position:absolute;box-sizing:border-box;border:1px solid {FURN};
  border-radius:50%;pointer-events:none;}}
.scf-arcwrap{{position:absolute;overflow:hidden;pointer-events:none;}}
/* the six named areas: the cuts shot_area() makes, drawn. Under the
   shots and dimmer than the court lines — they name the floor, they are
   not part of it. The rays are clipped to the court; one long enough to
   reach the far corner leaves it on three sides otherwise. */
.sczone{{position:absolute;left:0;top:0;pointer-events:none;}}
.sczclip{{position:absolute;left:0;top:0;overflow:hidden;}}
.sczl{{position:absolute;height:0.11cqw;transform-origin:0 50%;
  background:#2a2f36;}}
.sczt{{position:absolute;transform:translate(-50%,-50%);
  color:#4a515a;font-family:'DejaVu Sans Mono',monospace;
  font-size:{LAB_CQW * 0.95:.2f}cqw;font-weight:normal;}}
/* the tally under the court: one block per period, only the selected
   one on screen, so the numbers always count the shots being drawn */
.sctot{{display:none;white-space:pre;
  margin:{_TITLE_FONT_CQW * 1.5:.2f}cqw 0 0
         {_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;
  color:{_BOX_HEAD_COLOR};font-family:'DejaVu Sans Mono',monospace;
  font-size:{_TITLE_FONT_CQW:.2f}cqw;}}
/* the blank line between the two teams' blocks — a margin rather than a
   newline, so a hidden block takes its gap with it */
.sctb + .sctb{{margin-top:1em;}}
/* one shot: a dot at the launch point, and the line it flew */
.scq{{position:absolute;display:none;transform:translate(-50%,-50%);
  width:1.05cqw;height:1.05cqw;border-radius:50%;z-index:3;}}
.scq.v3{{width:1.35cqw;height:1.35cqw;}}
.scq.mk{{background:var(--c);}}
.scq.ms{{background:transparent;box-shadow:inset 0 0 0 0.16cqw var(--c);}}
.scl{{position:absolute;left:50%;top:50%;height:0.15cqw;
  transform-origin:0 50%;background:var(--c);pointer-events:none;}}
.mk .scl{{opacity:.55;}}
.ms .scl{{opacity:.20;}}
.scq:hover{{z-index:9;}}
.scq:hover .scl{{opacity:1;height:0.26cqw;}}
/* the free-throw stacks: containers take no mouse so the corner stays
   hoverable for shots; each circle takes its own */
.scftk{{position:absolute;inset:0;display:none;pointer-events:none;
  z-index:2;}}
.scfts{{position:absolute;inset:0;pointer-events:none;}}
.scfm{{position:absolute;width:{FTS_D}cqw;height:{FTS_D}cqw;
  border-radius:50%;pointer-events:auto;}}
.scfm.mk{{background:var(--c);}}
.scfm.ms{{background:transparent;box-shadow:inset 0 0 0 0.16cqw var(--c);}}
.scfm:hover{{z-index:9;}}
.scfm:hover .scf{{display:block;}}
/* the readout rides with its own shot and paints over everything */
.scf{{display:none;position:absolute;left:1.2cqw;top:-0.4cqw;z-index:10;
  white-space:pre;background:#000;color:{_BOX_HEAD_COLOR};
  border:1px solid #2a2f36;border-radius:3px;padding:0.15cqw 0.45cqw;
  font-family:'DejaVu Sans Mono',monospace;font-size:{LAB_CQW:.2f}cqw;
  box-shadow:0 2px 10px rgba(0,0,0,.9);}}
.scq:hover .scf{{display:block;}}
{period_css}
{filter_css}
{tally_css}
{area_css}
"""

    html = f"""<div class="chart-wrap">
<div class="scbox">
{radios}
<form class="scform">{boxes}{areaboxes}
<details class="lu-fold bx-fold sc-fold"><summary>
<div class="bx bx-title"><span class="bx-head">{matchup}Shot Chart</span></div>
</summary>
<div class="scside">{tabs}</div>
<div class="scfils">{controls}</div>
<div class="scwrap"><div class="scourt">{_court()}{_zones()}{''.join(marks)}{ftstacks}</div></div>
{tally}
</details>
</form>
</div>
</div>"""

    return ShotSection(html, css, {
        "shots": len(marks), "made": int(made), "missed": int(missed),
        "teams": teams, "periods": periods,
    })
