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


# one shared style for every panel/box-score title (team panels, player
# charts, lineup panels, lineup box scores) — player chart titles use this
# size/placement too, but keep their player color
_PANEL_TITLE_FONTSIZE = 13.0 * (8 / 12) * ((0.86 - 0.10) / (0.98 - 0.06)) * 1.15 * 1.15
_PANEL_TITLE_COLOR = "lightgray"

# the title block (matchup/date/venue) and per-period linescore at the top of
# the page — 80% of their original 15pt size
_HEADER_FONTSIZE = 15 * 0.8

# left edge, in figure-fraction, shared by every left-aligned header/box-score
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
    """Standard box-score linescore: each team's points per period, plus the
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
    """The monospace-aligned box-score column header, matching the layout of
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
        f"{_fit_name(s['lineup'], _BOX_NAME_WIDTH)}{round(s['MIN']):>3}{s['PTS']:>4}{pm_str:>5}"
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
        f"{_fit_name(s['displayName'], _BOX_NAME_WIDTH)}{round(s['MIN']):>3}{s['PTS']:>4}{pm_str:>5}"
        f"{s['FGM']:>4}{s['FGA']:>4}{pct(s['FGM'], s['FGA']):>5}"
        f"{s['FG3M']:>4}{s['FG3A']:>4}{pct(s['FG3M'], s['FG3A']):>5}"
        f"{s['FTM']:>4}{s['FTA']:>4}{pct(s['FTM'], s['FTA']):>5}"
        f"{s['OREB']:>5}{s['DREB']:>5}{s['REB']:>4}{s['AST']:>4}{s['STL']:>4}{s['BLK']:>4}"
        f"{s['TO']:>3}{s['PF']:>3}"
    )


# each lineup box-score column: (value for max comparison, cell renderer with
# its field width, is_red). Highlighted with the same rules as the player box
# score (`_box_score_overlays`).
def _pm_str(r):
    pm = r["PLUS_MINUS"]
    return f"+{pm}" if pm > 0 else f"{pm}"


def _lineup_pct(made, att):
    return round(made / att * 100) if att else 0


_LINEUP_BOX_HTML_COLUMNS = [
    (lambda r: round(r["MIN"]), lambda r: f"{round(r['MIN']):>3}", False),
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
# box-score column order (_BOX_MAX_COLUMNS / _LINEUP_BOX_HTML_COLUMNS) —
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
    """One player's monospace-aligned box-score row, aligned to
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

    totals = team_box[
        ["MIN", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "PTS"]
    ].sum()
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
    min_cell = " - " if per_minutes else f"{totals['MIN']:>3}"
    lines.append(
        f"{_fit_name(team, name_width)}{min_cell}{totals['PTS']:>4}{margin_str:>5}"
        f"{totals['FGM']:>4}{totals['FGA']:>4}{fg_pct:>5.0f}"
        f"{totals['FG3M']:>4}{totals['FG3A']:>4}{fg3_pct:>5.0f}"
        f"{totals['FTM']:>4}{totals['FTA']:>4}{ft_pct:>5.0f}"
        f"{totals['OREB']:>5}{totals['DREB']:>5}{totals['REB']:>4}{totals['AST']:>4}{totals['STL']:>4}{totals['BLK']:>4}"
        f"{totals['TO']:>3}{totals['PF']:>3}"
    )
    return "\n".join(lines)


# each stat column, in box-score order: (max-comparison value, rendered cell
# — matching `_box_score_player_line` exactly, field width, is_red). The
# rendered cell is what overlays the gray text, so it must be byte-identical.
def _pm_cell(r: pd.Series) -> str:
    pm = r["PLUS_MINUS"]
    return f"{('+' + format(pm, '.0f')) if pm > 0 else format(pm, '.0f'):>5}"


_BOX_MAX_COLUMNS = [
    (lambda r: r["MIN"], lambda r: f"{r['MIN']:>3}", 3, False),
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


def _measure_text_height_inches(text: str, fontsize: float, family: str, dpi: float = 150) -> float:
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
    artist = fig.text(0.5, 0.5, text, fontsize=fontsize, family=family, ha="center", va="center")
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


def load_shots(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    shots = df[df["isFieldGoal"] == 1].dropna(subset=["shotResult", "shotDistance", "playerName"]).copy()
    shots["game_minutes"] = [
        _game_seconds(p, c) / 60 for p, c in zip(shots["period"], shots["clock"])
    ]
    return shots


def plot_shots(csv_path: Path, output_path: Path, game_info: dict | None = None) -> Path:
    """2x1 grid: one subplot per team, Made solid / Missed at 0.5 alpha."""
    shots = load_shots(csv_path)
    if shots.empty:
        raise ValueError(f"No shot events found in {csv_path}")

    teams = sorted(shots["teamTricode"].dropna().unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 teams, found: {teams}")

    tick_positions, tick_labels = _quarter_ticks(int(shots["period"].max()))
    if _PROJECTION_OFFSET not in tick_positions:
        tick_positions = [_PROJECTION_OFFSET] + tick_positions
        tick_labels = [""] + tick_labels

    with plt.style.context("dark_background"):
        fig = plt.figure(figsize=(12, 15.6))

        for row, team in enumerate(teams):
            team_shots = shots[shots["teamTricode"] == team]
            players = sorted(team_shots["playerName"].unique())
            player_y = {name: i for i, name in enumerate(players)}
            n_players = len(players)
            cmap = plt.get_cmap("tab10" if n_players <= 10 else "tab20", n_players)

            ax = fig.add_subplot(2, 1, row + 1, projection="3d")
            ax.view_init(elev=_ELEV, azim=-60)

            made = team_shots[team_shots["shotResult"] == "Made"]
            missed = team_shots[team_shots["shotResult"] == "Missed"]
            norm = plt.Normalize(vmin=-0.5, vmax=n_players - 0.5)

            for subset, alpha, size_scale in ((made, 1.0, 0.35), (missed, 0.5, 0.35)):
                y_vals = subset["playerName"].map(player_y)
                sizes = subset["shotValue"].map({2: 30, 3: 45}).fillna(30) * size_scale
                proj_sizes = sizes * 0.4
                time_proj_sizes = sizes * 0.15
                shared_kwargs = dict(c=y_vals, cmap=cmap, vmin=-0.5, vmax=n_players - 0.5, depthshade=True)

                ax.scatter(
                    subset["game_minutes"],
                    y_vals,
                    subset["shotDistance"],
                    s=sizes,
                    alpha=alpha,
                    marker="D",
                    **shared_kwargs,
                )
                # projection onto the time=Q1 12:00 plane
                ax.scatter(
                    _PROJECTION_OFFSET, y_vals, subset["shotDistance"], s=time_proj_sizes, alpha=alpha,
                    marker="o", **shared_kwargs
                )
                # projection onto the shot-distance=-6 plane
                ax.scatter(
                    subset["game_minutes"], y_vals, _PROJECTION_OFFSET, s=proj_sizes, alpha=alpha,
                    marker="o", **shared_kwargs
                )

            for x, y, z in zip(made["game_minutes"], made["playerName"].map(player_y), made["shotDistance"]):
                ax.plot([x, x], [y, y], [0, z], color=cmap(norm(y)), alpha=0.4, linewidth=0.8)

            for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
                axis.set_pane_color(_PANE_COLOR)
                axis._axinfo["grid"]["color"] = (1, 1, 1, 0.15)

            ax.text2D(
                0.5, 0.85, f"{team} — Made ({len(made)}) / Missed ({len(missed)})",
                transform=ax.transAxes, ha="center", fontsize=9, color="white",
            )
            ax.set_zlabel("Shot distance (ft)")
            z_max = team_shots["shotDistance"].max()
            z_ticks = list(range(0, int(z_max) + 5, 5))
            z_labels = [str(t) for t in z_ticks]
            ax.set_zlim(_PROJECTION_OFFSET, z_max * 1.05)
            ax.zaxis.set_major_locator(FixedLocator(z_ticks))
            ax.zaxis.set_major_formatter(FixedFormatter(z_labels))
            ax.set_xlim(left=_PROJECTION_OFFSET)
            ax.xaxis.set_major_locator(FixedLocator(tick_positions))
            ax.xaxis.set_ticklabels([])
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            z0, z1 = ax.get_zlim()

            time_label_y = y0
            time_label_z = z0 - (z1 - z0) * 0.03
            for x, time_label in zip(tick_positions, tick_labels):
                if time_label:
                    ax.text(
                        x, time_label_y, time_label_z, time_label,
                        color="white", fontsize=7, ha="center", va="top",
                    )
            ax.set_yticks(list(player_y.values()))
            ax.set_yticklabels([])
            label_x = x1 + (x1 - x0) * 0.03
            label_z = z0
            for name, i in player_y.items():
                ax.text(label_x, i, label_z, name, color=cmap(norm(i)), fontsize=6, ha="left", va="center")

        game_id = shots["gameId"].iloc[0] if "gameId" in shots.columns else ""
        if game_info:
            subtitle = (
                f"{game_info['away_team']} @ {game_info['home_team']}\n"
                f"{game_info['date']} at {game_info['time']}\n"
                f"{game_info['location']}\n"
                f"Game ID: {game_id}"
            )
            fig.text(0.5, 0.98, subtitle, ha="center", va="top", fontsize=10, color="lightgray", linespacing=1.8)
        else:
            fig.suptitle(f"Shot chart — game {game_id}", fontsize=15, y=0.98)
        fig.subplots_adjust(hspace=0.15, top=0.92, bottom=0.04)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
    return output_path


def plot_plus_minus(csv_path: Path, output_path: Path, game_info: dict | None = None) -> Path:
    """2x1 grid of 2D plots (one per team): game time on x, on-court plus/minus
    on y. Each player is a color (legend, not an axis) — a straight line runs
    from a player's plus/minus at the start of each on-court stint to their
    plus/minus at the end of it, with diamond markers at the moments they
    personally took a shot (solid = made, faded = missed).

    Note: on-court plus/minus is reconstructed from substitution events in the
    play-by-play feed. That feed occasionally has real gaps/inconsistencies
    (a player's entrance missing entirely, or logged as entering when already
    tracked on court), so values can be off by a few points versus the box
    score for some players — treat this as an approximation, not ground truth.
    """
    from nba_pbp.plusminus import compute_shot_plus_minus, compute_stint_plus_minus, compute_team_margin_timeline

    shots, _ = compute_shot_plus_minus(csv_path)
    if shots.empty:
        raise ValueError(f"No shot events found in {csv_path}")
    stint_pm = compute_stint_plus_minus(csv_path)
    margin_timeline, margin_home_team, margin_away_team = compute_team_margin_timeline(csv_path)

    teams = sorted(shots["teamTricode"].dropna().unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 teams, found: {teams}")

    tick_positions, tick_labels = _quarter_ticks(int(shots["period"].max()))

    pm_min = min(shots["plusMinus"].min(), stint_pm["entry_pm"].min(), stint_pm["exit_pm"].min())
    pm_max = max(shots["plusMinus"].max(), stint_pm["entry_pm"].max(), stint_pm["exit_pm"].max())
    pm_pad = (pm_max - pm_min) * 0.05
    y_limits = (pm_min - pm_pad, pm_max + pm_pad)

    with plt.style.context("dark_background"):
        fig, axes = plt.subplots(2, 1, figsize=(12, 13))

        for ax, team in zip(axes, teams):
            team_shots = shots[shots["teamTricode"] == team]
            team_stint_pm = stint_pm[stint_pm["teamTricode"] == team]
            players = sorted(set(team_shots["displayName"]) | set(team_stint_pm["displayName"]))
            n_players = len(players)
            cmap = _vivid_cmap(n_players)
            player_color = {name: cmap(i) for i, name in enumerate(players)}

            made = team_shots[team_shots["shotResult"] == "Made"]

            # lightly shade the span of game time each player was on court
            for _, row in team_stint_pm.iterrows():
                ax.axvspan(
                    row["entry_minutes"], row["exit_minutes"],
                    color=player_color[row["displayName"]], alpha=0.12, zorder=0, linewidth=0,
                )

            # one curve per stint, tracing the team's actual score-margin shape
            # while the player was on court, rebased to start where their own
            # plus/minus line left off after their prior stint (a new stint
            # starts a new curve)
            margin_col = "home_margin" if team == margin_home_team else "away_margin"
            for _, row in team_stint_pm.iterrows():
                xs, ys = _stint_margin_curve(
                    margin_timeline, margin_col,
                    row["entry_minutes"], row["exit_minutes"],
                    row["entry_pm"], row["exit_pm"],
                )
                ax.plot(xs, ys, color="black", alpha=0.8, linewidth=3.2, zorder=1)

            colors = made["displayName"].map(player_color)
            ax.scatter(
                made["game_minutes"], made["plusMinus"],
                c=list(colors), s=35, alpha=0.75, marker="D", edgecolor="none", zorder=3,
            )

            # small circles marking the start and stop of every stint, for
            # every player — not just the ones who took shots
            ax.scatter(
                team_stint_pm["entry_minutes"], team_stint_pm["entry_pm"],
                color="black", s=18, marker="o", edgecolor="none", zorder=2,
            )
            ax.scatter(
                team_stint_pm["exit_minutes"], team_stint_pm["exit_pm"],
                color="black", s=18, marker="o", edgecolor="none", zorder=2,
            )

            ax.axhline(0, color="white", linewidth=0.6, alpha=0.3)
            ax.set_xlim(left=0)
            ax.set_ylim(y_limits)
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(tick_labels)
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_xlabel("Game time")
            ax.set_ylabel("Plus/minus")
            ax.set_title(f"{team} — Made shots ({len(made)})")
            ax.grid(True, color=(1, 1, 1, 0.15))

            handles = [
                plt.Line2D([0], [0], color=player_color[name], marker="D", linestyle="-", label=name)
                for name in players
            ]
            ax.legend(handles=handles, bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, frameon=False)

        game_id = shots["gameId"].iloc[0] if "gameId" in shots.columns else ""
        if game_info:
            subtitle = (
                f"{game_info['away_team']} @ {game_info['home_team']}  |  "
                f"{game_info['date']} at {game_info['time']}  |  {game_info['location']}  |  Game ID: {game_id}"
            )
            fig.suptitle(subtitle, fontsize=11, color="lightgray")
        else:
            fig.suptitle(f"Plus/minus chart — game {game_id}", fontsize=15)
        fig.tight_layout()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
    return output_path


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

    box_fontsize = 15 * 0.9 * 0.98 * 0.98 * (8 / 12) * ((0.86 - 0.10) / (0.98 - 0.06)) * 1.15 * 1.10
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
        team: _measure_text_height_inches(text, fontsize=box_fontsize, family="monospace")
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
    stint_segments = compute_lineup_stint_segments(csv_path, min_seconds=30.0)
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
                  "event_sum": 2.0}
    height_ratios = [
        (official_box_inches_by_team[r[1]] if r[0] == "box_score" else row_inches[r[0]])
        / inches_per_ratio_unit
        for r in row_labels
    ]

    body_inches = 3 * sum(height_ratios)
    total_inches = body_inches + header_inches
    top_fraction = body_inches / total_inches

    stint_hover_boxes = []  # precomputed {left,top,width,height,tooltip,center} per stint region
    title_tooltips = []  # (Text object, box-score line, pinned-line top) per player title

    with plt.style.context("dark_background"):
        fig = plt.figure(figsize=(8, total_inches))
        fig.set_dpi(150)  # match the dpi used at savefig time, so tooltip pixel math lines up
        fig_w_px = fig.get_size_inches()[0] * fig.dpi
        fig_h_px = fig.get_size_inches()[1] * fig.dpi
        gs = fig.add_gridspec(
            total_rows, ncols, height_ratios=height_ratios, hspace=hspace, wspace=0.3,
            top=top_fraction, bottom=0.03 * (body_inches / total_inches),
            left=_HEADER_LEFT_MARGIN, right=0.86,
        )

        # axes handles needed later for the slice-cut math
        summary_axes: dict[str, plt.Axes] = {}
        stint_axes: dict[str, plt.Axes] = {}
        # each team's base box-score text artist, for locating player rows
        box_text_artists: dict[str, plt.Text] = {}
        # each team's (body_top, text layers) for the per-32 redraw, and the
        # figure-fraction top of its box-score label line, where the
        # "show per 32" switch button sits
        box_layers_by_team: dict[str, tuple] = {}
        box_label_tops: dict[str, float] = {}
        box_label_artists: dict[str, plt.Text] = {}
        # per-team data for the box-score name hovers: rendered row order,
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
        # anchor for the box-score lines the karma band's stint hovers
        # reveal: just below the panel's x-axis (clearing the tick and
        # wall-clock labels), so the readout hangs under the Karma graph
        karma_label_top = (
            1 - event_ax.transAxes.transform((0, 0))[1] / fig_h_px
            + 32 * (fig.dpi / 72) / fig_h_px
        )

        for team in teams:
            players = team_players[team]
            n_players = len(players)
            cmap = _vivid_cmap(n_players)
            player_color = {name: cmap(i) for i, name in enumerate(players)}

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

            # a hovered lane segment shows that stint's own box-score row
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
                artist = fig.text(
                    _BOX_SCORE_LEFT_MARGIN, box_body_top, text, transform=fig.transFigure,
                    fontsize=box_fontsize, color=color, ha="left", va="top", family="monospace",
                )
                box_layer_artists.append(artist)
                if oi == 0:
                    box_text_artists[team] = artist
            box_layers_by_team[team] = (box_body_top, box_layer_artists)
            # overlay each player's name in the Player column in their chart
            # color (line 0 is the header; rendered rows are the MIN>0 players
            # in the same order `_format_official_box_score` prints them)
            rendered_names = boxes_by_team[team].loc[boxes_by_team[team]["MIN"] > 0, "displayName"]
            for i, box_name in enumerate(rendered_names):
                if box_name not in player_color:
                    continue
                fig.text(
                    _BOX_SCORE_LEFT_MARGIN, box_body_top,
                    "\n" * (i + 1) + _fit_name(box_name, _BOX_NAME_WIDTH),
                    transform=fig.transFigure, fontsize=box_fontsize,
                    color=player_color[box_name], ha="left", va="top", family="monospace",
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
                # anchor for the pinned box-score line the stint and title
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

        fig.text(0.5, 1.0, header_prose, transform=fig.transFigure, fontsize=_HEADER_FONTSIZE, color="lightgray", ha="center", va="top", family="monospace")
        table_y = 1.0 - prose_inches / total_inches
        fig.text(
            _HEADER_LEFT_MARGIN, table_y, header_table, transform=fig.transFigure,
            fontsize=_HEADER_FONTSIZE, color="lightgray", ha="left", va="top", family="monospace",
        )

        tooltip_boxes = list(stint_hover_boxes)

        # resolve each player title's on-canvas pixel bbox now (needs a draw
        # so text extents are known) into a hover target revealing that
        # player's full-game box-score line, pinned in the same place as the
        # stint hovers' lines (just above the plot title)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()

        # resolve each band hover's box-score row highlight into the row's
        # on-canvas rect: the box-score text block's extent divided evenly
        # over its lines (line 0 is the header, players follow in order)
        for b in stint_hover_boxes:
            hl = b.pop("_hl", None)
            if hl is None:
                continue
            hl_team, row_idx = hl
            bbox = box_text_artists[hl_team].get_window_extent(renderer=renderer)
            n_lines = official_box_text_by_team[hl_team].count("\n") + 1
            line_h = bbox.height / n_lines
            row_top_px = bbox.y1 - (row_idx + 1) * line_h
            b["row_hl"] = {
                "left": bbox.x0 / fig_w_px,
                "top": 1 - row_top_px / fig_h_px,
                "width": bbox.width / fig_w_px,
                "height": line_h / fig_h_px,
            }

        # hovering anywhere on a player's box-score row (name or data)
        # highlights the whole row and the player's stint segments in the
        # rotation band — one hover target per row, plus the highlight rects
        # it reveals (connected per player by a keyed :has() CSS rule)
        for team in teams:
            bbox = box_text_artists[team].get_window_extent(renderer=renderer)
            n_lines = official_box_text_by_team[team].count("\n") + 1
            line_h = bbox.height / n_lines
            for i, name in enumerate(box_names_by_team[team]):
                row = {
                    "left": bbox.x0 / fig_w_px,
                    "top": 1 - (bbox.y1 - (i + 1) * line_h) / fig_h_px,
                    "width": bbox.width / fig_w_px,
                    "height": line_h / fig_h_px,
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
        slices = []
        for i, team in enumerate(teams):
            if i == 0:
                # the first team's block opens with the Karma panel (it has
                # no team panel of its own): the always-visible header ends
                # one chart gap above the Karma title, and the team slice
                # picks up from there
                karma_top = (
                    1 - event_ax.get_tightbbox(renderer).y1 / fig_h_px
                    - std_blank_px / fig_h_px
                )
                slices.append({"top": 0.0, "bottom": karma_top})
                section_top = karma_top
            else:
                # start the team's slice exactly one standard chart gap
                # above its summary-panel title, so the wrapper opens with
                # the same blank between its toggle row and the team plot;
                # the blank remaining above that is cropped away
                content_top = 1 - summary_axes[team].get_tightbbox(renderer).y1 / fig_h_px
                section_top = content_top - std_blank_px / fig_h_px
            box_idx = row_labels.index(("box_score", team))
            player_rows = [j for j, r in enumerate(row_labels) if r[0] == "team" and r[1] == team]
            stint_idx = row_labels.index(("lineup_stints", team))
            players_top = _gap_mid_from_top(box_idx, player_rows[0])
            players_bottom = _gap_mid_from_top(player_rows[-1], stint_idx)
            stint_bottom_px = stint_axes[team].get_tightbbox(renderer).y0
            section_bottom = min(1 - (stint_bottom_px - std_blank_px) / fig_h_px, 1.0)
            # internal cut between the Karma panel and the box score, so
            # the HTML can stack them as two images in one chart-wrap: the
            # "hide stints" switch swaps only the Karma image, the per-32
            # switch only the box-score image
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
                 "box_right": box_text_artists[team].get_window_extent(renderer).x1 / fig_w_px},
                {"top": players_top, "bottom": players_bottom, "team": team, "toggle": "Players"},
                {"top": players_bottom, "bottom": section_bottom, "team": team, "toggle": "Lineups",
                 "lineup_box": True, "lineup_colors": lineup_colors_by_team.get(team, {}),
                 # right edge of the box-score columns, for right-aligning
                 # the "per 8" toggle button
                 "box_right": box_text_artists[team].get_window_extent(renderer).x1 / fig_w_px},
            ])
            section_top = section_bottom
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
                    fig.text(
                        _BOX_SCORE_LEFT_MARGIN, body_top, text, transform=fig.transFigure,
                        fontsize=box_fontsize, color=color, ha="left", va="top", family="monospace",
                    )

    return fig, tooltip_boxes, slices, redraw_rate_views, karma_layer_axes


def plot_plus_minus_by_player(csv_path: Path, output_path: Path, game_info: dict | None = None) -> Path:
    """Same made-shot, stint-line, and stint-circle data as `plot_plus_minus`,
    but small-multiples style: one subplot per player, grouped by team, instead
    of every player overlaid on one axes per team."""
    fig, _tooltip_boxes, _slices, _redraw, _karma_layers = _build_plus_minus_by_player_figure(csv_path, game_info)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output_path


def plot_plus_minus_by_player_html(
    csv_path: Path, output_path: Path, game_info: dict | None = None, tooltips: bool = False,
) -> Path:
    """Same chart as `plot_plus_minus_by_player`, saved as a static,
    non-interactive standalone HTML file — the figure rendered to a PNG and
    embedded directly in a minimal page (no JS/Plotly). A base64-embedded
    PNG is used instead of inline SVG because Chrome has a known rendering
    bug with very tall SVGs containing many clip-paths (as these figures do,
    one per subplot) — it leaves the top of the page blank until scrolled.

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
    reveals a box-score line pinned above the hovered plot's title, in the
    box-score (monospace) font — a player's title shows their full-game
    box-score row, a stint's shaded region shows that stint's own stats,
    and a lineup stint shows that stint's line above the lineup panel's
    title."""
    import base64
    import io

    from PIL import Image

    fig, tooltip_boxes, slices, redraw_rate_views, karma_layers = (
        _build_plus_minus_by_player_figure(csv_path, game_info, tooltips=tooltips)
    )

    def _render(transparent=False):
        buf = io.BytesIO()
        if transparent:
            fig.savefig(buf, format="png", dpi=150, transparent=True)
        else:
            fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor())
        return Image.open(io.BytesIO(buf.getvalue()))

    full_img = _render()
    img_w, img_h = full_img.size

    # second render with the lineup panels redrawn as per-8-minute rates and
    # the team box scores as per-32-minute rates — each rate switch swaps in
    # its own slice of this render
    redraw_rate_views()
    rate_img = _render()

    # the Karma panels' toggleable layers rendered separately (the rate
    # redraw above touched nothing in the Karma rows): an opaque base with
    # just the panel furniture (title, axes, grid), then a transparent
    # render per layer (stint lanes; cumulative scores and their axis; the
    # +/- line and its axis; the stacked bars with the corner team
    # labels). The HTML stacks the layers over the base, and each "hide"
    # switch simply hides its layer image — so toggles combine freely
    # without one baked image per combination.
    for a in (karma_layers["band"] + karma_layers["margin"]
              + karma_layers["bars"] + karma_layers["points"]
              + karma_layers["events"] + karma_layers["vevents"]
              + karma_layers["hevents"]):
        a.set_visible(False)
    karma_base_img = _render()
    for a in karma_layers["main"]:
        a.set_visible(False)
    for a in karma_layers["band"]:
        a.set_visible(True)
    lanes_layer_img = _render(transparent=True)
    for a in karma_layers["band"]:
        a.set_visible(False)
    for a in karma_layers["points"]:
        a.set_visible(True)
    scores_layer_img = _render(transparent=True)
    for a in karma_layers["points"]:
        a.set_visible(False)
    for a in karma_layers["margin"]:
        a.set_visible(True)
    pm_layer_img = _render(transparent=True)
    for a in karma_layers["margin"]:
        a.set_visible(False)
    for a in karma_layers["bars"]:
        a.set_visible(True)
    bars_layer_img = _render(transparent=True)
    for a in karma_layers["bars"]:
        a.set_visible(False)
    for a in karma_layers["events"]:
        a.set_visible(True)
    events_layer_img = _render(transparent=True)
    for a in karma_layers["events"]:
        a.set_visible(False)
    for a in karma_layers["vevents"]:
        a.set_visible(True)
    vevents_layer_img = _render(transparent=True)
    for a in karma_layers["vevents"]:
        a.set_visible(False)
    for a in karma_layers["hevents"]:
        a.set_visible(True)
    hevents_layer_img = _render(transparent=True)
    plt.close(fig)

    def _overlays_for_slice(s):
        """Overlay divs for the tooltips whose vertical center lands in this
        slice, with their top/height remapped from full-image fraction to
        this slice's local fraction (x is unchanged — slices are full width).
        Each hover target is an invisible .tt over its trigger region plus a
        sibling box-score line pinned above the panel/plot label, revealed
        by the .tt's hover."""
        if not tooltips:
            return ""
        span = s["bottom"] - s["top"]
        # lineup key -> hex, for the plane-highlight rects the box-score
        # row hovers reveal
        lu_hex_by_key = {
            _lu_key(s["team"], code): c
            for code, c in (s.get("lineup_colors") or {}).items()
        }
        parts = []
        for b in tooltip_boxes:
            center = b["top"] + b["height"] / 2
            if not (s["top"] <= center < s["bottom"]):
                continue
            local_top = (b["top"] - s["top"]) / span
            local_h = b["height"] / span
            if b.get("name_hover_key"):
                # box-score name cell: an invisible keyed target plus the
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
                # box-score header in the default gray, the player's own row
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
                sibling = (
                    f'<div class="tt-line" style="left:{b["label_left"] * 100:.3f}%;'
                    f'top:{label_top * 100:.3f}%;">{b["line_tooltip"]}</div>'
                )
            # lineup stints carry a data-lu key so :has() rules can highlight
            # their row in the lineup box score while hovered; the reverse
            # hover (box-score row -> planes) reveals a keyed highlight
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
            parts.append(
                f'<div class="{cls}"{attr} style="{var}left:{b["left"] * 100:.3f}%;top:{local_top * 100:.3f}%;'
                f'width:{b["width"] * 100:.3f}%;height:{local_h * 100:.3f}%;"></div>'
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

    def _slice_b64(img, s):
        crop = img.crop((0, round(s["top"] * img_h), img_w, round(s["bottom"] * img_h)))
        cbuf = io.BytesIO()
        crop.save(cbuf, format="png")
        return base64.b64encode(cbuf.getvalue()).decode("ascii")

    sections = []
    for s in slices:
        img_tag = f'<img src="data:image/png;base64,{_slice_b64(full_img, s)}" alt="Plus/minus by player">'
        if s.get("lineup_box"):
            # two renders of the lineup panel — per-game and per-8 diamonds/
            # y-axis — swapped by the same per 8 / per game switch as the
            # tables
            img_tag = (
                f'<img class="lu-img-raw" src="data:image/png;base64,{_slice_b64(full_img, s)}"'
                ' alt="Lineups">'
                f'<img class="lu-img-rate" src="data:image/png;base64,{_slice_b64(rate_img, s)}"'
                ' alt="Lineups, per 8 minutes">'
            )
        elif s.get("team_box"):
            # the Karma panel and box score as two stacked images (they
            # butt together seamlessly, so overlay math is unchanged): the
            # "hide stints" switch swaps the Karma image between the
            # lanes-on and lanes-off renders, and the per-32 switch swaps
            # the box-score image — independently
            ks = {"top": s["top"], "bottom": s["karma_cut"]}
            bs = {"top": s["karma_cut"], "bottom": s["bottom"]}
            img_tag = (
                f'<img class="kb-img-base" src="data:image/png;base64,{_slice_b64(karma_base_img, ks)}"'
                ' alt="Karma">'
                f'<img class="kb-ov kb-ov-lanes" src="data:image/png;base64,{_slice_b64(lanes_layer_img, ks)}"'
                ' alt="Karma stint lanes">'
                f'<img class="kb-ov kb-ov-scores" src="data:image/png;base64,{_slice_b64(scores_layer_img, ks)}"'
                ' alt="Karma cumulative scores">'
                f'<img class="kb-ov kb-ov-pm" src="data:image/png;base64,{_slice_b64(pm_layer_img, ks)}"'
                ' alt="Karma +/- line">'
                f'<img class="kb-ov kb-ov-bars" src="data:image/png;base64,{_slice_b64(bars_layer_img, ks)}"'
                ' alt="Karma event bars">'
                f'<img class="kb-ov kb-ov-events" src="data:image/png;base64,{_slice_b64(events_layer_img, ks)}"'
                ' alt="Karma per-player event markers (pEvents)">'
                f'<img class="kb-ov kb-ov-vevents" src="data:image/png;base64,{_slice_b64(vevents_layer_img, ks)}"'
                ' alt="Karma per-minute event columns (vEvents)">'
                f'<img class="kb-ov kb-ov-hevents" src="data:image/png;base64,{_slice_b64(hevents_layer_img, ks)}"'
                ' alt="Karma left-packed event rows (hEvents)">'
                f'<img class="tb-img-raw" src="data:image/png;base64,{_slice_b64(full_img, bs)}"'
                ' alt="Team box score">'
                f'<img class="tb-img-rate" src="data:image/png;base64,{_slice_b64(rate_img, bs)}"'
                ' alt="Team box score, per 32 minutes">'
            )
        # overlays are positioned in % of the IMAGE, so they live in their
        # own positioned box around just the images — the lineup slice's
        # chart-wrap also holds the flowing HTML box score below, which
        # must not stretch the overlay geometry
        inner = f'<div class="img-box">\n{img_tag}\n{_overlays_for_slice(s)}\n</div>'
        if s.get("team_box"):
            # the per 32 / per game switch, right-justified on the box-score
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
            # box-score line for a hovered stint plane or plot title, pinned
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
            ".tt-line{display:none;position:absolute;background:#222;color:lightgray;"
            "padding:2px 6px;border-radius:4px;font-family:DejaVu Sans Mono,monospace;"
            "font-weight:normal;font-size:1.54cqw;line-height:1.5;white-space:pre;z-index:3;"
            "pointer-events:none;transform:translateY(-100%);box-shadow:0 2px 6px rgba(0,0,0,0.5);}"
            ".tt:hover + .tt-line{display:block;}"
            # box-score line for a hovered stint segment in the team panel's
            # rotation band — same monospace styling as .tt-line, but below
            # the band's bottom-left corner (no translateY — it hangs below
            # its anchor); the player's row inside it carries their color
            ".tt-name{display:none;position:absolute;background:#222;color:lightgray;"
            "padding:2px 6px;border-radius:4px;font-family:DejaVu Sans Mono,monospace;"
            "font-weight:normal;font-size:1.54cqw;line-height:1.5;white-space:pre;z-index:3;"
            "pointer-events:none;box-shadow:0 2px 6px rgba(0,0,0,0.5);}"
            ".tt:hover + .tt-name{display:block;}"
            # translucent bar over the player's row in the team box score,
            # revealed together with its sibling .tt-name
            ".tt-hl{display:none;position:absolute;pointer-events:none;border-radius:2px;}"
            ".tt:hover + .tt-name + .tt-hl{display:block;}"
            # highlight rects revealed by hovering a player's box-score row
            # (the row itself + their band stints)
            ".bx-hl{display:none;position:absolute;pointer-events:none;border-radius:2px;}"
            # a hovered band stint segment lights itself up in the player's
            # color (set per element via --c)
            ".tt-seg:hover{background:var(--c);border-radius:2px;}"
        )
        # hovering a lineup's stint planes highlights that lineup's row in
        # the lineup box score — one :has() rule per lineup, tinted with the
        # lineup's own color — and hovering the row highlights the lineup's
        # planes in the plot (the .lu-hl rects emitted per plane). Both live
        # inside the same "lineups" <details>, which scopes the match.
        tooltip_css += (
            ".lu-hl{display:none;position:absolute;pointer-events:none;z-index:1;}"
        )
        tooltip_css += "".join(
            f'details:has(.tt[data-lu="{key}"]:hover) .lu-row-{key},'
            f".lu-row-{key}:hover"
            f"{{background:{color}40;border-radius:2px;}}"
            f'details:has(.lu-row-{key}:hover) .lu-hl-{key}{{display:block;}}'
            for s in slices if s.get("lineup_colors")
            for key, color in (
                (_lu_key(s["team"], code), c) for code, c in s["lineup_colors"].items()
            )
        )
        # one rule per player connecting their box-score name cell to their
        # highlight rects
        tooltip_css += "".join(
            f'.chart-wrap:has(.bx-name-{b["name_hover_key"]}:hover) '
            f'.bx-hl-{b["name_hover_key"]}{{display:block;}}'
            for b in tooltip_boxes if b.get("name_hover_key")
        )

    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        "<title>Plus/minus by player</title>"
        "<style>"
        "html,body{margin:0;padding:0;border:0;}"
        "img{display:block;vertical-align:top;width:100%;height:auto;}"
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
        "color:lightgray;font-size:1.54cqw;line-height:1.5;padding:0 0 18px 3.1%;}"
        # same style as the plot titles: the panel-title font size rendered
        # at 150dpi on the 1200px-wide figure is ~19.7px -> 1.64cqw
        ".lineup-box-title{color:lightgray;font-family:DejaVu Sans,sans-serif;font-size:1.64cqw;}"
        # per-column max highlight in the lineup box score
        ".mx-gold{color:goldenrod;}"
        ".mx-red{color:red;}"
        ".mx-grey{color:gray;}"
        # hover a lineup name in the box score to see its player names
        ".lu{position:relative;}"
        ".lu .lu-players{display:none;position:absolute;top:100%;left:0;margin-top:2px;"
        "background:#222;color:lightgray;padding:2px 8px;border-radius:4px;"
        "font-size:1.54cqw;white-space:nowrap;width:max-content;z-index:5;"
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
        "</style>"
        "</head>\n"
        "<body style=\"background:black;margin:0;\">\n"
        f"{body}\n"
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


def _wall_time_interpolator(game_id: str):
    """Return a function mapping game-clock minutes -> wall-clock POSIX
    timestamp (float seconds), built from every action's real timestamp in
    the NBA's live play-by-play feed. Used to find how much real time
    (stoppages included) actually elapsed during a given stretch of game
    clock. Returns None if that feed has no data for this game."""
    from nba_pbp.client import get_action_wall_times

    times_df = get_action_wall_times(game_id)
    if times_df is None:
        return None

    game_seconds = times_df.apply(lambda r: _game_seconds(int(r["period"]), r["clock"]), axis=1).to_numpy()
    wall_posix = times_df["wall_time"].apply(lambda dt: dt.timestamp()).to_numpy()
    order = np.argsort(game_seconds)
    game_seconds, wall_posix = game_seconds[order], wall_posix[order]

    def _interp(game_minutes: float) -> float:
        return float(np.interp(game_minutes * 60, game_seconds, wall_posix))

    return _interp


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
        # the box-score line is anchored at the top of the "Lineup stints"
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

            # hover readout: the box-score row in this lineup's color, and
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
        ax2.set_ylabel("Points", color="deepskyblue")
        ax2.tick_params(axis="y", colors="deepskyblue", labelsize=7)
        ax2.spines["top"].set_visible(False)

    return hover_boxes, color_by_lineup


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
    ax_p.set_ylabel("Score", color=score_color)
    ax_p.tick_params(axis="y", colors=score_color, labelsize=7)
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


def _draw_karma_hevent_markers(ax_hev, team, made_all, missed_all, missed_ft,
                               events, stint_pm, player_color, player_order):
    """The "hEvents" layer on a Karma panel's overlay axis: every player's
    events, good and bad mixed in game order, packed to the LEFT of their
    stint lane without overlap — so each lane reads as that player's
    event tally, longest row = most events."""
    stint_names = set(stint_pm["displayName"])
    order = [n for n in (player_order or []) if n in stint_names]
    order += sorted(stint_names - set(order))
    n = len(order)
    if not n:
        return
    lw_frac = min(1.0 / n * 0.7, 0.055)
    pitch = (1.0 - lw_frac) / (n - 1) if n > 1 else 0.0
    y_by_name = {
        name: 1 - lw_frac / 2 - i * pitch for i, name in enumerate(order)
    }

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
    stint_names = set(stint_pm["displayName"])
    order = [n for n in (player_order or []) if n in stint_names]
    order += sorted(stint_names - set(order))
    n = len(order)
    if not n:
        return
    lw_frac = min(1.0 / n * 0.7, 0.055)
    pitch = (1.0 - lw_frac) / (n - 1) if n > 1 else 0.0
    y_by_name = {
        name: 1 - lw_frac / 2 - i * pitch for i, name in enumerate(order)
    }
    pts = [
        (r["x"], y_by_name[r["name"]], r["kind"], r["name"], r["good"])
        for r in _karma_event_rows(team, made_all, missed_all, missed_ft, events)
        if r["name"] in y_by_name
    ]
    _scatter_karma_events(ax_ev, pts, player_color)


def _draw_karma_band_lanes(
    ax_band, team, stint_pm, player_color, player_order,
    fig_w_px, fig_h_px, label_top,
):
    """The first team's on-court stint lanes on the Karma panel's overlay
    axis (ylim 0..1), dim like the team panels' rotation band, spread over
    the full plot height with the first box-score row on top. Returns
    band-style hover boxes — each stint reveals its own box-score line and
    highlights itself."""
    boxes = []
    stint_names = set(stint_pm["displayName"])
    order = [n for n in (player_order or []) if n in stint_names]
    order += sorted(stint_names - set(order))
    n = len(order)
    if not n:
        return boxes
    lw_frac = min(1.0 / n * 0.7, 0.055)
    pitch = (1.0 - lw_frac) / (n - 1) if n > 1 else 0.0
    y_by_name = {
        name: 1 - lw_frac / 2 - i * pitch for i, name in enumerate(order)
    }
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


def _draw_team_panel(
    ax,
    team: str,
    home_team: str,
    margin_timeline: pd.DataFrame,
    made_all: pd.DataFrame,
    missed_all: pd.DataFrame,
    events: pd.DataFrame,
    tick_positions: list[float],
    tick_labels: list[str],
    y_limits: tuple[float, float],
    score_limits: tuple[float, float],
    show_title: bool = True,
    local_time_labels: list[str] | None = None,
    stint_pm: pd.DataFrame | None = None,
    player_color: dict | None = None,
    player_order: list[str] | None = None,
) -> None:
    """Draw the team-level +/- panel onto `ax`: the team's overall game
    plus/minus (score margin) traced continuously for the whole game, with
    every event by every player on that team — made/missed shots, rebounds,
    assists, blocks, steals, fouls, turnovers — plotted at the team's margin
    at that moment. Every marker is green except missed shots, free throws,
    and turnovers, which are red. A secondary axis traces the team's own
    cumulative score.

    If `stint_pm` (this team's rows from compute_stint_plus_minus) and
    `player_color` are given, each player's on-court stints are drawn as
    thin horizontal segments in that player's chart color — see the inline
    comment for the y placement rules. Returns one hover box (figure
    fractions) per drawn stint segment, revealing the player's name in
    their color below the band's bottom-left corner; empty if the band
    isn't drawn."""
    col = "home_margin" if team == home_team else "away_margin"
    score_col = "home_score" if team == home_team else "away_score"
    margin_sorted = margin_timeline.sort_values("game_minutes")

    def _with_team_margin(df_events: pd.DataFrame) -> pd.DataFrame:
        if df_events.empty:
            return df_events.assign(team_margin=[])
        merged = pd.merge_asof(
            df_events.sort_values("game_minutes"),
            margin_sorted[["game_minutes", col]],
            on="game_minutes",
            direction="backward",
        )
        merged["team_margin"] = merged[col]
        return merged

    team_made = _with_team_margin(made_all[made_all["teamTricode"] == team])
    team_missed = _with_team_margin(missed_all[missed_all["teamTricode"] == team])
    team_events = _with_team_margin(events[events["teamTricode"] == team]) if not events.empty else events

    # shotValue==1 only ever occurs for free throws (field goals are always
    # worth 2 or 3)
    event_markers = {"REB": "$R$", "AST": "$A$", "BLK": "$B$", "STL": "$S$"}
    shot_markers = {1: "$1$", 2: "$2$", 3: "$3$"}

    # the team's actual score-margin shape, continuous over the whole game —
    # drawn first, underneath every marker. Light gray (not black, like
    # the player-panel stint line) so it stands out against the dimmed
    # stint band behind it.
    ax.plot(
        margin_timeline["game_minutes"], margin_timeline[col],
        color="#8a8a8a", alpha=0.9, linewidth=3.2, zorder=1,
    )

    marker_rows = []
    for shot_value in shot_markers:
        subset = team_missed[team_missed["shotValue"] == shot_value]
        marker_rows.extend(
            {"x": r["game_minutes"], "y": r["team_margin"], "kind": f"missed{shot_value}"}
            for _, r in subset.iterrows()
        )
    for shot_value in shot_markers:
        subset = team_made[team_made["shotValue"] == shot_value]
        marker_rows.extend(
            {"x": r["game_minutes"], "y": r["team_margin"], "kind": f"shot{shot_value}"}
            for _, r in subset.iterrows()
        )
    if not team_events.empty:
        for event_type in list(event_markers) + ["FOUL", "TOV"]:
            subset = team_events[team_events["event_type"] == event_type]
            marker_rows.extend(
                {"x": r["game_minutes"], "y": r["team_margin"], "kind": event_type}
                for _, r in subset.iterrows()
            )
    marker_rows.sort(key=lambda r: r["x"])
    _declutter_marker_rows(marker_rows, tick_positions[-1] - tick_positions[0], y_limits[1] - y_limits[0])
    by_kind: dict[str, list[dict]] = {}
    for r in marker_rows:
        by_kind.setdefault(r["kind"], []).append(r)

    def _xy(kind: str) -> tuple[list[float], list[float]]:
        rs = by_kind.get(kind, [])
        return [r["x"] for r in rs], [r["y"] for r in rs]

    for shot_value, marker in shot_markers.items():
        mx, my = _xy(f"missed{shot_value}")
        ax.scatter(mx, my, color="red", s=32, alpha=0.85, marker=marker, linewidth=0.4, zorder=3)
    for shot_value, marker in shot_markers.items():
        sx, sy = _xy(f"shot{shot_value}")
        ax.scatter(sx, sy, color="green", s=32, alpha=0.85, marker=marker, linewidth=0.4, zorder=3)
    for event_type, marker in event_markers.items():
        ex, ey = _xy(event_type)
        ax.scatter(ex, ey, color="green", s=32, alpha=0.85, marker=marker, linewidth=0.4, zorder=3)
    fx, fy = _xy("FOUL")
    ax.scatter(fx, fy, color="red", s=32, alpha=0.85, marker="$F$", linewidth=0.4, zorder=3)
    tx, ty = _xy("TOV")
    ax.scatter(tx, ty, color="red", s=32, alpha=0.85, marker="$T$", linewidth=0.4, zorder=3)

    ax.axhline(0, color="white", linewidth=0.6, alpha=0.3)
    ax.set_xlim(left=0, right=tick_positions[-1])
    ax.set_ylim(y_limits)
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=8)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_ylabel("+/-", color="gray")
    if local_time_labels is not None:
        # the real local wall-clock time each period started, printed just
        # below its Q1/Q2/... tick label (offset in points so it clears the
        # tick text regardless of this panel's height)
        for xpos, label in zip(tick_positions, local_time_labels):
            ax.annotate(
                label, xy=(xpos, 0), xycoords=ax.get_xaxis_transform(),
                xytext=(0, -20), textcoords="offset points",
                ha="center", va="top", fontsize=7, color="dimgray", annotation_clip=False,
            )
    if show_title:
        ax.set_title(team, fontsize=_PANEL_TITLE_FONTSIZE, color=_PANEL_TITLE_COLOR, loc="left")
    ax.grid(True, color=(1, 1, 1, 0.15))
    ax.tick_params(axis="x", colors="gray")
    ax.tick_params(axis="y", labelsize=9, colors="gray")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("gray")
    ax.spines["bottom"].set_color("gray")
    ax.set_zorder(2)
    ax.patch.set_visible(False)

    # the team's own cumulative score, on a secondary axis so its
    # scale (0-100+) doesn't compress the plus/minus line
    ax2 = ax.twinx()
    ax2.set_zorder(1)
    ax2.plot(
        margin_timeline["game_minutes"], margin_timeline[score_col],
        color="deepskyblue", alpha=0.5, linewidth=1.6, zorder=1, linestyle="--",
    )
    ax2.set_ylim(score_limits)
    ax2.set_ylabel("Points", color="deepskyblue")
    ax2.tick_params(axis="y", colors="deepskyblue", labelsize=7)
    ax2.spines["top"].set_visible(False)

    # each player's on-court stints as horizontal segments (width: 5.5% of
    # the plot's height) in that player's chart color, on their own
    # undecorated overlay scale, drawn inside the plot area behind
    # everything else. Stacked in the box score's order (its top row is the
    # topmost line) and spread evenly so the stack fills the plot's full
    # height, top edge to bottom edge.
    hover_boxes = []
    if stint_pm is not None and not stint_pm.empty and player_color:
        ax3 = ax.twinx()
        ax3.set_zorder(0)  # under the +/- line, markers, and score line
        ax3.set_ylim(0, 1)
        stint_names = set(stint_pm["displayName"])
        order = [n for n in (player_order or []) if n in stint_names]
        order += sorted(stint_names - set(order))  # anyone missing from the box
        fig = ax.figure
        axes_h_inches = ax.get_position().height * fig.get_size_inches()[1]
        lw_frac = 0.055  # of the plot's height
        n = len(order)
        # spread evenly across the full plot height: the top line's upper
        # edge touches the plot top, the bottom line's lower edge the bottom
        pitch = (1 - lw_frac) / (n - 1) if n > 1 else 0
        y_by_name = {name: lw_frac / 2 + (n - 1 - i) * pitch for i, name in enumerate(order)}
        lw_points = lw_frac * axes_h_inches * 72

        # hover targets: one per stint segment, revealing that stint's
        # box-score line below the plot's bottom-left corner (clear of the
        # tick and wall-clock labels)
        fig_w_px = fig.get_size_inches()[0] * fig.dpi
        fig_h_px = fig.get_size_inches()[1] * fig.dpi
        name_top = 1 - (ax3.transData.transform((0, 0))[1] - 0.52 * fig.dpi) / fig_h_px
        name_left = _BOX_SCORE_LEFT_MARGIN  # columns align with the box score

        for _, s in stint_pm.iterrows():
            name = s["displayName"]
            y = y_by_name[name]
            color = player_color.get(name, "gray")
            # heavily dimmed — the band is background context; full color
            # lives in the hover readout and the box-score names
            ax3.plot(
                [s["entry_minutes"], s["exit_minutes"]], [y, y],
                color=color, alpha=0.18, linewidth=lw_points, solid_capstyle="butt",
            )
            x0_px, y_top_px = ax3.transData.transform((s["entry_minutes"], y + pitch / 2))
            x1_px, y_bot_px = ax3.transData.transform((s["exit_minutes"], y - pitch / 2))
            hover_boxes.append({
                "left": x0_px / fig_w_px,
                "top": 1 - y_top_px / fig_h_px,
                "width": (x1_px - x0_px) / fig_w_px,
                "height": (y_top_px - y_bot_px) / fig_h_px,
                "name_label": name,
                "stint_entry": s["entry_minutes"],
                "name_color": to_hex(color),
                "seg_color": f"{to_hex(color)}59",
                "label_left": name_left,
                "label_top": name_top,
            })
        ax3.set_yticks([])
        for spine in ax3.spines.values():
            spine.set_visible(False)
        ax3.patch.set_visible(False)
    return hover_boxes


def _build_team_events_figure(csv_path: Path, game_info: dict | None = None):
    """Build (but don't save/close) the team plus/minus figure: one subplot
    per team, the team's overall game plus/minus traced continuously, with
    every event by every player on that team plotted at the team's margin at
    that moment. Every marker is green except missed shots, free throws, and
    turnovers, which are red."""
    from nba_pbp.plusminus import (
        compute_event_plus_minus,
        compute_shot_plus_minus,
        compute_statline,
        compute_team_margin_timeline,
    )

    shots, final_pm = compute_shot_plus_minus(csv_path)
    if shots.empty:
        raise ValueError(f"No shot events found in {csv_path}")
    events = compute_event_plus_minus(csv_path)
    margin_timeline, home_team, away_team = compute_team_margin_timeline(csv_path)
    statline = compute_statline(csv_path)
    pid_to_display = shots.drop_duplicates("personId").set_index("personId")["displayName"].to_dict()
    final_pm_by_name = {pid_to_display.get(pid, str(pid)): value for pid, value in final_pm.items()}

    teams = sorted(shots["teamTricode"].dropna().unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 teams, found: {teams}")

    header_prose, header_table, _ = _build_header(
        csv_path, shots, statline, final_pm_by_name, teams, game_info, "Team plus/minus",
        include_box_score=False,
    )
    title_bar_text = f"{header_prose}\n{header_table}" if header_table else header_prose

    from nba_pbp.plusminus import compute_official_box_score

    official_team = "OKC" if "OKC" in teams else teams[0]
    other_team = next(t for t in teams if t != official_team)

    box1_df = compute_official_box_score(csv_path, team=official_team)
    box2_df = compute_official_box_score(csv_path, team=other_team)
    pts1, pts2 = box1_df["PTS"].sum(), box2_df["PTS"].sum()
    box1_text = _format_official_box_score(box1_df, official_team, team_margin=pts1 - pts2)
    box2_text = _format_official_box_score(box2_df, other_team, team_margin=pts2 - pts1)

    tick_positions, tick_labels = _quarter_ticks(int(shots["period"].max()))
    game_id = shots["gameId"].iloc[0] if "gameId" in shots.columns else None
    local_time_labels = _local_time_tick_labels(str(int(game_id)).zfill(10), tick_labels) if game_id else None
    made_all = shots[shots["shotResult"] == "Made"].copy()
    missed_all = shots[shots["shotResult"] == "Missed"].copy()

    y_min = margin_timeline[["home_margin", "away_margin"]].min().min()
    y_max = margin_timeline[["home_margin", "away_margin"]].max().max()
    y_limits = (y_min * 1.5, y_max * 1.5)

    score_max = margin_timeline[["home_score", "away_score"]].max().max()
    score_limits = (0, score_max * 1.05)

    # measure every text block so the figure can be sized to fit them exactly,
    # then lay everything out top-down: title bar, blank, team1 title, blank,
    # team1 box score, team1 chart, 2 blanks, team2 title, blank, team2 box
    # score, team2 chart
    box_fontsize = 15 * 0.9 * 0.98 * 0.98 * (8 / 12) * ((0.86 - 0.10) / (0.98 - 0.06)) * 1.15
    line_h = _measure_text_height_inches("Ag", fontsize=_HEADER_FONTSIZE, family="monospace")
    title_h = _measure_text_height_inches("Ag", fontsize=_PANEL_TITLE_FONTSIZE, family="DejaVu Sans")
    title_bar_h = _measure_text_height_inches(title_bar_text, fontsize=_HEADER_FONTSIZE, family="monospace")
    box1_h = _measure_text_height_inches(box1_text, fontsize=box_fontsize, family="monospace")
    box2_h = _measure_text_height_inches(box2_text, fontsize=box_fontsize, family="monospace")
    chart_h = 6.5
    top_margin = 0.25
    bottom_margin = 0.15
    right_margin = 0.86

    total_h = (
        top_margin + title_bar_h + line_h + title_h + line_h + box1_h + line_h + chart_h
        + 2 * line_h + title_h + line_h + box2_h + line_h + chart_h + bottom_margin
    )

    with plt.style.context("dark_background"):
        fig = plt.figure(figsize=(8, total_h))

        cursor = total_h - top_margin  # inches from the bottom; tracks the top of the next block

        def frac(inches_from_bottom: float) -> float:
            return inches_from_bottom / total_h

        fig.text(
            0.5, frac(cursor), title_bar_text, transform=fig.transFigure,
            fontsize=_HEADER_FONTSIZE, color="lightgray", ha="center", va="top", family="monospace",
        )
        cursor -= title_bar_h + line_h

        for team, box_text, box_df in (
            (official_team, box1_text, box1_df), (other_team, box2_text, box2_df)
        ):
            fig.text(
                _HEADER_LEFT_MARGIN, frac(cursor), team, transform=fig.transFigure,
                fontsize=_PANEL_TITLE_FONTSIZE, color=_PANEL_TITLE_COLOR, ha="left", va="top",
            )
            cursor -= title_h + line_h

            fig.text(
                _HEADER_LEFT_MARGIN, frac(cursor), box_text, transform=fig.transFigure,
                fontsize=box_fontsize, color="lightgray", ha="left", va="top", family="monospace",
            )
            gold_overlay, red_overlay, grey_overlay = _box_score_overlays(box_df, team)
            for overlay, color in (
                (gold_overlay, "goldenrod"), (red_overlay, "red"), (grey_overlay, "gray"),
            ):
                fig.text(
                    _HEADER_LEFT_MARGIN, frac(cursor), overlay, transform=fig.transFigure,
                    fontsize=box_fontsize, color=color, ha="left", va="top", family="monospace",
                )
            cursor -= (box1_h if team == official_team else box2_h) + line_h

            chart_top = cursor
            cursor -= chart_h
            ax = fig.add_axes([_HEADER_LEFT_MARGIN, frac(cursor), right_margin - _HEADER_LEFT_MARGIN, frac(chart_top) - frac(cursor)])
            _draw_team_panel(
                ax, team, home_team, margin_timeline, made_all, missed_all, events,
                tick_positions, tick_labels, y_limits, score_limits, show_title=False,
                local_time_labels=local_time_labels,
            )

            cursor -= 2 * line_h
    return fig


def plot_team_events(csv_path: Path, output_path: Path, game_info: dict | None = None) -> Path:
    """One subplot per team: the team's overall game plus/minus (score
    margin) traced continuously for the whole game, with every event by
    every player on that team — made/missed shots, rebounds, assists,
    blocks, steals, fouls, turnovers — plotted at the team's margin at that
    moment. Every marker is green except missed shots, free throws, and
    turnovers, which are red."""
    fig = _build_team_events_figure(csv_path, game_info)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return output_path


def plot_team_events_html(csv_path: Path, output_path: Path, game_info: dict | None = None) -> Path:
    """Same chart as `plot_team_events`, saved as a static, non-interactive
    standalone HTML file — the figure rendered to a PNG and embedded
    directly in a minimal page (no JS/Plotly). A base64-embedded PNG is used
    instead of inline SVG because Chrome has a known rendering bug with
    very tall SVGs containing many clip-paths (as these figures do) — it
    leaves the top of the page blank until scrolled."""
    import base64
    import io

    fig = _build_team_events_figure(csv_path, game_info)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    png_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    html = (
        "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
        "<title>Team plus/minus</title>"
        "<style>html,body{margin:0;padding:0;border:0;}img{display:block;vertical-align:top;max-width:100%;height:auto;}</style>"
        "</head>\n"
        "<body style=\"background:black;margin:0;display:flex;justify-content:center;\">\n"
        f"<img src=\"data:image/png;base64,{png_b64}\" alt=\"Team plus/minus\">\n</body></html>\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


def plot_time_height_grid(csv_path: Path, output_path: Path, game_info: dict | None = None) -> Path:
    """Flatten every shot (both teams) onto a 2D game-time x shot-distance grid,
    square markers colored by player."""
    shots = load_shots(csv_path)
    if shots.empty:
        raise ValueError(f"No shot events found in {csv_path}")

    players = sorted(shots["playerName"].unique())
    player_index = {name: i for i, name in enumerate(players)}
    n_players = len(players)
    cmap = plt.get_cmap("tab20" if n_players > 10 else "tab10", n_players)
    norm = plt.Normalize(vmin=-0.5, vmax=n_players - 0.5)

    tick_positions, tick_labels = _quarter_ticks(int(shots["period"].max()))

    with plt.style.context("dark_background"):
        fig, ax = plt.subplots(figsize=(14, 9))

        c = shots["playerName"].map(player_index)
        ax.scatter(shots["game_minutes"], shots["shotDistance"], c=c, cmap=cmap, norm=norm, marker="s", s=45)

        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels)
        ax.set_xlabel("Game time")
        ax.set_ylabel("Shot distance (ft)")
        ax.grid(True, color=(1, 1, 1, 0.15))

        handles = [
            plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=cmap(norm(i)), linestyle="", markersize=8, label=name)
            for name, i in player_index.items()
        ]
        ax.legend(handles=handles, bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, ncol=1)

        game_id = shots["gameId"].iloc[0] if "gameId" in shots.columns else ""
        title = f"Shot time/distance grid — game {game_id}"
        if game_info:
            title = f"{game_info['away_team']} @ {game_info['home_team']} — {game_info['date']}"
        ax.set_title(title)

        fig.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
    return output_path


def plot_stints(csv_path: Path, output_path: Path, game_info: dict | None = None) -> Path:
    """Gantt-chart style: one horizontal bar per on-court stint, player on the
    y-axis, game time on the x-axis. Reconstructed from substitution events —
    see `compute_stints` for the same data as a text/CSV report."""
    from nba_pbp.plusminus import compute_stints

    shots = load_shots(csv_path)
    stints = compute_stints(csv_path)
    if stints.empty:
        raise ValueError(f"No stints found in {csv_path}")

    teams = sorted(stints["teamTricode"].dropna().unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 teams, found: {teams}")

    tick_positions, tick_labels = _quarter_ticks(int(shots["period"].max()))

    with plt.style.context("dark_background"):
        fig, axes = plt.subplots(2, 1, figsize=(12, 13))

        for ax, team in zip(axes, teams):
            team_stints = stints[stints["teamTricode"] == team]
            totals = team_stints.groupby("displayName")["duration_minutes"].sum()
            players = totals.sort_values(ascending=False).index.tolist()
            player_y = {name: i for i, name in enumerate(players)}
            n_players = len(players)
            cmap = plt.get_cmap("tab10" if n_players <= 10 else "tab20", n_players)

            for name, y in player_y.items():
                player_stints = team_stints[team_stints["displayName"] == name]
                bars = list(zip(player_stints["entry_minutes"], player_stints["duration_minutes"]))
                ax.broken_barh(bars, (y - 0.4, 0.8), color=cmap(y), edgecolor="black", linewidth=0.5)

            ax.set_xlim(left=0)
            ax.set_ylim(-0.6, n_players - 0.4)
            ax.set_xticks(tick_positions)
            ax.set_xticklabels(tick_labels)
            ax.set_xlabel("Game time")
            ax.set_yticks(list(player_y.values()))
            ax.set_yticklabels(
                [f"{name}  ({totals[name]:.0f} min)" for name in players], fontsize=9
            )
            ax.invert_yaxis()
            ax.set_title(f"{team} — on-court stints")
            ax.grid(True, axis="x", color=(1, 1, 1, 0.15))

        game_id = shots["gameId"].iloc[0] if "gameId" in shots.columns else ""
        if game_info:
            subtitle = (
                f"{game_info['away_team']} @ {game_info['home_team']}  |  "
                f"{game_info['date']} at {game_info['time']}  |  {game_info['location']}  |  Game ID: {game_id}"
            )
            fig.suptitle(subtitle, fontsize=11, color="lightgray")
        else:
            fig.suptitle(f"Stint chart — game {game_id}", fontsize=15)
        fig.tight_layout()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
    return output_path
