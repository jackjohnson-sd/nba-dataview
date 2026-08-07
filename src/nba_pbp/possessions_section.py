#!/usr/bin/env python3
"""The possessions section — one plot + one box score, built once and
rendered identically on the standalone test page and at the foot of every
game page.

Two columns of possessions, one per team in that team's colour, laid on the
game clock running DOWN the page: each block starts where the possession
started and is as tall as it lasted, and the two halves butt against a
shared centre line so at every moment of the game the teams' possessions
meet in the middle. One PERIOD is shown at a time (the tabs on the left
margin pick it) so a period gets the whole canvas instead of a sixth of it,
which is what lets the event codes letter at rest.

TOO SMALL TO LABEL: a 4-second possession is a couple of pixels tall, far
too short for even one glyph. Rather than drop those possessions or let
their text spill over their neighbours, the rule is:

  * every block keeps a visible minimum height, but never one that would
    back into the possession above it in the same column (a real clamp, not
    a hope — the builder checks and reports the count)
  * the event code is drawn ONLY when the block is genuinely taller than
    the glyph, and
  * hovering any block — however thin — opens it to full label height AND
    lights its row in the box score below, so nothing is unreachable just
    because it is small.

EMBEDDING. The game page and this section share a stylesheet, so every
class and custom property here is private to the block (`ps-`/`ps`/`pp`
prefixes) EXCEPT the wrappers deliberately borrowed from the host —
`.kbox`, `.kb-fold`, `summary.ktitle`, `.bx-flow`/`.lu-fold.bx-fold`, and
`.lu-toggle` for the title-line Big/Normal switch. Those are borrowed
rather than copied so the fold arrows, the title font, the switch look
and the exact-40px closed-title pitch come from the page's own machinery
and stay in step with it. `css` therefore carries NO @font-face, no
html/body, no `.chart-wrap` and no host class definition — the standalone
page supplies that shell itself.
"""
from __future__ import annotations

import html
import math
from pathlib import Path
from typing import NamedTuple

from nba_pbp.plotting import (_BOX_FONT_CQW, _BOX_HEAD_COLOR, _BOX_HTML_TEXT,
                              _BOX_SCORE_LEFT_MARGIN, _MONO_ADVANCE_EM,
                              _PAGE_DPI, _PAGE_W_PX, _TEAM_BRAND_COLORS,
                              _TITLE_FONT_CQW)
from nba_pbp.possessions import compute_possessions


def _pt(points: float) -> float:
    """A matplotlib point size as cqw, the way the karma panels size their
    text — so this plot's furniture matches theirs instead of guessing."""
    return points * (_PAGE_DPI / 72) / (_PAGE_W_PX / 100)


BAR_THICK = 0.45                    # a block's height as a share of its
                                    # possession's span — the block sits
                                    # centred in the band, so durations stay
                                    # proportional but read far lighter
LABEL_FIT = 0.3                     # room a code needs to be lettered at
                                    # rest, in label heights. Swept against
                                    # measured label collisions: 1.05 letters
                                    # 317 blocks with none touching, 1.00
                                    # letters 338 but 5 pairs collide, 0.85
                                    # letters 397 with 20. The rest open on
                                    # hover, so this is the floor that keeps
                                    # the resting plot clean.
# The plot's type matches the karma / player panels role for role, so the
# two read as one page: an axis tick is sized like an axis tick, an in-plot
# glyph like a glyph. Each constant names the artist it mirrors, and _pt()
# is the same points->cqw conversion the karma panels are sized through.
YTICK_CQW = _BOX_FONT_CQW           # the game-clock scale. NOT the karma
                                    # panel's y-tick size (_pt(7)) any more:
                                    # the scale and the possession START
                                    # stamps beside it are both clock
                                    # readings, so they read as one class of
                                    # text. TICK_W below sizes the gutter
                                    # from this, so the two move together.
HEAD_CQW = _TITLE_FONT_CQW          # panel title  -> the period tabs AND
                                    # the team column heads (the heads sat
                                    # at the karma x-tick size for one
                                    # release; too small to carry the two
                                    # columns, so they read at Q1's size)
GLYPH_CQW = _pt(math.sqrt(32) / 0.72)   # the karma event glyphs (.kev) ->
                                    # the event codes. sqrt(32)/0.72 is the
                                    # marker footprint the karma panel's own
                                    # declutter pass spaces its glyphs by
LAB_CQW = _BOX_FONT_CQW             # the box score's own mono, for the two
                                    # things on the plot that are TABULAR
                                    # rather than furniture: the time stamps
                                    # and the possession counts
# Colour splits the same way the type does. The karma panels draw their
# in-plot labels in matplotlib "gray" (#808080, luminance 0.216); this
# section had been using the BOX SCORE's grey (#9BA3AD, 0.362) for its
# plot furniture too — 1.68x brighter than the panel directly above it.
# Furniture takes the karma grey; anything TABULAR (time stamps, counts,
# box rows) keeps the box-score grey, because it belongs to the tables.
# Contrast checked before adopting: 5.32:1 on the black page and 4.60:1
# on a tinted event block, both clearing WCAG AA.
FURN_COLOR = "#808080"

PLOT_T, PLOT_B = 1.0, 92.5          # top/bottom of the time axis, % of height.
                                    # The floor stops well short of the canvas
                                    # to leave room UNDER it for the period's
                                    # footer: the last row's stamp hangs ~0.7%
                                    # below the axis, then a blank line, the
                                    # totals, two more blank lines and the
                                    # rule of stars — 7.3% of height in all,
                                    # at ~1.23% a line.
COL_W = 24.0                        # each half's reach: the longest
                                    # possession in a game is 6 events
TICK_W = 5 * YTICK_CQW * _MONO_ADVANCE_EM   # "12:00" at the clock's own
                                    # size — this gutter IS the label, so it
                                    # has to move whenever the label does
# the time grid keeps the page's left margin (scale labels start where
# the Possessions title and the Q1 row start); the CONTENT — stamps,
# events, counts — sits a step to the right of it
GRID_L = _BOX_SCORE_LEFT_MARGIN * 100 + TICK_W + 1.0
# The stamps are FIXED columns and the event stacks are not, so the
# whitespace between them varies row to row. Measured over the showcase
# game: median 11.53% of the canvas on the left, 9.87% on the right — and
# a right-side minimum of -2.9%, i.e. the longest stacks were running INTO
# the stamp. Widening each column outward by a fifth of its own median is
# a +20% gap for the typical row and turns that collision into clearance.
PUSH_L = 0.20 * 11.53               # 2.31% — left column moves left
# The left time column is PINNED here rather than derived from the centre:
# it has only 2.18% of canvas before it runs into the clock scale, so when
# the space between a stamp and the centre line grows, it is the CENTRE
# that moves right — this column cannot go anywhere.
TIME_L = GRID_L + 3.5 - PUSH_L
# Clear canvas between a stamp and the centre line. Measured on the
# showcase game: the stamp is 8.44% wide ("12:00 29s" at LAB_CQW), leaving
# 18.37% clear on the left and 17.53% on the right. Both widened 30%.
STAMP_W = 8.44
CLEAR_L, CLEAR_R = 1.30 * 18.37, 1.30 * 17.53
SHIFT = TIME_L + STAMP_W + CLEAR_L - GRID_L - COL_W   # the content's step
CENTRE = GRID_L + SHIFT + COL_W                       # right off the grid
# the right column moves out to leave CLEAR_R; the possession counts ride
# just past it, so they clear the stamp wherever it lands
PUSH_R = CLEAR_R + STAMP_W - COL_W
TIME_R = CENTRE + COL_W + PUSH_R
# three right-hand columns, each three mono characters wide (a game runs
# past 200 possessions and past 100 points) with a character of air
# between: the possession number, then the game score, one column per
# team in that team's colour and in the same left-to-right order as the
# plot's own halves
COL_CH = LAB_CQW * _MONO_ADVANCE_EM         # one character at the box font
COL_W3 = 3 * COL_CH                         # a three-digit column
_R0 = TIME_R + 1.0                          # where the right-hand block starts
NUM_L = _R0 + 3 * COL_CH                    # the possession number
# the score reads as one string, "124-125": the first team's total right
# up against the dash and the second team's left off it, so the two stay
# joined however many digits each carries
SCORE_L = _R0 + 9 * COL_CH                  # first team's score, right-aligned
DASH_L = SCORE_L + COL_W3                   # the '-' between them
SCORE2_L = DASH_L + COL_CH                  # second team's, LEFT-aligned
PLOT_ASPECT = 1.82                  # height/width of the canvas — one
                                    # PERIOD fills it, so this is ~3.5x the
                                    # room a period had on the game-long axis
SEG_W = 3.8                         # block width for 3-4 char codes
SEG_W2 = 2.6                        # ...and for 2-char codes
EV_GAP = LAB_CQW * _MONO_ADVANCE_EM     # one character of daylight between
                                    # the two teams' event columns, split
                                    # either side of the centre line so the
                                    # axis itself stays where it was
VY = 2                              # decimals on every VERTICAL per cent.
                                    # 0.01% is 0.216px on the 2158px canvas
                                    # — above the layout quantum — while the
                                    # source clock is only good to 0.1s, i.e.
                                    # 0.288px on a 12-minute period, so a
                                    # third decimal would encode precision
                                    # the play-by-play does not have
PSCROLL_CQW = 70.0                  # the plot's own scroll window
BXSCROLL_CQW = 38.0                 # the table's
SCROLLBAR_PX = 14                   # our own scrollbar width. `.pscroll`
                                    # reserves it with scrollbar-gutter, so
                                    # the CANVAS is this much narrower than
                                    # the container — and anything outside
                                    # the canvas that must line up with it
                                    # has to lose the same width, or the
                                    # same percentage lands ~6px apart


class PossSection(NamedTuple):
    """`html` is exactly one `<div class="chart-wrap">…</div>`; `css` is
    block-private rules only (safe to concatenate into a game page's
    stylesheet); `info` is the builder's diagnostics."""
    html: str
    css: str
    info: dict


def _fmt_clock(rem: str) -> str:
    return rem.split(".")[0] if "." in rem else rem


def _pad_clock(rem: str) -> str:
    """"9:52" -> "09:52". A leading zero on single-digit minutes so every
    clock in the column is five characters and the colons line up."""
    t = _fmt_clock(rem)
    m, _, sec = t.partition(":")
    return f"{int(m):02d}:{sec}" if sec else t


def _initials(name: str) -> str:
    """"C. Holmgren" -> "CH". Two characters, so the column stays narrow
    enough to sit beside the codes; the full name rides along in a span
    the CSS reveals on hover.

    A TRICODE passes through whole: a timeout or a team rebound is the
    club's doing, and "HOU" abbreviated to "HO" would read as a player's
    initials rather than a team."""
    if not name or name == "-":
        return "--"
    if len(name) == 3 and name.isupper() and name.isalpha():
        return name
    parts = [x for x in name.replace(".", " ").split() if x]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (parts[0][:2] if parts else "--").upper()


def _suffix(shot: str) -> str:
    """"RM  1" -> ".RM.01". Zero-padded here where the Loc column
    right-aligned, because between two dots it reads as a code."""
    if not shot or shot == "-":
        return ""
    try:
        return f".{shot[:2]}.{int(shot[2:]):02d}"
    except ValueError:
        return ""


def _ev_forms(codes: str, shots: str):
    """(long, short, html) for one team's event list. LONG carries each
    shot's location on the code — M3.RW.27 — and SHORT is the bare codes;
    the html holds both, the suffixes in spans the view switch hides."""
    cs = [] if codes == "-" else codes.split()
    zs = str(shots).split("|") if shots else []
    long_p, html_p = [], []
    for i, c in enumerate(cs):
        sfx = _suffix(zs[i] if i < len(zs) else "")
        long_p.append(c + sfx)
        html_p.append(c + (f'<span class="sfx">{sfx}</span>' if sfx else ""))
    return " ".join(long_p), " ".join(cs), " ".join(html_p)


def _q(v: float) -> float:
    """Snap a vertical percentage to the grid the page is written on.

    Every vertical number here is emitted at VY decimals, so the browser
    only ever sees multiples of 10**-VY per cent. Quantising HERE, before
    the values leave the layout pass, is what keeps the no-overlap clamp
    true of the RENDERED page and not merely of the floats: a block's
    bottom is emitted as _q(top + h) — the identical number the block
    below emits as its top — so two flush blocks stay flush. Rounding top
    and height independently instead lets each drift by its own rounding
    unit, which silently un-flushes pairs the clamp made exact.
    """
    return float(f"{v:.{VY}f}")


def build_section(csv_path: Path | str, game_id: str, *,
                  open_default: bool = False) -> PossSection:
    poss = compute_possessions(str(csv_path))
    teams = list(dict.fromkeys(poss["team"]))
    date = poss["date"].iloc[0] if "date" in poss else ""

    # the matchup for the two title lines, "AWY @ HOM" in team colours.
    # The play-by-play never says who is home; the canonical csv path does
    # — outputs/<season>/<home>/csv/... (the CLI and the season fetcher
    # both file a game under its home tricode). An unconventional path
    # falls back to first-possession order under a neutral separator.
    def _tri(t: str) -> str:
        return (f'<span style="color:'
                f'{_TEAM_BRAND_COLORS.get(t, "lightgray")};">{t}</span>')
    _home = Path(csv_path).parent.parent.name.upper()
    if len(teams) == 2 and _home in teams:
        _away = teams[0] if teams[1] == _home else teams[1]
        matchup = f'{_tri(_away)} @ {_tri(_home)} '
    elif len(teams) == 2:
        matchup = f'{_tri(teams[0])} vs {_tri(teams[1])} '
    else:
        matchup = ""

    # each PERIOD is laid out on its own canvas and only the selected one
    # is shown, so a period gets the WHOLE plot height instead of a sixth
    # of it — which is what lets the events letter at rest
    periods = sorted(int(x) for x in poss["period"].unique())
    pspan = {}
    for pd_ in periods:
        rows_ = poss[poss.period == pd_]
        pspan[pd_] = (float(rows_["start_elapsed"].min()),
                      float(rows_["end_elapsed"].max()))
    pname = {pd_: (f"Q{pd_}" if pd_ <= 4 else f"OT{pd_ - 4}") for pd_ in periods}

    box_h_px = 1200 * PLOT_ASPECT
    MIN_H = 0.22 / PLOT_ASPECT
    label_h_pct = (GLYPH_CQW / 100 * 1200 * LABEL_FIT) / box_h_px * 100
    rects, clamped, labelled = [], 0, 0
    side_of = {t: (-1 if i == 0 else 1) for i, t in enumerate(teams)}

    def y_of(sec: float, pd_: int) -> float:
        """Position WITHIN the possession's own period, 0-100% of the plot."""
        a, b = pspan[pd_]
        return PLOT_T + (PLOT_B - PLOT_T) * ((sec - a) / max(b - a, 1e-9))

    # the no-overlap pass runs per period (each is its own canvas), still
    # once over every window since each is drawn in BOTH halves
    span_by_row = {}
    pbot = {}                       # each period's real drawn bottom — the
                                    # clamp can push the last rows past
                                    # PLOT_B, and the totals line hangs
                                    # off whatever actually rendered
    # a row's lowest ink is not its block: the time stamp and the counts
    # open to --ps-eh centred on the row, so a SHORT possession's stamp
    # hangs below its block. Measuring the bottom off the blocks alone put
    # the totals anywhere from 26 to 66px under the last row depending on
    # how short that row happened to be.
    EH_PCT = max(GLYPH_CQW * 1.45, LAB_CQW * 1.25) / PLOT_ASPECT
    for pd_ in periods:
        prev_bottom = -1e9
        ordered = poss[poss.period == pd_].sort_values("start_elapsed")
        ys = [(y_of(r.start_elapsed, pd_), y_of(r.end_elapsed, pd_), idx)
              for idx, r in ordered.iterrows()]
        for y0, y1, idx in ys:
            hb = max((y1 - y0) * BAR_THICK, MIN_H)
            top = y0 - hb / 2                    # centred on the START time
            if top < prev_bottom:                # never back into the row
                top = prev_bottom                # above
                clamped += 1
            prev_bottom = top + hb          # the clamp keeps comparing
                                            # exact floats; only what is
                                            # EMITTED gets snapped
            # round the block's two EDGES and let the height fall out of
            # them, so the bottom this block draws is the same number the
            # block below draws as its top
            _t = _q(top)
            _h = _q(prev_bottom) - _t
            span_by_row[idx] = (_t, _h)
            # the row's real ink bottom, stamp included. No PLOT_B floor:
            # rows are anchored on their START, so a period whose last
            # possession is long ends its ink well above the axis floor —
            # flooring at PLOT_B made the "blank line" 66px there and 37px
            # elsewhere. The line follows the possessions, not the axis.
            _ink = _t + _h + max(0.0, EH_PCT - _h) / 2
            pbot[pd_] = max(pbot.get(pd_, 0.0), _ink)

    seen: dict[str, int] = {t: 0 for t in teams}
    # the running score, accumulated the same way the counts are. These are
    # POSSESSION points, so a game with technical free throws can finish a
    # shade under the official linescore — the possession model's ledger,
    # the same one the per-period totals report.
    score: dict[str, int] = {t: 0 for t in teams}
    for i, (idx, r) in enumerate(
            poss.sort_values("start_elapsed").iterrows()):
        seen[r.team] += 1
        score[r.team] += int(r.points)
        y0, h = span_by_row[idx]                # already the drawn row box
        show_label = r.points > 0
        inside = h >= label_h_pct
        labelled += int(show_label)
        base = {"i": i, "top": y0, "h": h, "y0s": float(r.start_elapsed),
                # ONE number per game, not one per team: the same running
                # count the box score's "#" column shows
                "period": int(r.period), "num": i + 1,
                "score": tuple(score[t] for t in teams),
                "scored": r.scored == "Y", "pts": int(r.points),
                "row": int(idx)}
        rects.append({**base, "team": r.team, "dir": side_of[r.team],
                      "label": str(int(r.points)) if show_label else "",
                      "inside": inside, "events": r.off_events,
                      "times": r.off_times, "side": "o",
                      "start": _fmt_clock(r.start_clock),
                      "dur": f"{r.duration_s:.0f}s",
                      "success": r.off_success == "Y"})
        # the mirror: the same window as the OTHER team's defensive
        # possession, concluded by the same event the other way round
        rects.append({**base, "team": r.def_team, "dir": side_of[r.def_team],
                      "label": "", "inside": inside, "events": r.def_events,
                      "times": r.def_times, "side": "d",
                      "start": _fmt_clock(r.start_clock),
                      "dur": f"{r.duration_s:.0f}s",
                      "success": r.def_success == "Y"})

    # ---- the plot ----
    parts = []
    for pd_ in periods:                       # a clock rule every 2 minutes
        a, b = pspan[pd_]
        span, t = b - a, 0.0
        while t <= span + 1e-6:
            y = PLOT_T + (PLOT_B - PLOT_T) * (t / max(span, 1e-9))
            left = int(round(span - t))
            parts.append(f'<div class="ps-fnl psp{pd_}" style="top:{y:.{VY}f}%;'
                         f'left:{GRID_L:.2f}%;'
                         f'width:{TIME_R - GRID_L:.2f}%;"></div>')
            parts.append(f'<div class="ps-fnt ps-ytick psp{pd_}" '
                         f'style="top:{y:.{VY}f}%;left:{GRID_L - 1.0:.2f}%;">'
                         f'{left // 60}:{left % 60:02d}</div>')
            t += 120.0
    # ids are namespaced by game so the block can sit on a page that
    # already owns every short id it can think of
    radios = "".join(
        f'<input type="radio" class="pdsel pdsel-{pd_}" name="pdsel-{game_id}"'
        f' id="pd-{game_id}-{pd_}"'
        f'{" checked" if pd_ == periods[0] else ""}>' for pd_ in periods)
    pdlabels = "".join(
        f'<label class="pdl pdl-{pd_}" for="pd-{game_id}-{pd_}">'
        f'{pname[pd_]}</label>' for pd_ in periods)
    # only the selected period is displayed — everything else is hidden,
    # so a period fills the whole canvas
    period_css = "".join(
        f'.psbox:has(.pdsel-{pd_}:checked) .psp{pd_}{{display:block;}}'
        f'.psbox:has(.pdsel-{pd_}:checked) .evr.psp{pd_},'
        f'.psbox:has(.pdsel-{pd_}:checked) .pnum.psp{pd_}{{display:flex;}}'
        f'.psbox:has(.pdsel-{pd_}:checked) .pdl-{pd_}{{color:#c9ced4;'
        f'border-bottom-color:#4da3ff;}}'
        for pd_ in periods)
    # the two tricodes butt the centre gap the way their columns do: the
    # first ends on the gap's left edge, the second starts on its right.
    # No padding — the padding was insetting each code from the very edge
    # it is meant to sit on.
    heads = "".join(
        f'<div class="ps-fnt ps-xtick" '
        f'style="left:{CENTRE + side_of[team] * EV_GAP / 2:.2f}%;'
        f'transform:translateX({"-100%" if side_of[team] < 0 else "0"});">'
        f'<span style="color:{_TEAM_BRAND_COLORS.get(team, "gray")};">'
        f'{team}</span></div>'
        for team in teams)
    for r in rects:
        pd_ = r["period"]
        col = _TEAM_BRAND_COLORS.get(r["team"], "gray")
        codes = [c for c in str(r["events"]).split() if c != "-"][::-1]
        # every event of the possession, stacked OUT from the centre line
        # in the order it happened
        off = 0.0
        for n, code in enumerate(codes):
            w = SEG_W2 if len(code) <= 2 else SEG_W
            x = (CENTRE - EV_GAP / 2 - off - w if r["dir"] < 0
                 else CENTRE + EV_GAP / 2 + off)
            off += w
            scoring = code in ("M2", "M3", "FT")
            # no square: the fill alone marks the block, solid for a
            # score and translucent otherwise
            fill = (f"background:{col};" if scoring
                    else f"background:{col}3D;")
            if n == 0 and r["side"] == "o":
                parts.append(
                    f'<div class="pnum psp{pd_}" style="--ps-t:{r["top"]:.{VY}f}%;'
                    f'--ps-h:{r["h"]:.{VY}f}%;'
                    f'left:{NUM_L:.2f}%;'
                    f'color:{col};">{r["num"]}</div>')
                # the GAME score as of this possession, "124-125": one
                # column per team in its own colour, in the plot's own
                # order, with a neutral dash holding them together
                _geo = (f'--ps-t:{r["top"]:.{VY}f}%;'
                        f'--ps-h:{r["h"]:.{VY}f}%;')
                for _cls, _x, _t, _v in (
                        ("pnum", SCORE_L, teams[0], r["score"][0]),
                        ("pnum psdash", DASH_L, None, "-"),
                        ("pnum pnuml", SCORE2_L, teams[-1], r["score"][-1])):
                    _col = (f'color:{_TEAM_BRAND_COLORS.get(_t, "gray")};'
                            if _t else "")
                    parts.append(
                        f'<div class="{_cls} psp{pd_}" '
                        f'style="{_geo}left:{_x:.2f}%;{_col}">{_v}</div>')
                # fixed outer columns, both pushed clear of the widest
                # event stack: a left-side time grows right from TIME_L,
                # a right-side one ends flush at TIME_R
                _pos = (f'left:{TIME_L:.2f}%;' if r["dir"] < 0
                        else f'right:{100 - TIME_R:.2f}%;')
                parts.append(
                    f'<div class="evr psp{pd_}" style="--ps-t:{r["top"]:.{VY}f}%;'
                    f'--ps-h:{r["h"]:.{VY}f}%;{_pos}">'
                    f'{r["start"]} {r["dur"]}</div>')
            parts.append(
                f'<div class="psb psp{pd_}'
                f'{" psb-s" if scoring else " psb-n"}'
                f'{"" if r["inside"] else " psb-tiny"} pp{r["i"]}"'
                f' style="--ps-t:{r["top"]:.{VY}f}%;'
                f'--ps-h:{r["h"]:.{VY}f}%;'
                f'left:{x:.2f}%;width:{w:.2f}%;{fill}">'
                # the label is always in the DOM; on a block too short to
                # hold it, it stays hidden until the possession opens
                + (f'<span class="pslab">{code}</span>' if code else "")
                + "</div>"
            )

    # per-period totals, one line under each team's column: how many
    # possessions the period held and the points they produced, closing
    # the period the way the "0:00 0s" stamp closes its last row. Points
    # are POSSESSION points, so a period with technical free throws can
    # read a shade under the linescore — that is the possession model's
    # ledger, not an error.
    # one blank line of the plot's own type between the last possession and
    # the totals. A cqw is 1% of the 1200px container, and the canvas is
    # PLOT_ASPECT times that tall, so a cqw is 1/(PLOT_ASPECT) of a per cent
    # of canvas HEIGHT — the conversion every vertical measure here needs.
    BLANK = LAB_CQW * 1.45 / PLOT_ASPECT
    for pd_ in periods:
        y = _q(pbot[pd_] + 0.5 + BLANK)
        for t in teams:
            sel = poss[(poss.period == pd_) & (poss.team == t)]
            txt = f"{len(sel)} poss  {int(sel['points'].sum())} pts"
            pos = (f'right:{100 - CENTRE + EV_GAP / 2:.2f}%;' if side_of[t] < 0
                   else f'left:{CENTRE + EV_GAP / 2:.2f}%;')
            parts.append(
                f'<div class="ptot psp{pd_}" style="top:{y:.{VY}f}%;{pos}'
                f'color:{_TEAM_BRAND_COLORS.get(t, "gray")};">{txt}</div>')
        # the totals' own line, then two blank ones, then a rule of stars
        # closing the period out across the same span the clock rules use
        _stars = "*" * int((TIME_R - GRID_L) / COL_CH)
        parts.append(
            f'<div class="ptot pstar psp{pd_}" '
            f'style="top:{_q(y + 3 * BLANK):.{VY}f}%;left:{GRID_L:.2f}%;">'
            f'{_stars}</div>')

    # ---- the box score, in the game page's own table styling ----
    # no End column — the start and the duration already say when it ran.
    # Each line carries the possession's own event list on the end, the
    # offence's then the defence's, so the table reads as the play.
    # Pts/Sc are gone with them: M2 / M3 / FT already say what the
    # possession scored, and their absence says it scored nothing — the
    # columns only repeated the codes.
    # the events field is as wide as the widest row needs, so the divider
    # and the Players column land on one line down the whole table
    EV_W = max((len(str(x.off_events))
                + (3 + len(str(x.def_events)) if str(x.def_events) != "-" else 0)
                for _, x in poss.iterrows()), default=20)
    # the players field, like the events field, is as wide as the widest
    # row needs so the second divider lands on one line down the table.
    # Measured from the RENDERED tokens, not from a per-player constant:
    # a tricode is three characters where initials are two, so assuming
    # two put the divider in two different places down the table.
    PL_W = max((len(" ".join(_initials(n)
                             for n in str(x.off_players).split("|")))
                for _, x in poss.iterrows() if x.off_players), default=8)
    # the events field, sized for the codes WITH their .LL.DD suffixes
    def _form(x):
        a, _, _ = _ev_forms(str(x.off_events), x.off_shots)
        if str(x.def_events) != "-":
            c, _, _ = _ev_forms(str(x.def_events), x.def_shots)
            a = a + " | " + c
        return len(a)
    EV_LONG = max((_form(x) for _, x in poss.iterrows()), default=12)
    # the four leading columns, each only as wide as its widest value and
    # separated by ONE space. They were 4+2 / 5 / 11 / 6 + 3 = 31 characters
    # of which 9 were padding nothing needed — a third of the run-in before
    # the first divider, on a table that already overflows the page.
    # EVERY width is max(widest value, its own label). The header used to be
    # written with the data widths alone, so a label wider than its column —
    # "Team" over a 3-letter tricode — pushed the rest of the header one
    # character right of the data it names. Two of those errors happened to
    # cancel at the first divider, which is why only the second one showed.
    N_W = max(len(str(len(poss))), len("#"))
    TM_W = max(3, len("Team"))
    ST_W = max(max(len(pname[int(x.period)] + " " + _pad_clock(x.start_clock))
                   for _, x in poss.iterrows()), len("Start"))
    # the field carries the trailing "s", so the label competes with data + 1
    DUR_W = max(max(len(f"{x.duration_s:.0f}")
                    for _, x in poss.iterrows()) + 1, len("Dur"))
    # Per folds into Start: a possession's start IS its period plus the
    # clock, and "Q1 12:00" says that in one field where a bare "1" and a
    # bare "12:00" made the reader join them. Named like the period tabs,
    # so the table and the plot call a period the same thing.
    OF_W = max((len(str(x.off_offsets)) for _, x in poss.iterrows()
                if x.off_offsets), default=1)
    # Natural widths — what each field WANTS. The three run-on fields are no
    # longer padded to these; they are boxes this wide, and a value too long
    # for its box wraps and carries on at the box's own left edge.
    PL_W = max(PL_W, len("Players"))
    EV_W = max(EV_LONG, len("Events"))
    OF_W = max(OF_W, len("Offset"))
    # how many characters the page actually has. The section is 1200px wide
    # less its own left margin, and one character is the box font's advance,
    # both already in cqw — so the budget is a division, not a guess.
    LINE_CH = int((100.0 - _BOX_SCORE_LEFT_MARGIN * 100)
                  / (LAB_CQW * _MONO_ADVANCE_EM))
    # no separator between Team and Start: "Team" is one wider than a
    # tricode, so the label's own slack already spaces the two apart
    LEAD_W = N_W + 1 + TM_W + ST_W + 1 + DUR_W + 2
    _nat = [PL_W, EV_W, OF_W]
    _avail = LINE_CH - LEAD_W - len(_nat)          # one gutter per box
    if sum(_nat) <= _avail:
        PL_CAP, EV_CAP, OF_CAP = _nat              # everything fits; no wrap
    else:
        # hand each box its share of what is left, in proportion to what it
        # wanted, and never less than a couple of tokens' worth
        _s = sum(_nat)
        PL_CAP, EV_CAP, OF_CAP = (max(6, int(w * _avail / _s)) for w in _nat)
    head = (f'{"#":>{N_W}} {"Team":<{TM_W}}{"Start":>{ST_W}} {"Dur":>{DUR_W}}  ',
            "Players", "Events", "Offset")
    body = []
    # rank WITHIN the period, because the row limit counts what is on
    # screen and the other periods' rows are display:none, not removed —
    # so :nth-child, which counts DOM position, would count them too
    rank: dict[int, int] = {}
    _last_pd = None
    for r in [x for x in rects if x["side"] == "o"]:
        p_ = poss.loc[r["row"]]
        tri = (f'<span style="color:'
               f'{_TEAM_BRAND_COLORS.get(r["team"], "gray")};">'
               f'{r["team"]:<{TM_W}}</span>')
        # WHO did it, WHAT they did, WHERE from — the order a sentence
        # takes. A neutral rule wherever one team's list meets the other's
        # or one column meets the next, so the eye finds the boundary
        # without either colour claiming it.
        _bar = f'<span style="color:{FURN_COLOR};"> \u2502 </span>'
        _col = lambda t: _TEAM_BRAND_COLORS.get(t, "gray")
        _full = lambda n: (f"{n} \u2014 team" if len(n) == 3 and n.isupper()
                           and n.isalpha() else n)
        _who = lambda names: " ".join(
            f'<span class="plq">{_initials(n)}'
            f'<span class="plf">{html.escape(_full(n))}</span></span>'
            for n in names)
        _plain = lambda names: " ".join(_initials(n) for n in names)

        off_ev, def_ev = str(p_.off_events), str(p_.def_events)
        _op = str(p_.off_players).split("|") if p_.off_players else []
        _dp = str(p_.def_players).split("|") if p_.def_players else []
        _has_def = def_ev != "-"

        # padding is measured on the VISIBLE text, never on the markup
        _who_txt = _plain(_op) + (" | " + _plain(_dp) if _dp else "")
        _oL, _oS, _oH = _ev_forms(off_ev, p_.off_shots)
        _dL, _dS, _dH = _ev_forms(def_ev, p_.def_shots) if _has_def else ("", "", "")
        _long = _oL + (" | " + _dL if _has_def else "")

        # three boxes, no padding — the box widths hold the columns, and a
        # value longer than its box wraps inside it. Only the rule BETWEEN
        # the two teams' lists is still drawn.
        ev = ('<span class="cp">'
              + f'<span style="color:{_col(r["team"])};">{_who(_op)}</span>'
              + (_bar + f'<span style="color:{_col(p_.def_team)};">'
                 f'{_who(_dp)}</span>' if _dp else "")
              + '</span><span class="ce">'
              + f'<span style="color:{_col(r["team"])};">{_oH}</span>'
              + (_bar + f'<span style="color:{_col(p_.def_team)};">{_dH}</span>'
                 if _has_def else "")
              + '</span><span class="co">'
              + f'<span style="color:{_col(r["team"])};">'
              + (str(p_.off_offsets) if p_.off_offsets else "")
              + "</span></span>")
        # ALL runs every period together, so each period announces itself
        # once, ahead of its own rows. Carries no .pspN — it is wanted only
        # in the ALL view, and a period class would let the single-period
        # rule (heavier, .psbox:has(...) .pspN) switch it back on there.
        if r["period"] != _last_pd:
            body.append(f'<span class="pdh">{pname[r["period"]]}</span>')
            _last_pd = r["period"]
        _k = rank[r["period"]] = rank.get(r["period"], -1) + 1
        body.append(
            f'<span class="psp{r["period"]} bxr{_k} pp{r["i"]}">'
            f'<span class="cl">{r["i"] + 1:>{N_W}} {tri}'
            f'{pname[int(p_.period)] + " " + _pad_clock(p_.start_clock):>{ST_W}} '
            f'{f"{p_.duration_s:.0f}s":>{DUR_W}}  </span>{ev}</span>')

    # ---- both-way hover links: block -> row, row -> block ----
    # ONE grouped rule per effect rather than four rules per possession:
    # a 230-possession game is ~19KB of selectors this way against ~208KB
    # written out per possession, and a third of the :has(:hover) count.
    # ---- ALL ----
    # ALL is no longer a row limit sitting beside the period tabs; it is one
    # more member OF them, in the same radio group, so picking it drops the
    # period and picking a period drops it. It shows every possession in the
    # game with each period headed by its own name.
    bxlim_css = (
        # one selector per period rather than a comma list with a shared
        # prefix — a leading combinator does NOT distribute across commas
        "".join(f'.psbox:has(.pdsel-all:checked) .psp{pd_}{{display:block;}}'
                for pd_ in periods)
        + '.psbox:has(.pdsel-all:checked) .bxl-all{color:#c9ced4;'
          'border-bottom-color:#4da3ff;}'
        # the period headings exist only in the ALL view; each opens with a
        # blank table line except the first, which already follows one
        + '.pdh{display:none;}'
        + f'.psbox:has(.pdsel-all:checked) .bxs > .pdh{{display:block;'
          f'color:{_BOX_HEAD_COLOR};margin-top:{LAB_CQW * 1.5:.2f}cqw;}}'
        + '.psbox:has(.pdsel-all:checked) .bxs > .pdh:first-child'
          '{margin-top:0;}')
    # ---- Where: the shot-location legend ----
    # The codes are the middle field of M3.LW.25. RM is a radius, the other
    # five are the 45-degree sectors shot_area() cuts the floor into, named
    # the way the sectors are named there so the two never drift apart.
    _LOCS = (("RM", "at the rim", "inside 4 ft"),
             ("RC", "right corner", ""), ("RW", "right wing", ""),
             ("SO", "straight on", ""), ("LW", "left wing", ""),
             ("LC", "left corner", ""))
    legend = ('<span class="lgh">Where a shot came from</span>\n'
              'the middle field of M3.LW.25\n\n'
              + "".join(f'<span class="lgc">{c}</span>   {n:<13}{x}\n'
                        for c, n, x in _LOCS)
              + '\n<span class="lgc">M3.LW.25</span>   made 3, left wing, 25 ft\n'
                '<span class="lgc">X2.RM.01</span>   missed 2, at the rim, 1 ft')
    # ---- What: the event legend ----
    # Every code _event_code() can return, plus the three the possession
    # walk adds itself (AST, STL, BLK) and the two rebound directions.
    _EVENTS = (("M2 / M3", "made 2 / made 3"),
               ("X2 / X3", "missed 2 / missed 3"),
               ("FT / X1", "free throw made / missed"),
               ("AST", "assist"),
               ("OR / DR", "offensive / defensive rebound"),
               ("STL", "steal"),
               ("BLK", "block"),
               ("TO", "turnover"),
               ("FL", "foul"),
               ("OF", "offensive foul — ends the possession"),
               ("VIOL", "violation"),
               ("JUMP", "jump ball"),
               ("TM", "timeout"),
               ("IR", "instant replay"),
               ("HE", "heave at the buzzer, filed to the team"))
    legend_what = ('<span class="lgh">What happened</span>\n'
                   'the codes in the Events column\n\n'
                   + "".join(f'<span class="lgc">{c:<7}</span>   {n}\n'
                             for c, n in _EVENTS).rstrip("\n"))
    bxradios = (f'<input type="radio" class="pdsel pdsel-all"'
                f' name="pdsel-{game_id}" id="pd-{game_id}-all">')
    bxlabels = (f'<label class="pdl bxl-all" for="pd-{game_id}-all">'
                f'ALL</label>')

    n_poss = len([x for x in rects if x["side"] == "o"])
    _sel = lambda tail: ",".join(f".psbox:has(.pp{i}:hover) {tail.format(i=i)}"
                                 for i in range(n_poss))
    link_css = (
        (f'{_sel("span.pp{i}")}{{background:#ffffff1f;}}'
         f'{_sel("div.pp{i}")}{{outline:2px solid #fff;outline-offset:1px;'
         f'height:max(var(--ps-h),var(--ps-eh))!important;'
         f'top:calc(var(--ps-t) - '
         f'(max(var(--ps-h),var(--ps-eh)) - var(--ps-h))/2)!important;'
         f'z-index:5;}}'
         f'{_sel("div.pp{i} .pslab")}{{display:block;}}')
        if n_poss else "")

    css = f"""
/* ---- possessions section (block-private; borrows only .kbox/.kb-fold/
   summary.ktitle/.bx-flow/.bx-fold from the page's own furniture) ---- */
.psbox{{position:relative;--ps-eh:{max(GLYPH_CQW * 1.45, LAB_CQW * 1.25):.3f}cqw;}}
.ps-canvas{{position:relative;width:100%;aspect-ratio:{1 / PLOT_ASPECT:.4f};}}
/* the title is absolutely positioned (it is a .ktitle), so the plot
   reserves its line here */
.pbox{{position:relative;padding-top:{_TITLE_FONT_CQW * 1.5:.2f}cqw;}}
/* The title is absolutely positioned but .pbox is a LATER positioned
   sibling, so .pbox painted over it and swallowed the click — the fold
   opened and then could not be closed, because .pbox is display:none
   while closed and only covers the title once open. A z-index above
   .pbox (and above the Big/Normal switch's 2) puts the title back on
   top. It shrink-wraps to its text, so it blocks nothing beside it. */
.psbox summary.ktitle{{z-index:4;}}
.psbox > .kbox:has(> .kb-fold:not([open])) .pbox{{display:none;}}
/* furniture, same treatment as the karma panels */
.ps-fnl{{position:absolute;height:0;border-top:1px solid #FFFFFF26;
  pointer-events:none;}}
/* mono here is not cosmetic: TICK_W sizes the gutter as 5 character
   advances of "12:00", so the clock column only stays flush in a fixed
   pitch face */
.ps-fnt{{position:absolute;color:{FURN_COLOR};
  font-family:'DejaVu Sans Mono',monospace;
  font-size:{YTICK_CQW:.3f}cqw;pointer-events:none;white-space:nowrap;}}
.ps-xtick{{font-size:{HEAD_CQW:.2f}cqw;transform:translate(0,-100%);}}
.ps-ytick{{transform:translate(-100%,-50%);}}
/* possession blocks. top/height come off the same two custom
   properties the hover rule reads, so a block carries each number once */
.psb{{position:absolute;border-radius:1px;
  top:var(--ps-t);height:var(--ps-h);}}
/* the title line's Big/Normal switch, which ships OPEN — big is the
   default view. Open holds EVERY possession at the height hover would
   give it — max(its own span, one label line) — and letters every code,
   so a whole period reads without the mouse. Thin neighbours overlap in
   this view by construction; that is the trade the switch buys, and
   clicking "Normal" returns to proportional heights. Hover still
   outlines and links rows (its rules carry !important and win the tie
   with the same geometry). */
.psbox:has(.ps-big[open]) .psb{{height:max(var(--ps-h),var(--ps-eh));
  top:calc(var(--ps-t) - (max(var(--ps-h),var(--ps-eh)) - var(--ps-h))/2);}}
.psbox:has(.ps-big[open]) .psb-tiny .pslab{{display:block;}}
/* per-period totals: one line under each team's column, butting the
   centre like the columns themselves */
.ptot{{position:absolute;font-family:'DejaVu Sans Mono',monospace;
  font-size:{LAB_CQW:.3f}cqw;pointer-events:none;white-space:pre;}}
.pstar{{color:{FURN_COLOR};letter-spacing:0;}}
/* the team's own possession count, level with the possession, just past
   the right end of the time grid */
/* fixed three-character columns, right-aligned, so a 9 and a 125 stack on
   their last digit. Width in cqw and not %, because these sit on the
   canvas — which is the container MINUS the scrollbar gutter, so a % here
   would be ~1.2% short of the character width it is meant to hold */
.pnum{{position:absolute;font-family:'DejaVu Sans Mono',monospace;
  font-size:{LAB_CQW:.3f}cqw;pointer-events:none;
  width:{COL_W3:.3f}cqw;justify-content:flex-end;
  top:calc(var(--ps-t) - (max(var(--ps-h),var(--ps-eh)) - var(--ps-h))/2);
  height:max(var(--ps-h),var(--ps-eh));display:flex;align-items:center;}}
/* the score's second half hangs LEFT off the dash, and the dash itself is
   a single neutral character between the two team colours */
.pnuml{{justify-content:flex-start;}}
.psdash{{width:{COL_CH:.3f}cqw;justify-content:center;
  color:{_BOX_HEAD_COLOR};}}
/* the game time in fixed outer columns, backdropped so it stays legible
   over a tick label or a long event stack */
.evr{{position:absolute;color:{_BOX_HEAD_COLOR};background:#000;
  box-shadow:0 0 0 2px #000;border-radius:2px;
  font-family:'DejaVu Sans Mono',monospace;font-size:{LAB_CQW:.3f}cqw;
  white-space:pre;z-index:7;pointer-events:none;
  top:calc(var(--ps-t) - (max(var(--ps-h),var(--ps-eh)) - var(--ps-h))/2);
  height:max(var(--ps-h),var(--ps-eh));display:flex;align-items:center;}}
/* --ps-eh is one line of the code type — or of the stamp type where that
   is taller, since .evr and .pnum open to the same height and carry the
   larger tabular face. A possession too short to letter opens to it while
   hovered, centred on its own middle so it stays over the moment it
   happened, and collapses again on exit */
.psb-tiny .pslab{{display:none;}}
.pslab{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
  font-family:'DejaVu Sans Mono',monospace;font-size:{GLYPH_CQW:.3f}cqw;
  color:#000;pointer-events:none;white-space:nowrap;}}
.psb-n .pslab{{color:{FURN_COLOR};}}
/* both blocks scroll inside their own window: the plot is 3,600px tall
   and the table 200-odd rows, so the page would otherwise run for metres.
   Sized in cqw like everything else on the page, not vh */
/* narrowed by the scrollbar gutter so the team heads sit in the SAME
   coordinate space as the canvas below and land on the centre gap */
.pshead{{position:relative;height:{HEAD_CQW * 1.5:.2f}cqw;
  width:calc(100% - {SCROLLBAR_PX}px);}}
.pshead .ps-xtick{{top:0;transform:none;}}
.pscroll{{position:relative;height:{PSCROLL_CQW:.0f}cqw;min-height:320px;
  overflow-y:auto;overflow-x:hidden;scrollbar-gutter:stable;}}
/* max-height, not height: at 10 or 25 rows the window shrinks to its
   content instead of leaving a tall empty box below the table */
/* Every column is padded to the widest row in the game so the dividers
   stack, which means one seven-event possession sets the width for all
   225 — about 1,420px of table in a 1,200px page. It simply RUNS PAST the
   right edge for now: CSS will not give one axis `visible` while the
   other scrolls (it silently promotes both to `auto`), so keeping the
   vertical scroll box would have meant a sideways scrollbar. The table
   overflows instead and the page carries the rows. */
.bxscroll{{position:relative;overflow:visible;}}
/* the four boxes a line is made of. The lead never wraps; the three
   run-on fields do, and because each is an inline-block the continuation
   starts at that box's own left edge — the column boundary — rather than
   at the start of the line. Widths are in ch, which in a monospace face
   IS one character, so a box is exactly as many columns as it says.
   break-word is the backstop for a single token wider than its box. */
.psbox :is(.cl,.cp,.ce,.co){{display:inline-block;vertical-align:top;}}
.psbox .cl{{white-space:pre;width:{LEAD_W}ch;}}
/* border-box + a 1ch right pad, NOT width = cap + 1: with the gutter
   inside the width, a value exactly one character over its cap still
   fitted the box, so it never wrapped and ate the gap to the next
   column instead. The pad makes the content box exactly `cap` wide. */
.psbox :is(.cp,.ce,.co){{white-space:pre-wrap;overflow-wrap:break-word;
  box-sizing:border-box;padding-right:1ch;}}
.psbox .cp{{width:{PL_CAP + 1}ch;}}
.psbox .ce{{width:{EV_CAP + 1}ch;}}
.psbox .co{{width:{OF_CAP + 1}ch;}}
/* What / Where: the two legends sit together on the box score's title
   line. ONE anchored cluster rather than two hand-placed toggles — the
   labels are proportional text, so their widths are not something to
   compute. Each panel OVERLAYS the table: absolute, so opening one
   cannot reflow a single row or make the section any taller. The
   cluster hides with the fold, the way the row limit used to. */
.bxctl{{position:absolute;top:0;
  right:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;z-index:5;
  display:flex;gap:1.4cqw;
  font-family:'DejaVu Sans',sans-serif;font-size:{HEAD_CQW:.2f}cqw;}}
.ps-leg > summary{{cursor:pointer;list-style:none;color:#4da3ff;}}
.ps-leg > summary::-webkit-details-marker{{display:none;}}
.ps-leg > summary:hover{{text-decoration:underline;}}
.bx-flow:has(> .bx-fold:not([open])) .bxctl{{display:none;}}
/* right:0 against .bxctl, which is itself the anchor — both panels hang
   from the same edge whatever their toggles measure */
.leg{{position:absolute;top:{LAB_CQW * 1.5 * 1.6:.2f}cqw;right:0;
  z-index:9;white-space:pre;
  background:#000;border:1px solid #2a2f36;border-radius:4px;
  padding:0.8cqw 1.2cqw;color:{_BOX_HTML_TEXT};
  font-family:'DejaVu Sans Mono',monospace;font-size:{LAB_CQW:.2f}cqw;
  box-shadow:0 4px 18px rgba(0,0,0,.85);}}
.leg .lgh{{color:{_BOX_HEAD_COLOR};}}
.leg .lgc{{color:#4da3ff;}}
.bx-headrow{{padding-bottom:0;}}
/* one blank table line between the period tabs and the column header,
   the same 1.5x-the-box-font line the tabs get below the title. Scoped
   to .psbox so the page's other box scores keep their own spacing. */
.psbox .bx-headrow{{margin-top:{LAB_CQW * 1.5:.2f}cqw;}}
/* a player is two initials on the line; the full name is carried in a
   span that only paints on hover, positioned absolutely so revealing it
   never reflows the monospace row. One rule pair covers every player on
   the page rather than one per name. */
.plq{{position:relative;}}
.plf{{display:none;position:absolute;left:0;top:1.15em;z-index:9;
  background:#000;box-shadow:0 0 0 3px #000;border-radius:2px;
  color:{_BOX_HEAD_COLOR};white-space:pre;pointer-events:none;}}
.plq:hover{{color:#fff;}}
.plq:hover .plf{{display:block;}}
.pscroll::-webkit-scrollbar,.bxscroll::-webkit-scrollbar{{width:{SCROLLBAR_PX}px;}}
.pscroll::-webkit-scrollbar-thumb,.bxscroll::-webkit-scrollbar-thumb{{
  background:linear-gradient(#8a8a8a,#333);border-radius:5px;
  border:4px solid #000;}}
.pscroll::-webkit-scrollbar-thumb:hover,
.bxscroll::-webkit-scrollbar-thumb:hover{{
  background:linear-gradient(#c0c0c0,#666);box-shadow:0 0 8px #B0B0B0;}}
.pscroll::-webkit-scrollbar-track,.bxscroll::-webkit-scrollbar-track{{
  background:rgba(255,255,255,.06);}}
{link_css}
{period_css}
{bxlim_css}
/* one period at a time: everything period-tagged hides until its tab is
   picked, so the selected period gets the entire canvas */
.psbox .psp1,.psbox .psp2,.psbox .psp3,.psbox .psp4,
.psbox .psp5,.psbox .psp6,.psbox .psp7,.psbox .psp8{{display:none;}}
.pdsel{{position:absolute;opacity:0;pointer-events:none;}}
/* the period selectors: one line, hard against the left margin, and one
   blank table line below the section title — the box font's line box is
   exactly 1.5x its size, so that is what a row of this table measures */
.pdside{{position:relative;display:flex;gap:1.1cqw;
  margin-left:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;
  margin-top:{LAB_CQW * 1.5:.2f}cqw;
  padding:0 0 0.5cqw 0;
  font-family:'DejaVu Sans',sans-serif;font-size:{HEAD_CQW:.2f}cqw;}}
.pdl{{color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;
  padding:0 0.2cqw 0.15cqw;}}
.pdl:hover{{color:#9BA3AD;}}
"""

    # The plot is gone; the box score is the whole section. The period
    # radios stay — they are the state machine the rows' .pspN classes read,
    # and every rule that reads them is scoped to .psbox, so they only have
    # to live somewhere inside it. The selector they drive moves down onto
    # the table, between its title and its column header.
    _open = " open" if open_default else ""
    markup = f"""<div class="chart-wrap">
<div class="psbox">
<div class="bx-flow">
{radios}
{bxradios}
<div class="bxctl"><details class="ps-leg"><summary>What</summary
><div class="leg">{legend_what}</div></details
><details class="ps-leg"><summary>Where</summary
><div class="leg">{legend}</div></details></div>
<details class="lu-fold bx-fold"{_open}><summary>
<div class="bx bx-title"><span class="bx-head">{matchup}Possessions box score</span></div>
</summary>
<div class="pdside">{pdlabels}{bxlabels}</div>
<div class="bx bx-headrow"><span class="bx-head"><span class="cl">{head[0]}</span
><span class="cp">{head[1]}</span><span class="ce">{head[2]}</span
><span class="co">{head[3]}</span></span></div>
<div class="bxscroll"><div class="bx"><span class="bxs">{''.join(body)}</span></div></div>
</details></div>
</div>
</div>"""

    return PossSection(markup, css, {
        "possessions": n_poss, "bars": len(rects), "teams": teams,
        "date": date, "labelled": labelled,
        "unlabelled_scored": sum(1 for r in rects
                                 if r["scored"] and not r["label"]),
        "clamped": clamped,
    })
