"""3D shot chart: game time x player x shot distance, colored by make/miss."""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap, to_hex
from matplotlib.ticker import FixedFormatter, FixedLocator, MaxNLocator, MultipleLocator
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)

_CLOCK_RE = re.compile(r"PT(\d+)M([\d.]+)S")
_REGULATION_PERIOD_SECONDS = 12 * 60
_OT_PERIOD_SECONDS = 5 * 60
_PANE_COLOR = (0.12, 0.12, 0.12, 1.0)
_ELEV = 15
_PROJECTION_OFFSET = 0

# saturated, high-contrast colors chosen to pop against a black background —
# tab10/tab20 include muted browns/olives that wash out on dark_background
_VIVID_COLORS = [
    "#2EEAFF", "#FF5E55", "#5DFF3E", "#FFDC2E", "#FF2EFF",
    "#FFA12E", "#937DFF", "#2EFFAE", "#FF3EA6", "#62E6D8",
    "#FFB192", "#BCFF54", "#46A4FF", "#FF84C2", "#FFEFA0",
    "#C674DB", "#2EFBAC", "#F39797", "#9DD7FB", "#FFFFFF",
]


def _vivid_cmap(n_players: int) -> ListedColormap:
    colors = [_VIVID_COLORS[i % len(_VIVID_COLORS)] for i in range(n_players)]
    return ListedColormap(colors)


# --- HTML-only graphic output -----------------------------------------
# Every chart this module emits is an HTML page; matplotlib figures are
# rendered to SVG (never PNG) and embedded as data URIs.

def _fig_svg(fig, transparent: bool = False, tight: bool = False,
             text_as_paths: bool = False) -> str:
    """The figure rendered to SVG markup.

    By default text is emitted as real SVG <text> (svg.fonttype
    "none"), an order of magnitude smaller than glyph outlines on
    text-heavy figures — correct ONLY when the page provides the exact
    DejaVu fonts via @font-face and the SVG is INLINED in the document
    (Chrome refuses to load fonts, even data URIs, inside SVG used as an
    image). For self-contained SVGs embedded via <img>, pass
    `text_as_paths=True` so the text is baked into vector outlines."""
    import io

    buf = io.BytesIO()
    kwargs = {"format": "svg", "dpi": 150}
    if tight:
        kwargs["bbox_inches"] = "tight"
    if transparent:
        kwargs["transparent"] = True
    else:
        kwargs["facecolor"] = fig.get_facecolor()
    with plt.rc_context({"svg.fonttype": "path" if text_as_paths else "none"}):
        fig.savefig(buf, **kwargs)
    import re

    svg = buf.getvalue().decode("utf-8")
    if not text_as_paths:
        # matplotlib's <text> carries no whitespace directive, and XML
        # collapses space runs — which shreds the monospace box score
        # overlays (mostly-blank lines positioned by their spaces)
        svg = svg.replace("<text ", '<text xml:space="preserve" ')
    # strip inter-tag whitespace (only all-whitespace text nodes match,
    # and those render nothing anyway)
    return re.sub(r">\s+<", "><", svg)


def _svg_data_uri(svg_text: str) -> str:
    """URL-encoded (NOT base64) SVG data URI. Base64 inflates the bytes
    by a third and gzips poorly; path-heavy SVG needs almost no escaping
    when embedded as text. Also drops the XML metadata block, rounds
    matplotlib's 6-decimal coordinates to 2 (sub-pixel at 150dpi), and
    swaps attribute quotes to single so the URI can sit inside CSS
    url("...") / src="..." unescaped.

    Three extra squeezes (~12% smaller, pixel-identical): matplotlib's
    verbose element ids (``DejaVuSans-30``, ``p1a2b3c4``) are renamed to
    short tokens (a, b, ...) in both the ``id=`` and every ``#ref``; the
    ``xlink:`` prefix is dropped (SVG2 ``href``); and the thousands of
    glyph ``<use>`` x/y positions are rounded to whole pixels."""
    svg = re.sub(r"<metadata>.*?</metadata>", "", svg_text, flags=re.S)
    svg = re.sub(r"[\n\r\t]+", " ", svg)

    def _round(m):
        s = format(float(m.group()), ".2f").rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s

    svg = re.sub(r"-?\d+\.\d{3,}", _round, svg)

    # short ids: rename every id and its #references (longest first so
    # one id is never a prefix of another)
    def _short(k):
        s, k = "", k + 1
        while k:
            k, r = divmod(k - 1, 52)
            s = _ID_ALPHABET[r] + s
        return s
    ids = list(dict.fromkeys(re.findall(r'id="([^"]+)"', svg)))
    mapping = {old: _short(i) for i, old in enumerate(ids)}
    for old in sorted(mapping, key=len, reverse=True):
        new = mapping[old]
        svg = (svg.replace(f'id="{old}"', f'id="{new}"')
                  .replace(f'#{old}"', f'#{new}"')
                  .replace(f'#{old})', f'#{new})'))
    svg = svg.replace("xlink:href", "href")

    def _round_use(m):
        return re.sub(r'(x|y)="(-?\d+)\.\d+"', r'\1="\2"', m.group())
    svg = re.sub(r"<use[^>]*>", _round_use, svg)

    svg = svg.replace("'", "&apos;").replace('"', "'")
    for ch, enc in (("%", "%25"), ("#", "%23"), ("<", "%3C"), (">", "%3E")):
        svg = svg.replace(ch, enc)
    return "data:image/svg+xml," + svg


_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _save_fig_html(fig, output_path: Path, title: str, alt: str) -> Path:
    """Save a figure as a standalone dark HTML page with the chart
    embedded as a single SVG image. A `.png` output path is quietly
    retargeted to `.html` — this package no longer emits raster files."""
    if output_path.suffix.lower() in (".png", ".svg"):
        output_path = output_path.with_suffix(".html")
    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">\n"
        f"<title>{title}</title>\n"
        "<style>html,body{margin:0;padding:0;border:0;background:black;}"
        "img{display:block;vertical-align:top;max-width:100%;height:auto;margin:0 auto;}"
        "</style>\n</head>\n<body>\n"
        f"<img src=\"{_svg_data_uri(_fig_svg(fig, tight=True, text_as_paths=True))}\" alt=\"{alt}\">\n"
        "</body></html>\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


# lineup colors: a 20-slot wheel generated in OKLCH — even 18° hue coverage,
# hue-dependent lightness (brighter through yellow/green, dimmer through
# blue/violet where sRGB holds chroma at lower lightness), chroma near the
# sRGB gamut edge — then greedily ordered so consecutive slots, which land on
# chronologically adjacent stints in the lineup panel, stay far apart under
# all three Machado-2009 colorblindness simulations (worst adjacent ΔE 49 vs
# the ≥12 target; every slot ≥3:1 WCAG contrast on the black background)
_LINEUP_COLORS = [
    "#2699E0", "#F8972C", "#29A7CD", "#E8AA2E", "#2CB2C0",
    "#D4BA2F", "#2FBDB3", "#976DEC", "#F98856", "#4588F6",
    "#F97A70", "#7378F6", "#F9688B", "#B6C630", "#EA62AA",
    "#84D048", "#D362C6", "#34D375", "#B766DC", "#32C89F",
]


# each team's primary brand color — used by the Karma panel's axes and
# score lines
_TEAM_BRAND_COLORS = {
    "ATL": "#E03A3E", "BOS": "#007A33", "BKN": "#FFFFFF", "CHA": "#00788C",
    "CHI": "#CE1141", "CLE": "#860038", "DAL": "#00538C", "DEN": "#4D90CD",
    "DET": "#C8102E", "GSW": "#1D428A", "HOU": "#CE1141", "IND": "#FDBB30",
    "LAC": "#C8102E", "LAL": "#552583", "MEM": "#5D76A9", "MIA": "#F9A01B",
    "MIL": "#00471B", "MIN": "#78BE20", "NOP": "#C8102E", "NYK": "#F58426",
    "OKC": "#007AC1", "ORL": "#0077C0", "PHI": "#006BB6", "PHX": "#E56020",
    "POR": "#E03A3E", "SAC": "#5A2D81", "SAS": "#C4CED4", "TOR": "#CE1141",
    "UTA": "#F9A01B", "WAS": "#E31837",
}


def _lineup_cmap(n_lineups: int) -> ListedColormap:
    colors = [_LINEUP_COLORS[i % len(_LINEUP_COLORS)] for i in range(n_lineups)]
    return ListedColormap(colors)


# one shared style for every panel/box score title (team panels, player
# charts, lineup panels, lineup box scores) — player chart titles use this
# size/placement too, but keep their player color
_PANEL_TITLE_FONTSIZE = 13.0 * (8 / 12) * ((0.86 - 0.10) / (0.98 - 0.06)) * 1.15 * 1.15

# ---------------------------------------------------------------------------
# Game-page typography — the ONE place that decides every box score-ish
# text on the page. The page is built around a 1200px figure (8in x 150dpi
# = _PAGE_W_PX), and the HTML sizes in cqw resolve against that same width,
# so 1cqw == 12px at full size and the baked (matplotlib) and HTML sides
# stay in lockstep: change a value here and both move together.
_PAGE_DPI = 150
_PAGE_W_PX = 1200
_BOX_FONT_CQW = 1.54        # box scores, lineup tables, hover popups
_BOX_LINE_HEIGHT = 1.5      # shared line-height / matplotlib linespacing
_TITLE_WEIGHT_HTML = 300    # browser sans renders heavier than the baked
                            # DejaVu paths; 300 brings HTML titles level
# the one canonical HTML box-score palette, shared by the game-page
# lineup box, the team-season card, and the league page so every box
# score looks the same: gray body, unbold light header, and the same
# league-leader-gold / worst-red / dnp-gray highlights.
_BOX_HEAD_COLOR = "#e0e0e0"
_BOX_GOLD, _BOX_RED, _BOX_GREY = "goldenrod", "#ff4d4d", "#808080"
_BOX_HTML_TEXT = "#c0c0c0"  # the HTML tables' body text: the system
                            # monospace has no light weight, so a dimmed
                            # lightgray matches the thinner baked glyphs
_READOUT_LINES = 5          # popup: header, values, players, in, out
_READOUT_PAD_CQW = 1.95     # popup padding/shadow allowance in the gaps

# derived — use these, never re-derive at a call site
_BOX_FONT_PT = _BOX_FONT_CQW / 100 * _PAGE_W_PX * 72 / _PAGE_DPI   # 8.87pt
_TITLE_FONT_CQW = _PANEL_TITLE_FONTSIZE * (_PAGE_DPI / 72) / (_PAGE_W_PX / 100)
_BOX_LINE_FRAC = _BOX_FONT_CQW / 100 * _BOX_LINE_HEIGHT  # one line, as a
                                                         # fraction of page width
_MONO_ADVANCE_EM = 0.6024  # DejaVu Sans Mono per-character advance. Size
                           # monospace-row widths as chars * advance —
                           # Agg ink extents under-measure the rendered
                           # width by ~1 char over a 100-char line, which
                           # clipped the PF column out of the row rects
_BOX_FONT_CSS = f"font-size:{_BOX_FONT_CQW:.2f}cqw;line-height:{_BOX_LINE_HEIGHT:g};"
_TITLE_FONT_CSS = (f"font-size:{_TITLE_FONT_CQW:.2f}cqw;"
                   f"font-weight:{_TITLE_WEIGHT_HTML};")
# ---------------------------------------------------------------------------


_PANEL_TITLE_COLOR = "lightgray"

# the title block (matchup/date/venue) and per-period linescore at the top of
# the page — 80% of their original 15pt size
_HEADER_FONTSIZE = 15 * 0.8

# left edge, in figure-fraction, shared by every left-aligned header/box score
# text block and every gridspec so their columns all start at the same x
_HEADER_LEFT_MARGIN = 0.10
# further-left edge for the per-team box score, so it lines up with the team
# panel's "+/-" y-axis label (which sits left of the axes spine at 0.10)
# rather than with the spine itself
_BOX_SCORE_LEFT_MARGIN = 0.031


def _period_length_seconds(period: int) -> int:
    return _REGULATION_PERIOD_SECONDS if period <= 4 else _OT_PERIOD_SECONDS


def _game_seconds(period: int, clock: str) -> float:
    minutes, seconds = _CLOCK_RE.match(clock).groups()
    remaining = int(minutes) * 60 + float(seconds)
    elapsed_before = sum(_period_length_seconds(p) for p in range(1, period))
    return elapsed_before + (_period_length_seconds(period) - remaining)


def _period_label(period: int) -> str:
    return f"Q{period}" if period <= 4 else f"OT{period - 4}"


def _quarter_ticks(max_period: int) -> tuple[list[float], list[str]]:
    """Tick at the start of each period, plus one final tick at game end."""
    positions = []
    labels = []
    cumulative = 0
    for period in range(1, max_period + 1):
        positions.append(cumulative / 60)
        labels.append(_period_label(period))
        cumulative += _period_length_seconds(period)
    positions.append(cumulative / 60)
    labels.append("END")
    return positions, labels


def _stint_margin_curve(
    timeline: pd.DataFrame,
    margin_col: str,
    entry_minutes: float,
    exit_minutes: float,
    entry_pm: float,
    exit_pm: float,
) -> tuple[list[float], list[float]]:
    """Trace the team's actual score-margin shape during [entry_minutes,
    exit_minutes] (instead of a straight line to exit_pm), rebased so the
    curve starts at entry_pm — i.e. wherever the player's own plus/minus line
    left off after their prior stint (or 0 for their first stint) — and ends
    exactly at exit_pm, matching the stint's exit-circle marker."""
    before = timeline[timeline["game_minutes"] <= entry_minutes]
    baseline = before[margin_col].iloc[-1] if not before.empty else 0.0
    window = timeline[(timeline["game_minutes"] > entry_minutes) & (timeline["game_minutes"] < exit_minutes)]

    xs = [entry_minutes, *window["game_minutes"].tolist(), exit_minutes]
    ys = [entry_pm, *(window[margin_col] - baseline + entry_pm).tolist(), exit_pm]
    return xs, ys


def _declutter_marker_rows(rows: list[dict], x_range: float, y_range: float) -> None:
    """Mutates each row's 'y' in place. `rows` must already be in the order
    markers should be considered (earlier ones keep their position). A
    marker's assumed footprint is a small fraction of the axes' data range
    (glyph width/height, since these are all small text/dot markers). If a
    marker's footprint overlaps an already-placed one by more than 50% in
    either the x or y direction, it's nudged up by half a 'T' character's
    height, repeating until clear of every already-placed marker."""
    footprint_w = x_range * 0.02
    footprint_h = y_range * 0.05
    t_char_height = footprint_h
    bump = t_char_height * 0.4
    placed: list[tuple[float, float]] = []
    for row in rows:
        y = row["y"]
        for _ in range(30):
            collided = False
            for px, py in placed:
                dx = abs(row["x"] - px)
                dy = abs(y - py)
                overlaps = dx < footprint_w and dy < footprint_h
                overlap_over_half = dx < footprint_w * 0.5 or dy < footprint_h * 0.4
                if overlaps and overlap_over_half:
                    collided = True
                    break
            if not collided:
                break
            y += bump
        row["y"] = y
        placed.append((row["x"], y))


def _format_linescore(
    periods: pd.DataFrame, home_team: str, away_team: str, home_final: int, away_final: int
) -> str:
    """Standard box score linescore: each team's points per period, plus the
    final score, as a monospace-aligned table."""
    header = "      " + "".join(f"{p:>5}" for p in periods["period"]) + "  Final"
    home_row = f"{home_team:<6}" + "".join(f"{v:>5}" for v in periods["home_points"]) + f"{home_final:>7}"
    away_row = f"{away_team:<6}" + "".join(f"{v:>5}" for v in periods["away_points"]) + f"{away_final:>7}"
    return f"{header}\n{home_row}\n{away_row}"


def _format_box_score(statline: pd.DataFrame, final_pm_by_name: dict, teams: list[str]) -> str:
    """Both teams' box score — MIN/PTS/REB/STOX/+/- per player, ordered by
    minutes descending within each team — as a monospace-aligned table."""
    lines = []
    for team in teams:
        team_stats = statline[statline["teamTricode"] == team].sort_values("MIN", ascending=False)
        lines.append(team)
        lines.append(f"{'Player':<20}{'MIN':>5}{'PTS':>5}{'REB':>5}{'STOX':>6}{'+/-':>6}")
        for _, row in team_stats.iterrows():
            pm_value = final_pm_by_name.get(row["displayName"], 0)
            pm_str = f"+{pm_value:.0f}" if pm_value > 0 else f"{pm_value:.0f}"
            lines.append(
                f"{row['displayName']:<20}{row['MIN']:>5}{row['PTS']:>5}{row['REB']:>5}"
                f"{row['STOCKS']:>6}{pm_str:>6}"
            )
        lines.append("")
    return "\n".join(lines).rstrip("\n")


def _fit_name(name: str, width: int) -> str:
    """Truncate `name` to fit within `width` characters, deleting trailing
    characters as needed so at least one space remains before the next
    column, then left-pad to that width."""
    if len(name) > width - 1:
        name = name[: width - 1]
    return f"{name:<{width}}"


_BOX_NAME_WIDTH = 17


def _box_score_header_line() -> str:
    """The monospace-aligned box score column header, matching the layout of
    each player row from `_box_score_player_line`."""
    return (
        f"{'Player':<{_BOX_NAME_WIDTH}}{'MIN':>3}{'PTS':>4}{'+/-':>5}"
        f"{'FGM':>4}{'FGA':>4}{'FG%':>5}"
        f"{'3PM':>4}{'3PA':>4}{'3P%':>5}{'FTM':>4}{'FTA':>4}{'FT%':>5}"
        f"{'OREB':>5}{'DREB':>5}{'REB':>4}{'AST':>4}{'STL':>4}{'BLK':>4}"
        f"{'TO':>3}{'PF':>3}"
    )


def _lineup_stint_box_line(s) -> str:
    """Box-score header + one row for a lineup stint (in the same monospace
    column layout as `_box_score_player_line`, so it aligns under the box
    score above), then a third line listing the lineup's player names. The
    lineup code is the row label; MIN is whole minutes."""
    def pct(made, att):
        return round(made / att * 100) if att else 0

    pm = s["PLUS_MINUS"]
    pm_str = f"+{pm}" if pm > 0 else f"{pm}"
    row = (
        f"{_fit_name(s['lineup'], _BOX_NAME_WIDTH)}{_fmt_min(s['MIN']):>3}{s['PTS']:>4}{pm_str:>5}"
        f"{s['FGM']:>4}{s['FGA']:>4}{pct(s['FGM'], s['FGA']):>5}"
        f"{s['FG3M']:>4}{s['FG3A']:>4}{pct(s['FG3M'], s['FG3A']):>5}"
        f"{s['FTM']:>4}{s['FTA']:>4}{pct(s['FTM'], s['FTA']):>5}"
        f"{s['OREB']:>5}{s['DREB']:>5}{s['REB']:>4}{s['AST']:>4}{s['STL']:>4}{s['BLK']:>4}"
        f"{s['TO']:>3}{s['PF']:>3}"
    )
    header = "Lineup" + _box_score_header_line()[len("Lineup"):]  # "Player" -> "Lineup" (same width)
    return header + "\n" + row + "\n" + str(s["players"])


def _player_stint_row(s) -> str:
    """One row for a single player stint (in the same monospace column
    layout as `_box_score_player_line`), showing only that stint's stats —
    from `compute_player_stint_stats`."""
    def pct(made, att):
        return round(made / att * 100) if att else 0

    pm = s["PLUS_MINUS"]
    pm_str = f"+{pm}" if pm > 0 else f"{pm}"
    return (
        f"{_fit_name(s['displayName'], _BOX_NAME_WIDTH)}{_fmt_min(s['MIN']):>3}{s['PTS']:>4}{pm_str:>5}"
        f"{s['FGM']:>4}{s['FGA']:>4}{pct(s['FGM'], s['FGA']):>5}"
        f"{s['FG3M']:>4}{s['FG3A']:>4}{pct(s['FG3M'], s['FG3A']):>5}"
        f"{s['FTM']:>4}{s['FTA']:>4}{pct(s['FTM'], s['FTA']):>5}"
        f"{s['OREB']:>5}{s['DREB']:>5}{s['REB']:>4}{s['AST']:>4}{s['STL']:>4}{s['BLK']:>4}"
        f"{s['TO']:>3}{s['PF']:>3}"
    )


# each lineup box score column: (value for max comparison, cell renderer with
# its field width, is_red). Highlighted with the same rules as the player box
# score (`_box_score_overlays`).
def _pm_str(r):
    pm = r["PLUS_MINUS"]
    return f"+{pm}" if pm > 0 else f"{pm}"


def _fmt_min(m) -> str:
    """A MIN cell: whole minutes normally, ":SS" for a sub-minute
    appearance (0:16 -> ":16") so it reads as seconds instead of
    rounding to a blank-looking 0."""
    if 0 < m < 1:
        return f":{round(m * 60):02d}"
    return f"{round(m)}"


def _draw_box_text_lines(fig, x_frac, top_frac, text, color, fontsize,
                         linespacing, fig_h_px):
    """A box score text block as ONE artist PER LINE, each anchored by its
    BASELINE on a uniform grid.

    A single multiline artist seats each line's baseline by that line's
    own descent, so two artists whose line contents differ — the table and
    its colour overlays — drift a few px apart exactly on rows whose names
    have descenders, and the overlay digits sit visibly off the lightgray
    originals underneath (a bold/embossed look). Per-line baseline
    anchoring on a shared grid makes every layer land identically by
    construction. Blank lines draw nothing but still advance the grid."""
    px = fig.dpi / 72
    pitch = fontsize * linespacing * px
    baseline0 = fontsize * px  # first baseline one em below the block top
    arts = []
    for k, line in enumerate(text.split("\n")):
        if line.strip():
            arts.append(fig.text(
                x_frac, top_frac - (baseline0 + k * pitch) / fig_h_px, line,
                transform=fig.transFigure, fontsize=fontsize, color=color,
                ha="left", va="baseline", family="monospace",
            ))
    return arts



def _lineup_pct(made, att):
    return round(made / att * 100) if att else 0


_LINEUP_BOX_HTML_COLUMNS = [
    (lambda r: r["MIN"], lambda r: f"{_fmt_min(r['MIN']):>3}", False),
    (lambda r: r["PTS"], lambda r: f"{r['PTS']:>4}", False),
    (lambda r: r["PLUS_MINUS"], lambda r: f"{_pm_str(r):>5}", False),
    (lambda r: r["FGM"], lambda r: f"{r['FGM']:>4}", False),
    (lambda r: r["FGA"], lambda r: f"{r['FGA']:>4}", False),
    (lambda r: _lineup_pct(r["FGM"], r["FGA"]), lambda r: f"{_lineup_pct(r['FGM'], r['FGA']):>5}", False),
    (lambda r: r["FG3M"], lambda r: f"{r['FG3M']:>4}", False),
    (lambda r: r["FG3A"], lambda r: f"{r['FG3A']:>4}", False),
    (lambda r: _lineup_pct(r["FG3M"], r["FG3A"]), lambda r: f"{_lineup_pct(r['FG3M'], r['FG3A']):>5}", False),
    (lambda r: r["FTM"], lambda r: f"{r['FTM']:>4}", False),
    (lambda r: r["FTA"], lambda r: f"{r['FTA']:>4}", False),
    (lambda r: _lineup_pct(r["FTM"], r["FTA"]), lambda r: f"{_lineup_pct(r['FTM'], r['FTA']):>5}", False),
    (lambda r: r["OREB"], lambda r: f"{r['OREB']:>5}", False),
    (lambda r: r["DREB"], lambda r: f"{r['DREB']:>5}", False),
    (lambda r: r["REB"], lambda r: f"{r['REB']:>4}", False),
    (lambda r: r["AST"], lambda r: f"{r['AST']:>4}", False),
    (lambda r: r["STL"], lambda r: f"{r['STL']:>4}", False),
    (lambda r: r["BLK"], lambda r: f"{r['BLK']:>4}", False),
    (lambda r: r["TO"], lambda r: f"{r['TO']:>3}", True),
    (lambda r: r["PF"], lambda r: f"{r['PF']:>3}", True),
]


def _lu_key(team: str, code: str) -> str:
    """CSS-safe identifier tying a lineup's hover targets (its stint planes
    in the lineup panel) to its row in the lineup box score."""
    return re.sub(r"[^A-Za-z0-9]", "", f"{team}{code}")


def _lineup_box_score_html(
    box_df, team: str, lineup_colors: dict[str, str] | None = None,
    per_minutes: float | None = None,
) -> str:
    """One team's lineup box score as monospace HTML — a header (first column
    "Lineup") plus one row per lineup (ordered by lineup name), in the
    same column layout as the player box score. Each lineup code is a hover
    target showing its player names, colored to match that lineup in the
    lineup-stint panel (via `lineup_colors`, lineup code -> hex), and each
    column's max value is colored (goldenrod, or red for TO/PF).

    If `per_minutes` is given, every counting stat (and +/-) is scaled to a
    per-`per_minutes`-minutes rate — value / MIN * per_minutes, rounded to
    whole numbers — so short and long lineups compare fairly. The shooting
    percentages stay raw and MIN renders as a dash."""
    import html as _html

    team_box = box_df[box_df["teamTricode"] == team].sort_values("lineup")
    header = "Lineup" + _box_score_header_line()[len("Lineup"):]  # "Player" -> "Lineup" (same width)
    lines = [_html.escape(header)]

    rows = [r for _, r in team_box.iterrows()]
    if per_minutes:
        rows = _per_minutes_rows(rows, per_minutes)
    col_max = [max((val_fn(r) for r in rows), default=None) for val_fn, _, _ in _LINEUP_BOX_HTML_COLUMNS]
    col_min = [min((val_fn(r) for r in rows), default=None) for val_fn, _, _ in _LINEUP_BOX_HTML_COLUMNS]
    # smallest *non-zero* value per column, for the red highlight on non-TO/PF
    # columns (so the many 0s aren't all reddened)
    col_min_nz = [
        min((v for v in (val_fn(r) for r in rows) if v != 0), default=None)
        for val_fn, _, _ in _LINEUP_BOX_HTML_COLUMNS
    ]

    for r in rows:
        # 17-char padded lineup code, with how many stints it appeared for
        label = _fit_name(f"{r['lineup']} ({r['stints']})", _BOX_NAME_WIDTH)
        no_3p = r["FG3A"] == 0
        no_ft = r["FTA"] == 0
        cells = []
        for i, ((val_fn, render_fn, is_red), cmax, cmin, cmin_nz) in enumerate(zip(
            _LINEUP_BOX_HTML_COLUMNS, col_max, col_min, col_min_nz
        )):
            if per_minutes and i == 0:  # MIN has no meaning in a rate table
                cells.append(" - ")
                continue
            cell = _html.escape(render_fn(r))
            # no attempts -> grey dash across that shot group's three columns
            if (no_3p and i in _3P_COLUMNS) or (no_ft and i in _FT_COLUMNS):
                width = len(render_fn(r))
                cells.append(f'<span class="mx-grey">{"-".rjust(width)}</span>')
                continue
            v = val_fn(r)
            if is_red:
                # TO/PF: smallest value goldenrod, largest red
                if cmin is not None and v == cmin:
                    cell = f'<span class="mx-gold">{cell}</span>'
                elif cmax is not None and v == cmax:
                    cell = f'<span class="mx-red">{cell}</span>'
            else:
                # other columns: largest goldenrod, smallest non-zero red
                if cmax is not None and v == cmax:
                    cell = f'<span class="mx-gold">{cell}</span>'
                elif cmin_nz is not None and v == cmin_nz:
                    cell = f'<span class="mx-red">{cell}</span>'
            cells.append(cell)
        lu_color = (lineup_colors or {}).get(r["lineup"])
        lu_style = f' style="color:{lu_color};"' if lu_color else ""
        # the whole row is wrapped in a keyed span so hovering this lineup's
        # stint planes in the lineup panel can highlight it
        lines.append(
            f'<span class="lu-row-{_lu_key(team, r["lineup"])}">'
            f'<span class="lu"{lu_style}>{_html.escape(label)}'
            f'<span class="lu-players">{_html.escape(str(r["players"]))}</span></span>'
            f'{"".join(cells)}</span>'
        )
    return "\n".join(lines)


# column indices of the 3P (3PM/3PA/3P%) and FT (FTM/FTA/FT%) groups in the
# box score column order (_BOX_MAX_COLUMNS / _LINEUP_BOX_HTML_COLUMNS) —
# rendered as gray dashes when that group has no attempts
_3P_COLUMNS = {6, 7, 8}
_FT_COLUMNS = {9, 10, 11}

# every counting stat (and +/-) that scales in a per-N-minutes rate view;
# MIN stays raw (it renders as a dash) and percentages are ratios anyway
_RATE_COLS = ("FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB",
              "REB", "AST", "STL", "BLK", "TO", "PF", "PTS", "PLUS_MINUS")


def _per_minutes_rows(rows, per_minutes: float):
    """Scale each row's `_RATE_COLS` to a per-`per_minutes`-minutes rate
    (value / MIN * per_minutes), rounded to whole numbers."""
    scaled = []
    for r in rows:
        r = r.copy()
        factor = per_minutes / r["MIN"] if r["MIN"] else 0
        for c in _RATE_COLS:
            r[c] = round(r[c] * factor)
        scaled.append(r)
    return scaled


def _box_score_player_line(r: pd.Series, min_dash: bool = False) -> str:
    """One player's monospace-aligned box score row, aligned to
    `_box_score_header_line`. Shot groups with no attempts (3P, FT) render
    as right-aligned dashes, like the lineup box score; `min_dash` renders
    the MIN cell as a dash (for rate views, where minutes have no meaning).
    Works whether the row carries displayName as a column or as its index
    label (e.g. after set_index("displayName"))."""
    display_name = r["displayName"] if "displayName" in r.index else r.name
    no_3p, no_ft = r["FG3A"] == 0, r["FTA"] == 0
    cells = [_fit_name(display_name, _BOX_NAME_WIDTH)]
    for i, (_val_fn, render_fn, width, _is_red) in enumerate(_BOX_MAX_COLUMNS):
        if min_dash and i == 0:
            cells.append(" - ")
        elif (no_3p and i in _3P_COLUMNS) or (no_ft and i in _FT_COLUMNS):
            cells.append("-".rjust(width))
        else:
            cells.append(render_fn(r))
    return "".join(cells)


def _format_official_box_score(
    box: pd.DataFrame, team: str, team_margin: float | None = None,
    per_minutes: float | None = None,
) -> str:
    """One team's official NBA box score — MIN/PTS/+/-/FGM/FGA/FG%/3PM/3PA/
    3P%/FTM/FTA/FT%/OREB/DREB/REB/AST/STL/BLK/TO/PF per player, ordered by
    minutes descending — as a monospace-aligned table. The final row is
    labeled with the team name and, if `team_margin` (the team's final
    scoring margin) is given, shows it in the +/- column.

    If `per_minutes` is given, each player's counting stats and +/- are
    scaled to per-`per_minutes`-minutes rates (rounded; MIN renders as a
    dash), and the totals row is scaled to the team's rate per
    `per_minutes` minutes of game time (team minutes / 5 on-court slots)."""
    name_width = _BOX_NAME_WIDTH
    team_box = box[(box["teamTricode"] == team) & (box["MIN"] > 0)]
    lines = [_box_score_header_line()]
    rows = [r for _, r in team_box.iterrows()]
    if per_minutes:
        rows = _per_minutes_rows(rows, per_minutes)
    for r in rows:
        lines.append(_box_score_player_line(r, min_dash=bool(per_minutes)))

    # a summed Series takes ONE dtype, and MIN is fractional now — so sum
    # into a dict and pin the counting totals back to int, or every cell
    # below renders "103.0"
    totals = {
        c: (v if c == "MIN" else int(round(v)))
        for c, v in team_box[
            ["MIN", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "PTS"]
        ].sum().items()
    }
    fg_pct = totals["FGM"] / totals["FGA"] * 100 if totals["FGA"] else 0
    fg3_pct = totals["FG3M"] / totals["FG3A"] * 100 if totals["FG3A"] else 0
    ft_pct = totals["FTM"] / totals["FTA"] * 100 if totals["FTA"] else 0
    if per_minutes and totals["MIN"]:
        team_factor = per_minutes / (totals["MIN"] / 5)
        for c in _RATE_COLS[:-1]:  # PLUS_MINUS isn't in the totals sum
            totals[c] = round(totals[c] * team_factor)
        if team_margin is not None:
            team_margin = round(team_margin * team_factor)
    if team_margin is None:
        margin_str = ""
    else:
        margin_str = f"+{team_margin:.0f}" if team_margin > 0 else f"{team_margin:.0f}"
    min_cell = " - " if per_minutes else f"{round(totals['MIN']):>3}"
    lines.append(
        f"{_fit_name(team, name_width)}{min_cell}{totals['PTS']:>4}{margin_str:>5}"
        f"{totals['FGM']:>4}{totals['FGA']:>4}{fg_pct:>5.0f}"
        f"{totals['FG3M']:>4}{totals['FG3A']:>4}{fg3_pct:>5.0f}"
        f"{totals['FTM']:>4}{totals['FTA']:>4}{ft_pct:>5.0f}"
        f"{totals['OREB']:>5}{totals['DREB']:>5}{totals['REB']:>4}{totals['AST']:>4}{totals['STL']:>4}{totals['BLK']:>4}"
        f"{totals['TO']:>3}{totals['PF']:>3}"
    )
    return "\n".join(lines)


# each stat column, in box score order: (max-comparison value, rendered cell
# — matching `_box_score_player_line` exactly, field width, is_red). The
# rendered cell is what overlays the gray text, so it must be byte-identical.
def _pm_cell(r: pd.Series) -> str:
    pm = r["PLUS_MINUS"]
    return f"{('+' + format(pm, '.0f')) if pm > 0 else format(pm, '.0f'):>5}"


_BOX_MAX_COLUMNS = [
    (lambda r: r["MIN"], lambda r: f"{_fmt_min(r['MIN']):>3}", 3, False),
    (lambda r: r["PTS"], lambda r: f"{r['PTS']:>4}", 4, False),
    (lambda r: r["PLUS_MINUS"], _pm_cell, 5, False),
    (lambda r: r["FGM"], lambda r: f"{r['FGM']:>4}", 4, False),
    (lambda r: r["FGA"], lambda r: f"{r['FGA']:>4}", 4, False),
    (lambda r: r["FG_PCT"], lambda r: f"{r['FG_PCT'] * 100:>5.0f}", 5, False),
    (lambda r: r["FG3M"], lambda r: f"{r['FG3M']:>4}", 4, False),
    (lambda r: r["FG3A"], lambda r: f"{r['FG3A']:>4}", 4, False),
    (lambda r: r["FG3_PCT"], lambda r: f"{r['FG3_PCT'] * 100:>5.0f}", 5, False),
    (lambda r: r["FTM"], lambda r: f"{r['FTM']:>4}", 4, False),
    (lambda r: r["FTA"], lambda r: f"{r['FTA']:>4}", 4, False),
    (lambda r: r["FT_PCT"], lambda r: f"{r['FT_PCT'] * 100:>5.0f}", 5, False),
    (lambda r: r["OREB"], lambda r: f"{r['OREB']:>5}", 5, False),
    (lambda r: r["DREB"], lambda r: f"{r['DREB']:>5}", 5, False),
    (lambda r: r["REB"], lambda r: f"{r['REB']:>4}", 4, False),
    (lambda r: r["AST"], lambda r: f"{r['AST']:>4}", 4, False),
    (lambda r: r["STL"], lambda r: f"{r['STL']:>4}", 4, False),
    (lambda r: r["BLK"], lambda r: f"{r['BLK']:>4}", 4, False),
    (lambda r: r["TO"], lambda r: f"{r['TO']:>3}", 3, True),   # red
    (lambda r: r["PF"], lambda r: f"{r['PF']:>3}", 3, True),   # red
]


def _box_score_overlays(
    box: pd.DataFrame, team: str, per_minutes: float | None = None,
) -> tuple[str, str, str]:
    """Three same-shape, same-line-count overlays for
    `_format_official_box_score` (over players only — the header and team
    totals rows are never highlighted), drawn in goldenrod, red, and gray on
    top of the gray box score so only those cells are recolored. Same
    highlighting rules as the lineup box score: per column, the max value in
    goldenrod and the smallest non-zero value in red — except TO/PF, where
    lower is better, so their min is goldenrod and their max red — and shot
    groups with no attempts (3P, FT) as gray dashes. Ties are all
    highlighted; cell rendering and column widths mirror
    `_box_score_player_line` exactly so the overlays align."""
    team_box = box[(box["teamTricode"] == team) & (box["MIN"] > 0)]
    if team_box.empty:
        return "", "", ""
    rows = [r for _, r in team_box.iterrows()]
    if per_minutes:
        rows = _per_minutes_rows(rows, per_minutes)
    col_vals = [[val_fn(r) for r in rows] for val_fn, _, _, _ in _BOX_MAX_COLUMNS]
    col_max = [max(vals) for vals in col_vals]
    col_min = [min(vals) for vals in col_vals]
    col_min_nz = [min((v for v in vals if v != 0), default=None) for vals in col_vals]

    gold_lines, red_lines, grey_lines = [""], [""], [""]  # header row
    for r in rows:
        no_3p, no_ft = r["FG3A"] == 0, r["FTA"] == 0
        gold_parts, red_parts, grey_parts = ([" " * _BOX_NAME_WIDTH] for _ in range(3))
        for i, (val_fn, render_fn, width, is_red) in enumerate(_BOX_MAX_COLUMNS):
            blank = " " * width
            if per_minutes and i == 0:  # MIN is a dash in rate views
                gold_parts.append(blank)
                red_parts.append(blank)
                grey_parts.append(blank)
                continue
            if (no_3p and i in _3P_COLUMNS) or (no_ft and i in _FT_COLUMNS):
                gold_parts.append(blank)
                red_parts.append(blank)
                grey_parts.append("-".rjust(width))
                continue
            v = val_fn(r)
            if is_red:
                gold = v == col_min[i]
                red = not gold and v == col_max[i]
            else:
                gold = v == col_max[i]
                red = not gold and v == col_min_nz[i]
            gold_parts.append(render_fn(r) if gold else blank)
            red_parts.append(render_fn(r) if red else blank)
            grey_parts.append(blank)
        gold_lines.append("".join(gold_parts))
        red_lines.append("".join(red_parts))
        grey_lines.append("".join(grey_parts))
    gold_lines.append("")  # team totals row
    red_lines.append("")
    grey_lines.append("")
    return "\n".join(gold_lines), "\n".join(red_lines), "\n".join(grey_lines)


def _measure_text_height_inches(text: str, fontsize: float, family: str, dpi: float = 150,
                                linespacing: float = 1.2) -> float:
    """Render `text` in a throwaway figure and measure its actual rendered
    height, in inches — more reliable than guessing a per-line height, since
    real line spacing depends on the font's own metrics. Uses an explicit
    Agg canvas (not pyplot's current backend) so the measurement is
    consistent regardless of whatever backend the caller's environment
    happens to select (an interactive GUI backend can use a different
    rendering DPI than Agg, throwing this measurement off)."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    fig = Figure(figsize=(20, 1), dpi=dpi)
    FigureCanvasAgg(fig)
    artist = fig.text(0.5, 0.5, text, fontsize=fontsize, family=family, ha="center", va="center",
                      linespacing=linespacing)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox = artist.get_window_extent(renderer)
    height_inches = bbox.height / dpi
    return height_inches


def _build_header(
    csv_path: Path, shots: pd.DataFrame, statline: pd.DataFrame, final_pm_by_name: dict,
    teams: list[str], game_info: dict | None, chart_name: str, include_box_score: bool = True,
) -> tuple[str, str, float]:
    """Build the header as two separate blocks — `header_prose` (matchup/
    date/venue and the linescore, meant to be centered — safe to center
    because every linescore line is padded to the same fixed width) and
    `header_table` (optionally the two-team box score, meant to be
    left-aligned so its columns stay put) — plus the total vertical space
    both need together, in inches. Kept as two blocks (not one combined,
    centered string) because centering a multi-line monospace table shifts
    each line independently and breaks its column alignment."""
    from nba_pbp.plusminus import compute_period_scores

    game_id = shots["gameId"].iloc[0] if "gameId" in shots.columns else ""
    periods, ls_home, ls_away, home_final, away_final = compute_period_scores(csv_path)
    linescore = _format_linescore(periods, ls_home, ls_away, home_final, away_final)
    box_score_block = ""
    if include_box_score:
        box_score = _format_box_score(statline, final_pm_by_name, teams)
        box_score_block = f"\n\n{box_score}"

    # the leading newline is one blank line of top margin above the title
    if game_info:
        header_prose = (
            f"\n{game_info['away_team']} @ {game_info['home_team']}\n"
            f"{game_info['date']} at {game_info['time']}\n"
            f"{game_info['location']}  |  Game ID: {game_id}\n"
            f"\n"
            f"{linescore}"
        )
    else:
        header_prose = f"\n{chart_name} — game {game_id}\n\n{linescore}"

    header_table = box_score_block.lstrip("\n")

    header_inches = _measure_text_height_inches(
        f"{header_prose}\n{header_table}", fontsize=_HEADER_FONTSIZE, family="monospace"
    ) + 0.3
    return header_prose, header_table, header_inches


def _build_plus_minus_by_player_figure(csv_path: Path, game_info: dict | None = None, tooltips: bool = False):
    """Build (but don't save/close) the per-player plus/minus figure: same
    made-shot, stint-line, and stint-circle data as `plot_plus_minus`, but
    small-multiples style — one subplot per player, grouped by team, instead
    of every player overlaid on one axes per team."""
    from nba_pbp.plusminus import (
        compute_event_plus_minus,
        compute_shot_plus_minus,
        compute_statline,
        compute_stint_plus_minus,
        compute_team_margin_timeline,
    )

    shots, final_pm = compute_shot_plus_minus(csv_path)
    if shots.empty:
        raise ValueError(f"No shot events found in {csv_path}")
    stint_pm = compute_stint_plus_minus(csv_path)
    margin_timeline, margin_home_team, margin_away_team = compute_team_margin_timeline(csv_path)
    statline_indexed = compute_statline(csv_path).set_index(["teamTricode", "displayName"])
    statline = statline_indexed.reset_index()
    pid_to_display = stint_pm.drop_duplicates("personId").set_index("personId")["displayName"].to_dict()
    final_pm_by_name = {pid_to_display.get(pid, str(pid)): value for pid, value in final_pm.items()}
    events = compute_event_plus_minus(csv_path)
    event_markers = {"REB": "$R$", "AST": "$A$", "BLK": "$B$", "STL": "$S$"}
    foul_tov_markers = {"FOUL": "$F$", "TOV": "$T$"}
    shot_markers = {1: "$1$", 2: "$2$", 3: "$3$"}

    teams = sorted(shots["teamTricode"].dropna().unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 teams, found: {teams}")

    header_prose, header_table, header_inches = _build_header(
        csv_path, shots, statline, final_pm_by_name, teams, game_info, "Plus/minus by player",
        include_box_score=False,
    )
    header_inches += 0.5  # extra gap between the linescore and the first team name
    prose_inches = _measure_text_height_inches(header_prose, fontsize=_HEADER_FONTSIZE, family="monospace")

    from nba_pbp.plusminus import compute_official_box_score

    # every box score size comes from the page typography block up top
    box_fontsize = _BOX_FONT_PT
    box_linespacing = _BOX_LINE_HEIGHT
    boxes_by_team = {team: compute_official_box_score(csv_path, team=team) for team in teams}
    pts_by_team = {team: box["PTS"].sum() for team, box in boxes_by_team.items()}
    official_box_text_by_team = {
        team: _format_official_box_score(
            boxes_by_team[team], team,
            team_margin=pts_by_team[team] - pts_by_team[next(t for t in teams if t != team)],
        )
        for team in teams
    }
    # label line above each team box score ("OKC box score"), in the shared
    # panel-title style. The label is drawn one line down into its budget
    # (see box_label_y below) so it sits right above the table's header.
    box_label_line_inches = _measure_text_height_inches(
        "Ag", fontsize=_PANEL_TITLE_FONTSIZE, family="DejaVu Sans"
    )
    box_label_inches = box_label_line_inches + 0.16
    official_box_inches_by_team = {
        team: _measure_text_height_inches(text, fontsize=box_fontsize, family="monospace",
                                          linespacing=box_linespacing)
        + box_label_inches + 0.2
        for team, text in official_box_text_by_team.items()
    }
    box_row_by_name = {
        team: boxes_by_team[team].set_index("displayName") for team in teams
    }

    tick_positions, tick_labels = _quarter_ticks(int(shots["period"].max()))
    game_id = shots["gameId"].iloc[0] if "gameId" in shots.columns else None
    game_id_str = str(int(game_id)).zfill(10) if game_id else None
    local_time_labels = _local_time_tick_labels(game_id_str, tick_labels) if game_id_str else None
    made_all = shots[shots["shotResult"] == "Made"]
    missed_all = shots[shots["shotResult"] == "Missed"]

    team_y_min = margin_timeline[["home_margin", "away_margin"]].min().min()
    team_y_max = margin_timeline[["home_margin", "away_margin"]].max().max()
    team_y_limits = (team_y_min * 1.5, team_y_max * 1.5)
    team_score_max = margin_timeline[["home_score", "away_score"]].max().max()
    team_score_limits = (0, team_score_max * 1.05)

    ncols = 1
    team_players = {}
    team_rows = {}
    for team in teams:
        team_shots = made_all[made_all["teamTricode"] == team]
        team_stint_pm = stint_pm[stint_pm["teamTricode"] == team]
        all_players = set(team_shots["displayName"]) | set(team_stint_pm["displayName"])
        # order players within the team by total minutes played, descending
        team_minutes = statline_indexed[statline_indexed.index.get_level_values("teamTricode") == team]["MIN"]
        minutes_by_name = {name: team_minutes.get((team, name), 0) for name in all_players}
        players = sorted(all_players, key=lambda name: (-minutes_by_name[name], name))
        team_players[team] = players
        team_rows[team] = -(-len(players) // ncols)  # ceil division

    from nba_pbp.plusminus import compute_lineup_stint_segments, compute_player_stint_stats
    stint_segments = compute_lineup_stint_segments(csv_path, min_seconds=45.0)
    player_stint_stats = compute_player_stint_stats(csv_path)

    # missed free throws, for the events panel's bad-event counts (they
    # appear in no other computed dataset — `shots` only has made FTs)
    from nba_pbp.plusminus import _load_full_pbp
    _raw = _load_full_pbp(csv_path)
    missed_ft = _raw[
        (_raw["actionType"] == "Free Throw")
        & _raw["description"].astype(str).str.startswith("MISS")
    ].copy()
    missed_ft["game_minutes"] = missed_ft["game_seconds"] / 60
    missed_ft["displayName"] = missed_ft["personId"].map(
        dict(zip(stint_pm["personId"], stint_pm["displayName"]))
    ).fillna(missed_ft["playerName"])

    # a game-level cumulative-events panel sits above the team sections;
    # each team's section, top to bottom: summary panel, box score, one row
    # per player, then the lineup-stint panel closing the section. The
    # FIRST team gets no summary panel of its own — the Karma panel (whose
    # backdrop carries that team's stint lanes) stands in for it.
    spacer_rows = 1
    row_labels = []  # ("event_sum"|"team_summary"|"box_score"|"team"|"lineup_stints"|"spacer", team) per grid row
    row_labels.append(("event_sum",))
    for i, team in enumerate(teams):
        if i > 0:
            row_labels.append(("team_summary", team))
        row_labels.append(("box_score", team))
        row_labels.extend(("team", team) for _ in range(team_rows[team]))
        row_labels.append(("lineup_stints", team))
        if i < len(teams) - 1:
            row_labels.extend(("spacer",) for _ in range(spacer_rows))
    # both teams' lineups on one shared +/- axis, closing the page
    if len(teams) > 1:
        row_labels.extend(("spacer",) for _ in range(spacer_rows))
        row_labels.append(("lineup_combined",))
    total_rows = len(row_labels)
    hspace = 0.72  # tuned so the blank between player charts is ~86px, 25% less than its old 114px
    bottom_shrink = 0.97  # matches the "0.03 * (body_inches / total_inches)" bottom margin below
    # A gridspec's `hspace` eats into row heights (it's carved out of the
    # same budget, not added on top), so 1 height-ratio unit does NOT map to
    # a flat 3 inches — it maps to less, by a factor depending on the row
    # count. Solve for that factor so every row can be sized in physical
    # inches: heights then hold still when hspace or the row count changes,
    # and hspace alone dials the gaps between rows.
    inches_per_ratio_unit = bottom_shrink * 3 * total_rows / (total_rows + hspace * (total_rows - 1))
    # player rows: two successive 25% cuts from their original ~1.85in
    # team_summary rows hold the later teams' Karma panels, so they match
    # the game-level Karma row's height
    row_inches = {"spacer": 1.3, "team_summary": 2.0, "lineup_stints": 2.4, "team": 1.04,
                  "event_sum": 2.0, "lineup_combined": 2.4}
    height_ratios = [
        (official_box_inches_by_team[r[1]] if r[0] == "box_score" else row_inches[r[0]])
        / inches_per_ratio_unit
        for r in row_labels
    ]

    body_inches = 3 * sum(height_ratios)
    total_inches = body_inches + header_inches
    top_fraction = body_inches / total_inches

    stint_hover_boxes = []  # precomputed {left,top,width,height,tooltip,center} per stint region
    title_tooltips = []  # (Text object, box score line, pinned-line top) per player title

    with plt.style.context("dark_background"):
        fig = plt.figure(figsize=(8, total_inches))
        fig.set_dpi(150)  # match the dpi used at savefig time, so tooltip pixel math lines up
        fig_w_px = fig.get_size_inches()[0] * fig.dpi
        fig_h_px = fig.get_size_inches()[1] * fig.dpi
        # plots span the box score tables' width: right edges align exactly
        # (the tables' monospace block ends at ~0.948), and the left spine
        # sits as far left as the y furniture allows — the rotated "+/-"
        # ylabel plus 3-char tick labels need ~0.072 of margin, so 0.076
        # keeps them on the figure with a small cushion. The tables start
        # at 0.031; the labels fill the sliver between.
        gs = fig.add_gridspec(
            total_rows, ncols, height_ratios=height_ratios, hspace=hspace, wspace=0.3,
            top=top_fraction, bottom=0.03 * (body_inches / total_inches),
            left=0.076, right=0.948,
        )

        # axes handles needed later for the slice-cut math
        summary_axes: dict[str, plt.Axes] = {}
        stint_axes: dict[str, plt.Axes] = {}
        # each team's base box score text artist, for locating player rows
        box_text_artists: dict[str, plt.Text] = {}
        # each team's (body_top, text layers) for the per-32 redraw, and the
        # figure-fraction top of its box score label line, where the
        # "show per 32" switch button sits
        box_layers_by_team: dict[str, tuple] = {}
        box_label_tops: dict[str, float] = {}
        box_label_artists: dict[str, plt.Text] = {}
        # per-team data for the box score name hovers: rendered row order,
        # player colors as hex, and each player's band segment rects
        box_names_by_team: dict[str, list] = {}
        player_hex_by_team: dict[str, dict] = {}
        band_rects_by_team: dict[str, dict] = {}
        # each Karma panel's axes grouped by layer, so the caller can
        # render the panels' toggleable layers (stint lanes, +/- margin)
        # as separate transparent overlays over a bars+score base; plus
        # the top of each panel's title line (for the switch buttons)
        karma_layer_axes: dict[str, list[plt.Axes]] = {
            "main": [], "band": [], "margin": [], "points": [], "bars": [],
            "events": [], "vevents": [], "hevents": [],
        }
        kb_label_tops: dict[str, float] = {}
        player_axes: dict[str, list[plt.Axes]] = {team: [] for team in teams}
        # each team's lineup-code -> hex color, from its lineup-stint panel,
        # for coloring the lineup names in the HTML lineup box score
        lineup_colors_by_team: dict[str, dict[str, str]] = {}

        # game-level good/bad events panel, right under the linescore
        event_ax = fig.add_subplot(gs[row_labels.index(("event_sum",)), 0])
        (karma_band_ax, karma_margin_ax, karma_points_ax, karma_bars_ax,
         karma_events_ax, karma_vevents_ax, karma_hevents_ax) = _draw_event_sum_panel(
            event_ax, teams, made_all, missed_all, missed_ft, events,
            margin_timeline, margin_home_team, tick_positions, tick_labels,
            local_time_labels=local_time_labels,
        )
        # anchor for the box score lines the karma band's stint hovers
        # reveal: just below the panel's x-axis (clearing the tick and
        # wall-clock labels), so the readout hangs under the Karma graph
        karma_label_top = (
            1 - event_ax.transAxes.transform((0, 0))[1] / fig_h_px
            + 32 * (fig.dpi / 72) / fig_h_px
        )

        # player_color is rebound per team below; the combined lineup panel
        # runs AFTER this loop and needs BOTH rosters' colours, so keep a
        # merged map too (its popups colour whichever team's stint you hover)
        all_player_colors: dict = {}
        for team in teams:
            players = team_players[team]
            n_players = len(players)
            cmap = _vivid_cmap(n_players)
            player_color = {name: cmap(i) for i, name in enumerate(players)}
            all_player_colors.update(player_color)

            team_shots = made_all[made_all["teamTricode"] == team]
            team_missed_shots = missed_all[missed_all["teamTricode"] == team]
            team_stint_pm = stint_pm[stint_pm["teamTricode"] == team]

            box_names = boxes_by_team[team].loc[
                boxes_by_team[team]["MIN"] > 0, "displayName"
            ].tolist()
            box_names_by_team[team] = box_names
            player_hex_by_team[team] = {n: to_hex(c) for n, c in player_color.items()}
            if team == teams[0]:
                # the first team's Karma panel is the game-level one drawn
                # above; its stint-lane backdrop is this team's rotation
                # band, with hover wiring to the box score below
                team_karma_band_ax = karma_band_ax
                team_karma_margin_ax = karma_margin_ax
                team_karma_points_ax = karma_points_ax
                team_karma_bars_ax = karma_bars_ax
                team_karma_events_ax = karma_events_ax
                team_karma_vevents_ax = karma_vevents_ax
                team_karma_hevents_ax = karma_hevents_ax
                team_karma_label_top = karma_label_top
                karma_panel_ax = event_ax
            else:
                # every other team gets its own Karma panel, from its
                # perspective (its good events point up)
                summary_row = next(i for i, r in enumerate(row_labels) if r[0] == "team_summary" and r[1] == team)
                summary_ax = fig.add_subplot(gs[summary_row, 0])
                summary_axes[team] = summary_ax
                teams_rev = [team] + [t for t in teams if t != team]
                (team_karma_band_ax, team_karma_margin_ax, team_karma_points_ax,
                 team_karma_bars_ax, team_karma_events_ax,
                 team_karma_vevents_ax, team_karma_hevents_ax) = _draw_event_sum_panel(
                    summary_ax, teams_rev, made_all, missed_all, missed_ft, events,
                    margin_timeline, margin_home_team, tick_positions, tick_labels,
                    local_time_labels=local_time_labels,
                )
                team_karma_label_top = (
                    1 - summary_ax.transAxes.transform((0, 0))[1] / fig_h_px
                    + 32 * (fig.dpi / 72) / fig_h_px
                )
                karma_panel_ax = summary_ax
            karma_layer_axes["main"].append(karma_panel_ax)
            karma_layer_axes["band"].append(team_karma_band_ax)
            karma_layer_axes["margin"].append(team_karma_margin_ax)
            karma_layer_axes["points"].append(team_karma_points_ax)
            karma_layer_axes["bars"].append(team_karma_bars_ax)
            karma_layer_axes["events"].append(team_karma_events_ax)
            karma_layer_axes["vevents"].append(team_karma_vevents_ax)
            karma_layer_axes["hevents"].append(team_karma_hevents_ax)
            # top of the panel's title line, where the "hide stints"
            # switch button sits (right-aligned like the per-32 switch)
            kb_label_tops[team] = (
                1 - karma_panel_ax.transAxes.transform((0, 1))[1] / fig_h_px
                - (_PANEL_TITLE_FONTSIZE + plt.rcParams["axes.titlepad"]) * (fig.dpi / 72) / fig_h_px
            )
            karma_boxes = _draw_karma_band_lanes(
                team_karma_band_ax, team, team_stint_pm,
                player_color, box_names, fig_w_px, fig_h_px, team_karma_label_top,
            )
            _draw_karma_event_markers(
                team_karma_events_ax, team, made_all, missed_all, missed_ft,
                events, team_stint_pm, player_color, box_names,
            )
            _draw_karma_vevent_markers(
                team_karma_vevents_ax, team, made_all, missed_all, missed_ft,
                events, player_color,
            )
            _draw_karma_hevent_markers(
                team_karma_hevents_ax, team, made_all, missed_all, missed_ft,
                events, team_stint_pm, player_color, box_names,
            )

            def _stint_line(name, entry):
                srow = player_stint_stats[
                    (player_stint_stats["teamTricode"] == team)
                    & (player_stint_stats["displayName"] == name)
                    & (player_stint_stats["entry_minutes"].round(4) == round(entry, 4))
                ]
                if not srow.empty:
                    return _player_stint_row(srow.iloc[0])
                if name in box_row_by_name[team].index:
                    return _box_score_player_line(box_row_by_name[team].loc[name])
                return name

            # a hovered lane segment shows that stint's own box score row
            # (in the player's color, under the shared header) and
            # highlights the player's row in the team box score — the
            # row's on-canvas rect is resolved after the draw below
            for b in karma_boxes:
                name = b.pop("name_label")
                entry = b.pop("stint_entry")
                band_rects_by_team.setdefault(team, {}).setdefault(name, []).append(
                    {k: b[k] for k in ("left", "top", "width", "height")}
                )
                b["player_line"] = _stint_line(name, entry)
                # same key as the box score row target, so hovering ANY of
                # this player's stints lights up the same set of rects
                # (their row + every one of their stints) as hovering the row
                b["player_key"] = re.sub(r"[^A-Za-z0-9]", "", f"{team}{name}")
                if name in box_names:
                    b["_hl"] = (team, box_names.index(name))
            stint_hover_boxes.extend(karma_boxes)

            box_row = next(i for i, r in enumerate(row_labels) if r[0] == "box_score" and r[1] == team)
            box_ax = fig.add_subplot(gs[box_row, 0])
            box_ax.axis("off")
            # left-align the box score with the team panel's "+/-" y-axis
            # label (which sits left of the axes spine), not with the spine
            box_top_fig = box_ax.get_position().y1
            # one line down from the row top, so the label hugs the table
            box_label_y = box_top_fig - box_label_line_inches / total_inches
            box_label_tops[team] = 1 - box_label_y
            box_label_artists[team] = fig.text(
                _BOX_SCORE_LEFT_MARGIN, box_label_y, f"{team} box score", transform=fig.transFigure,
                fontsize=_PANEL_TITLE_FONTSIZE, color=_PANEL_TITLE_COLOR, ha="left", va="top",
            )
            box_body_top = box_top_fig - box_label_inches / total_inches
            gold_overlay, red_overlay, grey_overlay = _box_score_overlays(boxes_by_team[team], team)
            box_layer_artists = []
            for oi, (text, color) in enumerate((
                (official_box_text_by_team[team], "lightgray"),
                (gold_overlay, "goldenrod"),
                (red_overlay, "red"),
                (grey_overlay, "gray"),
            )):
                arts = _draw_box_text_lines(
                    fig, _BOX_SCORE_LEFT_MARGIN, box_body_top, text, color,
                    box_fontsize, box_linespacing, fig_h_px,
                )
                box_layer_artists.extend(arts)
                if oi == 0:
                    # the header line spans the full table width, so its
                    # extent still yields box_right for the toggle buttons
                    box_text_artists[team] = arts[0]
            box_layers_by_team[team] = (box_body_top, box_layer_artists)
            # overlay each player's name in the Player column in their chart
            # color (line 0 is the header; rendered rows are the MIN>0 players
            # in the same order `_format_official_box_score` prints them)
            rendered_names = boxes_by_team[team].loc[boxes_by_team[team]["MIN"] > 0, "displayName"]
            for i, box_name in enumerate(rendered_names):
                if box_name not in player_color:
                    continue
                _draw_box_text_lines(
                    fig, _BOX_SCORE_LEFT_MARGIN, box_body_top,
                    "\n" * (i + 1) + _fit_name(box_name, _BOX_NAME_WIDTH),
                    player_color[box_name], box_fontsize, box_linespacing,
                    fig_h_px,
                )

            stint_row = next(i for i, r in enumerate(row_labels) if r[0] == "lineup_stints" and r[1] == team)
            stint_ax = fig.add_subplot(gs[stint_row, 0])
            stint_axes[team] = stint_ax
            lineup_hover_boxes, lineup_colors = _draw_lineup_stint_panel(
                stint_ax, team, stint_segments[stint_segments["teamTricode"] == team],
                margin_timeline, margin_home_team, tick_positions, tick_labels,
                team_score_limits, fig_w_px, fig_h_px, player_color=player_color,
            )
            stint_hover_boxes.extend(lineup_hover_boxes)
            lineup_colors_by_team[team] = {lu: to_hex(c) for lu, c in lineup_colors.items()}

            grid_rows = [i for i, r in enumerate(row_labels) if r[0] == "team" and r[1] == team]
            for player_idx, (name, (row, col)) in enumerate(
                zip(players, ((r, c) for r in grid_rows for c in range(ncols)))
            ):
                ax = fig.add_subplot(gs[row, col])
                player_axes[team].append(ax)
                color = player_color[name]
                player_stint_pm = team_stint_pm[team_stint_pm["displayName"] == name]
                player_shots = team_shots[team_shots["displayName"] == name]
                player_missed_shots = team_missed_shots[team_missed_shots["displayName"] == name]
                player_events = events[
                    (events["teamTricode"] == team) & (events["displayName"] == name)
                ] if not events.empty else events

                # lightly shade the span of game time this player was on court
                for _, srow in player_stint_pm.iterrows():
                    ax.axvspan(
                        srow["entry_minutes"], srow["exit_minutes"],
                        color=color, alpha=0.3, zorder=0, linewidth=0,
                    )

                y_plotted: list[float] = []  # everything on this chart's y-axis
                margin_col = "home_margin" if team == margin_home_team else "away_margin"
                for _, srow in player_stint_pm.iterrows():
                    xs, ys = _stint_margin_curve(
                        margin_timeline, margin_col,
                        srow["entry_minutes"], srow["exit_minutes"],
                        srow["entry_pm"], srow["exit_pm"],
                    )
                    ax.plot(xs, ys, color="black", alpha=0.8, linewidth=3.2, zorder=1)
                    y_plotted.extend(ys)

                marker_rows = []
                for shot_value in shot_markers:
                    subset = player_missed_shots[player_missed_shots["shotValue"] == shot_value]
                    marker_rows.extend(
                        {"x": r["game_minutes"], "y": r["plusMinus"], "kind": f"missed{shot_value}"}
                        for _, r in subset.iterrows()
                    )
                for shot_value in shot_markers:
                    subset = player_shots[player_shots["shotValue"] == shot_value]
                    marker_rows.extend(
                        {"x": r["game_minutes"], "y": r["plusMinus"], "kind": f"shot{shot_value}"}
                        for _, r in subset.iterrows()
                    )
                for event_type in list(event_markers) + list(foul_tov_markers):
                    subset = player_events[player_events["event_type"] == event_type]
                    marker_rows.extend(
                        {"x": r["game_minutes"], "y": r["plusMinus"], "kind": event_type}
                        for _, r in subset.iterrows()
                    )
                marker_rows.sort(key=lambda r: r["x"])
                # per-chart auto range, snapped outward to multiples of 5
                y_plotted += [r["y"] for r in marker_rows]
                y_plotted += list(player_stint_pm["entry_pm"]) + list(player_stint_pm["exit_pm"])
                if y_plotted:
                    y_lo = int(np.floor(min(y_plotted) / 5) * 5)
                    y_hi = int(np.ceil(max(y_plotted) / 5) * 5)
                    if y_lo == y_hi:
                        y_lo, y_hi = y_lo - 5, y_hi + 5
                else:
                    y_lo, y_hi = -5, 5
                _declutter_marker_rows(marker_rows, tick_positions[-1] - tick_positions[0], y_hi - y_lo)
                by_kind: dict[str, list[dict]] = {}
                for r in marker_rows:
                    by_kind.setdefault(r["kind"], []).append(r)

                def _xy(kind: str) -> tuple[list[float], list[float]]:
                    rs = by_kind.get(kind, [])
                    return [r["x"] for r in rs], [r["y"] for r in rs]

                for shot_value, marker in shot_markers.items():
                    mx, my = _xy(f"missed{shot_value}")
                    ax.scatter(mx, my, color="red", s=32, alpha=0.6, marker=marker, linewidth=0.4, zorder=3)
                for shot_value, marker in shot_markers.items():
                    sx, sy = _xy(f"shot{shot_value}")
                    ax.scatter(sx, sy, color=color, s=32, alpha=0.6, marker=marker, linewidth=0.4, zorder=3)
                for event_type, marker in event_markers.items():
                    ex, ey = _xy(event_type)
                    ax.scatter(ex, ey, color=color, s=32, alpha=0.4, marker=marker, linewidth=0.4, zorder=3)
                for event_type, marker in foul_tov_markers.items():
                    ex, ey = _xy(event_type)
                    ax.scatter(ex, ey, color="red", s=32, alpha=0.4, marker=marker, linewidth=0.4, zorder=3)
                ax.scatter(
                    player_stint_pm["entry_minutes"], player_stint_pm["entry_pm"],
                    color="black", s=22, marker="o", edgecolor="none", zorder=2,
                )
                ax.scatter(
                    player_stint_pm["exit_minutes"], player_stint_pm["exit_pm"],
                    color="black", s=22, marker="o", edgecolor="none", zorder=2,
                )

                ax.axhline(0, color="white", linewidth=0.6, alpha=0.3)
                # pin the right limit so every chart shares the exact same
                # time axis (autoscaling to each player's own data would
                # shift the tick positions from chart to chart)
                ax.set_xlim(left=0, right=tick_positions[-1])
                ax.set_ylim(y_lo, y_hi)
                ax.set_xticks(tick_positions)
                ax.set_xticklabels(tick_labels, fontsize=8)
                ax.yaxis.set_major_locator(MultipleLocator(5))
                if player_idx == 0:
                    # label the series once, on each team's first chart
                    # (15% above the default label size)
                    ax.set_ylabel("+/-", color="gray", fontsize=11.5)
                title_obj = ax.set_title(name, fontsize=_PANEL_TITLE_FONTSIZE, color=color, loc="left")
                # anchor for the pinned box score line the stint and title
                # hovers reveal: just above this plot's title label, aligned
                # with the team box score (same mechanism as the lineup-stint
                # panel). Stint hovers show that stint's own stats; the title
                # hover shows the player's full-game line.
                axes_top_frac = 1 - ax.transAxes.transform((0, 1))[1] / fig_h_px
                label_top = axes_top_frac - (
                    _PANEL_TITLE_FONTSIZE + plt.rcParams["axes.titlepad"]
                ) * (fig.dpi / 72) / fig_h_px
                if name in box_row_by_name[team].index:
                    box_tooltip = (
                        _box_score_header_line() + "\n"
                        f'<span style="color:{to_hex(color)};">'
                        f'{_box_score_player_line(box_row_by_name[team].loc[name])}</span>'
                    )
                    title_tooltips.append((title_obj, box_tooltip, label_top))
                player_stints_stats = player_stint_stats[
                    (player_stint_stats["teamTricode"] == team)
                    & (player_stint_stats["displayName"] == name)
                ]
                for _, srow in player_stints_stats.iterrows():
                    entry_m, exit_m = srow["entry_minutes"], srow["exit_minutes"]
                    x_entry_px, _ = ax.transData.transform((entry_m, 0))
                    x_exit_px, _ = ax.transData.transform((exit_m, 0))
                    top_axes_y = ax.transAxes.transform((0, 1))[1]
                    bottom_axes_y = ax.transAxes.transform((0, 0))[1]
                    # the trigger covers the whole stint plane, so its
                    # self-highlight (seg_color) lights the plane exactly
                    stint_hover_boxes.append({
                        "left": x_entry_px / fig_w_px,
                        "top": 1 - top_axes_y / fig_h_px,
                        "width": (x_exit_px - x_entry_px) / fig_w_px,
                        "height": (top_axes_y - bottom_axes_y) / fig_h_px,
                        "seg_color": f"{to_hex(color)}40",
                        "line_tooltip": (
                            _box_score_header_line() + "\n"
                            f'<span style="color:{to_hex(color)};">{_player_stint_row(srow)}</span>'
                        ),
                        "label_left": _BOX_SCORE_LEFT_MARGIN,
                        "label_top": label_top,
                    })
                ax.grid(True, color=(1, 1, 1, 0.15))
                ax.tick_params(axis="x", colors="gray")
                ax.tick_params(axis="y", labelsize=9, colors="gray")
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.spines["left"].set_color("gray")
                ax.spines["bottom"].set_color("gray")

            # blank out unused slots in the last row of this team's block
            n_slots = len(grid_rows) * ncols
            for _row, col in list((r, c) for r in grid_rows for c in range(ncols))[n_players:n_slots]:
                fig.add_subplot(gs[_row, col]).axis("off")

        # both teams' lineups against one shared +/- axis — drawn after the
        # per-team loop because it needs every team's stints at once
        combined_lineup_ax = None
        if ("lineup_combined",) in row_labels:
            combined_row = row_labels.index(("lineup_combined",))
            combined_lineup_ax = fig.add_subplot(gs[combined_row, 0])
            combined_boxes, combined_lineup_colors = _draw_combined_lineup_stint_panel(
                combined_lineup_ax, teams, stint_segments, margin_timeline,
                margin_home_team, tick_positions, tick_labels,
                fig_w_px, fig_h_px, player_color=all_player_colors,
            )
            stint_hover_boxes.extend(combined_boxes)
            # the lineup box score tables now sit around THIS panel, so
            # their row colours (and the lu-hl plane highlights) follow its
            # cool/warm wheels, not the hidden per-team panels'
            lineup_colors_by_team.update({
                t: {lu: to_hex(c) for lu, c in cmap.items()}
                for t, cmap in combined_lineup_colors.items()
            })

        fig.text(0.5, 1.0, header_prose, transform=fig.transFigure, fontsize=_HEADER_FONTSIZE, color="lightgray", ha="center", va="top", family="monospace")
        table_y = 1.0 - prose_inches / total_inches
        fig.text(
            _HEADER_LEFT_MARGIN, table_y, header_table, transform=fig.transFigure,
            fontsize=_HEADER_FONTSIZE, color="lightgray", ha="left", va="top", family="monospace",
        )

        tooltip_boxes = list(stint_hover_boxes)

        # resolve each player title's on-canvas pixel bbox now (needs a draw
        # so text extents are known) into a hover target revealing that
        # player's full-game box score line, pinned in the same place as the
        # stint hovers' lines (just above the plot title)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        # resolve each band hover's box score row highlight into the row's
        # on-canvas rect: the box score text block's extent divided evenly
        # over its lines (line 0 is the header, players follow in order)
        for b in stint_hover_boxes:
            hl = b.pop("_hl", None)
            if hl is None:
                continue
            hl_team, row_idx = hl
            # rows sit on the per-line baseline grid now (see
            # _draw_box_text_lines), so rects come from the grid, not from
            # dividing a block extent that no longer exists
            bbox = box_text_artists[hl_team].get_window_extent(renderer=renderer)
            body_top_frac = box_layers_by_team[hl_team][0]
            pitch_px = box_fontsize * box_linespacing * fig.dpi / 72
            n_chars = len(official_box_text_by_team[hl_team].split("\n")[0])
            row_w_px = n_chars * box_fontsize * (fig.dpi / 72) * _MONO_ADVANCE_EM
            b["row_hl"] = {
                "left": bbox.x0 / fig_w_px,
                "top": 1 - body_top_frac + (row_idx + 1) * pitch_px / fig_h_px,
                "width": row_w_px / fig_w_px,
                "height": pitch_px / fig_h_px,
            }

        # hovering anywhere on a player's box score row (name or data)
        # highlights the whole row and the player's stint segments in the
        # rotation band — one hover target per row, plus the highlight rects
        # it reveals (connected per player by a keyed :has() CSS rule)
        for team in teams:
            bbox = box_text_artists[team].get_window_extent(renderer=renderer)
            body_top_frac = box_layers_by_team[team][0]
            pitch_px = box_fontsize * box_linespacing * fig.dpi / 72
            n_chars = len(official_box_text_by_team[team].split("\n")[0])
            row_w_px = n_chars * box_fontsize * (fig.dpi / 72) * _MONO_ADVANCE_EM
            for i, name in enumerate(box_names_by_team[team]):
                row = {
                    "left": bbox.x0 / fig_w_px,
                    "top": 1 - body_top_frac + (i + 1) * pitch_px / fig_h_px,
                    "width": row_w_px / fig_w_px,
                    "height": pitch_px / fig_h_px,
                }
                tooltip_boxes.append({
                    **row,
                    "name_hover_key": re.sub(r"[^A-Za-z0-9]", "", f"{team}{name}"),
                    "hl_color": player_hex_by_team[team].get(name, "#aaaaaa"),
                    "hl_rects": [row] + band_rects_by_team.get(team, {}).get(name, []),
                })

        for title_obj, box_tooltip, label_top in title_tooltips:
            bbox = title_obj.get_window_extent(renderer=renderer)
            tooltip_boxes.append({
                "left": bbox.x0 / fig_w_px,
                "top": 1 - (bbox.y1 / fig_h_px),
                "width": bbox.width / fig_w_px,
                "height": bbox.height / fig_h_px,
                "line_tooltip": box_tooltip,
                "label_left": _BOX_SCORE_LEFT_MARGIN,
                "label_top": label_top,
            })

        # horizontal cut lines (fraction from the top of the figure) that
        # split the rendered PNG into stackable slices: per team, the summary
        # panel + box score stay visible, the player-plot grid goes behind a
        # "players" toggle, and the lineup-stint panel (followed in the HTML
        # by that team's lineup box score) behind a "lineups" toggle. Cuts
        # land in the gaps around the player grid; each section's bottom cut
        # sits exactly one standard chart gap — the blank between two
        # adjacent player charts, measured from their rendered extents —
        # below the lineup panel's tick labels, so the margin-less HTML
        # table lands at the same vertical spacing as the charts.
        def _gap_mid_from_top(idx_above, idx_below):
            above_bottom = 1 - gs[idx_above, 0].get_position(fig).y0
            below_top = 1 - gs[idx_below, 0].get_position(fig).y1
            return (above_bottom + below_top) / 2

        first_team_axes = player_axes[teams[0]]
        std_blank_px = (
            first_team_axes[0].get_tightbbox(renderer).y0
            - first_team_axes[1].get_tightbbox(renderer).y1
        )
        # every toggled segment opens with the same blank between its
        # toggle row and its first item: TWO box score lines. A line is
        # 1.54cqw x 1.5 line-height, and cqw resolves against the image
        # width (= fig_w_px), so 2 lines = 4.62% of the figure width.
        two_lines_px = 2 * _BOX_LINE_FRAC * fig_w_px
        slices = []
        for i, team in enumerate(teams):
            if i == 0:
                # the first team's block opens with the Karma panel (it has
                # no team panel of its own): the always-visible header ends
                # two lines above the Karma title, and the team slice
                # picks up from there
                karma_top = (
                    1 - event_ax.get_tightbbox(renderer).y1 / fig_h_px
                    - two_lines_px / fig_h_px
                )
                slices.append({"top": 0.0, "bottom": karma_top})
                section_top = karma_top
            else:
                # start the team's slice exactly two lines above its
                # summary-panel title, so the wrapper opens with the same
                # blank between its toggle row and the team plot; the
                # blank remaining above that is cropped away
                content_top = 1 - summary_axes[team].get_tightbbox(renderer).y1 / fig_h_px
                section_top = content_top - two_lines_px / fig_h_px
            box_idx = row_labels.index(("box_score", team))
            player_rows = [j for j, r in enumerate(row_labels) if r[0] == "team" and r[1] == team]
            stint_idx = row_labels.index(("lineup_stints", team))
            players_top = _gap_mid_from_top(box_idx, player_rows[0])
            # the Players segment likewise opens two lines above its first
            # player-chart title (players_top, the mid-row gap, stays the
            # TEAM slice's bottom — the region between the two is blank
            # and simply appears in neither crop)
            players_row_top = 1 - max(
                a.get_tightbbox(renderer).y1 for a in player_axes[team][:ncols]
            ) / fig_h_px
            players_slice_top = players_row_top - two_lines_px / fig_h_px
            players_bottom = _gap_mid_from_top(player_rows[-1], stint_idx)
            stint_bottom_px = stint_axes[team].get_tightbbox(renderer).y0
            section_bottom = min(1 - (stint_bottom_px - std_blank_px) / fig_h_px, 1.0)
            # internal cut between the Karma panel and the box score, so
            # the HTML can stack them as two images in one chart-wrap: the
            # "hide stints" switch swaps only the Karma image, the per-32
            # switch only the box score image
            karma_idx = row_labels.index(("event_sum",) if i == 0 else ("team_summary", team))
            karma_cut = _gap_mid_from_top(karma_idx, box_idx)
            slices.extend([
                # the team's Karma panel and box score toggle under the
                # team's own name (label stays the team name while open)
                # and start visible, unlike the players/lineups toggles.
                # team_box marks the slice that carries the switches.
                {"top": section_top, "bottom": players_top, "team": team,
                 "toggle": team, "toggle_open": team, "toggle_open_default": True,
                 "team_box": True, "tb_label_top": box_label_tops[team],
                 "karma_cut": karma_cut, "kb_label_top": kb_label_tops[team],
                 "box_right": (box_text_artists[team].get_window_extent(renderer).x0
                               + len(official_box_text_by_team[team].split("\n")[0])
                               * box_fontsize * (fig.dpi / 72) * _MONO_ADVANCE_EM) / fig_w_px},
                {"top": players_slice_top, "bottom": players_bottom, "team": team, "toggle": "Players"},
                # the per-team lineup plot is OFF the page (superseded by
                # the combined lineups section below) — its slice stays
                # commented out, not deleted, in case it comes back:
                # {"top": players_bottom, "bottom": section_bottom, "team": team, "toggle": "Lineups",
                #  "lineup_box": True, "lineup_colors": lineup_colors_by_team.get(team, {}),
                #  "box_right": box_text_artists[team].get_window_extent(renderer).x1 / fig_w_px},
            ])
            section_top = section_bottom

        # the page is composed only from the slices listed above, so the
        # combined-lineup row needs its own or it is drawn into the figure
        # and then cropped away. It is the page's ONE lineups section:
        # the first team's lineup box score, then the combined plot, then
        # the second team's box score (assembled in the HTML step).
        if combined_lineup_ax is not None:
            # crop BOTH edges to the panel's tight bbox plus the SAME blank,
            # so the plot sits centred between the two lineup box scores.
            # The blank must also hold a hover readout: 5 lines (header,
            # values, players, in, out) at 1.54cqw x 1.5 line-height is
            # ~11.6% of the image width plus box padding, so reserve 13.5% (the readout
            # scales with the image, so the fit holds at any viewport
            # width). Never less than the page's standard gap.
            combined_bb = combined_lineup_ax.get_tightbbox(renderer)
            combined_blank_px = max(std_blank_px, (_READOUT_LINES * _BOX_LINE_FRAC + _READOUT_PAD_CQW / 100) * fig_w_px)
            slices.append({
                "top": max(1 - (combined_bb.y1 + combined_blank_px) / fig_h_px, 0.0),
                "bottom": min(1 - (combined_bb.y0 - combined_blank_px) / fig_h_px, 1.0),
                "toggle": "Lineups", "toggle_open_default": True,
                "combined_lineups": True, "teams": list(teams),
                "lineup_colors_by_team": {
                    t: lineup_colors_by_team.get(t, {}) for t in teams},
                "box_right_by_team": {
                    t: (box_text_artists[t].get_window_extent(renderer).x0
                        + len(official_box_text_by_team[t].split("\n")[0])
                        * box_fontsize * (fig.dpi / 72) * _MONO_ADVANCE_EM) / fig_w_px
                    for t in teams},
            })

        def redraw_rate_views():
            """Mutate the figure in place for the single alternate render:
            each lineup panel gets per-8-minute diamonds and a rescaled
            y-axis (the score twin axis is left untouched), and each team
            box score is rewritten as per-32-minute rates. The "show per 8"
            and "show per 32" switches each swap in their own slice of this
            render, so the two views are independent."""
            for team in teams:
                ax = stint_axes[team]
                ax.clear()
                _draw_lineup_stint_panel(
                    ax, team, stint_segments[stint_segments["teamTricode"] == team],
                    margin_timeline, margin_home_team, tick_positions, tick_labels,
                    team_score_limits, fig_w_px, fig_h_px,
                    per_minutes=8, draw_score_axis=False,
                )

                box_label_artists[team].set_text(f"{team} box score (per 32)")
                body_top, layer_artists = box_layers_by_team[team]
                for artist in layer_artists:
                    artist.remove()
                margin = pts_by_team[team] - pts_by_team[next(t for t in teams if t != team)]
                text32 = _format_official_box_score(
                    boxes_by_team[team], team, team_margin=margin, per_minutes=32,
                )
                gold32, red32, grey32 = _box_score_overlays(boxes_by_team[team], team, per_minutes=32)
                for text, color in (
                    (text32, "lightgray"), (gold32, "goldenrod"),
                    (red32, "red"), (grey32, "gray"),
                ):
                    _draw_box_text_lines(
                        fig, _BOX_SCORE_LEFT_MARGIN, body_top, text, color,
                        box_fontsize, box_linespacing, fig_h_px,
                    )

    return fig, tooltip_boxes, slices, redraw_rate_views, karma_layer_axes


def plot_plus_minus_by_player_html(
    csv_path: Path, output_path: Path, game_info: dict | None = None, tooltips: bool = False,
) -> Path:
    """Same chart as `plot_plus_minus_by_player`, saved as a static,
    non-interactive standalone HTML file — the figure rendered to SVG,
    never PNG. Each distinct render (full, rate views, karma base and
    layers) is embedded exactly ONCE as a data URI in a CSS custom
    property, and every page slice is a div showing a vertical crop of
    one render via background-size/background-position — so the many
    slices share the handful of renders instead of each carrying its own
    copy. SVG-as-background sidesteps Chrome's rendering bug with very
    tall INLINE SVGs full of clip-paths (blank top of page until
    scrolled), the reason these pages originally used PNGs.

    The page reads top to bottom as: title block and per-period linescore
    (always visible), a "Summary" toggle with the AP game recap (closed by
    default; omitted if no recap is available), then three toggles per team
    — the team's summary panel
    (team plus/minus, event markers, team score) and box score under the
    team's own name (open by default; the label stays the team name), its
    per-player plus/minus grid under "Players", and its lineup-stint plot
    plus lineup box score (an HTML table, not part of the PNG) under
    "Lineups" (both closed by default, reading "Less" while open). All
    toggles are native <details>, no JS. The single rendered PNG is sliced
    at those boundaries and stacked so everything still lines up seamlessly
    when expanded.

    If `tooltips` is True (pure CSS, no JS; off by default): every hover
    reveals a box score line pinned above the hovered plot's title, in the
    box score (monospace) font — a player's title shows their full-game
    box score row, a stint's shaded region shows that stint's own stats,
    and a lineup stint shows that stint's line above the lineup panel's
    title."""
    fig, tooltip_boxes, slices, redraw_rate_views, karma_layers = (
        _build_plus_minus_by_player_figure(csv_path, game_info, tooltips=tooltips)
    )

    # per-team schedule stacks in the top corners: the HOME team's
    # previous/next game upper-left, the visitor's upper-right, rows like
    # "Prev OKC @ NYK 10/10/26". A row is a link when that game's page
    # exists in this collection (sibling pbp CSV), plain text when the
    # game happened but has no page, and "--" past the schedule's ends.
    # Each stack also links its team's season page when that page exists
    # in the collection.
    nav_html = ""
    try:
        from nba_pbp.edge import league_history as _league_history
        _gid = str(pd.read_csv(csv_path, usecols=["gameId"], dtype=str)
                   .iloc[0, 0]).zfill(10)
        _y = 2000 + int(_gid[3:5])
        _hist = _league_history(f"{_y}-{str(_y + 1)[-2:]}")
        _rows = _hist[_hist["GAME_ID"] == _gid]

        def _fmt(row):
            _m = str(row["MATCHUP"])
            _d = pd.Timestamp(row["GAME_DATE"])
            return (f'{row["TEAM_ABBREVIATION"]} '
                    + ("@ " if "@" in _m else "vs ") + _m.split()[-1]
                    + f" {_d.month}/{_d.day}/{_d.strftime('%y')}")

        for _, _trow in _rows.iterrows():
            _t = str(_trow["TEAM_ABBREVIATION"])
            _side = "l" if "@" not in str(_trow["MATCHUP"]) else "r"
            _tg = (_hist[_hist["TEAM_ABBREVIATION"] == _t]
                   .sort_values("GAME_DATE").reset_index(drop=True))
            _pos = int(_tg.index[_tg["GAME_ID"] == _gid][0])
            _stack = []
            for _lab, _idx in (("Prev", _pos - 1), ("Next", _pos + 1)):
                if 0 <= _idx < len(_tg):
                    _g = _tg.iloc[_idx]
                    _txt = f"{_lab} {_fmt(_g)}"
                    if (csv_path.parent / f'pbp_{_g["GAME_ID"]}.csv').exists():
                        _stack.append(
                            (f'href="pm_players_{_g["GAME_ID"]}.html"', _txt))
                    else:
                        _stack.append((None, _txt))
                else:
                    _stack.append((None, f"{_lab} --"))
            if (csv_path.parent / f"season_events_2d_{_t.lower()}.html").exists():
                _stack.append((f'href="season_events_2d_{_t.lower()}.html"',
                               f"{_t} {_y}-{_y + 1}"))
            for _i, (_href, _txt) in enumerate(_stack):
                _pos_css = f'style="top:calc(8px + {_i * 1.5:.1f}em);"'
                if _href:
                    nav_html += (f'<a class="gnav gnav-{_side}" {_pos_css} '
                                 f'{_href}>{_txt}</a>')
                else:
                    nav_html += (f'<span class="gnav gnavn gnav-{_side}" '
                                 f'{_pos_css}>{_txt}</span>')
    except Exception:
        nav_html = ""

    def _render(transparent=False):
        # text as paths: these SVGs are consumed as IMAGES (CSS
        # backgrounds), where Chrome refuses to load fonts, so glyph
        # positions must be baked in
        return _fig_svg(fig, transparent=transparent, text_as_paths=True)

    fig_w_in, fig_h_in = fig.get_size_inches()
    img_w, img_h = fig_w_in * 150, fig_h_in * 150

    # the karma LAYERS are hidden up front: every slice composes its
    # karma band from the furniture base + the per-layer images, so no
    # other render needs karma content
    for a in (karma_layers["band"] + karma_layers["margin"]
              + karma_layers["bars"] + karma_layers["points"]
              + karma_layers["events"] + karma_layers["vevents"]
              + karma_layers["hevents"]):
        a.set_visible(False)

    # Every page slice gets its own BAND-LIMITED render: same full-page
    # canvas (so the slicing math is untouched), but only the artists in
    # that slice's vertical band are drawn. One shared full-page render
    # would be both too big (Chrome caps a single CSS value around
    # 2 MiB) and too slow (Chrome re-rasterizes the whole vector page
    # whenever a slice scrolls in; small per-band files rasterize
    # lazily and cheaply).
    renders: dict[str, str] = {}
    karma_artists = {id(a) for lst in karma_layers.values() for a in lst}
    karma_axes = {a.axes for lst in karma_layers.values()
                  for a in lst if getattr(a, "axes", None) is not None}
    orig_ax_vis = {id(ax): ax.get_visible() for ax in fig.axes}
    orig_txt_vis = {id(t): t.get_visible() for t in fig.texts}

    def _apply_band(top, bot):
        """Show only the axes / figure texts whose position intersects
        the [top, bot) band (fractions of page height, top-down). The
        margin is generous: an artist near a boundary lands in both
        neighboring renders, and the background crop trims it exactly.
        Karma-layer artists keep whatever the layer logic set."""
        y1, y0 = 1 - top, 1 - bot  # figure coords, bottom-up
        pad = 0.01
        for ax in fig.axes:
            p = ax.get_position()
            ax.set_visible(orig_ax_vis.get(id(ax), True)
                           and p.y1 > y0 - pad and p.y0 < y1 + pad)
        for t in fig.texts:
            if id(t) in karma_artists:
                continue
            ty = t.get_position()[1]
            t.set_visible(orig_txt_vis.get(id(t), True)
                          and y0 - pad <= ty <= y1 + pad)

    def _crop_svg(svg, top, bot):
        """Rewrite the SVG root so the canvas IS the band: the browser
        then lays out and rasterizes only band-sized images instead of
        full-page canvases that are empty outside the band."""
        import re as _re

        m = _re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
        w, h = float(m.group(1)), float(m.group(2))
        span = bot - top
        svg = svg.replace(
            m.group(0), f'viewBox="0 {top * h:.2f} {w} {span * h:.2f}"', 1)
        hm = _re.search(r'height="([\d.]+)pt"', svg)
        return svg.replace(
            hm.group(0), f'height="{float(hm.group(1)) * span:.2f}pt"', 1)

    def _band_render(name, top, bot):
        _apply_band(top, bot)
        renders[name] = _crop_svg(_render(), top, bot)

    def _layer_band_render(name, top, bot):
        """A transparent render of the currently-toggled karma layer,
        restricted to the karma axes inside the band (so each team's
        layer file carries just that team's marks). The karma "layers"
        are overlay AXES, so the band filter must AND with the toggle
        state — forcing visibility here would re-show every layer — and
        restore it afterwards so the toggle sequence stays intact."""
        y1, y0 = 1 - top, 1 - bot
        pad = 0.01
        prev_ax = {ax: ax.get_visible() for ax in fig.axes}
        prev_txt = {t: t.get_visible() for t in fig.texts}
        for ax in fig.axes:
            p = ax.get_position()
            ax.set_visible(prev_ax[ax] and ax in karma_axes
                           and p.y1 > y0 - pad and p.y0 < y1 + pad)
        for t in fig.texts:
            if id(t) not in karma_artists:
                t.set_visible(False)
        renders[name] = _crop_svg(_render(transparent=True), top, bot)
        for ax, v in prev_ax.items():
            ax.set_visible(v)
        for t, v in prev_txt.items():
            t.set_visible(v)

    for idx, s in enumerate(slices):
        if s.get("team_box"):
            _band_render(f"--im-s{idx}-k", s["top"], s["karma_cut"])
            _band_render(f"--im-s{idx}-b", s["karma_cut"], s["bottom"])
        else:
            _band_render(f"--im-s{idx}", s["top"], s["bottom"])

    # alternate renders with the lineup panels redrawn as per-8-minute
    # rates and the team box scores as per-32-minute rates — each rate
    # switch swaps in its own band
    redraw_rate_views()
    for idx, s in enumerate(slices):
        if s.get("lineup_box"):
            _band_render(f"--im-s{idx}-rate", s["top"], s["bottom"])
        elif s.get("team_box"):
            _band_render(f"--im-s{idx}-brate", s["karma_cut"], s["bottom"])

    # the toggleable karma layers render one at a time, transparently —
    # the HTML stacks them over the karma furniture band, and each
    # "hide" switch simply hides its layer image, so toggles combine
    # freely without one baked image per combination. One render per
    # layer PER TEAM, cropped to that team's karma band.
    layer_groups = [("lanes", "band"), ("scores", "points"),
                    ("pm", "margin"), ("bars", "bars"), ("events", "events"),
                    ("vevents", "vevents"), ("hevents", "hevents")]
    for a in karma_layers["main"]:
        a.set_visible(False)
    for idx, s_ in enumerate(slices):
        if not s_.get("team_box"):
            continue
        for css_name, key in layer_groups:
            for a in karma_layers[key]:
                a.set_visible(True)
            _layer_band_render(f"--im-s{idx}-{css_name}",
                               s_["top"], s_["karma_cut"])
            for a in karma_layers[key]:
                a.set_visible(False)
    plt.close(fig)

    def _overlays_for_slice(s):
        """Overlay divs for the tooltips whose vertical center lands in this
        slice, with their top/height remapped from full-image fraction to
        this slice's local fraction (x is unchanged — slices are full width).
        Each hover target is an invisible .tt over its trigger region plus a
        sibling box score line pinned above the panel/plot label, revealed
        by the .tt's hover."""
        if not tooltips:
            return ""
        span = s["bottom"] - s["top"]
        # lineup key -> hex, for the plane-highlight rects the box score
        # row hovers reveal
        lu_hex_by_key = {
            _lu_key(s["team"], code): c
            for code, c in (s.get("lineup_colors") or {}).items()
        }
        # the combined lineups slice carries BOTH teams' colour maps
        for t, cmap in (s.get("lineup_colors_by_team") or {}).items():
            lu_hex_by_key.update({_lu_key(t, code): c for code, c in cmap.items()})
        parts = []
        for b in tooltip_boxes:
            center = b["top"] + b["height"] / 2
            if not (s["top"] <= center < s["bottom"]):
                continue
            local_top = (b["top"] - s["top"]) / span
            local_h = b["height"] / span
            if b.get("name_hover_key"):
                # box score name cell: an invisible keyed target plus the
                # highlight rects (row data + band stints) its :has() rule
                # reveals
                key = b["name_hover_key"]
                parts.append(
                    f'<div class="tt bx-name-{key}" style="left:{b["left"] * 100:.3f}%;'
                    f'top:{local_top * 100:.3f}%;width:{b["width"] * 100:.3f}%;'
                    f'height:{local_h * 100:.3f}%;"></div>'
                )
                for r in b["hl_rects"]:
                    parts.append(
                        f'<div class="bx-hl bx-hl-{key}" style="left:{r["left"] * 100:.3f}%;'
                        f'top:{(r["top"] - s["top"]) / span * 100:.3f}%;'
                        f'width:{r["width"] * 100:.3f}%;height:{r["height"] / span * 100:.3f}%;'
                        f'background:{b["hl_color"]}50;"></div>'
                    )
                continue
            label_top = (b["label_top"] - s["top"]) / span
            if b.get("player_line"):
                # box score header in the default gray, the player's own row
                # in their chart color, plus a translucent highlight bar over
                # that player's row in the team box score
                sibling = (
                    f'<div class="tt-name" style="left:{b["label_left"] * 100:.3f}%;'
                    f'top:{label_top * 100:.3f}%;">{_box_score_header_line()}\n'
                    f'<span style="color:{b["name_color"]};">{b["player_line"]}</span></div>'
                )
                if b.get("row_hl"):
                    r = b["row_hl"]
                    sibling += (
                        f'<div class="tt-hl" style="left:{r["left"] * 100:.3f}%;'
                        f'top:{(r["top"] - s["top"]) / span * 100:.3f}%;'
                        f'width:{r["width"] * 100:.3f}%;height:{r["height"] / span * 100:.3f}%;'
                        f'background:{b["name_color"]}38;"></div>'
                    )
            else:
                # tt-below anchors its TOP at label_top (no translateY),
                # for readouts that sit under the plot instead of above it
                line_cls = "tt-line tt-below" if b.get("label_below") else "tt-line"
                if b.get("pin_id") is not None:
                    line_cls += f' ttl-{b["pin_id"]}'
                sibling = (
                    f'<div class="{line_cls}" style="left:{b["label_left"] * 100:.3f}%;'
                    f'top:{label_top * 100:.3f}%;">{b["line_tooltip"]}</div>'
                )
            if b.get("marker_left") is not None:
                # a ring over the stint's own +/- marker, revealed with the
                # tooltip so the hovered lineup's diamond/dot lights up
                mk_cls = "mk-hl" + (f' mkh-{b["pin_id"]}' if b.get("pin_id") is not None else "")
                sibling += (
                    f'<div class="{mk_cls}" style="left:{b["marker_left"] * 100:.3f}%;'
                    f'top:{(b["marker_top"] - s["top"]) / span * 100:.3f}%;"></div>'
                )
            # lineup stints carry a data-lu key so :has() rules can highlight
            # their row in the lineup box score while hovered; the reverse
            # hover (box score row -> planes) reveals a keyed highlight
            # rect over each of the lineup's planes
            attr = f' data-lu="{b["lu_key"]}"' if b.get("lu_key") else ""
            if b.get("lu_key") and b["lu_key"] in lu_hex_by_key:
                parts.append(
                    f'<div class="lu-hl lu-hl-{b["lu_key"]}" style="left:{b["left"] * 100:.3f}%;'
                    f'top:{local_top * 100:.3f}%;width:{b["width"] * 100:.3f}%;'
                    f'height:{local_h * 100:.3f}%;background:{lu_hex_by_key[b["lu_key"]]}40;"></div>'
                )
            cls, var = "tt", ""
            if b.get("seg_color"):
                # stint planes/segments highlight themselves under the
                # cursor, in the player's color
                cls = "tt tt-seg"
                var = f"--c:{b['seg_color']};"
            if b.get("player_key"):
                # keyed so hovering this stint reveals that player's whole
                # highlight set (box score row + all their stints)
                cls += f" pl-{b['player_key']}"
            geo = (f'left:{b["left"] * 100:.3f}%;top:{local_top * 100:.3f}%;'
                   f'width:{b["width"] * 100:.3f}%;height:{local_h * 100:.3f}%;')
            if b.get("pin_id") is not None:
                # click-to-pin: the hover target is a LABEL toggling this
                # stint's radio; the unpin twin (earlier in DOM, above via
                # z-index, shown only while pinned) points back at lus-none
                # so a second click deselects. Both keep the tt classes, so
                # every hover behaviour is identical to the plain box.
                n, g = b["pin_id"], b.get("pin_group", 0)
                parts.append(
                    f'<label class="{cls} ttg-{g} lup lup-{n}" for="lus-g{g}-none"{attr} style="{var}{geo}"></label>'
                    f'<label class="{cls} ttg-{g}"{attr} for="lus-{n}" style="{var}{geo}"></label>'
                    f'{sibling}'
                )
            else:
                parts.append(
                    f'<div class="{cls}"{attr} style="{var}{geo}"></div>'
                    f'{sibling}'
                )
        return "\n".join(parts)

    from nba_pbp.plusminus import compute_lineup_box_score
    lineup_box = compute_lineup_box_score(csv_path)

    # AP game recap (via ESPN), shown in a "Summary" toggle right under the
    # linescore — closed by default; skipped entirely if no recap is found
    import html as _html

    from nba_pbp.client import get_game_recap

    game_id = pd.read_csv(csv_path, usecols=["gameId"], dtype=str).iloc[0, 0].zfill(10)
    recap = get_game_recap(game_id)
    recap_html = ""
    if recap:
        # paragraphs are separated by blank lines (and sometimes <p> tags);
        # strip all other markup (ESPN wraps names/teams in <a> links)
        paragraphs = "".join(
            f"<p>{_html.escape(text)}</p>"
            for chunk in re.split(r"</p>|\n\s*\n", recap["story"])
            if (text := " ".join(re.sub(r"<[^>]+>", " ", chunk).split()))
        )
        recap_html = (
            '<details class="more"><summary>'
            '<span class="more-txt">Summary</span>'
            '<span class="less-txt">Less</span></summary>\n'
            '<div class="chart-wrap"><div class="recap">'
            f'<span class="recap-headline">{_html.escape(recap["headline"])}</span>\n'
            f'{paragraphs}'
            '<p class="recap-source">AP recap, via ESPN</p>'
            '</div></div>\n</details>'
        )

    # every render is embedded exactly once, as a data URI in a CSS
    # custom property; each page slice is a div showing a vertical band
    # of its render via background positioning. Images (not inline SVG):
    # Chrome rasterizes and caches each image, where inlining these
    # trees — or <use>-cloning them per slice — made the renderer
    # unusably slow, and inline SVG was what the original PNG pipeline
    # existed to avoid in the first place.

    def _slice_svg(var, s, classes="", alt=""):
        """Rows [top, bottom) of one shared render: the background is
        scaled so the full image spans 1/span of the div's height, then
        offset so the wanted band is the visible part; aspect-ratio
        keeps the div the exact shape of the band at any page width."""
        span = s["bottom"] - s["top"]
        cls = f"simg {classes}".strip()
        role = f' role="img" aria-label="{alt}"' if alt else ""
        return (
            f'<div class="{cls}"{role} style="background-image:var({var});'
            f"background-size:100% 100%;"
            f'aspect-ratio:{img_w:.0f}/{img_h * span:.1f};"></div>'
        )

    sections = []
    for idx, s in enumerate(slices):
        img_tag = _slice_svg(f"--im-s{idx}", s, alt="Plus/minus by player")
        if s.get("lineup_box"):
            # two renders of the lineup panel — per-game and per-8 diamonds/
            # y-axis — swapped by the same per 8 / per game switch as the
            # tables
            img_tag = (
                _slice_svg(f"--im-s{idx}", s, "lu-img-raw", "Lineups")
                + _slice_svg(f"--im-s{idx}-rate", s, "lu-img-rate",
                             "Lineups, per 8 minutes")
            )
        elif s.get("team_box"):
            # the Karma panel and box score as two stacked slices (they
            # butt together seamlessly, so overlay math is unchanged): the
            # "hide stints" switch swaps the Karma slice between the
            # lanes-on and lanes-off renders, and the per-32 switch swaps
            # the box score slice — independently
            ks = {"top": s["top"], "bottom": s["karma_cut"]}
            bs = {"top": s["karma_cut"], "bottom": s["bottom"]}
            img_tag = (
                _slice_svg(f"--im-s{idx}-k", ks, "kb-img-base", "Karma")
                + _slice_svg(f"--im-s{idx}-lanes", ks, "kb-ov kb-ov-lanes", "Karma stint lanes")
                + _slice_svg(f"--im-s{idx}-scores", ks, "kb-ov kb-ov-scores", "Karma cumulative scores")
                + _slice_svg(f"--im-s{idx}-pm", ks, "kb-ov kb-ov-pm", "Karma +/- line")
                + _slice_svg(f"--im-s{idx}-bars", ks, "kb-ov kb-ov-bars", "Karma event bars")
                + _slice_svg(f"--im-s{idx}-events", ks, "kb-ov kb-ov-events",
                             "Karma per-player event markers (pEvents)")
                + _slice_svg(f"--im-s{idx}-vevents", ks, "kb-ov kb-ov-vevents",
                             "Karma per-minute event columns (vEvents)")
                + _slice_svg(f"--im-s{idx}-hevents", ks, "kb-ov kb-ov-hevents",
                             "Karma left-packed event rows (hEvents)")
                + _slice_svg(f"--im-s{idx}-b", bs, "tb-img-raw", "Team box score")
                + _slice_svg(f"--im-s{idx}-brate", bs, "tb-img-rate",
                             "Team box score, per 32 minutes")
            )
        # overlays are positioned in % of the IMAGE, so they live in their
        # own positioned box around just the images — the lineup slice's
        # chart-wrap also holds the flowing HTML box score below, which
        # must not stretch the overlay geometry
        inner = f'<div class="img-box">\n{img_tag}\n{_overlays_for_slice(s)}\n</div>'
        if s.get("team_box"):
            # the per 32 / per game switch, right-justified on the box score
            # label line (right edge on the table's right edge)
            span = s["bottom"] - s["top"]
            btn_top = (s["tb_label_top"] - s["top"]) / span * 100
            inner += (
                f'\n<details class="lu-toggle tb-per32"><summary style="'
                f'right:{(1 - s["box_right"]) * 100:.3f}%;top:{btn_top:.3f}%;">'
                '<span class="more-txt">Show per 32</span>'
                '<span class="less-txt">Show per game</span></summary></details>'
            )
            # the hide / show stints switch, right-justified on the Karma
            # panel's title line, with the hide / show +/- switch to its
            # left (offset in % of the wrap width, like the cqw-sized
            # labels, so the two scale together)
            kb_top = (s["kb_label_top"] - s["top"]) / span * 100
            inner += (
                f'\n<details class="lu-toggle kb-hide"><summary style="'
                f'right:{(1 - s["box_right"]) * 100:.3f}%;top:{kb_top:.3f}%;">'
                '<span class="more-txt">Hide Stints</span>'
                '<span class="less-txt">Show Stints</span></summary></details>'
                f'\n<details class="lu-toggle pm-hide"><summary style="'
                f'right:{(1 - s["box_right"]) * 100 + 13:.3f}%;top:{kb_top:.3f}%;">'
                '<span class="more-txt">Hide +/-</span>'
                '<span class="less-txt">Show +/-</span></summary></details>'
                f'\n<details class="lu-toggle bar-hide"><summary style="'
                f'right:{(1 - s["box_right"]) * 100 + 23.5:.3f}%;top:{kb_top:.3f}%;">'
                '<span class="more-txt">Hide Karma</span>'
                '<span class="less-txt">Show Karma</span></summary></details>'
                f'\n<details class="lu-toggle sc-hide"><summary style="'
                f'right:{(1 - s["box_right"]) * 100 + 37:.3f}%;top:{kb_top:.3f}%;">'
                '<span class="more-txt">Hide Scores</span>'
                '<span class="less-txt">Show Scores</span></summary></details>'
            )
            # the event-layer cycler: a hidden radio group (pure CSS state
            # machine). The visible label names the presentation currently
            # SHOWN, and clicking it advances to the next state — no
            # Events -> player Events (pEvents) -> +/- Events (vEvents)
            # -> total Events (hEvents) -> no Events. The radios sit
            # before .img-box so `:checked ~` rules can reach both the
            # layer images and the labels.
            rid = f"ev-{s['team']}"
            inner = "".join(
                f'<input type="radio" class="ev-st ev-st{i}" name="{rid}"'
                f' id="{rid}-{i}"{" checked" if i == 0 else ""}>'
                for i in range(4)
            ) + inner
            ev_right = (1 - s["box_right"]) * 100 + 51
            inner += "".join(
                f'\n<label class="ev-lbl ev-lbl{i}" for="{rid}-{(i + 1) % 4}"'
                f' style="right:{ev_right:.3f}%;top:{kb_top:.3f}%;">{txt}</label>'
                for i, txt in enumerate(
                    ("No Events", "player Events", "+/- Events", "total Events")
                )
            )
        if s.get("lineup_box"):
            # the lineup box score always shows with the lineups section. On
            # its title line, right-justified (right edge on the table's
            # right edge), a per 8 / per game switch: open shows the
            # per-8-minutes table instead of the per-game totals, and the
            # label flips to "per game"
            per8_switch = (
                f'<details class="lu-toggle lu-per8"><summary style="'
                f'right:{(1 - s["box_right"]) * 100:.3f}%;top:0;">'
                '<span class="more-txt">Show per 8</span>'
                '<span class="less-txt">Show per game</span></summary></details>'
            )
            raw_tbl = _lineup_box_score_html(lineup_box, s["team"], s.get("lineup_colors"))
            rate_tbl = _lineup_box_score_html(
                lineup_box, s["team"], s.get("lineup_colors"), per_minutes=8
            )
            inner += (
                '\n<div class="lineup-box">'
                f'{per8_switch}'
                '<span class="lu-raw">'
                f'<span class="lineup-box-title">{s["team"]} Lineups box score</span>\n'
                f'{raw_tbl}</span>'
                '<span class="lu-rate">'
                f'<span class="lineup-box-title">{s["team"]} Lineups box score (per 8)</span>\n'
                f'{rate_tbl}</span>'
                '</div>'
            )
        if s.get("combined_lineups"):
            # the ONE lineups section: first team's box score, the combined
            # plot, second team's box score. Each table keeps its own
            # per-8 switch (scoped per .lineup-box) and its rows wear the
            # combined plot's wheel colours.
            def _lineup_table(team, top_gap=False):
                colors = (s.get("lineup_colors_by_team") or {}).get(team, {})
                br = s.get("box_right_by_team", {}).get(team, 0.9)
                per8_switch = (
                    f'<details class="lu-toggle lu-per8"><summary style="'
                    f'right:{(1 - br) * 100:.3f}%;top:0;">'
                    '<span class="more-txt">Show per 8</span>'
                    '<span class="less-txt">Show per game</span></summary></details>'
                )
                raw_tbl = _lineup_box_score_html(lineup_box, team, colors)
                rate_tbl = _lineup_box_score_html(lineup_box, team, colors, per_minutes=8)
                # the section's first item opens the same TWO box score
                # lines below the toggle as the image segments do
                gap = f' style="margin-top:{2 * _BOX_LINE_FRAC * 100:.2f}cqw;"' if top_gap else ""
                return (
                    f'<div class="lineup-box"{gap}>'
                    f'{per8_switch}'
                    '<span class="lu-raw">'
                    f'<span class="lineup-box-title">{team} Lineups box score</span>\n'
                    f'{raw_tbl}</span>'
                    '<span class="lu-rate">'
                    f'<span class="lineup-box-title">{team} Lineups box score (per 8)</span>\n'
                    f'{rate_tbl}</span>'
                    '</div>'
                )
            pins = sorted((b["pin_id"], b.get("pin_group", 0)) for b in tooltip_boxes
                          if b.get("pin_id") is not None)
            groups = sorted({g for _, g in pins})
            # one radio group per half, so a top-team stint and a bottom-team
            # stint can be pinned at the same time (their readouts anchor on
            # opposite sides of the plot, so they never collide)
            radios = "".join(
                f'<input type="radio" class="lusel" name="lusel-g{g}" id="lus-g{g}-none" checked>'
                for g in groups
            ) + "".join(
                f'<input type="radio" class="lusel" name="lusel-g{g}" id="lus-{n}">'
                for n, g in pins
            )
            inner = (radios + "\n" + _lineup_table(s["teams"][0], top_gap=True) + "\n" + inner + "\n"
                     + _lineup_table(s["teams"][-1]))
        wrap = f'<div class="chart-wrap">\n{inner}\n</div>'
        if s.get("toggle"):
            open_attr = " open" if s.get("toggle_open_default") else ""
            sections.append(
                f'<details class="more"{open_attr}><summary>'
                f'<span class="more-txt">{s["toggle"]}</span>'
                f'<span class="less-txt">{s.get("toggle_open", "Less")}</span>'
                f'</summary>\n{wrap}\n</details>'
            )
        else:
            sections.append(wrap)
    if recap_html:
        # right after the always-visible header/linescore slice
        sections.insert(1, recap_html)
    body = "\n".join(sections)

    tooltip_css = ""
    if tooltips:
        tooltip_css = (
            ".tt{position:absolute;}"
            # box score line for a hovered stint plane or plot title, pinned
            # at the panel/plot label (absolute within .chart-wrap) and
            # revealed by its sibling .tt's hover. Monospace, whitespace-
            # aligned to the chart's box scores, sized in cqw (% of the
            # .chart-wrap container/image width) so the ~99-char row scales
            # with the image and always fits. Anchored at the label top and
            # lifted by its own full height (translateY(-100%)) so the
            # block's bottom ends there, clearing the plot below.
            # pointer-events:none so the line (which overlaps the trigger
            # region) never steals hover from it — the box score then clears
            # and the label restores cleanly on mouse-out.
            # the -6px x-shift cancels the box's own horizontal padding, so
            # the popup's monospace TEXT (not its background box) lands
            # exactly on the box score tables' left text edge
            ".tt-line{display:none;position:absolute;background:#222;color:lightgray;"
            "padding:2px 6px;border-radius:4px;font-family:DejaVu Sans Mono,monospace;"
            "font-weight:normal;" + _BOX_FONT_CSS + "white-space:pre;z-index:3;"
            "pointer-events:none;transform:translate(-6px,-100%);box-shadow:0 2px 6px rgba(0,0,0,0.5);}"
            ".tt:hover + .tt-line{display:block;}"
            # variant anchored by its TOP edge — readouts below a plot
            ".tt-line.tt-below{transform:translateX(-6px);}"
            # box score line for a hovered stint segment in the team panel's
            # rotation band — same monospace styling as .tt-line, but below
            # the band's bottom-left corner (no translateY — it hangs below
            # its anchor); the player's row inside it carries their color
            ".tt-name{display:none;position:absolute;background:#222;color:lightgray;"
            "padding:2px 6px;border-radius:4px;font-family:DejaVu Sans Mono,monospace;"
            "font-weight:normal;" + _BOX_FONT_CSS + "white-space:pre;z-index:3;"
            "pointer-events:none;transform:translateX(-6px);box-shadow:0 2px 6px rgba(0,0,0,0.5);}"
            ".tt:hover + .tt-name{display:block;}"
            # translucent bar over the player's row in the team box score,
            # revealed together with its sibling .tt-name
            ".tt-hl{display:none;position:absolute;pointer-events:none;border-radius:2px;}"
            ".tt:hover + .tt-name + .tt-hl{display:block;}"
            # highlight rects revealed by hovering a player's box score row
            # (the row itself + their band stints)
            ".bx-hl{display:none;position:absolute;pointer-events:none;border-radius:2px;}"
            # a hovered band stint segment lights itself up in the player's
            # color (set per element via --c)
            ".tt-seg:hover{background:var(--c);border-radius:2px;}"
            # ring over the hovered lineup stint's own +/- marker (combined
            # panel), revealed together with its tooltip line. Sized in cqw
            # so it tracks the responsive image scale, centred on the
            # marker's baked pixel position.
            ".mk-hl{display:none;position:absolute;pointer-events:none;z-index:2;"
            "width:1.9cqw;aspect-ratio:1;transform:translate(-50%,-50%);"
            "border:2px solid #fff;border-radius:50%;box-shadow:0 0 8px #fff;}"
            ".tt:hover + .tt-line + .mk-hl{display:block;}"
            # click-to-pin (combined lineups plot): hidden radios; the unpin
            # twin sits above its base label only while pinned. Hovering the
            # twin drives the same tooltip/ring chain, one element later.
            ".lusel{display:none;}"
            "label.tt{cursor:pointer;}"
            ".lup{display:none;z-index:2;}"
            ".lup:hover + .tt + .tt-line{display:block;}"
            ".lup:hover + .tt + .tt-line + .mk-hl{display:block;}"
        )
        # per-stint pin rules: while pinned, the band stays lit, the marker
        # stays ringed, its table row stays tinted, and the readout stays up
        # except while some stint is hovered (the hover chain shows that
        # one instead, so exactly one readout is ever visible)
        tooltip_css += "".join(
            f'.chart-wrap:has(#lus-{b["pin_id"]}:checked) .lup-{b["pin_id"]}'
            f"{{display:block;background:var(--c);border-radius:2px;}}"
            f'.chart-wrap:has(#lus-{b["pin_id"]}:checked) .mkh-{b["pin_id"]}{{display:block;}}'
            f'.chart-wrap:has(#lus-{b["pin_id"]}:checked)'
            f':not(:has(label.ttg-{b.get("pin_group", 0)}:hover)) '
            f'.ttl-{b["pin_id"]}{{display:block;}}'
            + (
                f'details:has(#lus-{b["pin_id"]}:checked) .lu-row-{b["lu_key"]}'
                f'{{background:{b["seg_color"]};border-radius:2px;}}'
                f'details:has(#lus-{b["pin_id"]}:checked) .lu-hl-{b["lu_key"]}{{display:block;}}'
                if b.get("lu_key") else ""
            )
            for b in tooltip_boxes if b.get("pin_id") is not None
        )
        # hovering a lineup's stint planes highlights that lineup's row in
        # the lineup box score — one :has() rule per lineup, tinted with the
        # lineup's own color — and hovering the row highlights the lineup's
        # planes in the plot (the .lu-hl rects emitted per plane). Both live
        # inside the same "lineups" <details>, which scopes the match.
        tooltip_css += (
            ".lu-hl{display:none;position:absolute;pointer-events:none;z-index:1;}"
        )
        # one colour map per team, whether it came from a per-team lineups
        # slice ("lineup_colors") or the combined slice, which carries both
        # teams' maps ("lineup_colors_by_team")
        _lu_color_maps = [
            (s["team"], s["lineup_colors"]) for s in slices if s.get("lineup_colors")
        ] + [
            (t, cmap) for s in slices
            for t, cmap in (s.get("lineup_colors_by_team") or {}).items()
        ]
        tooltip_css += "".join(
            f'details:has(.tt[data-lu="{key}"]:hover) .lu-row-{key},'
            f".lu-row-{key}:hover"
            f"{{background:{color}40;border-radius:2px;}}"
            f'details:has(.lu-row-{key}:hover) .lu-hl-{key}{{display:block;}}'
            for team_, cmap in _lu_color_maps
            for key, color in (
                (_lu_key(team_, code), c) for code, c in cmap.items()
            )
        )
        # one rule per player connecting their box score row AND every one
        # of their stints to the same highlight set (the row rect plus a
        # rect over each stint), so the hover works in both directions
        tooltip_css += "".join(
            f'.chart-wrap:has(.bx-name-{b["name_hover_key"]}:hover) '
            f'.bx-hl-{b["name_hover_key"]},'
            f'.chart-wrap:has(.pl-{b["name_hover_key"]}:hover) '
            f'.bx-hl-{b["name_hover_key"]}{{display:block;}}'
            for b in tooltip_boxes if b.get("name_hover_key")
        )

    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        "<title>Plus/minus by player</title>"
        "<style>"
        "html,body{margin:0;padding:0;border:0;}"
        "img{display:block;vertical-align:top;width:100%;height:auto;}"
        # the shared full-page SVG renders, one data URI each; slice
        # divs show vertical bands of them via background positioning
        ":root{" + "".join(
            f'{var}:url("{_svg_data_uri(svg)}");'
            for var, svg in renders.items()
        ) + "}"
        ".simg{display:block;width:100%;background-repeat:no-repeat;}"
        # explicit width (= the PNG's native 8in*150dpi) capped at 100% so
        # the container has a real inline size for cqw units to resolve
        # against, while the image fills it; container-type enables cqw
        ".chart-wrap{position:relative;display:block;width:1200px;max-width:100%;"
        "margin:0 auto;container-type:inline-size;}"
        # the positioning context for the hover overlays: exactly the
        # images' box, excluding any HTML table flowing below in the wrap
        ".img-box{position:relative;}"
        # lineup box score appended after the graph — monospace, sized in cqw
        # (% of image width) so its columns match the chart's box scores
        # no top margin/padding: the standard chart gap is baked into the
        # bottom of the PNG slice above, so it scales with the charts
        # position:relative so the "per 8" toggle button can anchor to the
        # box score's own title line
        ".lineup-box{position:relative;white-space:pre;font-family:DejaVu Sans Mono,monospace;"
        f"color:{_BOX_HTML_TEXT};" + _BOX_FONT_CSS + "padding:0 0 18px 3.1%;}"
        # same style as the plot titles: the panel-title font size rendered
        # at 150dpi on the 1200px-wide figure is ~19.7px -> 1.64cqw
        # font-weight 300: the browser falls back from DejaVu Sans to the
        # system sans, whose regular weight renders heavier than the baked
        # DejaVu glyph paths of the in-image panel titles — the light
        # weight brings the two visually level
        ".lineup-box-title{color:lightgray;font-family:DejaVu Sans,sans-serif;"
        + _TITLE_FONT_CSS + "}"
        # per-column max highlight in the lineup box score
        f".mx-gold{{color:{_BOX_GOLD};}}"
        f".mx-red{{color:{_BOX_RED};}}"
        f".mx-grey{{color:{_BOX_GREY};}}"
        # hover a lineup name in the box score to see its player names
        ".lu{position:relative;}"
        ".lu .lu-players{display:none;position:absolute;top:100%;left:0;margin-top:2px;"
        "background:#222;color:lightgray;padding:2px 8px;border-radius:4px;"
        + _BOX_FONT_CSS + "white-space:nowrap;width:max-content;z-index:5;"
        "box-shadow:0 2px 6px rgba(0,0,0,0.5);}"
        ".lu:hover .lu-players{display:block;}"
        # the AP recap inside the "summary" toggle — prose, sized in cqw so
        # it scales with the charts; headline matches the panel-title style
        ".recap{font-family:DejaVu Sans,sans-serif;color:lightgray;"
        "font-size:1.5cqw;line-height:1.6;padding:6px 3.1% 12px 3.1%;}"
        ".recap p{margin:0 0 1em 0;max-width:80ch;}"
        ".recap-headline{display:block;font-size:1.64cqw;margin-bottom:14px;}"
        ".recap-source{color:gray;font-size:1.2cqw;}"
        # collapsible sections ("players" / "lineups"), closed by default;
        # an open toggle's label swaps to "less". Sized in cqw (container-
        # relative, like the titles) so the labels scale with the page
        # instead of staying a fixed pixel size.
        ".more{width:1200px;max-width:100%;margin:0 auto;container-type:inline-size;}"
        ".more>summary{cursor:pointer;color:#4da3ff;"
        "font:1.8cqw 'DejaVu Sans',sans-serif;"  # panel-title size + 10%
        "padding:6px 0 6px 12px;list-style:none;user-select:none;}"
        ".more>summary::-webkit-details-marker{display:none;}"
        ".more>summary::before{content:'▸ ';}"
        ".more[open]>summary::before{content:'▾ ';}"
        ".more>summary .less-txt{display:none;}"
        ".more[open]>summary .more-txt{display:none;}"
        ".more[open]>summary .less-txt{display:inline;}"
        # the lineup box score's own toggle: its button floats on the lineup
        # plot's title line (absolute within the chart-wrap, left-aligned
        # with the box score); the opened table flows below the image
        ".lu-toggle>summary{position:absolute;cursor:pointer;color:#4da3ff;"
        "font:1.62cqw 'DejaVu Sans',sans-serif;list-style:none;user-select:none;z-index:2;}"
        ".lu-toggle>summary::-webkit-details-marker{display:none;}"
        ".lu-toggle>summary::before{content:'▸ ';}"
        ".lu-toggle[open]>summary::before{content:'▾ ';}"
        ".lu-toggle>summary .less-txt{display:none;}"
        ".lu-toggle[open]>summary .more-txt{display:none;}"
        ".lu-toggle[open]>summary .less-txt{display:inline;}"
        # the per 8 / per game switch: a contentless <details> whose open
        # state swaps which of the two tables (.lu-raw / .lu-rate) shows;
        # no disclosure arrow — it's a mode switch, not a reveal
        ".lu-per8{display:inline;}"
        ".lu-per8>summary::before,.lu-per8[open]>summary::before,"
        ".tb-per32>summary::before,.tb-per32[open]>summary::before{content:none;}"
        ".lineup-box .lu-rate{display:none;}"
        ".lineup-box:has(.lu-per8[open]) .lu-raw{display:none;}"
        ".lineup-box:has(.lu-per8[open]) .lu-rate{display:inline;}"
        # ...and the switch also swaps the lineup plot image, whose per-8
        # render has rate diamonds and a rescaled y-axis
        ".lu-img-rate{display:none;}"
        ".chart-wrap:has(.lu-per8[open]) .lu-img-raw{display:none;}"
        ".chart-wrap:has(.lu-per8[open]) .lu-img-rate{display:block;}"
        # the team section's per 32 / per game switch swaps its slice image
        # (per-game vs per-32 box score; the team plot is identical in both)
        ".tb-img-rate{display:none;}"
        ".chart-wrap:has(.tb-per32[open]) .tb-img-raw{display:none;}"
        ".chart-wrap:has(.tb-per32[open]) .tb-img-rate{display:block;}"
        # the Karma panel's toggleable layers are transparent images
        # pinned over the base (which sits at the top of the wrap); each
        # hide / show switch simply hides its layer, so the switches
        # combine freely. Hiding stints also disables the lane hovers.
        ".kb-ov{position:absolute;top:0;left:0;pointer-events:none;}"
        ".chart-wrap:has(.kb-hide[open]) .kb-ov-lanes{display:none;}"
        ".chart-wrap:has(.pm-hide[open]) .kb-ov-pm{display:none;}"
        ".chart-wrap:has(.bar-hide[open]) .kb-ov-bars{display:none;}"
        ".chart-wrap:has(.sc-hide[open]) .kb-ov-scores{display:none;}"
        ".chart-wrap:has(.kb-hide[open]) .tt.tt-seg{display:none;}"
        # the event-layer cycler: hidden radios hold the state (0 = no
        # events, 1 = pEvents, 2 = vEvents, 3 = hEvents); the matching
        # label is shown (each label advances to the next state) and the
        # matching layer image revealed
        ".ev-st{display:none;}"
        ".ev-lbl{display:none;position:absolute;cursor:pointer;color:#4da3ff;"
        "font:1.62cqw 'DejaVu Sans',sans-serif;user-select:none;z-index:2;}"
        # closed arrow while nothing is shown, open arrow otherwise
        ".ev-lbl::before{content:'\\25BE ';}"
        ".ev-lbl0::before{content:'\\25B8 ';}"
        ".ev-st0:checked~.ev-lbl0,.ev-st1:checked~.ev-lbl1,"
        ".ev-st2:checked~.ev-lbl2,.ev-st3:checked~.ev-lbl3{display:block;}"
        ".kb-ov-events,.kb-ov-vevents,.kb-ov-hevents{display:none;}"
        ".ev-st1:checked~.img-box .kb-ov-events{display:block;}"
        ".ev-st2:checked~.img-box .kb-ov-vevents{display:block;}"
        ".ev-st3:checked~.img-box .kb-ov-hevents{display:block;}"
        f"{tooltip_css}"
        # the nav scales with the page (whose text is baked into the
        # SVG renders and grows with the window) instead of a fixed px
        # size that looks oversized in narrow windows
        ".gnav{position:absolute;color:#6ca0ff;text-decoration:none;"
        "font:clamp(9px, 1vw, 14px) 'DejaVu Sans',sans-serif;z-index:50;}"
        ".gnav-l{left:12px;}.gnav-r{right:12px;}"
        ".gnavn{color:#777;}"
        ".gnav:hover{text-decoration:underline;}"
        "</style>"
        "</head>\n"
        "<body style=\"background:black;margin:0;\">\n"
        f"{nav_html}{body}\n"
        "</body></html>\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


def _local_time_tick_labels(game_id: str, tick_labels: list[str]) -> list[str] | None:
    """Map each quarter/OT tick label to the actual local wall-clock time
    that period started (or the final buzzer, for "END"), using the NBA's
    live play-by-play feed — the only source with real per-event
    timestamps. Returns None if that feed has no data for this game (it
    only retains a rolling window of recent games), so callers can skip
    the secondary time axis entirely rather than show a partial one."""
    from nba_pbp.client import get_period_boundary_times

    times = get_period_boundary_times(game_id)
    if times is None:
        return None

    labels = []
    for label in tick_labels:
        if label == "END":
            key = "end"
        elif label.startswith("OT"):
            key = str(4 + int(label[2:]))
        else:
            key = str(int(label[1:]))
        when = times.get(key)
        if when is None:
            return None
        labels.append(when.strftime("%-I:%M %p"))
    return labels


def _draw_lineup_stint_panel(
    ax, team, team_stints, margin_timeline, home_team, tick_positions, tick_labels,
    score_limits, fig_w_px, fig_h_px, player_color: dict | None = None,
    per_minutes: float | None = None, draw_score_axis: bool = True,
) -> tuple[list, dict]:
    """Draw a team's lineup stints over game time. Each stint is a translucent
    colored "plane" (axvspan) spanning the time it was on court — one distinct
    vivid-wheel color per lineup, like the on-court shading in the player
    plots — with a solid bar at its net +/-. Left axis is +/-, the team's
    cumulative game points ride a secondary right axis, and the game-time (x)
    axis matches the team panel above. Returns (hover_boxes, color_by_lineup):
    per-stint hover boxes (figure fractions) so each stint's box score can be
    shown on mouseover, and the lineup-code -> color mapping so the lineup
    box score can color its lineup names to match this panel.

    With `per_minutes` set, each diamond shows the stint's +/- scaled to a
    per-`per_minutes`-minutes rate (rounded, matching the rate table) and
    the y-axis rescales to fit — used for the alternate render the "per 8"
    switch swaps in. `draw_score_axis=False` skips creating the score twin
    axis (for redrawing onto an axes whose twin already exists)."""
    ax.axhline(0, color="white", linewidth=0.6, alpha=0.3)

    # fix the axis limits up front so transData is correct when we compute the
    # per-stint hover-box pixel positions below (otherwise autoscale from the
    # axvspans gives wrong x positions and the hover targets collapse onto one)
    ax.set_xlim(left=0, right=tick_positions[-1])

    hover_boxes = []
    color_by_lineup = {}
    if not team_stints.empty:
        unique_lineups = list(dict.fromkeys(team_stints["lineup"]))
        cmap = _lineup_cmap(len(unique_lineups))
        color_by_lineup = {lu: cmap(i) for i, lu in enumerate(unique_lineups)}

        def _pm_value(s):
            if per_minutes and s["MIN"]:
                return round(s["PLUS_MINUS"] / s["MIN"] * per_minutes)
            return s["PLUS_MINUS"]

        pm_values = [_pm_value(s) for _, s in team_stints.iterrows()]
        pm_max = max(abs(min(pm_values)), abs(max(pm_values)), 1)
        y_limits = (-pm_max * 1.5, pm_max * 1.5)
        ax.set_ylim(y_limits)
        top_axes_y = ax.transAxes.transform((0, 1))[1]
        bottom_axes_y = ax.transAxes.transform((0, 0))[1]
        # the box score line is anchored at the top of the "Lineup stints"
        # title (axes top, lifted by the title's height + pad) and aligned
        # under the box score above; translateY(-100%) then ends its bottom
        # right where that label starts
        label_left = _BOX_SCORE_LEFT_MARGIN
        axes_top_frac = 1 - top_axes_y / fig_h_px
        title_offset_frac = (_PANEL_TITLE_FONTSIZE + plt.rcParams["axes.titlepad"]) * (ax.figure.dpi / 72) / fig_h_px
        label_top = axes_top_frac - title_offset_frac
        for _, s in team_stints.iterrows():
            pm = _pm_value(s)
            color = color_by_lineup[s["lineup"]]
            ax.axvspan(s["start_min"], s["end_min"], color=color, alpha=0.3, zorder=0, linewidth=0)
            # the stint's net +/- as a diamond at the stint's horizontal center
            ax.scatter(
                (s["start_min"] + s["end_min"]) / 2, pm,
                color=color, s=45, marker="D", edgecolor="none", zorder=3,
            )

            # hover readout: the box score row in this lineup's color, and
            # each player in the names line in their own chart color
            header, row, players_txt = _lineup_stint_box_line(s).split("\n", 2)
            players_html = ", ".join(
                f'<span style="color:{to_hex(player_color[n])};">{n}</span>'
                if player_color and n in player_color else n
                for n in players_txt.split(", ")
            )
            tooltip = (
                f'{header}\n<span style="color:{to_hex(color)};">{row}</span>\n{players_html}'
            )

            x0_px = ax.transData.transform((s["start_min"], 0))[0]
            x1_px = ax.transData.transform((s["end_min"], 0))[0]
            hover_boxes.append({
                "left": x0_px / fig_w_px,
                "top": axes_top_frac,
                "width": (x1_px - x0_px) / fig_w_px,
                "height": (top_axes_y - bottom_axes_y) / fig_h_px,
                "line_tooltip": tooltip,
                "label_left": label_left,
                "label_top": label_top,
                "lu_key": _lu_key(team, s["lineup"]),
                # the plane lights itself up under the cursor, in its
                # lineup's color
                "seg_color": f"{to_hex(color)}40",
            })

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylabel("+/-", color="gray")
    ax.set_title(f"{team} Lineups", fontsize=_PANEL_TITLE_FONTSIZE, color=_PANEL_TITLE_COLOR, loc="left")
    ax.grid(True, color=(1, 1, 1, 0.15))
    ax.tick_params(axis="x", colors="gray")
    ax.tick_params(axis="y", labelsize=9, colors="gray")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("gray")
    ax.spines["bottom"].set_color("gray")
    ax.set_zorder(2)
    ax.patch.set_visible(False)

    if draw_score_axis:
        # cumulative game points (the team's own score) on a secondary right axis
        score_col = "home_score" if team == home_team else "away_score"
        ax2 = ax.twinx()
        ax2.set_zorder(1)
        ax2.plot(
            margin_timeline["game_minutes"], margin_timeline[score_col],
            color="deepskyblue", alpha=0.5, linewidth=1.6, zorder=1, linestyle="--",
        )
        ax2.set_ylim(score_limits)
        ax2.set_ylabel("Points", color="deepskyblue", labelpad=-1)
        ax2.tick_params(axis="y", colors="deepskyblue", labelsize=7, pad=1)
        ax2.spines["top"].set_visible(False)

    return hover_boxes, color_by_lineup


_COMBINED_LINEUP_MARKERS = ("D", "o")  # first team diamonds, second circles

# the combined panel needs the two teams' wheels DISJOINT — with a shared
# wheel both teams' first lineups wear the identical colour. Split the
# 20-slot wheel by temperature (original order kept within each half, so
# the adjacent-slot separation it was ordered for survives): cool hues
# for the first team, warm for the second, and no colour on both halves.
_COMBINED_LINEUP_WHEELS = (
    ["#2699E0", "#29A7CD", "#2CB2C0", "#2FBDB3", "#976DEC", "#4588F6",
     "#7378F6", "#84D048", "#34D375", "#B766DC", "#32C89F"],
    ["#F8972C", "#E8AA2E", "#D4BA2F", "#F98856", "#F97A70", "#F9688B",
     "#B6C630", "#EA62AA", "#D362C6"],
)


def _draw_combined_lineup_stint_panel(
    ax, teams, stint_segments, margin_timeline, home_team,
    tick_positions, tick_labels, fig_w_px, fig_h_px,
    player_color: dict | None = None,
) -> list:
    """Both teams' lineup stints on ONE axes against a single shared +/-
    axis, so the two rotations can be read against each other directly.

    The translucent on-court planes split the height — the first team's in
    the top half, the second's in the bottom — so it is always clear whose
    lineup a band belongs to. The +/- markers are NOT confined that way:
    they sit at their true value on the one shared axis, which is the whole
    point of combining the panels. The teams are told apart by marker shape
    instead: diamonds for the first team, filled circles for the second.

    Returns (hover_boxes, colors_by_team): per-stint hover boxes in the
    same shape the per-team panels return, so the page's existing
    box score-on-hover machinery works, and each team's lineup-code -> hex
    map so the lineup box score tables can colour their rows to match
    THIS panel's bands."""
    ax.axhline(0, color="white", linewidth=0.6, alpha=0.3)
    ax.set_xlim(left=0, right=tick_positions[-1])

    per_team = {t: stint_segments[stint_segments["teamTricode"] == t] for t in teams}
    all_pm = [s["PLUS_MINUS"] for st in per_team.values() for _, s in st.iterrows()]
    pm_max = max((abs(v) for v in all_pm), default=1) or 1
    # the game's running score margin rides the SAME +/- axis (same
    # units — that is what the shared axis buys), from the top team's
    # perspective: above zero, the top team leads. Widen the limits so
    # the margin always fits alongside the lineup markers.
    margin_col = "home_margin" if teams[0] == home_team else "away_margin"
    m_max = max(abs(margin_timeline[margin_col].min()),
                abs(margin_timeline[margin_col].max()), 1)
    y_max = max(pm_max * 1.5, m_max * 1.08)
    ax.set_ylim(-y_max, y_max)
    ax.plot(
        margin_timeline["game_minutes"], margin_timeline[margin_col],
        color="#8a8a3a", alpha=0.9, linewidth=1.6, zorder=2,
    )

    top_axes_y = ax.transAxes.transform((0, 1))[1]
    bottom_axes_y = ax.transAxes.transform((0, 0))[1]
    axes_top_frac = 1 - top_axes_y / fig_h_px
    title_offset_frac = (
        (_PANEL_TITLE_FONTSIZE + plt.rcParams["axes.titlepad"])
        * (ax.figure.dpi / 72) / fig_h_px
    )
    label_top = axes_top_frac - title_offset_frac
    # the second team's readout goes BELOW the plot, next to its own box
    # score, cleared past the x tick labels (8pt + pad, in device px)
    label_below = (1 - bottom_axes_y / fig_h_px
                   + (8 + 8) * (ax.figure.dpi / 72) / fig_h_px)

    # the popup's third line: team | stint players | entering | exiting,
    # each list starting on a column boundary shared by EVERY popup, so
    # the eye can compare across stints. Entering/exiting diff against
    # the team's previous DRAWN stint (stints under the plot cutoff are
    # not drawn, so their subs fold into the next drawn stint's lists);
    # a list with nobody in it shows '---'.
    stint_meta: dict[tuple[str, int], tuple[list, list, list]] = {}
    for team in teams:
        prev = None
        for pos, (_, s) in enumerate(per_team[team].iterrows()):
            cur = [n.strip() for n in str(s["players"]).split(",") if n.strip()]
            ent = sorted(set(cur) - prev) if prev is not None else []
            exi = sorted(prev - set(cur)) if prev is not None else []
            stint_meta[(team, pos)] = (cur, ent, exi)
            prev = set(cur)

    hover_boxes = []
    colors_by_team: dict[str, dict[str, str]] = {}
    pin_id = 0  # sequential over BOTH teams' drawn stints, for click-to-pin
    for ti, team in enumerate(teams):
        team_stints = per_team[team]
        if team_stints.empty:
            continue
        # disjoint wheels per team (cool / warm), so colour alone says
        # whose lineup a mark is. This deliberately BREAKS colour parity
        # with the team's own lineup panel, which starts the shared wheel
        # at slot 0 for both teams and would collide here.
        wheel = _COMBINED_LINEUP_WHEELS[ti % len(_COMBINED_LINEUP_WHEELS)]
        unique_lineups = list(dict.fromkeys(team_stints["lineup"]))
        color_by_lineup = {lu: wheel[i % len(wheel)]
                           for i, lu in enumerate(unique_lineups)}
        colors_by_team[team] = dict(color_by_lineup)
        marker = _COMBINED_LINEUP_MARKERS[ti % len(_COMBINED_LINEUP_MARKERS)]
        band_lo, band_hi = (0.5, 1.0) if ti == 0 else (0.0, 0.5)
        # the +/- markers wear the TEAM's brand colour, every one of them —
        # the wheel colours name the lineup only on its translucent band
        team_color = _TEAM_BRAND_COLORS.get(team, "lightgray")

        for pos, (_, s) in enumerate(team_stints.iterrows()):
            color = color_by_lineup[s["lineup"]]
            ax.axvspan(s["start_min"], s["end_min"], ymin=band_lo, ymax=band_hi,
                       color=color, alpha=0.3, zorder=0, linewidth=0)
            ax.scatter(
                (s["start_min"] + s["end_min"]) / 2, s["PLUS_MINUS"],
                color=team_color, s=45, marker=marker, edgecolor="none", zorder=3,
            )

            header, row, _players_txt = _lineup_stint_box_line(s).split("\n", 2)

            def _colored_list(names):
                if not names:
                    return "---"
                return ", ".join(
                    f'<span style="color:{to_hex(player_color[n])};">{n}</span>'
                    if player_color and n in player_color else n
                    for n in names
                )

            # team / stint players / entering / exiting as stacked rows,
            # every list starting on the SAME column boundary. One row per
            # list (rather than one wide line) because a 5-man list is
            # ~64 monospace chars — three of those side by side is wider
            # than the page at any viewport size.
            cur, ent, exi = stint_meta[(team, pos)]
            players_line = (
                f"{team:<5}{_colored_list(cur)}\n"
                f"{'in':<5}{_colored_list(ent)}\n"
                f"{'out':<5}{_colored_list(exi)}"
            )
            # the header/row pair is column-exact monospace — prefixing the
            # header with the team shifts every label off its value, so the
            # team goes on the players line instead
            tooltip = (f'{header}\n'
                       f'<span style="color:{to_hex(color)};">{row}</span>\n'
                       f'{players_line}')
            x0_px = ax.transData.transform((s["start_min"], 0))[0]
            x1_px = ax.transData.transform((s["end_min"], 0))[0]
            # the stint's own +/- marker, so hovering the stint can ring it
            # (safe here because this panel has no rate-view alternate
            # render that would move the markers under a static overlay)
            mx_px, my_px = ax.transData.transform(
                ((s["start_min"] + s["end_min"]) / 2, s["PLUS_MINUS"]))
            # the hover target covers only this team's half, so overlapping
            # stints from the two teams stay separately hoverable
            half_px = (top_axes_y - bottom_axes_y) / 2
            top_px = top_axes_y if ti == 0 else top_axes_y - half_px
            hover_boxes.append({
                "left": x0_px / fig_w_px,
                "top": 1 - top_px / fig_h_px,
                "width": (x1_px - x0_px) / fig_w_px,
                "height": half_px / fig_h_px,
                "line_tooltip": tooltip,
                "label_left": _BOX_SCORE_LEFT_MARGIN,
                # the readout appears on the hovered team's side of the
                # plot: above it for the top-half team, below for the
                # bottom-half team — each next to its own box score
                "label_top": label_top if ti == 0 else label_below,
                "label_below": ti != 0,
                "lu_key": _lu_key(team, s["lineup"]),
                "seg_color": f"{to_hex(color)}40",
                "marker_left": mx_px / fig_w_px,
                "marker_top": 1 - my_px / fig_h_px,
                "pin_id": pin_id,
                "pin_group": ti,
            })
            pin_id += 1

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylabel("+/-", color="gray")
    ax.set_title("Lineups", fontsize=_PANEL_TITLE_FONTSIZE,
                 color=_PANEL_TITLE_COLOR, loc="left")
    # the shape key sits INSIDE the plot at its left edge, by the +/-
    # axis — first team's in the upper-left corner of its half, second's
    # in the lower-left — so the top/bottom band split is labelled where
    # the eye starts reading. Each entry in its team's brand colour,
    # above the bands.
    for ti_, t in enumerate(teams):
        sym = "◆" if _COMBINED_LINEUP_MARKERS[ti_ % len(_COMBINED_LINEUP_MARKERS)] == "D" else "●"
        y, va = (0.97, "top") if ti_ == 0 else (0.03, "bottom")
        ax.text(0.008, y, f"{t} {sym}", transform=ax.transAxes,
                ha="left", va=va, fontsize=_PANEL_TITLE_FONTSIZE,
                color=_TEAM_BRAND_COLORS.get(t, _PANEL_TITLE_COLOR), zorder=4)
    ax.grid(True, color=(1, 1, 1, 0.15))
    ax.tick_params(axis="x", colors="gray")
    ax.tick_params(axis="y", labelsize=9, colors="gray")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("gray")
    ax.spines["bottom"].set_color("gray")
    ax.set_zorder(2)
    ax.patch.set_visible(False)
    return hover_boxes, colors_by_team


def _draw_event_sum_panel(ax, teams, made_all, missed_all, missed_ft, events,
                          margin_timeline, home_team, tick_positions, tick_labels,
                          local_time_labels=None):
    """The "Karma" panel: weighted good/bad event counts per 20-second
    interval, as stacked bars centered on each interval's midpoint. Good
    events: made shots weighted by their value (3P=3, 2P=2, FT=1) plus
    rebounds, assists, blocks, and steals at 1 each. Bad events (all
    weight 1): missed FG/3P/FT, turnovers, fouls. Every event favors exactly one team, and each segment
    wears the brand color of the team that PRODUCED it: the upward stack
    is the first team's good events in its bright team color, tipped with
    the second team's bad events in the second team's dimmed color; the
    downward stack mirrors it."""
    good_kinds = ("REB", "AST", "BLK", "STL")
    bad_kinds = ("FOUL", "TOV")

    def _good_times(team):
        """(times, weights): made shots weigh their shot value (3P=3, 2P=2,
        FT=1); rebounds/assists/blocks/steals weigh 1."""
        made = made_all.loc[made_all["teamTricode"] == team, ["game_minutes", "shotValue"]]
        ev = events.loc[
            (events["teamTricode"] == team) & events["event_type"].isin(good_kinds),
            "game_minutes",
        ] if not events.empty else pd.Series(dtype=float)
        times = np.concatenate([made["game_minutes"].to_numpy(), ev.to_numpy()])
        weights = np.concatenate([made["shotValue"].fillna(2).to_numpy(), np.ones(len(ev))])
        return times, weights

    def _bad_times(team):
        """(times, weights): every miss, turnover, and foul weighs 1."""
        times = pd.concat([
            missed_all.loc[missed_all["teamTricode"] == team, "game_minutes"],
            missed_ft.loc[missed_ft["teamTricode"] == team, "game_minutes"],
            events.loc[
                (events["teamTricode"] == team) & events["event_type"].isin(bad_kinds),
                "game_minutes",
            ] if not events.empty else pd.Series(dtype=float),
        ]).to_numpy()
        return times, np.ones(len(times))

    interval = 20 / 60  # 20 seconds, in minutes
    edges = np.arange(0, tick_positions[-1] + interval, interval)
    mids = (edges[:-1] + edges[1:]) / 2

    def _hist(times_weights):
        times, weights = times_weights
        counts, _ = np.histogram(times, bins=edges, weights=weights)
        return counts

    # stacked bars, goods hugging the axis and bads outside them: the top
    # (green shades) stacks my good then your bad; the bottom (red shades,
    # mirrored) stacks your good then my bad
    my_good, my_bad = _hist(_good_times(teams[0])), _hist(_bad_times(teams[0]))
    your_good, your_bad = _hist(_good_times(teams[1])), _hist(_bad_times(teams[1]))
    w = interval * 0.5
    def _tip(hex_color):
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
        # dark brand colors dim to near-black, so they take a gentler dim
        f = 0.65 if (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.5 else 0.45
        return f"#{int(r * f):02x}{int(g * f):02x}{int(b * f):02x}"

    c_mine = _TEAM_BRAND_COLORS.get(teams[0], "#00c244")
    c_yours = _TEAM_BRAND_COLORS.get(teams[1], "#e82222")
    # the bars (and the corner team labels below) live on their own twin
    # axis so they can render as a separate toggleable layer
    ax_bars = ax.twinx()
    ax_bars.bar(mids, my_good, width=w, color=c_mine, alpha=0.55, linewidth=0)
    ax_bars.bar(mids, your_bad, bottom=my_good, width=w, color=_tip(c_yours), alpha=0.55, linewidth=0)
    ax_bars.bar(mids, -your_good, width=w, color=c_yours, alpha=0.55, linewidth=0)
    ax_bars.bar(mids, -my_bad, bottom=-your_good, width=w, color=_tip(c_mine), alpha=0.55, linewidth=0)
    # symmetric limits so zero sits mid-panel, aligned with the margin axis
    bar_max = max((my_good + your_bad).max(), (your_good + my_bad).max(), 1)
    ax_bars.set_ylim(-bar_max * 1.08, bar_max * 1.08)
    ax_bars.set_yticks([])
    for spine in ax_bars.spines.values():
        spine.set_visible(False)
    # keep the main axis zero-centered so its zero line matches the bars
    ax.set_ylim(-1, 1)

    # the first team's score margin (+/-) as a thin line behind the bars
    # (z=0), on its own hidden scale, zero-aligned with the bars — no axis
    # decorations of its own
    margin_col = "home_margin" if teams[0] == home_team else "away_margin"
    timeline = margin_timeline.sort_values("game_minutes")
    t = timeline["game_minutes"].to_numpy()
    margin = timeline[margin_col].to_numpy()
    # smooth the stepped margin: sample it every 5 seconds, then take a
    # centered 1-minute moving average (edge-normalized)
    grid = np.arange(0, tick_positions[-1] + 1 / 12, 1 / 12)
    stepped = margin[np.maximum(np.searchsorted(t, grid, side="right") - 1, 0)]
    kernel = np.ones(12)
    smooth = np.convolve(stepped, kernel, "same") / np.convolve(np.ones_like(stepped), kernel, "same")
    ax_m = ax.twinx()
    ax_m.plot(grid, smooth, color="#8a8a3a", alpha=0.9, linewidth=0.8, zorder=0)
    m_max = max(abs(margin_timeline[margin_col].min()), abs(margin_timeline[margin_col].max()), 1)
    ax_m.set_ylim(-m_max * 1.08, m_max * 1.08)
    # the margin's scale IS the panel's visible left axis, colored like
    # the +/- line itself
    ax_m.yaxis.tick_left()
    ax_m.yaxis.set_label_position("left")
    ax_m.set_ylabel("+/-", color="#8a8a3a")
    ax_m.tick_params(axis="y", colors="#8a8a3a", labelsize=9)
    for spine in ax_m.spines.values():
        spine.set_visible(False)

    # both teams' cumulative scores, dashed in each team's brand color, on
    # a right-hand Score axis
    ax_p = ax.twinx()
    for team in teams:
        score_col = "home_score" if team == home_team else "away_score"
        ax_p.plot(
            timeline["game_minutes"], timeline[score_col],
            color=_TEAM_BRAND_COLORS.get(team, "gray"), alpha=0.6,
            linewidth=1.2, linestyle="--", zorder=0,
        )
    ax_p.set_ylim(0, timeline[["home_score", "away_score"]].max().max() * 1.05)
    score_color = _TEAM_BRAND_COLORS.get(teams[0], "gray")
    ax_p.set_ylabel("Score", color=score_color, labelpad=-1)
    ax_p.tick_params(axis="y", colors=score_color, labelsize=7, pad=1)
    # no spines of its own: the panel frame belongs to the base axis, so
    # the scores layer holds only the lines and the right ticks/label
    for spine in ax_p.spines.values():
        spine.set_visible(False)

    # overlay axis for the player stint lanes (drawn per team later by
    # _draw_karma_band_lanes)
    ax_band = ax.twinx()
    ax_band.set_ylim(0, 1)
    ax_band.set_yticks([])
    for spine in ax_band.spines.values():
        spine.set_visible(False)

    # overlay axis for the per-player event markers (drawn per team later
    # by _draw_karma_event_markers), sharing the stint-lane band's 0..1
    # coordinates so each marker sits on its player's lane
    ax_ev = ax.twinx()
    ax_ev.set_ylim(0, 1)
    ax_ev.set_yticks([])
    for spine in ax_ev.spines.values():
        spine.set_visible(False)

    # overlay axis for the per-minute event columns ("vEvents", drawn per
    # team later by _draw_karma_vevent_markers) — its y scale is set by
    # the drawing helper from the tallest column
    ax_vev = ax.twinx()
    ax_vev.set_ylim(0, 1)
    ax_vev.set_yticks([])
    for spine in ax_vev.spines.values():
        spine.set_visible(False)

    # overlay axis for the per-player left-packed event rows ("hEvents",
    # drawn per team later by _draw_karma_hevent_markers), sharing the
    # stint-lane band's 0..1 coordinates
    ax_hev = ax.twinx()
    ax_hev.set_ylim(0, 1)
    ax_hev.set_yticks([])
    for spine in ax_hev.spines.values():
        spine.set_visible(False)

    # layering: event markers on top, bars, then the main axis furniture
    # (grid, zero line, title), margin line, points, stint lanes at the
    # back
    ax_hev.set_zorder(8)
    ax_hev.patch.set_visible(False)
    ax_vev.set_zorder(7)
    ax_vev.patch.set_visible(False)
    ax_ev.set_zorder(6)
    ax_ev.patch.set_visible(False)
    ax_bars.set_zorder(5)
    ax_bars.patch.set_visible(False)
    ax.set_zorder(4)
    ax.patch.set_visible(False)
    ax_m.set_zorder(3)
    ax_m.patch.set_visible(False)
    ax_p.set_zorder(2)
    ax_p.patch.set_visible(False)
    ax_band.set_zorder(1)
    ax_bars.text(0.005, 0.95, teams[0], transform=ax_bars.transAxes,
                 color=_TEAM_BRAND_COLORS.get(teams[0], "lightgray"), fontsize=9, va="top")
    ax_bars.text(0.005, 0.05, teams[1], transform=ax_bars.transAxes,
                 color=_TEAM_BRAND_COLORS.get(teams[1], "lightgray"), fontsize=9, va="bottom")
    ax.axhline(0, color="white", linewidth=0.6, alpha=0.3)
    ax.set_xlim(0, tick_positions[-1])
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=8)
    ax.set_yticks([])
    if local_time_labels is not None:
        # the real local wall-clock time each period started, printed just
        # below its Q1/Q2/... tick label — same as the team panels
        for xpos, label in zip(tick_positions, local_time_labels):
            ax.annotate(
                label, xy=(xpos, 0), xycoords=ax.get_xaxis_transform(),
                xytext=(0, -20), textcoords="offset points",
                ha="center", va="top", fontsize=7, color="dimgray", annotation_clip=False,
            )
    ax.set_title(f"{teams[0]} Karma", fontsize=_PANEL_TITLE_FONTSIZE, color=_PANEL_TITLE_COLOR, loc="left")
    ax.grid(True, color=(1, 1, 1, 0.15))
    ax.tick_params(axis="x", colors="gray")
    ax.tick_params(axis="y", labelsize=9, colors="gray")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("gray")
    ax.spines["bottom"].set_color("gray")
    return ax_band, ax_m, ax_p, ax_bars, ax_ev, ax_vev, ax_hev


def _karma_event_rows(team, made_all, missed_all, missed_ft, events):
    """Every event by `team` as a marker row: {x, kind, name, good} —
    made shots as shot{value}, missed field goals as missed{value},
    missed free throws as missed1, plus REB/AST/BLK/STL (good) and
    FOUL/TOV (bad)."""
    good_kinds = ("REB", "AST", "BLK", "STL")
    rows = []
    for _, r in made_all[made_all["teamTricode"] == team].iterrows():
        v = int(r["shotValue"]) if pd.notna(r["shotValue"]) else 2
        rows.append({"x": r["game_minutes"], "kind": f"shot{v}",
                     "name": r["displayName"], "good": True})
    for _, r in missed_all[missed_all["teamTricode"] == team].iterrows():
        v = int(r["shotValue"]) if pd.notna(r["shotValue"]) else 2
        rows.append({"x": r["game_minutes"], "kind": f"missed{v}",
                     "name": r["displayName"], "good": False})
    # missed free throws live in their own frame — `missed_all` only has
    # missed field goals
    for _, r in missed_ft[missed_ft["teamTricode"] == team].iterrows():
        rows.append({"x": r["game_minutes"], "kind": "missed1",
                     "name": r["displayName"], "good": False})
    # the OPPONENT's offensive rebounds are bad events for `team`, marked
    # 'o'. The feed doesn't label rebound type, so it's inferred the same
    # way as the box scores: a rebound by the team that just missed is
    # offensive. (These carry an opponent's name, so the lane-based views
    # skip them; the minute stacks include them.)
    opp_reb = events[
        (events["teamTricode"] != team) & (events["event_type"] == "REB")
    ] if not events.empty else events
    if not opp_reb.empty:
        misses = pd.concat([
            missed_all[["game_minutes", "teamTricode"]],
            missed_ft[["game_minutes", "teamTricode"]],
        ]).sort_values("game_minutes")
        miss_t = misses["game_minutes"].to_numpy()
        miss_team = misses["teamTricode"].to_numpy()
        for _, r in opp_reb.iterrows():
            i = np.searchsorted(miss_t, r["game_minutes"] + 1e-9, side="right") - 1
            if i >= 0 and miss_team[i] == r["teamTricode"]:
                rows.append({"x": r["game_minutes"], "kind": "OREB_OPP",
                             "name": r["displayName"], "good": False})
    if not events.empty:
        for _, r in events[events["teamTricode"] == team].iterrows():
            kind = r["event_type"]
            if kind not in good_kinds and kind not in ("FOUL", "TOV"):
                continue
            rows.append({"x": r["game_minutes"], "kind": kind,
                         "name": r["displayName"], "good": kind in good_kinds})
    return rows


_KARMA_EVENT_GLYPHS = {
    "shot1": "$1$", "shot2": "$2$", "shot3": "$3$",
    "missed1": "$1$", "missed2": "$2$", "missed3": "$3$",
    "REB": "$R$", "AST": "$A$", "BLK": "$B$", "STL": "$S$",
    "FOUL": "$F$", "TOV": "$T$", "OREB_OPP": "$o$",
}


def _scatter_karma_events(ax, pts, player_color, own_color_for_bad=False):
    """Scatter marker rows given as (x, y, kind, name, good) tuples: one
    scatter per (kind, color) — good events in the player's chart color,
    bad events in red. With `own_color_for_bad`, a bad event by one of
    OUR players also wears the player's color; only events with no
    matching player (e.g. an opponent's offensive rebound) stay red."""
    groups: dict[tuple, list[tuple]] = {}
    for x, y, kind, name, good in pts:
        keep_name = good or (own_color_for_bad and name in player_color)
        groups.setdefault((kind, name if keep_name else None), []).append((x, y))
    for (kind, name), xy in groups.items():
        color = "red" if name is None else player_color.get(name, "lightgray")
        ax.scatter(
            [p[0] for p in xy], [p[1] for p in xy],
            color=color, s=32, alpha=0.85, marker=_KARMA_EVENT_GLYPHS[kind],
            linewidth=0.4, zorder=3,
        )


def _karma_lane_geometry(stint_pm, player_order):
    """The shared 0..1 player-lane geometry for one Karma panel: player
    order (first box score row on top), each player's lane centre, the row
    pitch, and the bar thickness as a fraction of the axis.

    The stint bands and every event layer MUST agree on this — they are
    drawn on separate overlay axes, so any difference silently floats the
    markers off the bars they belong to. It lives here so there is one
    definition to change, not three to keep in sync.

    Lanes fill the whole plot area: one row per player, so the pitch (and
    bar width) scales with the roster size, and each bar fills FILL of its
    row, leaving the rest as the gap between players.

    Returns ([] , {}, 0, 0) when the team has no stints."""
    stint_names = set(stint_pm["displayName"])
    order = [n for n in (player_order or []) if n in stint_names]
    order += sorted(stint_names - set(order))
    n = len(order)
    if not n:
        return [], {}, 0.0, 0.0
    FILL = 0.75
    pitch = 1.0 / n
    lw_frac = pitch * FILL
    # centre each bar in its own row: row i spans [1-(i+1)*pitch, 1-i*pitch],
    # so its centre is half a PITCH down, not half a bar width — the latter
    # left every bar riding high in its row by (pitch - lw_frac)/2.
    y_by_name = {
        name: 1 - pitch / 2 - i * pitch for i, name in enumerate(order)
    }
    return order, y_by_name, pitch, lw_frac


def _draw_karma_hevent_markers(ax_hev, team, made_all, missed_all, missed_ft,
                               events, stint_pm, player_color, player_order):
    """The "hEvents" layer on a Karma panel's overlay axis: every player's
    events, good and bad mixed in game order, packed to the LEFT of their
    stint lane without overlap — so each lane reads as that player's
    event tally, longest row = most events."""
    order, y_by_name, pitch, lw_frac = _karma_lane_geometry(stint_pm, player_order)
    if not order:
        return
    n = len(order)

    by_name: dict[str, list[dict]] = {}
    for r in sorted(_karma_event_rows(team, made_all, missed_all, missed_ft, events),
                    key=lambda r: r["x"]):
        if r["name"] in y_by_name:
            by_name.setdefault(r["name"], []).append(r)
    # 0.7 game-minutes per slot leaves a little air between adjacent
    # letter glyphs at this panel's scale
    x0, dx = 0.5, 0.7
    pts = [
        (x0 + i * dx, y_by_name[name], r["kind"], name, r["good"])
        for name, rows in by_name.items()
        for i, r in enumerate(rows)
    ]
    _scatter_karma_events(ax_hev, pts, player_color)


def _draw_karma_vevent_markers(ax_vev, team, made_all, missed_all, missed_ft,
                               events, player_color):
    """The "vEvents" layer on a Karma panel's overlay axis: the team's
    event markers collected per game minute and stacked vertically at
    that minute's center line — good events climb up from zero, bad
    events hang below it. Every marker tied to one of the team's players
    wears that player's chart color (good and bad alike); only markers
    with no player of ours (opponent offensive rebounds, `o`) are red.
    The y value is simply the marker's position in its minute's stack."""
    # stack chronologically within each minute: goods up from the zero
    # line, bads down
    up: dict[int, int] = {}
    down: dict[int, int] = {}
    pts = []
    for r in sorted(_karma_event_rows(team, made_all, missed_all, missed_ft, events),
                    key=lambda r: r["x"]):
        minute = int(r["x"])
        if r["good"]:
            up[minute] = up.get(minute, 0) + 1
            y = up[minute]
        else:
            down[minute] = down.get(minute, 0) + 1
            y = -down[minute]
        pts.append((minute + 0.5, y, r["kind"], r["name"], r["good"]))
    max_n = max(list(up.values()) + list(down.values()) + [1])
    ax_vev.set_ylim(-max_n * 1.12, max_n * 1.12)
    _scatter_karma_events(ax_vev, pts, player_color, own_color_for_bad=True)


def _draw_karma_event_markers(ax_ev, team, made_all, missed_all, missed_ft,
                              events, stint_pm, player_color, player_order):
    """The "pEvents" layer on a Karma panel's overlay axis: x is game
    time and y is the PLAYER — each marker sits on that player's stint
    lane (the same 0..1 lane geometry as _draw_karma_band_lanes), so
    events line up on top of the stint bars. Made shots show their value
    (`1 2 3`) and rebounds/assists/blocks/steals show `R A B S`, each in
    the player's chart color; missed shots, fouls (`F`), and turnovers
    (`T`) in red."""
    order, y_by_name, _pitch, _lw = _karma_lane_geometry(stint_pm, player_order)
    if not order:
        return
    pts = [
        (r["x"], y_by_name[r["name"]], r["kind"], r["name"], r["good"])
        for r in _karma_event_rows(team, made_all, missed_all, missed_ft, events)
        if r["name"] in y_by_name
    ]
    # de-overlap within each player's lane: markers keep their order but
    # get nudged apart to at least one glyph width, so a rebound-putback
    # seconds apart reads as two marks instead of an ink blot. Forward
    # pass pushes right; the reverse pass pulls the chain back inside the
    # axis if the last marker was pushed past the end. Sub-glyph time
    # distortion, never reordering.
    xmin, xmax = ax_ev.get_xlim()
    axes_w_pt = (ax_ev.get_position().width
                 * ax_ev.figure.get_size_inches()[0] * 72)
    min_dx = (xmax - xmin) * (np.sqrt(32) * 1.15) / axes_w_pt
    by_lane: dict[float, list] = {}
    for p in pts:
        by_lane.setdefault(p[1], []).append(p)
    pts = []
    for items in by_lane.values():
        items.sort(key=lambda t: t[0])
        xs = [t[0] for t in items]
        for i in range(1, len(xs)):
            xs[i] = max(xs[i], xs[i - 1] + min_dx)
        if xs and xs[-1] > xmax:
            xs[-1] = xmax
            for i in range(len(xs) - 2, -1, -1):
                xs[i] = min(xs[i], xs[i + 1] - min_dx)
        pts.extend((x, t[1], t[2], t[3], t[4]) for x, t in zip(xs, items))
    _scatter_karma_events(ax_ev, pts, player_color)


def _draw_karma_band_lanes(
    ax_band, team, stint_pm, player_color, player_order,
    fig_w_px, fig_h_px, label_top,
):
    """The first team's on-court stint lanes on the Karma panel's overlay
    axis (ylim 0..1), dim like the team panels' rotation band, spread over
    the full plot height with the first box score row on top. Returns
    band-style hover boxes — each stint reveals its own box score line and
    highlights itself."""
    boxes = []
    order, y_by_name, pitch, lw_frac = _karma_lane_geometry(stint_pm, player_order)
    if not order:
        return boxes
    axes_h_inches = ax_band.get_position().height * ax_band.figure.get_size_inches()[1]
    lw_points = lw_frac * axes_h_inches * 72
    half = max(pitch, lw_frac) / 2
    for _, s in stint_pm.iterrows():
        name = s["displayName"]
        y = y_by_name[name]
        color = player_color.get(name, "gray")
        ax_band.plot(
            [s["entry_minutes"], s["exit_minutes"]], [y, y],
            color=color, alpha=0.18, linewidth=lw_points, solid_capstyle="butt",
        )
        x0_px, y_top_px = ax_band.transData.transform((s["entry_minutes"], y + half))
        x1_px, y_bot_px = ax_band.transData.transform((s["exit_minutes"], y - half))
        boxes.append({
            "left": x0_px / fig_w_px,
            "top": 1 - y_top_px / fig_h_px,
            "width": (x1_px - x0_px) / fig_w_px,
            "height": (y_top_px - y_bot_px) / fig_h_px,
            "name_label": name,
            "stint_entry": s["entry_minutes"],
            "name_color": to_hex(color),
            "seg_color": f"{to_hex(color)}59",
            "label_left": _BOX_SCORE_LEFT_MARGIN,
            "label_top": label_top,
        })
    return boxes


_SEASON_EVENT_KINDS = [
    "made FT", "made 2", "made 3", "missed FT", "missed 2", "missed 3",
    "DREB", "OREB", "AST", "STL", "BLK", "TOV", "FOUL", "B2B", "+/-",
    "HOM", "W/L",
]


def _reb_split(df: pd.DataFrame, own: pd.Series) -> tuple[int, int]:
    """(defensive, offensive) rebound totals for one side, from the
    per-player running counters the feed puts in every rebound
    description — "X REBOUND (Off:1 Def:2)". Each player's final
    counters are their game totals, so the team total is the sum of
    per-player maxima. Team rebounds (personId 0) carry no counters and
    are excluded, matching the old REB count."""
    reb = df[(df["actionType"] == "Rebound") & own
             & df["personId"].notna() & (df["personId"] != 0)]
    if reb.empty:
        return 0, 0
    cnts = reb["description"].astype(str).str.extract(
        r"\(Off:(\d+) Def:(\d+)\)").astype(float)
    cnts["pid"] = reb["personId"].values
    fin = cnts.dropna().groupby("pid").max()
    if fin.empty:
        return 0, 0
    return int(fin[1].sum()), int(fin[0].sum())


def _game_event_counts(df: pd.DataFrame, team: str | None = None) -> dict[str, int]:
    """Event counts for one game, straight from the raw play-by-play
    frame (vectorized — no on-court simulation). With `team`, only that
    team's events. Steals and blocks are standalone rows credited
    directly to the stealer's/blocker's team ("Caruso STEAL (1 STL)"),
    so every kind filters on the same side."""
    desc = df["description"].astype(str)
    if team is None:
        own = pd.Series(True, index=df.index)
    else:
        own = df["teamTricode"] == team
    made_fg = (df["isFieldGoal"] == 1) & (df["shotResult"] == "Made") & own
    missed_fg = (df["isFieldGoal"] == 1) & (df["shotResult"] == "Missed") & own
    ft = (df["actionType"] == "Free Throw") & own
    miss_desc = desc.str.startswith("MISS")
    # game length in minutes (48 plus 5 per overtime), and the team's
    # final margin (0 in league-wide mode, where margins cancel)
    minutes = 48 + 5 * max(0, int(df["period"].max()) - 4)
    margin = 0.0
    is_home = 0
    if team is not None:
        scored = df[df["scoreHome"].notna() & (df["scoreHome"].astype(str) != "")]
        if not scored.empty:
            last = scored.iloc[-1]
            home_team = df.loc[
                (df["location"] == "h") & df["teamTricode"].notna()
                & (df["teamTricode"] != ""), "teamTricode",
            ].iloc[0]
            diff = float(last["scoreHome"]) - float(last["scoreAway"])
            margin = diff if team == home_team else -diff
            is_home = int(team == home_team)
    return {
        "made FT": int((ft & ~miss_desc).sum()),
        "made 2": int((made_fg & (df["shotValue"] == 2)).sum()),
        "made 3": int((made_fg & (df["shotValue"] == 3)).sum()),
        "missed FT": int((ft & miss_desc).sum()),
        "missed 2": int((missed_fg & (df["shotValue"] == 2)).sum()),
        "missed 3": int((missed_fg & (df["shotValue"] == 3)).sum()),
        "DREB": _reb_split(df, own)[0],
        "OREB": _reb_split(df, own)[1],
        "AST": int((made_fg & desc.str.contains(r"AST\)")).sum()),
        "STL": int((desc.str.contains("STEAL") & own).sum()),
        "BLK": int((desc.str.contains("BLOCK") & own).sum()),
        "TOV": int(((df["actionType"] == "Turnover") & own).sum()),
        "FOUL": int(((df["actionType"] == "Foul") & own).sum()),
        "B2B": minutes,  # placeholder; replaced by schedule density downstream
        "+/-": margin,
        "HOM": is_home,
        "W/L": int(margin > 0),
    }


def _season_events_daily(season: str, smooth: int = 2,
                         team: str | None = None):
    """The season 3D plots' shared data step: per-calendar-day mean event
    counts per game (optionally one team's games/events only, optionally
    smoothed by a centered rolling average over game days). Returns the
    daily frame and the event kinds ordered by mean, smallest first."""
    from nba_pbp import client
    from nba_pbp.edge import league_history

    history = league_history(season)
    if team:
        games = history[history["TEAM_ABBREVIATION"] == team]
    else:
        games = history[history["MATCHUP"].str.contains(" vs. ")]
    games = games.sort_values("GAME_DATE")
    counts: dict[str, list[int]] = {k: [] for k in _SEASON_EVENT_KINDS}
    dates = []
    skipped = []
    for _, g in games.iterrows():
        if not client.has_cached_play_by_play(g["GAME_ID"]):
            # a game with no cached play-by-play is simply absent from the
            # plot. Say so — silently dropping it looks identical to the
            # game never having been played, which is impossible to spot
            # in a 97-game ridge and sent us chasing a rendering bug once.
            skipped.append((str(g["GAME_ID"]), str(g["GAME_DATE"])[:10]))
            continue
        c = _game_event_counts(client.get_play_by_play_cached(g["GAME_ID"]), team)
        for k in _SEASON_EVENT_KINDS:
            counts[k].append(c[k])
        dates.append(g["GAME_DATE"])
    if not dates:
        raise ValueError(f"no cached play-by-play for season {season}")
    if skipped:
        import click

        shown = skipped[:10]
        click.echo(
            f"warning: {len(skipped)} game(s) missing from the plot — no cached "
            f"play-by-play:", err=True)
        for gid, date in shown:
            click.echo(f"  {gid}  {date}", err=True)
        if len(skipped) > len(shown):
            click.echo(f"  ... and {len(skipped) - len(shown)} more", err=True)
        click.echo(
            "  fetch them with `nba-pbp fetch-games` (plain `fetch` writes only "
            "the CSV, not the cache this plot reads)", err=True)

    # B2B: 1 on the second night of a back-to-back (prior game 0-1 days
    # earlier), then decaying with rest — halving every day since the
    # last back-to-back night — so fatigue fades instead of vanishing.
    # Only meaningful with a single team's schedule.
    b2b_vals = []
    last_b2b = None
    for j in range(len(dates)):
        if j > 0 and (dates[j] - dates[j - 1]).days <= 1:
            last_b2b = dates[j]
        if last_b2b is None:
            b2b_vals.append(0.0)
        else:
            b2b_vals.append(float(0.5 ** (dates[j] - last_b2b).days))
    counts["B2B"] = b2b_vals

    # aggregate to calendar days: each day's value is the mean count per
    # game across that day's games, and x is real elapsed time — so the
    # playoffs stretch out to their true span instead of compressing
    daily = (
        pd.DataFrame({"date": [d.normalize() for d in dates], **counts})
        .groupby("date").mean().sort_index()
    )
    if smooth > 1:
        kernel = np.ones(smooth)
        for k in _SEASON_EVENT_KINDS:
            if k in ("B2B", "HOM", "W/L", "+/-"):
                continue  # schedule, venue, results and margins stay raw
            z = daily[k].to_numpy(dtype=float)
            daily[k] = np.convolve(z, kernel, "same") / np.convolve(
                np.ones_like(z), kernel, "same"
            )
    order = sorted(_SEASON_EVENT_KINDS, key=lambda k: float(daily[k].mean()))
    return daily, order


def plot_season_events_2d_html(season: str, output_path: Path, smooth: int = 2,
                               team: str | None = None) -> Path:
    """The season event plot: one lane per stat, stacked as horizontal
    strips over one shared date axis — pure HTML/CSS, no JavaScript, no
    images. Hover the schedule bands (B2B/HOM/W/L) to scrub games and
    preview box scores; click in the plot to pin a game and stat
    together; hover or click a lane label to spotlight the lane and
    reveal its own value axis."""
    import html as _html
    import math
    import time as _time

    daily, _kind_order = _season_events_daily(season, smooth, team)
    # unsmoothed counts for the per-game bar lanes; the percentage
    # lanes keep the smoothed view
    daily_raw = daily if smooth <= 1 else _season_events_daily(season, 1, team)[0]
    BAR_RAW = {
        "FL": daily_raw["FOUL"], "TOV": daily_raw["TOV"],
        "BLK": daily_raw["BLK"], "STL": daily_raw["STL"],
        "AST": daily_raw["AST"], "DR": daily_raw["DREB"],
        "DO": daily_raw["OREB"],
        "FTM": daily_raw["made FT"],
        "FTA": daily_raw["made FT"] + daily_raw["missed FT"],
        "3PM": daily_raw["made 3"],
        "3PA": daily_raw["made 3"] + daily_raw["missed 3"],
        "2PM": daily_raw["made 2"],
        "2PA": daily_raw["made 2"] + daily_raw["missed 2"],
    }
    view = pd.DataFrame(index=daily.index)
    view["W/L"] = daily["W/L"]
    view["HOM"] = daily["HOM"]
    view["B2B"] = daily["B2B"]
    view["+/-"] = daily["+/-"]
    view["2PM"] = daily["made 2"]
    view["2PA"] = daily["made 2"] + daily["missed 2"]
    view["3PM"] = daily["made 3"]
    view["3PA"] = daily["made 3"] + daily["missed 3"]
    view["FTM"] = daily["made FT"]
    view["FTA"] = daily["made FT"] + daily["missed FT"]
    for pct, m, a in (("2P%", "2PM", "2PA"), ("3P%", "3PM", "3PA"),
                      ("FT%", "FTM", "FTA")):
        view[pct] = (100 * view[m] / view[a].where(view[a] > 0)).fillna(0)
    for src_, dst in (("DREB", "DR"), ("OREB", "DO"), ("AST", "AST"),
                      ("STL", "STL"), ("BLK", "BLK"), ("TOV", "TOV"),
                      ("FOUL", "FL")):
        view[dst] = daily[src_]

    order = ["FL", "TOV", "BLK", "STL", "AST", "DR", "FTA", "3PA", "2PA",
             "+/-", "B2B", "HOM", "W/L"]
    # each combined lane draws a second kind's bars inside its own, and
    # (for the shooting trios) a % line on top: attempts/makes/% — and
    # the rebound duo, DO (offensive) inside DR (defensive), no line
    COMBO = {"FTA": ("FTM", "FT%"), "3PA": ("3PM", "3P%"),
             "2PA": ("2PM", "2P%"), "DR": ("DO", None)}
    n = len(order)
    days = daily.index
    span_days = max((days[-1] - days[0]).days, 1)
    x_frac = [(d - days[0]).days / span_days for d in days]

    HOME_GREEN, AWAY_RED = "#2ecc55", "#8b1a1a"
    WIN_GREEN, LOSS_RED = "#2ecc55", "#e04545"

    def _brighten(hexc, f=0.4):
        hexc = hexc.lstrip("#")
        r, g, b = (int(hexc[k:k + 2], 16) for k in (0, 2, 4))
        return "#%02X%02X%02X" % tuple(int(c + (255 - c) * f) for c in (r, g, b))

    def _dim(hexc, f=0.2):
        hexc = hexc.lstrip("#")
        r, g, b = (int(hexc[k:k + 2], 16) for k in (0, 2, 4))
        return "#%02X%02X%02X" % tuple(int(c * (1 - f)) for c in (r, g, b))

    _base_home = _TEAM_BRAND_COLORS.get(team, HOME_GREEN) if team else HOME_GREEN
    home_color = _brighten(_base_home)
    hex_by_kind = {
        "W/L": WIN_GREEN, "HOM": home_color, "B2B": "#9BA3AD",
        "+/-": "#F2F2F2",
        "2PM": "#FF9F1C", "2PA": "#C96A0A", "2P%": "#FFD08A",
        "3PM": "#FF4FA3", "3PA": "#B01E6E", "3P%": "#FFA9D4",
        "FTA": "#B7A214", "FTM": "#E8DC3E", "FT%": "#FFF3A0",
        "DR": "#3D7BFF", "DO": "#9CC2FF", "AST": "#6FD9F2", "STL": "#2FD98C",
        "BLK": "#9E6FFF", "TOV": "#C23B3B", "FL": "#FF5555",
    }

    def lane_scale(kind):
        vmin = float(view[kind].min())
        vmax = float(view[kind].max())
        span = max(vmax - vmin, 1.0)
        raw = span / 4
        step = next(t for t in (1, 2, 5, 10, 20, 25, 50) if t >= raw)
        lo = math.floor(vmin / step) * step
        hi = math.ceil(vmax / step) * step
        if hi <= lo:
            hi = lo + step
        return lo, hi, step

    def _pulse_edges(fx: float, hw: float) -> tuple[float, float]:
        """Same edge-game nudge as the 3D page: centre a pulse inward by
        up to `hw` so the season's first and last games keep full width
        instead of being clipped at the pane edge."""
        c = min(max(fx, hw), 1.0 - hw)
        return (c - hw) * 100, (c + hw) * 100

    # flat geometry: stat lanes tall, schedule lanes short, all sharing
    # one x axis; x positions are % of the plot width (responsive), y in
    # px inside a fixed-height plot
    LANE_H, SHORT_H, LANE_GAP = 46, 26, 6
    STAT_H = LANE_H * 0.75  # the stat lanes (2PM and above) run 25% shorter;
                            # +/- keeps the full height
    # with nothing selected every stat lane shows the same SMALL
    # version; selecting (or hovering) a lane grows it to 2x
    heights = [SHORT_H if k in ("W/L", "HOM", "B2B")
               else (LANE_H if k == "+/-" else STAT_H) for k in order]
    # the stat lanes (2PM and above) stack tight — a sliver of a gap
    # between neighbouring stat lanes, the full gap everywhere else
    TIGHT_GAP = 2   # a sliver between bar lanes: room for the trio
                    # label stacks beside the small shooting lanes
    is_stat = [k not in ("W/L", "HOM", "B2B", "+/-") for k in order]
    tops = []
    y = 0
    gap = LANE_GAP
    GROUP_GAP = 18  # extra air above each combined group so the label
                    # stacks don't crowd the lane above
    for idx, h in enumerate(heights):
        tops.append(y)
        gap = (TIGHT_GAP if is_stat[idx] and idx + 1 < n and is_stat[idx + 1]
               else LANE_GAP)
        if idx + 1 < n and order[idx + 1] in COMBO:
            gap = GROUP_GAP
        y += h + gap
    PLOT_H = y - gap
    PW = "min(100vw - 180px, 1152px)"  # the app stays as wide as before
                                       # (plot + 180px of margins = 1320);
                                       # the plot gave up 48px to the
                                       # selected-game value column on the
                                       # right (48px left tick margin,
                                       # labels + values on the right)

    NOSEL = {"+/-", "B2B", "HOM", "W/L"}   # always displayed, never selectable
    sel_idx = [i for i, k_ in enumerate(order) if k_ not in NOSEL]

    # per-game columns: box-score cards, stepper radios, date lines
    game_strips = []
    box_blocks = []
    strip_ids = []
    pair_cells = []
    game_values = []
    pu_labels = []
    ltu_labels = []
    # pair radios are emitted lane-major (all games of one lane adjacent)
    # so keyboard arrows on a focused pair radio step to the SAME lane's
    # previous/next game — left/right keeps moving the game line after
    # plot and scrubber clicks while an event is pinned
    pair_lane_radios = {ci: [] for ci in sel_idx}
    pair_game_radios = []
    gc_css = []
    pu_css = []
    radios = []
    date_lines = []
    strip_css = []
    opp_by_date = {}
    if team:
        from nba_pbp import client
        from nba_pbp.edge import league_history
        from nba_pbp.plusminus import compute_official_box_score_for_game

        hist = league_history(season)
        team_games = hist[hist["TEAM_ABBREVIATION"] == team].sort_values("GAME_DATE")
        team_games = team_games[
            [client.has_cached_play_by_play(g) for g in team_games["GAME_ID"]]
        ]
        opp_by_date = {
            pd.Timestamp(g["GAME_DATE"]).normalize(): str(g["MATCHUP"]).split()[-1]
            for _, g in team_games.iterrows()
        }
        fxs = [(d - days[0]).days / span_days for d in team_games["GAME_DATE"]]
        minutes_by_player: dict[str, float] = {}
        cards = []
        for j, (_, g) in enumerate(team_games.iterrows()):
            fx = fxs[j]
            lo = (fxs[j - 1] + fx) / 2 if j > 0 else 0.0
            hi = (fx + fxs[j + 1]) / 2 if j + 1 < len(fxs) else 1.0
            try:
                gid = g["GAME_ID"]
                was_cached = (client.CACHE_DIR / f"box_score_traditional_{gid}.pkl").exists()
                box = compute_official_box_score_for_game(gid, team)
                if not was_cached:
                    _time.sleep(0.5)
                margin = int(g["PTS"] - g["OPP_PTS"])
                text = _format_official_box_score(box, team, team_margin=margin)
                overlays = _box_score_overlays(box, team)
            except Exception:
                continue
            strip_ids.append(j)
            # the selected-game value column: one entry per lane, from THIS
            # game's own box totals (not the smoothed lane values)
            _tot = box[(box["teamTricode"] == team) & (box["MIN"] > 0)][
                ["FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "REB", "OREB",
                 "DREB", "AST", "STL", "BLK", "TO", "PF"]].sum()
            _margin = int(g["PTS"] - g["OPP_PTS"])
            def _pctv(m, a):
                return f"{round(100 * m / a)}" if a else "-"
            _p2m = int(_tot["FGM"] - _tot["FG3M"])
            _p2a = int(_tot["FGA"] - _tot["FG3A"])
            _date = pd.Timestamp(g["GAME_DATE"]).normalize()
            _away = "@" in str(g["MATCHUP"])
            # venue-coded b2b label (HH/HA/AH/AA), "rest" after 2+ days off
            _b2b = "-"
            if j > 0:
                _pg = team_games.iloc[j - 1]
                _gap = (_date - pd.Timestamp(_pg["GAME_DATE"]).normalize()).days
                if _gap == 1:
                    _b2b = (("A" if "@" in str(_pg["MATCHUP"]) else "H")
                            + ("A" if _away else "H"))
                elif _gap >= 3:
                    _b2b = "OFF"
            _vals = {
                "FL": int(_tot["PF"]), "TOV": int(_tot["TO"]),
                "BLK": int(_tot["BLK"]), "STL": int(_tot["STL"]),
                "AST": int(_tot["AST"]), "DR": int(_tot["DREB"]),
                "DO": int(_tot["OREB"]),
                "FT%": _pctv(_tot["FTM"], _tot["FTA"]),
                "FTM": int(_tot["FTM"]), "FTA": int(_tot["FTA"]),
                "3P%": _pctv(_tot["FG3M"], _tot["FG3A"]),
                "3PA": int(_tot["FG3A"]), "3PM": int(_tot["FG3M"]),
                "2P%": _pctv(_p2m, _p2a), "2PA": _p2a, "2PM": _p2m,
                "+/-": f"{_margin:+d}",
                "B2B": _b2b,
                "HOM": ("@ " if _away else "vs ") + str(g["MATCHUP"]).split()[-1],
                "W/L": str(g["WL"] or ""),
                "score": f"{int(g['PTS'])}-{int(g['OPP_PTS'])}",
            }
            for gi, gkind in enumerate(order):
                cy = tops[gi] + heights[gi] / 2
                if gkind == "W/L":
                    _c = "#2ecc55" if _vals["W/L"] == "W" else "#ff5252"
                elif gkind == "B2B":
                    _c = {"HH": "#FFD54F", "AA": "#e04545", "HA": "#FF69B4",
                          "AH": "#FF69B4", "OFF": "#2ecc55"}.get(
                              _b2b, hex_by_kind["B2B"])
                elif gkind == "HOM":
                    _opp = str(g["MATCHUP"]).split()[-1]
                    _c = _TEAM_BRAND_COLORS.get(_opp, hex_by_kind["HOM"])
                else:
                    _c = hex_by_kind[gkind]
                ay = tops[gi] + heights[gi] - 6.4
                if gkind == "W/L":
                    # the W/L row's "name" is the selected game's result
                    # (W/L, in its win/loss color) followed by the score;
                    # there is no separate value cell
                    game_values.append(
                        f'<div class="gv gv-{j}" style="top:{ay:.0f}px;'
                        f'margin-left:18px;padding-left:6px;color:#ddd;">'
                        f'<span style="color:{_c}">{_vals["W/L"]}</span> '
                        f'{_vals["score"]}</div>')
                elif gkind in COMBO:
                    _mk, _pct = COMBO[gkind]
                    _rows = ((_pct, -32), (gkind, -16), (_mk, 0)) \
                        if _pct is not None else ((gkind, -16), (_mk, 0))
                    for _k, _dy in _rows:
                        game_values.append(
                            f'<div class="gv gv-{j}" style="top:{ay + _dy:.0f}px;'
                            f'color:{hex_by_kind[_k]};">{_vals[_k]}</div>')
                else:
                    game_values.append(
                        f'<div class="gv gv-{j}" style="top:{ay:.0f}px;'
                        f'color:{_c};">{_vals[gkind]}</div>')
            geo = (f'style="left:{max(lo, 0) * 100:.3f}%;'
                   f'width:{(min(hi, 1) - max(lo, 0)) * 100:.3f}%;"')
            game_strips.append(f'<label class="gd gd-{j}" for="g-{j}" {geo}></label>')
            game_strips.append(
                f'<label class="gd gd-{j} gu gu-{j}" for="g-none" {geo}></label>')
            date_lines.append(f'<div class="dl dl-{j}" style="left:{fx * 100:.3f}%;"></div>')
            date_lines.append(f'<div class="ds ds-{j}" {geo}></div>')
            # one PAIR cell per lane in this game's column: a label whose
            # radio encodes (game, lane), so a single plot click pins both.
            # Horizontal geometry via .gc-{j}, vertical via .lc-{i}.
            gc_css.append(f".gc-{j}{{left:{max(lo, 0) * 100:.3f}%;"
                          f"width:{(min(hi, 1) - max(lo, 0)) * 100:.3f}%;}}")
            # the pair's second click TOGGLES the event type, not the whole
            # pin: a game-only state (pg class, no pl) that the per-game
            # unpin twin points at — the game stays selected, the lane
            # clears; a third click on the cell re-selects the pair. Fully
            # unpinning happens on the gap twin (visible in game-only
            # state, under the cells, so lane bands still hit cells).
            pair_game_radios.append(
                f'<input type="radio" class="psel psel-on pg-{j}"'
                f' name="psel" id="p-{j}-g">')
            pu_labels.append(f'<label class="pu pu-{j}" for="p-{j}-g"></label>')
            ltu_labels.append(f'<label class="ltu ltu-{j}" for="p-{j}-g"></label>')
            game_strips.append(
                f'<label class="gd gd-{j} pgu pgu-{j}" for="p-none" {geo}></label>')
            strip_css.append(
                f".st:has(#p-{j}-g:checked) ~ .wrap .pgu-{j}{{display:block;}}"
                f".st:has(.pg-{j}:checked) ~ .wrap .lt-{j}{{display:block;}}")
            for ci in sel_idx:
                pair_cells.append(
                    f'<label class="pc lc lc-{ci} gc-{j}" for="p-{j}-{ci}"></label>')
                pair_lane_radios[ci].append(
                    f'<input type="radio" class="psel psel-on plon pg-{j} pl-{ci}"'
                    f' name="psel" id="p-{j}-{ci}">')
                pu_css.append(
                    f".st:has(#p-{j}-{ci}:checked) ~ .wrap .pu-{j}"
                    f"{{display:block;left:{max(lo, 0) * 100:.3f}%;"
                    f"width:{(min(hi, 1) - max(lo, 0)) * 100:.3f}%;"
                    f"top:{tops[ci]}px;height:{heights[ci]}px;}}"
                    f".st:has(#p-{j}-{ci}:checked) ~ .wrap .ltu-{j}"
                    f"{{display:block;top:{tops[ci] + heights[ci] / 2:.0f}px;}}")
            # state keying: all radios live in the tiny .st container that
            # precedes .wrap and .bxwrap, so `.st:has(#g-j:checked) ~ ...`
            # replaces the former `body:has(#g-j:checked)` form — whole-
            # document :has() invalidation (and later, selector matching
            # across the 1650-radio sibling list) made every game step a
            # 220-270ms style recalc; scoping both to .st makes it ~10ms.
            # GP = game j selected with no pair pinned; WNH = the wrap while
            # the scrubber isn't hovered (hover overrides selection visuals).
            GP = f".st:has(#g-{j}:checked):has(#p-none:checked) ~ "
            WNH = ".wrap:not(:has(.wc:hover))"
            # the game line tracks the mouse ONLY over the W/L lane: a
            # per-game hover cell rides that band; strips and pair cells
            # elsewhere are click targets with no hover behaviour
            game_strips.append(
                f'<label class="wc wc-{j} gc-{j}" for="g-{j}"></label>')
            for ci in sel_idx:
                game_strips.append(
                    f'<label class="wc wc-{j} gc-{j} wcp wcp-{ci}"'
                    f' for="p-{j}-{ci}"></label>')
            game_strips.append(
                f'<label class="wc wc-{j} gc-{j} wcg" for="p-{j}-g"></label>')
            strip_css.append(
                f".wrap:has(.wc-{j}:hover) ~ .bxwrap .bx.bx-{j}"
                f"{{display:block;visibility:visible;transition-delay:0s;}}"
                f"{GP}{WNH} ~ .bxwrap .bx-{j}"
                f"{{display:block;visibility:visible;transition-delay:0s;}}"
                f".st:has(.pg-{j}:checked) ~ {WNH} ~ .bxwrap .bx-{j}"
                f"{{display:block;visibility:visible;transition-delay:0s;}}"
                f".wrap:has(.wc-{j}:hover) .dl-{j},"
                f".wrap:has(.wc-{j}:hover) .gv-{j}{{display:block;}}"
                f"{GP}{WNH} .gv-{j}{{display:block;}}"
                f".st:has(.pg-{j}:checked) ~ {WNH} .gv-{j}{{display:block;}}"
                f"{GP}{WNH} .dl-{j}{{display:block;}}"
                f".st:has(.pg-{j}:checked) ~ {WNH} .dl-{j}{{display:block;}}"
                f"{GP}.wrap .gu-{j}{{display:block;}}"
                f"{GP}{WNH} .ds-{j},"
                f".st:has(.pg-{j}:checked) ~ {WNH} .ds-{j}{{display:block;}}"
                f"{GP}{WNH} .dl-{j},"
                f".st:has(.pg-{j}:checked) ~ {WNH} .dl-{j}"
                f"{{background:#fff;box-shadow:0 0 7px rgba(255,255,255,.85);}}"
                f"{GP}.wrap .wc-{j},"
                f".st:has(.pg-{j}:checked) ~ .wrap .wc-{j}"
                f"{{background:rgba(255,255,255,.20);}}")
            rendered = box[(box["teamTricode"] == team) & (box["MIN"] > 0)]
            for _, r in rendered.iterrows():
                minutes_by_player[r["displayName"]] = (
                    minutes_by_player.get(r["displayName"], 0) + r["MIN"]
                )
            cards.append((j, g, text, overlays, list(rendered["displayName"])))
        player_color = {
            name: _VIVID_COLORS[rank % len(_VIVID_COLORS)]
            for rank, name in enumerate(sorted(
                minutes_by_player, key=minutes_by_player.get, reverse=True))
        }
        for j, g, text, (gold, red, grey), names in cards:
            wl = str(g["WL"] or "")
            res = f"{wl}  {int(g['PTS'])}-{int(g['OPP_PTS'])}"
            head_html = (
                _html.escape(f"{g['GAME_DATE'].date()}  {g['MATCHUP']}  ")
                + f'<span style="color:{"#2ecc55" if wl == "W" else "#ff5252"}">'
                + f"{_html.escape(res)}</span>"
                + (f'  <a href="pm_players_{_html.escape(str(g["GAME_ID"]))}.html"'
                   ' style="color:#6ca0ff">game details</a>'
                   if (output_path.parent / f'pbp_{g["GAME_ID"]}.csv').exists()
                   else '')
            )
            lines = text.split("\n")
            name_ov = "\n".join([""] + [
                f'<span style="color:{player_color[nm]}">'
                f"{_html.escape(line[:_BOX_NAME_WIDTH])}</span>"
                for line, nm in zip(lines[1:1 + len(names)], names)
            ])
            box_blocks.append(
                f'<div class="bx bx-{j}"><span class="bx-head">{head_html}</span>\n\n'
                f'<span class="bxs">{_html.escape(text)}'
                f'<span class="bxo" style="color:goldenrod">{_html.escape(gold)}</span>'
                f'<span class="bxo" style="color:#ff4d4d">{_html.escape(red)}</span>'
                f'<span class="bxo" style="color:#808080">{_html.escape(grey)}</span>'
                f'<span class="bxo">{name_ov}</span>'
                '<span class="cx"></span></span></div>'
            )
        # g-none is display:none so the keyboard's radio-group arrow keys
        # skip it — right/left step through the games and wrap at the ends.
        # It stays in the DOM as the click target for deselecting.
        radios = ['<input type="radio" class="bsel bsel-none" name="bsel" id="g-none">']
        for k, j in enumerate(strip_ids):
            sel = " checked autofocus" if k == 0 else ""
            radios.append(f'<input type="radio" class="bsel" name="bsel" id="g-{j}"{sel}>')

    hom_vals = view["HOM"].to_numpy(dtype=float)
    last_stat = max(i for i in range(n) if is_stat[i])
    stat_bottom = tops[last_stat] + heights[last_stat]
    lanes = [
        # one shared backdrop behind the overlapping stat lanes, instead of
        # per-lane backgrounds that would stack in the overlap zones
        f'<div class="lane" style="top:{tops[0]}px;'
        f'height:{stat_bottom - tops[0]}px;"></div>'
    ]
    ticks = []
    grow_css = []
    for i, kind in enumerate(order):
        h, top = heights[i], tops[i]
        hw = max(0.35 / span_days, 0.0015)
        fills = []
        if kind == "W/L":
            # one vertical line per game day: a 2/3-height green line on
            # a win, full-height red on a loss — losses stand tall
            wl = view["W/L"].to_numpy(dtype=float)
            for fx, v in zip(x_frac, wl):
                win = v >= 0.5
                left, right = _pulse_edges(fx, hw)
                fills.append(
                    f'<div class="fl bar" style="left:{left:.2f}%;'
                    f'width:{right - left:.2f}%;'
                    f'top:{100 / 3 if win else 0.0:.2f}%;bottom:0;'
                    f'background:{WIN_GREEN if win else LOSS_RED};"></div>')
        elif kind == "HOM":
            # away games full height, home games half — road games stand out
            for fx, hom, date in zip(x_frac, hom_vals, view.index):
                if hom >= 0.5:
                    color, top_pct = home_color, 50.0
                else:
                    opp = opp_by_date.get(pd.Timestamp(date).normalize()) if team else None
                    color = _dim(_TEAM_BRAND_COLORS.get(opp, AWAY_RED))
                    top_pct = 0.0
                left, right = _pulse_edges(fx, hw)
                fills.append(
                    f'<div class="fl bar" style="left:{left:.2f}%;'
                    f'width:{right - left:.2f}%;top:{top_pct:.0f}%;bottom:0;'
                    f'background:{color};"></div>')
        elif kind == "B2B":
            # b2b pairs by venue: HH yellow, AA red, HA/AH pink; a small
            # green mark on any game following 2+ full days off
            B2B_COLORS = {2: "#FFD54F", 1: "#FF69B4", 0: "#e04545"}
            REST_GREEN = "#2ecc55"
            game_dates = [pd.Timestamp(d).normalize() for d in view.index]
            for j, (fx, v) in enumerate(zip(x_frac, view["B2B"])):
                top_pct = 0.0
                if v >= 0.99:
                    n_home = int(hom_vals[j] >= 0.5)
                    if j > 0:
                        n_home += int(hom_vals[j - 1] >= 0.5)
                    color = B2B_COLORS[n_home]
                elif j > 0 and (game_dates[j] - game_dates[j - 1]).days >= 3:
                    color = REST_GREEN
                    top_pct = 50.0
                else:
                    continue
                left, right = _pulse_edges(fx, hw)
                fills.append(
                    f'<div class="fl bar" style="left:{left:.2f}%;'
                    f'width:{right - left:.2f}%;top:{top_pct:.0f}%;bottom:0;'
                    f'background:{color};"></div>')
        elif kind == "+/-":
            # one vertical bar per game: its length is the raw margin's
            # absolute value (lane-normalized), green on a win margin,
            # red on a loss
            POS, NEG = "#2ecc55", "#e04545"
            z = view["+/-"].to_numpy(dtype=float)
            vmax = max((abs(float(v)) for v in z), default=1.0) or 1.0
            for fx, v in zip(x_frac, z):
                left, right = _pulse_edges(fx, hw)
                fills.append(
                    f'<div class="fl bar" style="left:{left:.2f}%;'
                    f'width:{right - left:.2f}%;'
                    f'top:{(1 - abs(float(v)) / vmax) * 100:.2f}%;bottom:0;'
                    f'background:{POS if v >= 0 else NEG};"></div>')
        else:
            lo, hi, step = lane_scale(kind)
            rng = hi - lo
            z = view[kind].to_numpy(dtype=float)
            if kind in BAR_RAW:
                # per-game vertical bars on the raw counts, bar length
                # is the value, in the lane's own color. Makes share
                # their attempts lane's range so the pair is comparable.
                z = BAR_RAW[kind].to_numpy(dtype=float)
                if kind in COMBO:
                    # the makes draw on top of the attempts, one lane
                    # reading makes-within-attempts. Auto-ranged from the
                    # makes' floor to the attempts' ceiling (attempts are
                    # always the larger), with integer ticks
                    _mk, _pct = COMBO[kind]
                    zm = BAR_RAW[_mk].to_numpy(dtype=float)
                    vmin, vmax = float(zm.min()), float(z.max())
                    for step in (1, 2, 5, 10, 20):
                        if (vmax - vmin) / step <= 6:
                            break
                    lo = math.floor(vmin / step) * step
                    hi = max(math.ceil(vmax / step) * step, lo + step)
                    rng = hi - lo
                    for fx, va, vm in zip(x_frac, z, zm):
                        left, right = _pulse_edges(fx, hw)
                        for v, c in ((va, hex_by_kind[kind]),
                                     (vm, hex_by_kind[_mk])):
                            fills.append(
                                f'<div class="fl bar" style="left:{left:.2f}%;'
                                f'width:{right - left:.2f}%;'
                                f'top:{(1 - (float(v) - lo) / rng) * 100:.2f}%;'
                                f'bottom:0;background:{c};"></div>')
                    if _pct is not None:
                        # the smoothed % line rides on top, on its own scale
                        plo, phi, _ = lane_scale(_pct)
                        prng = phi - plo
                        pz = view[_pct].to_numpy(dtype=float)
                        PHW = 2.0
                        ptop = [f"{fx * 100:.2f}% {(1 - (v - plo) / prng) * 100 - PHW:.2f}%"
                                for fx, v in zip(x_frac, pz)]
                        pbot = [f"{fx * 100:.2f}% {(1 - (v - plo) / prng) * 100 + PHW:.2f}%"
                                for fx, v in zip(x_frac, pz)]
                        fills.append(
                            f'<div class="fl" style="inset:0;clip-path:polygon('
                            f'{", ".join(ptop + pbot[::-1])});'
                            f'background:{hex_by_kind[_pct]};"></div>')
                    bar_tops = []
                elif kind in ("FL", "TOV", "BLK", "STL", "AST"):
                    # auto-ranged like the shooting lanes: the axis hugs
                    # the data instead of reaching to 0, integer ticks
                    vmin, vmax = float(z.min()), float(z.max())
                    for step in (1, 2, 5, 10, 20):
                        if (vmax - vmin) / step <= 6:
                            break
                    lo = math.floor(vmin / step) * step
                    hi = max(math.ceil(vmax / step) * step, lo + step)
                    rng = hi - lo
                    bar_tops = ((1 - (float(v) - lo) / rng) * 100 for v in z)
                else:
                    vmax = max(float(z.max()), 1.0)
                    lo, hi, rng = 0.0, vmax, vmax   # axis follows the bars
                    bar_tops = ((1 - float(v) / vmax) * 100 for v in z)
                for fx, top_pct in zip(x_frac, bar_tops):
                    left, right = _pulse_edges(fx, hw)
                    fills.append(
                        f'<div class="fl bar" style="left:{left:.2f}%;'
                        f'width:{right - left:.2f}%;'
                        f'top:{top_pct:.2f}%;bottom:0;'
                        f'background:{hex_by_kind[kind]};"></div>')
            else:
                HW = 2.0  # band half-thickness, % of the lane height — a
                          # thin, basic line rather than a ribbon
                frac = [(v - lo) / rng for v in z]
                topl = [f"{fx * 100:.2f}% {(1 - f) * 100 - HW:.2f}%" for fx, f in zip(x_frac, frac)]
                botl = [f"{fx * 100:.2f}% {(1 - f) * 100 + HW:.2f}%" for fx, f in zip(x_frac, frac)]
                fills.append(
                    f'<div class="fl" style="inset:0;clip-path:polygon('
                    f'{", ".join(topl + botl[::-1])});'
                    f'background:{hex_by_kind[kind]};"></div>')
            # the lane's own value axis, revealed on spotlight. The
            # shrunk stat lanes GROW to 2x height while spotlighted (the
            # dimmed neighbours sit behind), so their axis is laid out for
            # the doubled geometry — it is only visible while doubled.
            # the expanded lane keeps its BASELINE: it grows upward
            # only, so the bars stay anchored exactly where the small
            # version drew them instead of the whole chart dropping
            ax_top, ax_h = top - h, 2 * h
            grow_css.append(
                f".wrap:has(.lbl-{i}:hover) .lane-{i},"
                f".st:has(#e-{i}:checked):has(#p-none:checked) ~ "
                f".wrap:not(:has(.lbl:hover)) .lane-{i},"
                f".st:has(.pl-{i}:checked) ~ .wrap:not(:has(.lbl:hover)) .lane-{i}"
                f"{{top:{ax_top:.1f}px!important;height:{ax_h:.1f}px!important;"
                f"z-index:2;}}")
            t = lo
            while t <= hi + 1e-9:
                fy = ax_top + (1 - (t - lo) / rng) * ax_h
                ticks.append(
                    f'<div class="zt zt-{i}" style="top:{fy:.1f}px;">{int(t)}</div>')
                ticks.append(
                    f'<div class="zg zg-{i}" style="top:{fy:.1f}px;"></div>')
                t += step
        bg = "background:none;" if is_stat[i] else ""
        lanes.append(
            f'<div class="lane lane-{i}" style="top:{top}px;height:{h}px;{bg}">'
            + "".join(fills) + "</div>")

    # month gridlines + static labels along the shared date axis
    months = []
    seen = None
    for j, d in enumerate(days):
        key = (d.year, d.month)
        if key != seen:
            seen = key
            months.append(
                f'<div class="mg" style="left:{x_frac[j] * 100:.2f}%;"></div>'
                f'<div class="ml" style="left:{x_frac[j] * 100:.2f}%;">'
                f'{d.strftime("%b")}</div>')

    # lane labels on the right edge, with the click-to-deselect twin
    lane_radios = ['<input type="radio" class="esel esel-none" name="esel" id="e-none" checked>']
    labels = []
    for i, kind in enumerate(order):
        cy = tops[i] + heights[i] / 2
        geo = f'style="top:{cy:.0f}px;color:{hex_by_kind[kind]};"'
        if i not in sel_idx:
            # always-on lanes: the name is plain text, not a control;
            # the HOM lane is titled with the team's own tricode. These
            # labels sit on their lane baselines like the stat labels.
            # W/L has no static name — its slot shows the selected game's
            # result (W/L) with the score beside it, from the value column.
            if kind == "W/L":
                continue
            shown = team if kind == "HOM" and team else kind
            ay = tops[i] + heights[i] - 6.4
            size = "font-size:22px;" if kind == "+/-" else ""
            labels.append(f'<div class="lbln" style="top:{ay:.0f}px;'
                          f'color:{hex_by_kind[kind]};{size}">{shown}</div>')
            continue
        pos = sel_idx.index(i)
        lane_radios.append(f'<input type="radio" class="esel esel-on" name="esel" id="e-{i}">')
        # stat labels sit ON their lane's baseline (the bars' zero line):
        # the anchor is nudged so the text baseline lands on the lane
        # bottom; a trio stacks upward from there, makes row on the base
        ay = tops[i] + heights[i] - 6.4
        geo = (f'style="top:{(ay - 16 if kind in COMBO else ay):.0f}px;'
               f'color:{hex_by_kind[kind]};"')
        if kind in COMBO:
            # a combined lane titles as a tight stack (%/attempts/makes,
            # or DR/DO); only the outer kind's line is a control
            _mk, _pct = COMBO[kind]
            if _pct is not None:
                labels.append(f'<div class="lbln" style="top:{ay - 32:.0f}px;'
                              f'color:{hex_by_kind[_pct]};">{_pct}</div>')
            labels.append(f'<div class="lbln" style="top:{ay:.0f}px;'
                          f'color:{hex_by_kind[_mk]};">{_mk}</div>')
        labels.append(f'<label class="lbl lbl-{i}" for="e-{i}" {geo}>{kind}</label>')
        labels.append(
            f'<label class="lbl lbl-{i} lblu lblu-{i}" for="e-none" {geo}>{kind}</label>')
        # while a game is pinned, label clicks reroute into pair-space:
        # they swap the pinned event instead of driving the (suppressed)
        # standalone lane group
        for j in strip_ids:
            labels.append(
                f'<label class="lbl lbl-{i} lt lt-{j}" for="p-{j}-{i}" {geo}>{kind}</label>')


    if team:
        try:
            from nba_api.stats.static import teams as _static_teams
            _info = next((t for t in _static_teams.get_teams()
                          if t["abbreviation"] == team), None)
            who = (_info["full_name"] if _info else team) + " "
        except Exception:
            who = f"{team} "
    else:
        who = ""
    try:
        _y0, _y1 = season.split("-")
        full_season = f"{_y0}-{_y0[:2]}{_y1}"
    except Exception:
        full_season = season
    title = f"{who}{full_season}"

    # the box-score column behind each lane name: character ranges from
    # the header layout (name column first, then fixed widths), in ch
    # units so the browser uses the mono font's EXACT advance (an em
    # guess drifts by a few px by the rightmost columns). 2P lanes map
    # onto the FG
    # columns (the box score has no 2P split); schedule lanes map nowhere.
    _cols = [("MIN", 3), ("PTS", 4), ("+/-", 5), ("FGM", 4), ("FGA", 4),
             ("FG%", 5), ("3PM", 4), ("3PA", 4), ("3P%", 5), ("FTM", 4),
             ("FTA", 4), ("FT%", 5), ("OREB", 5), ("DREB", 5), ("REB", 4),
             ("AST", 4), ("STL", 4), ("BLK", 4), ("TO", 3), ("PF", 3)]
    _col_range = {}
    _pos = _BOX_NAME_WIDTH
    for _cname, _cw in _cols:
        _col_range[_cname] = (_pos, _cw)
        _pos += _cw
    _lane_to_col = {"FL": "PF", "TOV": "TO", "BLK": "BLK", "STL": "STL",
                    "AST": "AST", "DR": "DREB", "FT%": "FT%", "FTM": "FTM",
                    "FTA": "FTA", "3P%": "3P%", "3PA": "3PA", "3PM": "3PM",
                    "2P%": "FG%", "2PA": "FGA", "2PM": "FGM", "+/-": "+/-"}
    col_css = []
    for i, kind in enumerate(order):
        col = _lane_to_col.get(kind)
        if not col or i not in sel_idx:
            continue
        start, width = _col_range[col]
        col_css.append(
            f".wrap:has(.lbl-{i}:hover) ~ .bxwrap .bx .cx,"
            f".st:has(#e-{i}:checked):has(#p-none:checked) ~ "
            f".wrap:not(:has(.lbl:hover)) ~ .bxwrap .bx .cx,"
            f".st:has(.pl-{i}:checked) ~ .wrap:not(:has(.lbl:hover)) ~ .bxwrap .bx .cx"
            f"{{display:block;left:{start + 1}ch;width:{width - 1}ch;}}")

    lc_css = (".lc{position:absolute;display:block;}"
              ".pc{cursor:pointer;z-index:5;}"
              ".pu{display:none;position:absolute;z-index:6;cursor:pointer;}"
              ".pgu{display:none;}"
              + (lambda t0, t1: f".wc{{position:absolute;top:{t0}px;"
                                f"height:{t1 - t0}px;"
                                "z-index:5;cursor:crosshair;}")(
                    tops[order.index('+/-')],
                    tops[order.index('W/L')] + heights[order.index('W/L')])
              + ".wc:hover{background:rgba(255,255,255,.08);}"
              + (lambda t0, t1: f".wcband{{position:absolute;left:0;right:0;"
                                f"top:{t0}px;height:{t1 - t0}px;"
                                "pointer-events:none;z-index:1;}")(
                    tops[order.index('+/-')],
                    tops[order.index('W/L')] + heights[order.index('W/L')])
              + ".wrap:has(.wc:hover) .wcband{background:rgba(255,255,255,.05);}"
              + (".st:has(.bsel:checked:not(.bsel-none)) ~ .wrap .wcband,"
                 ".st:has(.psel-on:checked) ~ .wrap .wcband"
                 "{background:rgba(255,255,255,.05);}")
              + (".kb{display:none;position:absolute;left:-4px;right:-4px;"
                 "box-sizing:border-box;border:2px solid #FFD54F;"
                 "border-radius:4px;pointer-events:none;z-index:6;}"
                 ".st:has(.bsel:focus) ~ .wrap .kb,"
                 ".st:has(.psel:focus) ~ .wrap .kb{display:block;}")
              + ".wcp,.wcg{display:none;z-index:6;}"
              + "".join(f".st:has(.pl-{ci}:checked) ~ .wrap .wcp-{ci}{{display:block;}}"
                        for ci in sel_idx)
              + ".st:has(.psel-on:checked:not(.plon)) ~ .wrap .wcg{display:block;}"
              + ".lt{display:none;z-index:7;}"
              # line-height pinned and the anchor nudged 0.8px so the
              # 15px values share the 13px labels' text BASELINE (their
              # ascents differ; box-center alignment leaves ~1px skew)
              ".gv{display:none;position:absolute;left:100%;margin-left:64px;"
              "transform:translateY(calc(-50% - .8px));line-height:1.05;"
              "font-size:17px;white-space:nowrap;z-index:5;}"
              ".ltu{display:none;position:absolute;left:100%;margin-left:6px;"
              "width:74px;height:22px;transform:translateY(-50%);"
              "z-index:8;cursor:pointer;}"
              ".st:has(.plon:checked) ~ .wrap .lane{opacity:.15;}"
              + ",".join(f".lane-{i}" for i in range(n) if order[i] in NOSEL)
              + "{opacity:1!important;}"
              ".lbln{position:absolute;left:100%;margin-left:18px;"
              "transform:translateY(-50%);white-space:nowrap;padding:1px 6px;"
              "font-size:15px;line-height:1.05;z-index:5;}"
              # pair radios stay focusable (offscreen): plot/scrubber
              # clicks hand the arrow keys to the pair group, whose
              # lane-major order makes l/r step previous/next game with
              # the same lane kept. p-none is display:none so keyboard
              # stepping skips it; esel stays fully hidden.
              ".psel{position:fixed;left:-30px;top:12px;opacity:0;"
              "width:2px;height:2px;}"
              ".psel-none{display:none;}"
              + "".join(
                  f".lc-{i}{{top:{tops[i]}px;height:{heights[i]}px;}}"
                  for i in range(n)))

    G = ":not(:has(.lbl:hover))"
    EP = ":has(#p-none:checked) ~ "   # AND no pair pinned
    spotlight_css = "".join(
        f".wrap:has(.lbl-{i}:hover) .lane-{i}{{opacity:1;}}"
        f".st:has(#e-{i}:checked){EP}.wrap{G} .lane-{i},"
        f".st:has(.pl-{i}:checked) ~ .wrap{G} .lane-{i}{{opacity:1;}}"
        f".wrap:has(.lbl-{i}:hover) .zt-{i},"
        f".wrap:has(.lbl-{i}:hover) .zg-{i}{{display:block;}}"
        f".st:has(#e-{i}:checked){EP}.wrap{G} .zt-{i},"
        f".st:has(#e-{i}:checked){EP}.wrap{G} .zg-{i},"
        f".st:has(.pl-{i}:checked) ~ .wrap{G} .zt-{i},"
        f".st:has(.pl-{i}:checked) ~ .wrap{G} .zg-{i}{{display:block;}}"
        f".st:has(#e-{i}:checked){EP}.wrap .lblu-{i}{{display:block;}}"
        f".st:has(#e-{i}:checked){EP}.wrap .lbl-{i},"
        f".st:has(.pl-{i}:checked) ~ .wrap .lbl-{i}"
        f"{{text-shadow:0 0 7px currentColor;background:rgba(255,255,255,.16);border-radius:4px;}}"
        for i in sel_idx
    )

    # an upper-right link to the league-wide season page, when it's in
    # this collection
    _league = (output_path.parent / "nba_season.html")
    league_link = (
        f'<a class="leaguelink" href="nba_season.html">NBA {full_season} Season Averages</a>'
        if _league.exists() else "")

    css = f"""
body{{background:#000;color:#ddd;font-family:'DejaVu Sans',sans-serif;margin:0 0 24px;}}
h1{{font-size:20px;font-weight:normal;color:#eee;text-align:center;margin:14px 0 10px;}}
.leaguelink{{position:absolute;top:12px;right:16px;color:#6ca0ff;
  text-decoration:none;font-size:14px;z-index:50;}}
.leaguelink:hover{{text-decoration:underline;}}
/* the 120px reserve splits asymmetrically: ~48px left for the spotlight
   tick labels, ~72px right for the always-visible event-selector column —
   the whole block (ticks + plot + labels) centres as a unit */
.wrap{{position:relative;width:{PW};
  margin:0 0 0 calc((100vw - {PW} - 180px) / 2 + 48px);}}
.plot{{position:relative;height:{PLOT_H}px;}}
.lane{{position:absolute;left:0;right:0;background:rgba(255,255,255,.035);}}
.fl{{position:absolute;}}
.lbl{{position:absolute;left:100%;margin-left:18px;transform:translateY(-50%);
  cursor:pointer;white-space:nowrap;padding:1px 6px;font-size:15px;line-height:1.05;z-index:5;}}
.lbl:hover{{text-shadow:0 0 6px currentColor;background:rgba(255,255,255,.14);border-radius:4px;}}
.lblu{{display:none;z-index:6;}}
.zt{{display:none;position:absolute;right:100%;margin-right:8px;
  transform:translateY(-50%);font-size:11px;color:#ccc;z-index:5;}}
.zg{{display:none;position:absolute;left:0;right:0;height:1px;
  background:rgba(255,255,255,.18);z-index:1;}}
.mg{{position:absolute;top:0;bottom:0;width:1px;background:rgba(255,255,255,.10);}}
.ml{{position:absolute;top:100%;margin-top:6px;transform:translateX(-50%);
  font-size:13px;color:#999;}}
.gd{{position:absolute;top:0;bottom:0;z-index:4;cursor:pointer;}}
.gu{{display:none;z-index:5;}}
.dl{{display:none;position:absolute;top:0;bottom:0;width:2px;margin-left:-1px;
  background:#8a8a8a;z-index:-1;}}
.ds{{display:none;position:absolute;top:0;bottom:0;
  background:rgba(255,255,255,.06);z-index:-1;pointer-events:none;}}
.wrap:has(.lbl:hover) .lane{{opacity:.15;}}
.st:has(.esel-on:checked) ~ .wrap:not(:has(.lbl:hover)) .lane{{opacity:.15;}}
.bsel{{position:fixed;left:-30px;top:0;opacity:0;width:2px;height:2px;}}
.bsel-none{{display:none;}}
.esel{{display:none;}}
/* the card scales with the viewport but CAPS at the app width (plot +
   margins = 1332px), so on wide/fullscreen windows it stays in scale
   with the width-capped plot instead of ballooning */
.bxwrap{{position:relative;height:calc(min(100vw, 1332px) * 0.48 + 8px);
  margin:34px 0 12px;}}
.bx{{visibility:hidden;transition:visibility 0s 999999s;
  position:absolute;top:0;left:50%;transform:translateX(-50%);
  box-sizing:border-box;width:min(100vw, 1332px);
  font-family:'DejaVu Sans Mono',monospace;line-height:1.5;
  font-size:calc((min(100vw, 1332px) - 34px) / 60.2);color:{_BOX_HTML_TEXT};
  white-space:pre;background:rgba(0,0,0,.95);padding:10px 16px;
  z-index:30;overflow-x:auto;}}
.wrap:has(.wc:hover) ~ .bxwrap .bx{{visibility:hidden;transition-delay:0s;}}
.st:has(.bsel:checked:not(.bsel-none)) ~ .bxwrap .bx{{display:none;
  visibility:visible;transition-delay:0s;}}
.bx-head{{color:{_BOX_HEAD_COLOR};}}
.bxs{{position:relative;display:inline-block;}}
.bxo{{position:absolute;left:0;top:0;white-space:pre;pointer-events:none;}}
.cx{{display:none;position:absolute;top:0;bottom:0;
  background:#909090;mix-blend-mode:color-dodge;pointer-events:none;}}
""" + lc_css + "".join(gc_css) + "".join(pu_css) + "".join(strip_css) + spotlight_css + "".join(grow_css) + "".join(col_css)

    pair_radios = (
        ['<input type="radio" class="psel psel-none" name="psel" id="p-none" checked>']
        + [r for ci in sel_idx for r in pair_lane_radios[ci]]
        + pair_game_radios)

    # a yellow frame around the four bottom plots whenever keyboard
    # focus is on a game/pair radio — i.e. the arrow keys are live and
    # will step the game line
    _kb_top = tops[order.index("+/-")] - 4
    _kb_bot = tops[order.index("W/L")] + heights[order.index("W/L")] + 4
    kb_box = (f'<div class="kb" style="top:{_kb_top:.0f}px;'
              f'height:{_kb_bot - _kb_top:.0f}px;"></div>')

    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        f"<title>{title}</title><style>{css}</style></head><body>"
        f"<h1>{title}</h1>{league_link}<div class=\"st\">{''.join(radios)}"
        f"{''.join(lane_radios)}{''.join(pair_radios)}</div>"
        '<div class="wrap"><div class="plot">'
        + "".join(lanes) + "".join(months) + "".join(date_lines)
        + '<div class="wcband"></div>'
        + "".join(game_strips) + "".join(pair_cells)
        + "".join(pu_labels)
        + kb_box + "".join(ltu_labels) + "".join(ticks)
        + f"</div>{''.join(labels)}{''.join(game_values)}</div>"
        + f'<div class="bxwrap">{"".join(box_blocks)}</div></body></html>'
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path
