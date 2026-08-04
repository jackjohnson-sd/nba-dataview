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

# the plot's own box, in container-width percent
PLOT_L, PLOT_R = 7.6, 98.0          # left spine matches the karma panels
ROW_H = 34.0                        # one team row, % of the plot's height
ROW_GAP = 8.0
PLOT_ASPECT = 0.20                  # height / width of the .img-box


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

    # ---- rects, one row per team, with a real no-overlap pass ----
    # the minimum width keeps a 3-second possession visible; where the
    # floor would run a rect into its neighbour it is trimmed instead
    MIN_W = 0.22                     # % of container width
    # LABELS DO NOT FIT AT THIS SCALE. A digit needs ~10px; the widest
    # possession in a whole game is ~13px and the typical one 4-5px, so
    # text would be legible on a handful of rects and absent from the
    # rest — worse than none. Points are encoded as HEIGHT instead (1/2/3+
    # points = a third, two thirds, all of the row), which reads at any
    # width, and the exact line stays one hover away.
    label_w = 1e9
    rects, clamped, labelled = [], 0, 0
    row_of = {t: ROW_GAP + i * (ROW_H + ROW_GAP) for i, t in enumerate(teams)}
    # walk each team's row in time order so a rect can be trimmed against
    # the NEXT one in its own row — that is what makes overlap impossible
    span_by_row = {}
    for team in teams:
        rows = poss[poss.team == team].sort_values("start_elapsed")
        xs = [(x_of(r.start_elapsed), x_of(r.end_elapsed), idx)
              for idx, r in rows.iterrows()]
        for k, (x0, x1, idx) in enumerate(xs):
            w = max(x1 - x0, MIN_W)
            nxt = xs[k + 1][0] if k + 1 < len(xs) else 100.0
            if x0 + w > nxt:                       # would run into its
                w = max(nxt - x0, 0.04)            # neighbour: trim it
                clamped += 1
            span_by_row[idx] = (x0, w)
    # number and list possessions in GAME order, not team order
    for i, (idx, r) in enumerate(
            poss.sort_values("start_elapsed").iterrows()):
        x0, w = span_by_row[idx]
        show_label = r.points > 0 and w >= label_w
        labelled += int(show_label)
        rects.append({
            "i": i, "team": r.team, "top": row_of[r.team], "left": x0,
            "w": w, "scored": r.scored == "Y", "pts": int(r.points),
            "label": str(int(r.points)) if show_label else "",
            "readout": (f"{r.team}  {_fmt_clock(r.start_clock)}"
                        f" - {_fmt_clock(r.end_clock)}"
                        f"  {r.duration_s:.0f}s"
                        f"  {'scored ' + str(int(r.points)) if r.points else 'no score'}"),
            "row": int(idx),
        })

    # ---- the plot ----
    parts = []
    for tx, lab in zip(ticks, labels):        # grid + x tick labels
        parts.append(f'<div class="fnl" style="left:{x_of(tx):.3f}%;'
                     f'top:0;height:100%;"></div>')
        parts.append(f'<div class="fnt xtick" style="left:{x_of(tx):.3f}%;'
                     f'top:100%;">{lab}</div>')
    for ti, team in enumerate(teams):         # y labels: the two teams
        row_top = ROW_GAP + ti * (ROW_H + ROW_GAP)
        parts.append(
            f'<div class="fnt ytick" style="left:{PLOT_L - 0.6:.2f}%;'
            f'top:{row_top + ROW_H / 2:.2f}%;'
            f'color:{_TEAM_BRAND_COLORS.get(team, "gray")};">{team}</div>')
    for r in rects:
        col = _TEAM_BRAND_COLORS.get(r["team"], "gray")
        # height carries the points; an empty possession stays a thin
        # baseline sliver so the timeline still shows it happened
        tier = {0: 0.18, 1: 0.40, 2: 0.68}.get(r["pts"], 1.0)
        h = ROW_H * tier
        style = (f'left:{r["left"]:.3f}%;'
                 f'top:{r["top"] + ROW_H - h:.2f}%;'
                 f'width:{r["w"]:.3f}%;height:{h:.2f}%;')
        cls = "psb psb-hit" + (" psb-s" if r["scored"] else " psb-n")
        fill = (f"background:{col};" if r["scored"]
                else f"background:{col}2E;box-shadow:inset 0 0 0 1px {col}80;")
        parts.append(
            f'<div class="{cls} ps-{r["i"]}" style="{style}{fill}">'
            + (f'<span class="pslab">{r["label"]}</span>' if r["label"] else "")
            + "</div>"
            f'<div class="psro psro-{r["i"]}" '
            f'style="left:{PLOT_L:.2f}%;top:-1.5%;">{html.escape(r["readout"])}</div>')

    # ---- the box score, in the game page's own table styling ----
    head = (f'{"#":>4}  {"Team":<5}{"Per":>4}{"Start":>8}{"End":>8}'
            f'{"Dur":>6}{"Pts":>5}  Scored')
    max_pts = max((r["pts"] for r in rects), default=0)
    max_dur = max((r["w"] for r in rects), default=0)
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
.fnl{{position:absolute;width:0;border-left:1px solid #FFFFFF26;
  pointer-events:none;}}
.fnt{{position:absolute;color:{_BOX_HEAD_COLOR};font-family:'DejaVu Sans',sans-serif;
  font-size:0.78cqw;pointer-events:none;white-space:nowrap;}}
.xtick{{transform:translate(-50%,4px);}}
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
  transform:translateY(-100%);}}
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
{link_css}
"""

    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Possessions — {game_id}</title>
<style>{css}</style></head><body>
<div class="chart-wrap">
<details class="kb-fold" open><summary class="ktitle">Possessions</summary></details>
<div class="pbox"><div class="img-box">{''.join(parts)}</div></div>
<div class="bx-flow"><details class="bx-fold" open><summary>
<div class="bx bx-title"><span class="bx-head">Possessions box score</span></div>
</summary>
<div class="bx"><span class="bxs"><span class="bx-head">{html.escape(head)}</span>
{chr(10).join(body)}</span></div>
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
