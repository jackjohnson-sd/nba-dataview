#!/usr/bin/env python3
"""Build test_page.html — the possessions section on a page of its own.

The section itself lives in `nba_pbp.possessions_section`, which the game
page also renders, so what you see here is byte-identical to what lands at
the foot of a game page. This script only supplies the shell the game page
would otherwise provide: the document, the two @font-face declarations, the
black background and the `.chart-wrap` container that everything sizes
against (`cqw`).

    .venv/bin/python scripts/possessions_page.py [GAME_ID] [-o PATH]
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

from nba_pbp.possessions_section import build_section
from nba_pbp.plotting import (_BOX_FONT_CSS, _BOX_GOLD, _BOX_GREY,
                              _BOX_HEAD_COLOR, _BOX_HTML_TEXT, _BOX_RED,
                              _BOX_SCORE_LEFT_MARGIN, _PANEL_TITLE_COLOR,
                              _TITLE_FONT_CSS)

# the host-page rules the section deliberately does NOT carry (the game
# page already defines every one of them); reproduced here so the
# standalone page renders the same block the same way
SHELL_CSS = f"""
@font-face{{font-family:'DejaVu Sans';src:url('fonts/dejavu-sans.woff2') format('woff2');
  font-weight:normal;font-style:normal;font-display:swap;}}
@font-face{{font-family:'DejaVu Sans Mono';src:url('fonts/dejavu-mono.woff2') format('woff2');
  font-weight:normal;font-style:normal;font-display:swap;}}
html,body{{margin:0;padding:0;background:#000;}}
.chart-wrap{{position:relative;width:1200px;max-width:100%;margin:0 auto;
  container-type:inline-size;}}
.kbox{{position:relative;}}
.ktitle{{position:absolute;left:7.6%;color:{_PANEL_TITLE_COLOR};
  font-family:'DejaVu Sans',sans-serif;{_TITLE_FONT_CSS}
  white-space:nowrap;pointer-events:none;}}
.kb-fold>summary.ktitle{{pointer-events:auto;cursor:pointer;list-style:none;}}
.kb-fold>summary::-webkit-details-marker{{display:none;}}
.kb-fold>summary.ktitle:hover{{color:#c9ced4;}}
.kb-fold>summary.ktitle::before{{content:'\\25b8 ';color:#4da3ff;}}
.kb-fold[open]>summary.ktitle::before{{content:'\\25be ';color:#4da3ff;}}
.kbox:has(> .kb-fold:not([open])){{height:40px !important;min-height:0 !important;
  margin-bottom:0;}}
.kbox:has(> .kb-fold:not([open])) > .kb-fold > summary.ktitle{{top:0 !important;}}
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
.bx-flow:has(> .bx-fold:not([open])){{height:40px;}}
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("game_id", nargs="?", default="0022500001")
    ap.add_argument("-o", "--out", type=Path,
                    default=Path("outputs/test_page.html"))
    args = ap.parse_args()

    csv = glob.glob(f"outputs/*/*/csv/pbp_{args.game_id}.csv")
    if not csv:
        raise SystemExit(f"no play-by-play csv for {args.game_id}")
    sec = build_section(csv[0], args.game_id, open_default=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        f"<title>Possessions — {args.game_id}</title>\n"
        f"<style>{SHELL_CSS}{sec.css}</style></head><body>\n"
        f"{sec.html}\n</body></html>\n")

    info = sec.info
    size = args.out.stat().st_size
    print(f"{args.out}: {info['possessions']} possessions "
          f"({' / '.join(info['teams'])}), {size / 1024:.0f}KB")
    print(f"  labelled {info['labelled']}, "
          f"scored-but-too-narrow {info['unlabelled_scored']}, "
          f"height-clamped {info['clamped']}")


if __name__ == "__main__":
    main()
