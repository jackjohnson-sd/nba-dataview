#!/usr/bin/env python3
"""Build test_page.html — the possessions plot, to fold into the game page.

Two rows of possessions, one per team in that team's colour, laid on the
game-clock axis: each rect starts where the possession started and is as
wide as the possession lasted. A scored possession is filled solid and
carries its point total; an empty one is a dim outline.

TOO SMALL TO LABEL: a 4-second possession is a couple of pixels wide, far
too narrow for even one digit. Rather than drop those possessions to
nothing or let the text spill over its neighbours, the rule is:

  * every rect keeps a visible minimum width, but never one that would
    push it into the next possession in the same row (a real clamp, not a
    hope — the builder checks and reports the count)
  * the point label is drawn ONLY when the rect is genuinely wider than
    the glyph; otherwise the fill alone carries "scored", and
  * hovering any rect — however thin — pops the full readout above the
    plot AND lights its row in the box score below, so nothing is
    unreachable just because it is small.

    .venv/bin/python scripts/possessions_page.py [GAME_ID] [-o PATH]
"""
from __future__ import annotations

import argparse
import glob
import html
from pathlib import Path

from nba_pbp.plotting import (_BOX_FONT_CQW, _BOX_FONT_CSS, _BOX_GOLD,
                              _BOX_GREY, _BOX_HEAD_COLOR, _BOX_HTML_TEXT,
                              _BOX_RED, _BOX_SCORE_LEFT_MARGIN,
                              _MONO_ADVANCE_EM, _PAGE_DPI, _PAGE_W_PX,
                              _PANEL_TITLE_COLOR, _TEAM_BRAND_COLORS,
                              _TITLE_FONT_CQW, _TITLE_FONT_CSS)


def _pt(points: float) -> float:
    """A matplotlib point size as cqw, the way the karma panels size their
    text — so this plot's furniture matches theirs instead of guessing."""
    return points * (_PAGE_DPI / 72) / (_PAGE_W_PX / 100)


BAR_THICK = 0.45                    # a block's height as a share of its
                                    # possession's span — the block sits
                                    # centred in the band, so durations stay
                                    # proportional but read far lighter
LABEL_FIT = 0.3                    # room a code needs to be lettered at
                                    # rest, in label heights. Swept against
                                    # measured label collisions: 1.05 letters
                                    # 317 blocks with none touching, 1.00
                                    # letters 338 but 5 pairs collide, 0.85
                                    # letters 397 with 20. The rest open on
                                    # hover, so this is the floor that keeps
                                    # the resting plot clean.
TICK_CQW = _pt(8)                   # karma's x tick labels
HEAD_CQW = _TITLE_FONT_CQW          # panel-title size, for the team heads
LAB_CQW = _pt(7)                    # karma's y ticks, for the in-bar points
from nba_pbp.possessions import compute_possessions

# VERTICAL timeline: game clock runs down the page, the two teams sit
# side by side. Going vertical buys pixels — the plot is 3x the container
# WIDE instead of a fifth of it, so a second of game clock is worth ~3x
# more space and possessions become tall enough to label.
PLOT_T, PLOT_B = 1.0, 97.0          # top/bottom of the time axis, % of height
# the two halves BUTT against a shared centre line: the first team's bars
# grow leftward from it, the second's rightward, so at every moment of the
# game the two teams' possessions meet in the middle
GUTTER = 18.0                       # left gutter: the period labels and
                                    # the hovered possession's time, ONCE
CENTRE = 47.0                       # % of container width
COL_W = 24.0                        # each half's reach: the longest
                                    # possession in a game is 6 events
PLOT_ASPECT = 1.82                   # height/width of the .img-box — one
                                    # PERIOD fills it, so this is ~3.5x the
                                    # room a period had on the game-long axis


# rebounds read as the same two codes everywhere on the page
_GAIN = {"defensive rebound": "DR", "offensive rebound": "OR",
         "opponent score": "opp score", "offensive foul": "off foul",
         "shot clock": "shot clock", "period start": "tip"}


def _fmt_clock(rem: str) -> str:
    return rem.split(".")[0] if "." in rem else rem


def build(game_id: str, out_path: Path) -> dict:
    csv = glob.glob(f"outputs/*/*/csv/pbp_{game_id}.csv")
    if not csv:
        raise SystemExit(f"no play-by-play csv for {game_id}")
    poss = compute_possessions(csv[0])
    teams = list(dict.fromkeys(poss["team"]))
    date = poss["date"].iloc[0] if "date" in poss else ""
    total = float(poss["end_elapsed"].max())

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
    label_h_pct = (LAB_CQW / 100 * 1200 * LABEL_FIT) / box_h_px * 100
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
        for k, (y0, y1, idx) in enumerate(ys):
            h = max(y1 - y0, MIN_H)
            top = (y0 + y1) / 2 - h / 2          # grow about the midpoint
            nxt = ys[k + 1][0] if k + 1 < len(ys) else 100.0
            if top < prev_bottom:
                top = prev_bottom
                clamped += 1
            if top + h > nxt:
                h = max(nxt - top, 0.01)
                clamped += 1
            span_by_row[idx] = (top, h)
            prev_bottom = top + h

    seen: dict[str, int] = {t: 0 for t in teams}
    for i, (idx, r) in enumerate(
            poss.sort_values("start_elapsed").iterrows()):
        seen[r.team] += 1
        y0, h = span_by_row[idx]
        show_label = r.points > 0
        inside = h * BAR_THICK >= label_h_pct
        labelled += int(show_label)
        hb = h * BAR_THICK
        base = {"i": i, "top": y0 + (h - hb) / 2, "h": hb,
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
            parts.append(f'<div class="fnl pd{pd_}" style="top:{y:.3f}%;'
                         f'left:{CENTRE - COL_W:.2f}%;'
                         f'width:{2 * COL_W:.2f}%;"></div>')
            parts.append(f'<div class="fnt ytick pd{pd_}" style="top:{y:.3f}%;'
                         f'left:{CENTRE - COL_W - 1.0:.2f}%;">'
                         f'{left // 60}:{left % 60:02d}</div>')
            t += 120.0
    radios = "".join(
        f'<input type="radio" class="pdsel" name="pdsel" id="pd-{pd_}"'
        f'{" checked" if pd_ == periods[0] else ""}>' for pd_ in periods)
    pdlabels = "".join(
        f'<label class="pdl pdl-{pd_}" for="pd-{pd_}">{pname[pd_]}</label>'
        for pd_ in periods)
    # only the selected period is displayed — everything else is hidden,
    # so a period fills the whole canvas
    period_css = "".join(
        f'.chart-wrap:has(#pd-{pd_}:checked) .pd{pd_}{{display:block;}}'
        f'.chart-wrap:has(#pd-{pd_}:checked) .pdl-{pd_}{{color:#c9ced4;'
        f'border-bottom-color:#4da3ff;}}'
        for pd_ in periods)
    heads = "".join(                          # column heads: pinned above
        f'<div class="fnt xtick" style="left:{CENTRE:.2f}%;'
        f'transform:translateX({"-100%" if side_of[team] < 0 else "0"});'
        f'padding:0 0.6cqw;">'
        f'<span style="color:{_TEAM_BRAND_COLORS.get(team, "gray")};">'
        f'{team}</span></div>'
        for team in teams)
    # SEG_W holds the widest code ("FOUL") at the label size
    SEG_W = 3.8                                    # % of container width
    for r in rects:
        pd_ = r["period"]
        col = _TEAM_BRAND_COLORS.get(r["team"], "gray")
        codes = [c for c in str(r["events"]).split() if c != "-"]
        clocks = str(r.get("times", "")).split()
        # every event of the possession, stacked OUT from the centre line
        # in the order it happened
        for n, code in enumerate(codes):
            w = SEG_W
            off = n * SEG_W
            x = CENTRE - off - w if r["dir"] < 0 else CENTRE + off
            scoring = code in ("M2", "M3", "FT")
            # no square: the fill alone marks the block, solid for a
            # score and translucent otherwise
            fill = (f"background:{col};" if scoring
                    else f"background:{col}3D;")
            if n == 0 and r["side"] == "o":
                parts.append(
                    f'<div class="pnum pd{pd_}" style="--t:{r["top"]:.3f}%;'
                    f'--h:{r["h"]:.3f}%;'
                    f'left:{_BOX_SCORE_LEFT_MARGIN * 100:.2f}%;'
                    f'color:{col};">{r["num"]}</div>')
                # the game time sits on the UPPER OUTER edge of the list
                _edge = len(codes) * SEG_W
                parts.append(
                    f'<div class="evr pd{pd_}" style="--t:{r["top"]:.3f}%;'
                    f'--h:{r["h"]:.3f}%;'
                    + (f'left:{CENTRE - _edge:.2f}%;'
                       if r["dir"] < 0 else
                       f'right:{100 - CENTRE - _edge:.2f}%;')
                    + f'">{r["start"]}  {r["dur"]}</div>')
            parts.append(
                f'<div class="psb psb-hit pd{pd_} ps{r["side"]}'
                f'{" psb-s" if scoring else " psb-n"}'
                f'{"" if r["inside"] else " psb-tiny"} ps-{r["i"]}{r["side"]}'
                f' evb-{r["i"]}{r["side"]}{n}"'
                f' style="--t:{r["top"]:.3f}%;--h:{r["h"]:.3f}%;'
                f'left:{x:.2f}%;top:{r["top"]:.3f}%;'
                f'width:{w:.2f}%;height:{r["h"]:.3f}%;{fill}">'
                # the label is always in the DOM; on a bar too short to
                # hold it, it stays hidden until the possession opens
                + (f'<span class="pslab">{code}</span>' if code else "")
                + "</div>"
)
    # ---- the box score, in the game page's own table styling ----
    # no End column — the start and the duration already say when it ran.
    # Each line carries the possession's own event list on the end, the
    # offence's then the defence's, so the table reads as the play.
    # the events follow straight after the timing. Pts/Sc are gone with
    # them: M2 / M3 / FT already say what the possession scored, and their
    # absence says it scored nothing — the columns only repeated the codes.
    head = (f'{"#":>4}  {"Team":<5}{"Per":>4}{"Start":>8}{"Dur":>6}   Events')
    max_pts = max((r["pts"] for r in rects), default=0)
    body = []
    for r in [x for x in rects if x["side"] == "o"]:
        p_ = poss.loc[r["row"]]
        pts = f'{r["pts"]:>5}'
        if r["pts"] and r["pts"] == max_pts:
            pts = f'<span class="mx-gold">{pts}</span>'
        elif not r["pts"]:
            pts = f'<span class="mx-grey">{pts}</span>'
        sc = ('<span class="mx-gold">Y</span>  ' if r["scored"]
              else '<span class="mx-red">N</span>  ')
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
            f'<span class="pd{r["period"]} pr-{r["i"]}">{r["i"] + 1:>4}  {tri}'
            f'{int(p_.period):>4}{_fmt_clock(p_.start_clock):>8}'
            f'{p_.duration_s:>5.0f}s   {ev}</span>')


    # ---- both-way hover links: rect -> row, row -> rect ----
    ev_css = ""          # the stamps are always on: nothing to reveal
    n_poss = len([x for x in rects if x["side"] == "o"])
    link_css = "".join(
        f'.chart-wrap:has(.ps-{i}o:hover) .pr-{i},'
        f'.chart-wrap:has(.ps-{i}d:hover) .pr-{i},'
        f'.chart-wrap:has(.pr-{i}:hover) .pr-{i}'
        f'{{background:#ffffff1f;}}'
        f'.chart-wrap:has(.pr-{i}:hover) .ps-{i}o,'
        f'.chart-wrap:has(.pr-{i}:hover) .ps-{i}d'
        f'{{outline:2px solid #fff;outline-offset:1px;z-index:4;}}'
        f'.chart-wrap:has(.ps-{i}o:hover) .ps-{i}o,'
        f'.chart-wrap:has(.ps-{i}o:hover) .ps-{i}d,'
        f'.chart-wrap:has(.ps-{i}d:hover) .ps-{i}o,'
        f'.chart-wrap:has(.ps-{i}d:hover) .ps-{i}d,'
        f'.chart-wrap:has(.pr-{i}:hover) .ps-{i}o,'
        f'.chart-wrap:has(.pr-{i}:hover) .ps-{i}d'
        f'{{height:max(var(--h),var(--eh))!important;'
        f'top:calc(var(--t) - (max(var(--h),var(--eh)) - var(--h))/2)'
        f'!important;z-index:5;}}'
        f'.chart-wrap:has(.ps-{i}o:hover) .ps-{i}o .pslab,'
        f'.chart-wrap:has(.ps-{i}o:hover) .ps-{i}d .pslab,'
        f'.chart-wrap:has(.ps-{i}d:hover) .ps-{i}o .pslab,'
        f'.chart-wrap:has(.ps-{i}d:hover) .ps-{i}d .pslab,'
        f'.chart-wrap:has(.pr-{i}:hover) .ps-{i}o .pslab,'
        f'.chart-wrap:has(.pr-{i}:hover) .ps-{i}d .pslab'
        f'{{display:block;}}'
        for i in range(n_poss))

    css = f"""
@font-face{{font-family:'DejaVu Sans';src:url('fonts/dejavu-sans.woff2') format('woff2');
  font-weight:normal;font-style:normal;font-display:swap;}}
@font-face{{font-family:'DejaVu Sans Mono';src:url('fonts/dejavu-mono.woff2') format('woff2');
  font-weight:normal;font-style:normal;font-display:swap;}}
html,body{{margin:0;padding:0;background:#000;}}
.chart-wrap{{position:relative;width:1200px;max-width:100%;margin:0 auto;
  container-type:inline-size;}}
.img-box{{position:relative;width:100%;aspect-ratio:{1 / PLOT_ASPECT:.4f};}}
.pbox{{position:relative;}}
.chart-wrap:has(.kb-fold:not([open])) .pbox{{display:none;}}
summary.ktitle{{color:{_PANEL_TITLE_COLOR};font-family:'DejaVu Sans',sans-serif;
  {_TITLE_FONT_CSS}cursor:pointer;list-style:none;position:relative;
  display:inline-block;margin-left:{_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;}}
summary.ktitle::-webkit-details-marker{{display:none;}}
summary.ktitle:hover{{color:#c9ced4;}}
.kb-fold>summary.ktitle::before{{content:'\\25b8 ';color:#4da3ff;}}
.kb-fold[open]>summary.ktitle::before{{content:'\\25be ';color:#4da3ff;}}
.kb-fold{{margin:1.65cqw 0 1.9cqw;}}
/* furniture, same treatment as the karma panels */
.fnl{{position:absolute;height:0;border-top:1px solid #FFFFFF26;
  pointer-events:none;}}
.fnt{{position:absolute;color:{_BOX_HEAD_COLOR};font-family:'DejaVu Sans',sans-serif;
  font-size:{TICK_CQW:.3f}cqw;pointer-events:none;white-space:nowrap;}}
.xtick{{font-size:{HEAD_CQW:.3f}cqw;}}
.xtick{{transform:translate(0,-100%);}}
.ytick{{transform:translate(-100%,-50%);}}
/* possession rects */
.psb{{position:absolute;border-radius:1px;}}
/* the team's own possession count, level with the possession, left-aligned
   where the clock column starts */
.pnum{{position:absolute;font-family:'DejaVu Sans Mono',monospace;
  font-size:{LAB_CQW:.3f}cqw;pointer-events:none;
  top:calc(var(--t) - (max(var(--h),var(--eh)) - var(--h))/2);
  height:max(var(--h),var(--eh));display:flex;align-items:center;}}
/* the event's own clock and the possession's length, hung on the centre
   line and running outward on that event's side */
/* the game time hangs on the UPPER OUTER corner of the event list */
.evr{{position:absolute;color:{_BOX_HEAD_COLOR};
  font-family:'DejaVu Sans Mono',monospace;font-size:{LAB_CQW:.3f}cqw;
  white-space:pre;z-index:7;pointer-events:none;
  top:calc(var(--t) - (max(var(--h),var(--eh)) - var(--h))/2);
  transform:translateY(-100%);}}
/* --eh is one line of the code type. A possession too short to letter
   opens to that height while hovered — centred on its own middle, so it
   stays over the moment it happened — and collapses again on exit */
.chart-wrap{{--eh:{LAB_CQW * 1.45:.3f}cqw;}}
.psb-tiny .pslab{{display:none;}}
.pslab{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
  font-family:'DejaVu Sans Mono',monospace;font-size:{LAB_CQW:.3f}cqw;
  color:#000;pointer-events:none;white-space:nowrap;}}
/* a possession too short to hold the digit inside hangs it at its base —
   the left edge it grows from — where the column is always clear */
.pslab-base{{top:50%;left:50%;transform:translate(-50%,-50%);
  color:#fff;text-shadow:0 0 3px #000,0 0 3px #000,0 0 3px #000;}}
.pbl,.pbr{{left:50%;right:auto;}}
.psb-n .pslab{{color:{_BOX_HTML_TEXT};}}
/* the box score: the game page's own table styling */
.bx{{position:relative;font-family:'DejaVu Sans Mono',monospace;
  color:{_BOX_HTML_TEXT};{_BOX_FONT_CSS}white-space:pre;
  padding:0 0 12px {_BOX_SCORE_LEFT_MARGIN * 100:.3f}%;}}
.bx .bx-head{{color:{_BOX_HEAD_COLOR};}}
.bx .bxs{{position:relative;display:inline-block;}}
.mx-gold{{color:{_BOX_GOLD};}}
.mx-red{{color:{_BOX_RED};}}
.mx-grey{{color:{_BOX_GREY};}}
.bx-fold>summary{{display:block;list-style:none;cursor:pointer;}}
.bx-fold>summary::-webkit-details-marker{{display:none;}}
.bx-fold .bx.bx-title{{padding-bottom:0;line-height:normal;
  font-family:'DejaVu Sans',sans-serif;{_TITLE_FONT_CSS}}}
.bx-fold>summary .bx-head::before{{content:'\\25b8 ';color:#4da3ff;}}
.bx-fold[open]>summary .bx-head::before{{content:'\\25be ';color:#4da3ff;}}
.bx-fold>summary .bx-head:hover{{color:#c9ced4;}}
.bx-flow{{position:relative;margin-top:1.5cqw;}}
/* both blocks scroll inside their own window: the plot is 3,600px tall
   and the table 227 rows, so the page would otherwise run for metres */
.pshead{{position:relative;height:{HEAD_CQW * 1.5:.2f}cqw;}}
.pshead .xtick{{top:0;transform:none;}}
.pscroll{{position:relative;height:62vh;min-height:320px;overflow-y:auto;
  overflow-x:hidden;scrollbar-gutter:stable;}}
.bxscroll{{position:relative;height:34vh;min-height:180px;overflow-y:auto;
  overflow-x:hidden;scrollbar-gutter:stable;}}
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
{ev_css}
{period_css}
/* one period at a time: everything period-tagged hides until its tab is
   picked, so the selected period gets the entire canvas */
.pd1,.pd2,.pd3,.pd4,.pd5,.pd6,.pd7,.pd8{{display:none;}}
.pdsel{{position:absolute;opacity:0;pointer-events:none;}}
/* the period selectors live in the LEFT MARGIN, stacked down beside the
   plot, level with the top of the canvas */
/* the period selectors: one line, hard against the left margin */
.pdside{{position:relative;left:0;display:flex;gap:1.1cqw;
  padding:0 0 0.5cqw 0;
  font-family:'DejaVu Sans',sans-serif;font-size:{HEAD_CQW:.3f}cqw;}}
.pdl{{color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;
  padding:0 0.2cqw 0.15cqw;}}
.pdl:hover{{color:#9BA3AD;}}
"""

    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Possessions — {game_id}</title>
<style>{css}</style></head><body>
<div class="chart-wrap">
<details class="kb-fold" open><summary class="ktitle">Possessions</summary></details>
<div class="pbox">
{radios}
<div class="pdside">{pdlabels}</div>
<div class="pshead">{heads}</div>
<div class="pscroll"><div class="img-box">{''.join(parts)}</div></div>
</div>
<div class="bx-flow"><details class="bx-fold" open><summary>
<div class="bx bx-title"><span class="bx-head">Possessions box score</span></div>
</summary>
<div class="bx bx-headrow"><span class="bx-head">{html.escape(head)}</span></div>
<div class="bxscroll"><div class="bx"><span class="bxs">{''.join(body)}</span></div></div>
</details></div>
</div>
</body></html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc)
    return {"possessions": len([x for x in rects if x["side"] == "o"]),
            "bars": len(rects), "teams": teams, "date": date,
            "labelled": labelled, "unlabelled_scored":
                sum(1 for r in rects if r["scored"] and not r["label"]),
            "clamped": clamped, "bytes": out_path.stat().st_size}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("game_id", nargs="?", default="0022500001")
    ap.add_argument("-o", "--out", type=Path,
                    default=Path("outputs/test_page.html"))
    args = ap.parse_args()
    info = build(args.game_id, args.out)
    print(f"{args.out}: {info['possessions']} possessions "
          f"({' / '.join(info['teams'])}), {info['bytes'] / 1024:.0f}KB")
    print(f"  labelled {info['labelled']}, "
          f"scored-but-too-narrow {info['unlabelled_scored']}, "
          f"width-clamped {info['clamped']}")


if __name__ == "__main__":
    main()
