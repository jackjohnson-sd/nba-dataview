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

    marks, made, missed = [], 0, 0
    for _, r in fg.iterrows():
        pd_ = int(r["period"])
        tri = str(r["teamTricode"])
        col = _TEAM_BRAND_COLORS.get(tri, "#999999")
        hit = str(r["shotResult"]) == "Made"
        made += hit
        missed += not hit
        val = int(r["v"])
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
            f' {"mk" if hit else "ms"} v{val}"'
            f' style="left:{ax:.3f}cqw;top:{ay:.3f}cqw;--c:{col};">'
            f'<i class="scl" style="width:{ln:.3f}cqw;'
            f'transform:rotate({ang:.2f}deg);"></i>'
            f'<b class="scf">{lab}</b></div>')

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
              f' id="scf-{game_id}-ln" checked>')

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
        + _tog("ln", "Lines", ""))
    filter_css = "".join(
        f'.scbox:has(.scfil-{k}:not(:checked)) div.{k}{{display:none;}}'
        f'.scbox:has(.scfil-{k}:checked) .tog-{k}{{opacity:1;}}'
        for k, _, _ in FILTERS)
    # Lines is a drawing switch, not a filter: it leaves every shot in place
    # and takes away only the flight line, which is the whole point of it
    filter_css += ('.scbox:has(.scfil-ln:not(:checked)) i.scl{display:none;}'
                   '.scbox:has(.scfil-ln:checked) .tog-ln{opacity:1;}')

    css = f"""
.scbox{{position:relative;}}
.scsel,.scfil{{position:absolute;opacity:0;pointer-events:none;}}
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
.sctog:hover{{text-decoration:underline;}}
.scsep{{color:#3a4048;}}
/* the court. both sizes are explicit, so the floor keeps its proportions
   whatever the window does */
.scourt{{position:relative;margin-left:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;
  width:{COURT_CQW:.3f}cqw;height:{COURT_H_CQW:.3f}cqw;
  border:1px solid {FURN};box-sizing:border-box;}}
.scf-line{{position:absolute;box-sizing:border-box;
  border:1px solid {FURN};pointer-events:none;}}
.scf-circ{{position:absolute;box-sizing:border-box;border:1px solid {FURN};
  border-radius:50%;pointer-events:none;}}
.scf-arcwrap{{position:absolute;overflow:hidden;pointer-events:none;}}
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
/* the readout rides with its own shot and paints over everything */
.scf{{display:none;position:absolute;left:1.2cqw;top:-0.4cqw;z-index:10;
  white-space:pre;background:#000;color:{_BOX_HEAD_COLOR};
  border:1px solid #2a2f36;border-radius:3px;padding:0.15cqw 0.45cqw;
  font-family:'DejaVu Sans Mono',monospace;font-size:{LAB_CQW:.2f}cqw;
  box-shadow:0 2px 10px rgba(0,0,0,.9);}}
.scq:hover .scf{{display:block;}}
{period_css}
{filter_css}
"""

    html = f"""<div class="chart-wrap">
<div class="scbox">
{radios}{boxes}
<details class="lu-fold bx-fold sc-fold"><summary>
<div class="bx bx-title"><span class="bx-head">{matchup}Shot chart</span></div>
</summary>
<div class="scside">{tabs}</div>
<div class="scfils">{controls}</div>
<div class="scourt">{_court()}{''.join(marks)}</div>
</details>
</div>
</div>"""

    return ShotSection(html, css, {
        "shots": len(marks), "made": int(made), "missed": int(missed),
        "teams": teams, "periods": periods,
    })
