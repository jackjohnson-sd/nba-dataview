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
                              _MONO_ADVANCE_EM, _PANEL_TITLE_COLOR,
                              _TEAM_BRAND_COLORS, _TITLE_FONT_CSS)
from nba_pbp.possessions import compute_possessions

# VERTICAL timeline: game clock runs down the page, the two teams sit
# side by side. Going vertical buys pixels — the plot is 3x the container
# WIDE instead of a fifth of it, so a second of game clock is worth ~3x
# more space and possessions become tall enough to label.
PLOT_T, PLOT_B = 1.0, 97.0          # top/bottom of the time axis, % of height
COL_L = 6.5                         # left spine (clock labels sit left of it)
COL_W = 43.5                        # one team column, % of container width
COL_GAP = 4.0
PLOT_ASPECT = 3.0                   # height / width of the .img-box


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

    # period boundaries for the x ticks, in elapsed seconds
    ticks, labels = [0.0], ["Q1"]
    for p in sorted(poss["period"].unique())[:-1]:
        end = float(poss[poss.period == p]["end_elapsed"].max())
        ticks.append(end)
        nxt = p + 1
        labels.append(f"Q{nxt}" if nxt <= 4 else f"OT{nxt - 4}")
    ticks.append(total)
    labels.append("END")

    def x_of(sec: float) -> float:
        return PLOT_L + (PLOT_R - PLOT_L) * (sec / total)

    # ---- rects, one COLUMN per team, with a real no-overlap pass ----
    box_h_px = 1200 * PLOT_ASPECT               # the .img-box at 1200 wide
    px_per_s = (PLOT_B - PLOT_T) / 100 * box_h_px / total
    MIN_H = 0.22 / PLOT_ASPECT                  # % of height, ~2.6px
    # a digit is ~10px tall; a bar shorter than that cannot hold one
    label_h_pct = (10.3 * 1.15) / box_h_px * 100
    rects, clamped, labelled = [], 0, 0
    col_of = {t: COL_L + i * (COL_W + COL_GAP) for i, t in enumerate(teams)}

    def y_of(sec: float) -> float:
        return PLOT_T + (PLOT_B - PLOT_T) * (sec / total)

    span_by_row = {}
    for team in teams:
        rows = poss[poss.team == team].sort_values("start_elapsed")
        ys = [(y_of(r.start_elapsed), y_of(r.end_elapsed), idx)
              for idx, r in rows.iterrows()]
        for k, (y0, y1, idx) in enumerate(ys):
            h = max(y1 - y0, MIN_H)
            nxt = ys[k + 1][0] if k + 1 < len(ys) else 100.0
            if y0 + h > nxt:                       # would run into the
                h = max(nxt - y0, 0.01)            # next one down: trim
                clamped += 1
            span_by_row[idx] = (y0, h)
    # number and list possessions in GAME order
    for i, (idx, r) in enumerate(
            poss.sort_values("start_elapsed").iterrows()):
        y0, h = span_by_row[idx]
        show_label = r.points > 0 and h >= label_h_pct
        labelled += int(show_label)
        rects.append({
            "i": i, "team": r.team, "top": y0, "h": h,
            "left": col_of[r.team],
            "scored": r.scored == "Y", "pts": int(r.points),
            "label": str(int(r.points)) if show_label else "",
            "readout": (f"{r.team}  {_fmt_clock(r.start_clock)}"
                        f" - {_fmt_clock(r.end_clock)}"
                        f"  {r.duration_s:.0f}s"
                        f"  {'scored ' + str(int(r.points)) if r.points else 'no score'}"),
            "row": int(idx),
        })

    # ---- the plot ----
    parts = []
    for tx, lab in zip(ticks, labels):        # period rules, running across
        parts.append(f'<div class="fnl" style="top:{y_of(tx):.3f}%;'
                     f'left:{COL_L:.2f}%;width:{2 * COL_W + COL_GAP:.2f}%;">'
                     "</div>")
        parts.append(f'<div class="fnt ytick" style="top:{y_of(tx):.3f}%;'
                     f'left:{COL_L - 1.0:.2f}%;">{lab}</div>')
    heads = "".join(                          # column heads: pinned above
        f'<div class="fnt xtick" style="left:{col_of[team]:.2f}%;">'
        f'<span style="color:{_TEAM_BRAND_COLORS.get(team, "gray")};">'
        f'{team}</span></div>'
        for team in teams)
    for r in rects:
        col = _TEAM_BRAND_COLORS.get(r["team"], "gray")
        # points now carry the WIDTH (1/2/3+ = a third, two thirds, all of
        # the column); duration is the height, as the clock runs down
        tier = {0: 0.18, 1: 0.40, 2: 0.68}.get(r["pts"], 1.0)
        w = COL_W * tier
        style = (f'left:{r["left"]:.2f}%;top:{r["top"]:.3f}%;'
                 f'width:{w:.2f}%;height:{r["h"]:.3f}%;')
        cls = "psb psb-hit" + (" psb-s" if r["scored"] else " psb-n")
        fill = (f"background:{col};" if r["scored"]
                else f"background:{col}2E;box-shadow:inset 0 0 0 1px {col}80;")
        parts.append(
            f'<div class="{cls} ps-{r["i"]}" style="{style}{fill}">'
            + (f'<span class="pslab">{r["label"]}</span>' if r["label"] else "")
            + "</div>"
            f'<div class="psro psro-{r["i"]}" '
            f'style="left:{r["left"]:.2f}%;top:{r["top"]:.3f}%;">'
            f'{html.escape(r["readout"])}</div>')

    # ---- the box score, in the game page's own table styling ----
    head = (f'{"#":>4}  {"Team":<5}{"Per":>4}{"Start":>8}{"End":>8}'
            f'{"Dur":>6}{"Pts":>5}  Scored')
    max_pts = max((r["pts"] for r in rects), default=0)
    body = []
    for r in rects:
        p = poss.loc[r["row"]]
        pts = f'{r["pts"]:>5}'
        if r["pts"] and r["pts"] == max_pts:
            pts = f'<span class="mx-gold">{pts}</span>'
        elif not r["pts"]:
            pts = f'<span class="mx-grey">{pts}</span>'
        sc = ('<span class="mx-gold">Y</span>' if r["scored"]
              else '<span class="mx-red">N</span>')
        tri = (f'<span style="color:'
               f'{_TEAM_BRAND_COLORS.get(r["team"], "gray")};">'
               f'{r["team"]:<5}</span>')
        body.append(
            f'<span class="pr-{r["i"]}">{r["i"] + 1:>4}  {tri}'
            f'{int(p.period):>4}{_fmt_clock(p.start_clock):>8}'
            f'{_fmt_clock(p.end_clock):>8}{p.duration_s:>5.0f}s{pts}  {sc}</span>')

    # ---- both-way hover links: rect -> row, row -> rect ----
    link_css = "".join(
        f'.chart-wrap:has(.ps-{i}:hover) .pr-{i},'
        f'.chart-wrap:has(.pr-{i}:hover) .pr-{i}'
        f'{{background:#ffffff1f;}}'
        f'.chart-wrap:has(.pr-{i}:hover) .ps-{i}'
        f'{{outline:2px solid #fff;outline-offset:1px;z-index:4;}}'
        f'.chart-wrap:has(.ps-{i}:hover) .psro-{i}{{display:block;}}'
        for i in range(len(rects)))

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
  font-size:0.78cqw;pointer-events:none;white-space:nowrap;}}
.xtick{{transform:translate(0,-100%);}}
.ytick{{transform:translate(-100%,-50%);}}
/* possession rects */
.psb{{position:absolute;border-radius:1px;}}
.pslab{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);
  font-family:'DejaVu Sans Mono',monospace;font-size:0.86cqw;color:#000;
  pointer-events:none;}}
.psb-n .pslab{{color:{_BOX_HTML_TEXT};}}
.psro{{display:none;position:absolute;color:{_BOX_HTML_TEXT};background:#000;
  padding:2px 6px;border-radius:4px;font-family:'DejaVu Sans Mono',monospace;
  {_BOX_FONT_CSS}white-space:pre;z-index:6;pointer-events:none;
  transform:translateY(-100%);box-shadow:0 0 0 2px #000;}}
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
.pshead{{position:relative;height:1.4cqw;}}
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
"""

    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Possessions — {game_id}</title>
<style>{css}</style></head><body>
<div class="chart-wrap">
<details class="kb-fold" open><summary class="ktitle">Possessions</summary></details>
<div class="pbox">
<div class="pshead">{heads}</div>
<div class="pscroll"><div class="img-box">{''.join(parts)}</div></div>
</div>
<div class="bx-flow"><details class="bx-fold" open><summary>
<div class="bx bx-title"><span class="bx-head">Possessions box score</span></div>
</summary>
<div class="bx bx-headrow"><span class="bx-head">{html.escape(head)}</span></div>
<div class="bxscroll"><div class="bx"><span class="bxs">{chr(10).join(body)}</span></div></div>
</details></div>
</div>
</body></html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc)
    return {"possessions": len(rects), "teams": teams, "date": date,
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
