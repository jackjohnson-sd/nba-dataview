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
YTICK_CQW = _pt(7)                  # y tick labels -> the game clock scale
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

PLOT_T, PLOT_B = 1.0, 97.0          # top/bottom of the time axis, % of height
COL_W = 24.0                        # each half's reach: the longest
                                    # possession in a game is 6 events
TICK_W = 5 * YTICK_CQW * _MONO_ADVANCE_EM   # "12:00" at the clock's own
                                    # size — this gutter IS the label, so it
                                    # has to move whenever the label does
# the time grid keeps the page's left margin (scale labels start where
# the Possessions title and the Q1 row start); the CONTENT — stamps,
# events, counts — sits a step to the right of it
GRID_L = _BOX_SCORE_LEFT_MARGIN * 100 + TICK_W + 1.0
SHIFT = 4.0                         # the content's step right off the grid
CENTRE = GRID_L + SHIFT + COL_W
# "12:00" is 5 mono chars at the shared size, so the left time column
# starts exactly where the clock labels themselves start
TIME_L = CENTRE - COL_W - 0.5
PLOT_ASPECT = 1.82                  # height/width of the canvas — one
                                    # PERIOD fills it, so this is ~3.5x the
                                    # room a period had on the game-long axis
SEG_W = 3.8                         # block width for 3-4 char codes
SEG_W2 = 2.6                        # ...and for 2-char codes
VY = 2                              # decimals on every VERTICAL per cent.
                                    # 0.01% is 0.216px on the 2158px canvas
                                    # — above the layout quantum — while the
                                    # source clock is only good to 0.1s, i.e.
                                    # 0.288px on a 12-minute period, so a
                                    # third decimal would encode precision
                                    # the play-by-play does not have
PSCROLL_CQW = 70.0                  # the plot's own scroll window
BXSCROLL_CQW = 38.0                 # the table's


class PossSection(NamedTuple):
    """`html` is exactly one `<div class="chart-wrap">…</div>`; `css` is
    block-private rules only (safe to concatenate into a game page's
    stylesheet); `info` is the builder's diagnostics."""
    html: str
    css: str
    info: dict


def _fmt_clock(rem: str) -> str:
    return rem.split(".")[0] if "." in rem else rem


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
            span_by_row[idx] = (_t, _q(prev_bottom) - _t)

    seen: dict[str, int] = {t: 0 for t in teams}
    for i, (idx, r) in enumerate(
            poss.sort_values("start_elapsed").iterrows()):
        seen[r.team] += 1
        y0, h = span_by_row[idx]                # already the drawn row box
        show_label = r.points > 0
        inside = h >= label_h_pct
        labelled += int(show_label)
        base = {"i": i, "top": y0, "h": h, "y0s": float(r.start_elapsed),
                "period": int(r.period), "num": seen[r.team],
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
                         f'width:{CENTRE + COL_W - GRID_L:.2f}%;"></div>')
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
    heads = "".join(                          # column heads: pinned above
        f'<div class="ps-fnt ps-xtick" style="left:{CENTRE:.2f}%;'
        f'transform:translateX({"-100%" if side_of[team] < 0 else "0"});'
        f'padding:0 0.6cqw;">'
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
            x = CENTRE - off - w if r["dir"] < 0 else CENTRE + off
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
                    f'left:{CENTRE + COL_W + 1.0:.2f}%;'
                    f'color:{col};">{r["num"]}</div>')
                # fixed outer columns: a left-side time LEFT-aligns with
                # the clock key labels' left edge; a right-side time ends
                # flush with the right end of the time grid
                _pos = (f'left:{TIME_L:.2f}%;' if r["dir"] < 0
                        else f'right:{100 - (CENTRE + COL_W):.2f}%;')
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

    # ---- the box score, in the game page's own table styling ----
    # no End column — the start and the duration already say when it ran.
    # Each line carries the possession's own event list on the end, the
    # offence's then the defence's, so the table reads as the play.
    # Pts/Sc are gone with them: M2 / M3 / FT already say what the
    # possession scored, and their absence says it scored nothing — the
    # columns only repeated the codes.
    head = f'{"#":>4}  {"Team":<5}{"Per":>4}{"Start":>8}{"Dur":>6}   Events'
    body = []
    for r in [x for x in rects if x["side"] == "o"]:
        p_ = poss.loc[r["row"]]
        tri = (f'<span style="color:'
               f'{_TEAM_BRAND_COLORS.get(r["team"], "gray")};">'
               f'{r["team"]:<5}</span>')
        off_ev = str(p_.off_events)
        def_ev = str(p_.def_events)
        ev = (f'<span style="color:'
              f'{_TEAM_BRAND_COLORS.get(r["team"], "gray")};">{off_ev}</span>'
              + (f'   <span style="color:'
                 f'{_TEAM_BRAND_COLORS.get(p_.def_team, "gray")};">'
                 f'{def_ev}</span>' if def_ev != "-" else ""))
        body.append(
            f'<span class="psp{r["period"]} pp{r["i"]}">{r["i"] + 1:>4}  {tri}'
            f'{int(p_.period):>4}{_fmt_clock(p_.start_clock):>8}'
            f'{p_.duration_s:>5.0f}s   {ev}</span>')

    # ---- both-way hover links: block -> row, row -> block ----
    # ONE grouped rule per effect rather than four rules per possession:
    # a 230-possession game is ~19KB of selectors this way against ~208KB
    # written out per possession, and a third of the :has(:hover) count.
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
.psbox > .kbox:has(> .kb-fold:not([open])) .pbox{{display:none;}}
/* furniture, same treatment as the karma panels */
.ps-fnl{{position:absolute;height:0;border-top:1px solid #FFFFFF26;
  pointer-events:none;}}
/* mono here is not cosmetic: TICK_W sizes the gutter as 5 character
   advances of "12:00", so the clock column only stays flush in a fixed
   pitch face */
.ps-fnt{{position:absolute;color:{_BOX_HEAD_COLOR};
  font-family:'DejaVu Sans Mono',monospace;
  font-size:{YTICK_CQW:.3f}cqw;pointer-events:none;white-space:nowrap;}}
.ps-xtick{{font-size:{HEAD_CQW:.2f}cqw;transform:translate(0,-100%);}}
.ps-ytick{{transform:translate(-100%,-50%);}}
/* possession blocks. top/height come off the same two custom
   properties the hover rule reads, so a block carries each number once */
.psb{{position:absolute;border-radius:1px;
  top:var(--ps-t);height:var(--ps-h);}}
/* the title line's Big/Normal switch: open holds EVERY possession at the
   height hover would give it — max(its own span, one label line) — and
   letters every code, so a whole period reads without the mouse. Thin
   neighbours overlap in this view by construction; that is the trade the
   switch buys. Hover still outlines and links rows (its rules carry
   !important and win the tie with the same geometry). */
.psbox:has(.ps-big[open]) .psb{{height:max(var(--ps-h),var(--ps-eh));
  top:calc(var(--ps-t) - (max(var(--ps-h),var(--ps-eh)) - var(--ps-h))/2);}}
.psbox:has(.ps-big[open]) .psb-tiny .pslab{{display:block;}}
/* the team's own possession count, level with the possession, just past
   the right end of the time grid */
.pnum{{position:absolute;font-family:'DejaVu Sans Mono',monospace;
  font-size:{LAB_CQW:.3f}cqw;pointer-events:none;
  top:calc(var(--ps-t) - (max(var(--ps-h),var(--ps-eh)) - var(--ps-h))/2);
  height:max(var(--ps-h),var(--ps-eh));display:flex;align-items:center;}}
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
.psb-n .pslab{{color:{_BOX_HTML_TEXT};}}
/* both blocks scroll inside their own window: the plot is 3,600px tall
   and the table 200-odd rows, so the page would otherwise run for metres.
   Sized in cqw like everything else on the page, not vh */
.pshead{{position:relative;height:{HEAD_CQW * 1.5:.2f}cqw;}}
.pshead .ps-xtick{{top:0;transform:none;}}
.pscroll{{position:relative;height:{PSCROLL_CQW:.0f}cqw;min-height:320px;
  overflow-y:auto;overflow-x:hidden;scrollbar-gutter:stable;}}
.bxscroll{{position:relative;height:{BXSCROLL_CQW:.0f}cqw;min-height:180px;
  overflow-y:auto;overflow-x:hidden;scrollbar-gutter:stable;}}
.bx-headrow{{padding-bottom:0;}}
.pscroll::-webkit-scrollbar,.bxscroll::-webkit-scrollbar{{width:14px;}}
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
/* one period at a time: everything period-tagged hides until its tab is
   picked, so the selected period gets the entire canvas */
.psbox .psp1,.psbox .psp2,.psbox .psp3,.psbox .psp4,
.psbox .psp5,.psbox .psp6,.psbox .psp7,.psbox .psp8{{display:none;}}
.pdsel{{position:absolute;opacity:0;pointer-events:none;}}
/* the period selectors: one line, hard against the left margin */
.pdside{{position:relative;display:flex;gap:1.1cqw;
  margin-left:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;
  padding:0 0 0.5cqw 0;
  font-family:'DejaVu Sans',sans-serif;font-size:{HEAD_CQW:.2f}cqw;}}
.pdl{{color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;
  padding:0 0.2cqw 0.15cqw;}}
.pdl:hover{{color:#9BA3AD;}}
"""

    _open = " open" if open_default else ""
    markup = f"""<div class="chart-wrap">
<div class="psbox">
<div class="kbox">
<details class="kb-fold"{_open}><summary class="ktitle"
 style="top:0;left:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;">{matchup}Possessions</summary></details>
<details class="lu-toggle ps-big"><summary
 style="right:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;top:0;"><span
 class="more-txt">Big</span><span class="less-txt">Normal</span></summary></details>
<div class="pbox">
{radios}
<div class="pdside">{pdlabels}</div>
<div class="pshead">{heads}</div>
<div class="pscroll"><div class="ps-canvas">{''.join(parts)}</div></div>
</div>
</div>
<div class="bx-flow"><details class="lu-fold bx-fold"{_open}><summary>
<div class="bx bx-title"><span class="bx-head">{matchup}box score</span></div>
</summary>
<div class="bx bx-headrow"><span class="bx-head">{html.escape(head)}</span></div>
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
