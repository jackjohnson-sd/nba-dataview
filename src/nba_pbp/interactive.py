"""Interactive HTML shot chart: hover a player's legend entry to highlight their shots."""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from nba_pbp.plotting import _quarter_ticks, load_shots

_SYMBOLS = {"Made": "diamond", "Missed": "circle"}
_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]
_AXIS_STYLE = dict(backgroundcolor="rgb(30,30,30)", gridcolor="rgba(255,255,255,0.1)")


def plot_interactive(csv_path: Path, output_path: Path, game_info: dict | None = None) -> Path:
    shots = load_shots(csv_path)
    if shots.empty:
        raise ValueError(f"No shot events found in {csv_path}")

    teams = sorted(shots["teamTricode"].dropna().unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 teams, found: {teams}")

    tick_positions, tick_labels = _quarter_ticks(int(shots["period"].max()))

    subplot_titles = []
    for team in teams:
        team_shots = shots[shots["teamTricode"] == team]
        made_n = int((team_shots["shotResult"] == "Made").sum())
        missed_n = int((team_shots["shotResult"] == "Missed").sum())
        subplot_titles.append(f"{team} — Made ({made_n}) / Missed ({missed_n})")

    fig = make_subplots(
        rows=2, cols=1,
        specs=[[{"type": "scene"}], [{"type": "scene"}]],
        subplot_titles=subplot_titles,
        vertical_spacing=0.08,
    )

    for row, team in enumerate(teams, start=1):
        team_shots = shots[shots["teamTricode"] == team]
        players = sorted(team_shots["playerName"].unique())
        player_y = {name: i for i, name in enumerate(players)}

        for i, player in enumerate(players):
            player_shots = team_shots[team_shots["playerName"] == player]
            color = _PALETTE[i % len(_PALETTE)]
            sizes = player_shots["shotValue"].map({2: 6, 3: 9}).fillna(6)
            symbols = player_shots["shotResult"].map(_SYMBOLS)
            hover_text = player_shots["shotResult"] + " · " + player_shots["shotDistance"].astype(str) + " ft"

            fig.add_trace(
                go.Scatter3d(
                    x=player_shots["game_minutes"],
                    y=[player_y[player]] * len(player_shots),
                    z=player_shots["shotDistance"],
                    mode="markers",
                    marker=dict(
                        size=list(sizes), symbol=list(symbols), color=color, opacity=0.85,
                        line=dict(width=0.5, color="white"),
                    ),
                    name=player,
                    text=hover_text,
                    hovertemplate=f"<b>{player}</b><br>%{{text}}<extra></extra>",
                ),
                row=row, col=1,
            )

        scene_key = "scene" if row == 1 else "scene2"
        fig.update_layout(**{
            scene_key: dict(
                xaxis=dict(title="Game time", tickvals=tick_positions, ticktext=tick_labels, **_AXIS_STYLE),
                yaxis=dict(
                    title="Player", tickvals=list(player_y.values()), ticktext=list(player_y.keys()), **_AXIS_STYLE
                ),
                zaxis=dict(title="Shot distance (ft)", **_AXIS_STYLE),
            )
        })

    title = f"Shot chart — game {shots['gameId'].iloc[0]}"
    if game_info:
        title = f"{game_info['away_team']} @ {game_info['home_team']} — {game_info['date']}"

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=1400,
        showlegend=True,
        legend=dict(itemsizing="constant"),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs="cdn")
    _inject_legend_hover_script(output_path)
    return output_path


_EVENT_SYMBOLS = {"REB": "R", "AST": "A", "BLK": "B", "STL": "S"}
_FOUL_TOV_SYMBOLS = {"FOUL": "F", "TOV": "T"}


def plot_plus_minus_players_interactive(
    csv_path: Path, output_path: Path, game_info: dict | None = None
) -> Path:
    """Interactive HTML version of `plotting.plot_plus_minus_by_player`: one
    subplot per player (grouped by team), each showing their on-court
    plus/minus stints, made shots, and box score events. Hover any point for
    details."""
    from nba_pbp.plusminus import (
        compute_event_plus_minus,
        compute_shot_plus_minus,
        compute_statline,
        compute_stint_plus_minus,
    )

    shots, _ = compute_shot_plus_minus(csv_path)
    if shots.empty:
        raise ValueError(f"No shot events found in {csv_path}")
    stint_pm = compute_stint_plus_minus(csv_path)
    statline = compute_statline(csv_path).set_index(["teamTricode", "displayName"])
    events = compute_event_plus_minus(csv_path)

    teams = sorted(shots["teamTricode"].dropna().unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 teams, found: {teams}")

    tick_positions, tick_labels = _quarter_ticks(int(shots["period"].max()))
    made_all = shots[shots["shotResult"] == "Made"]

    pm_min = min(made_all["plusMinus"].min(), stint_pm["entry_pm"].min(), stint_pm["exit_pm"].min())
    pm_max = max(made_all["plusMinus"].max(), stint_pm["entry_pm"].max(), stint_pm["exit_pm"].max())
    pm_pad = (pm_max - pm_min) * 0.05
    y_range = [pm_min - pm_pad, pm_max + pm_pad]

    ncols = 2
    team_players = {}
    for team in teams:
        team_shots = made_all[made_all["teamTricode"] == team]
        team_stint_pm = stint_pm[stint_pm["teamTricode"] == team]
        all_players = set(team_shots["displayName"]) | set(team_stint_pm["displayName"])
        starters = set(team_stint_pm.loc[team_stint_pm["entry_minutes"] < 0.01, "displayName"])
        players = sorted(starters) + sorted(all_players - starters)
        team_players[team] = players

    # flat (team, player) cells in row-major order, padded to full rows per team
    cells: list[tuple[str, str] | None] = []
    for team in teams:
        players = team_players[team]
        rows_needed = -(-len(players) // ncols)
        for i in range(rows_needed * ncols):
            cells.append((team, players[i]) if i < len(players) else None)

    total_rows = len(cells) // ncols
    subplot_titles = []
    for cell in cells:
        if cell is None:
            subplot_titles.append("")
            continue
        team, name = cell
        if (team, name) in statline.index:
            line = statline.loc[(team, name)]
            subplot_titles.append(f"{team} {name} — {line['MIN']}, {line['PTS']}, {line['REB']}, {line['STOCKS']}")
        else:
            subplot_titles.append(f"{team} {name}")

    fig = make_subplots(
        rows=total_rows, cols=ncols, subplot_titles=subplot_titles,
        vertical_spacing=0.35 / total_rows, horizontal_spacing=0.08,
    )

    for idx, cell in enumerate(cells):
        if cell is None:
            continue
        row, col = idx // ncols + 1, idx % ncols + 1
        team, name = cell
        color = _PALETTE[team_players[team].index(name) % len(_PALETTE)]

        player_stint_pm = stint_pm[(stint_pm["teamTricode"] == team) & (stint_pm["displayName"] == name)]
        player_shots = made_all[(made_all["teamTricode"] == team) & (made_all["displayName"] == name)]
        player_events = events[(events["teamTricode"] == team) & (events["displayName"] == name)] if not events.empty else events

        for _, srow in player_stint_pm.iterrows():
            fig.add_vrect(
                x0=srow["entry_minutes"], x1=srow["exit_minutes"],
                fillcolor=color, opacity=0.15, line_width=0,
                row=row, col=col,
            )
            fig.add_trace(
                go.Scatter(
                    x=[srow["entry_minutes"], srow["exit_minutes"]],
                    y=[srow["entry_pm"], srow["exit_pm"]],
                    mode="lines+markers",
                    line=dict(color=color, width=1.5),
                    marker=dict(size=6, color=color),
                    showlegend=False,
                    hovertemplate=f"<b>{name}</b><br>%{{x:.1f}} min, %{{y}} +/-<extra></extra>",
                ),
                row=row, col=col,
            )

        if not player_shots.empty:
            hover_text = (
                player_shots["shotValue"].astype(int).astype(str) + "pt made at "
                + player_shots["game_minutes"].round(1).astype(str) + " min"
            )
            fig.add_trace(
                go.Scatter(
                    x=player_shots["game_minutes"], y=player_shots["plusMinus"],
                    mode="markers", marker=dict(symbol="diamond", size=7, color=color, opacity=0.85),
                    showlegend=False, text=hover_text,
                    hovertemplate=f"<b>{name}</b><br>%{{text}}<extra></extra>",
                ),
                row=row, col=col,
            )

        if not player_events.empty:
            for event_type, letter in {**_EVENT_SYMBOLS, **_FOUL_TOV_SYMBOLS}.items():
                subset = player_events[player_events["event_type"] == event_type]
                if subset.empty:
                    continue
                text_color = "red" if event_type in _FOUL_TOV_SYMBOLS else color
                fig.add_trace(
                    go.Scatter(
                        x=subset["game_minutes"], y=subset["plusMinus"],
                        mode="text", text=[letter] * len(subset),
                        textfont=dict(size=9, color=text_color),
                        showlegend=False,
                        hovertemplate=f"<b>{name}</b><br>{event_type}<extra></extra>",
                    ),
                    row=row, col=col,
                )

        fig.add_hline(y=0, line=dict(color="white", width=0.5), opacity=0.3, row=row, col=col)
        fig.update_xaxes(
            tickvals=tick_positions, ticktext=tick_labels, range=[0, max(tick_positions)],
            row=row, col=col,
        )
        fig.update_yaxes(range=y_range, row=row, col=col)

    title = f"Plus/minus by player — game {shots['gameId'].iloc[0]}"
    if game_info:
        title = (
            f"{game_info['away_team']} @ {game_info['home_team']}  |  "
            f"{game_info['date']} at {game_info['time']}  |  {game_info['location']}"
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=280 * total_rows,
        width=950,
        showlegend=False,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(output_path), include_plotlyjs="cdn")
    return output_path


def _inject_legend_hover_script(html_path: Path) -> None:
    """Hovering a legend entry brightens that player's shots and dims the rest."""
    script = """
<script>
document.addEventListener("DOMContentLoaded", function () {
    var gd = document.querySelector(".plotly-graph-div");
    if (!gd) return;
    gd.on("plotly_afterplot", function initOnce() {
        gd.removeListener("plotly_afterplot", initOnce);
        var original = gd.data.map(function (t) { return t.marker.opacity; });
        gd.on("plotly_legendhover", function (e) {
            var idx = e.curveNumber;
            var opacities = gd.data.map(function (_, i) { return i === idx ? 1.0 : 0.05; });
            Plotly.restyle(gd, { "marker.opacity": opacities });
        });
        gd.on("plotly_legendunhover", function () {
            Plotly.restyle(gd, { "marker.opacity": original });
        });
    });
});
</script>
"""
    html = html_path.read_text()
    html = html.replace("</body>", script + "</body>")
    html_path.write_text(html)
