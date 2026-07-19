"""Command-line interface for collecting NBA play-by-play data."""
from __future__ import annotations

from pathlib import Path

import click
import pandas as pd

from nba_pbp import client, interactive, plotting, storage


@click.group()
def main():
    """Collect NBA play-by-play data from stats.nba.com."""


@main.command("games")
@click.option("--date", required=True, help="Game date, e.g. 2024-01-15")
def games_cmd(date: str):
    """List games (and their game_id) scheduled on a given date."""
    games = client.get_games_for_date(date)
    if not games:
        click.echo(f"No games found for {date}")
        return
    for g in games:
        click.echo(
            f"{g['game_id']}  {g['away_team']:>3} @ {g['home_team']:<3}  {g['status']}"
        )


@main.command("team-games")
@click.option("--team", required=True, help="Team abbreviation, city, or nickname, e.g. LAL")
@click.option("--season", required=True, help="Season, e.g. 2023-24")
def team_games_cmd(team: str, season: str):
    """List all game_ids for a team in a given season."""
    games = client.get_games_for_team_season(team, season)
    if not games:
        click.echo(f"No games found for {team} in {season}")
        return
    for g in games:
        click.echo(f"{g['game_id']}  {g['date']}  {g['matchup']:<12} {g['win_loss'] or ''}")


@main.command("fetch")
@click.option("--game-id", "game_ids", multiple=True, help="One or more game IDs to fetch.")
@click.option("--date", help="Fetch play-by-play for every game on this date instead of --game-id.")
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    help="Output file (single --game-id) or directory (--date / multiple game IDs).",
    default=Path("outputs"),
)
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv")
def fetch_cmd(game_ids: tuple[str, ...], date: str | None, output_path: Path, fmt: str):
    """Fetch play-by-play data and save it to disk."""
    if not game_ids and not date:
        raise click.UsageError("Provide --game-id (one or more) or --date")

    ids_to_fetch = list(game_ids)
    if date:
        games = client.get_games_for_date(date)
        ids_to_fetch.extend(g["game_id"] for g in games)
        if not games:
            click.echo(f"No games found for {date}")
            return

    single_file_mode = len(ids_to_fetch) == 1 and output_path.suffix != ""

    for game_id in ids_to_fetch:
        click.echo(f"Fetching play-by-play for {game_id}...")
        try:
            df = client.get_play_by_play(game_id)
        except Exception as err:
            click.echo(f"  failed: {err}", err=True)
            continue

        if single_file_mode:
            target = output_path
        else:
            target = output_path / f"pbp_{game_id}.{fmt}"

        saved_path = storage.save_dataframe(df, target, fmt)
        click.echo(f"  saved {len(df)} events -> {saved_path}")


def _load_game_info(input_path: Path) -> dict | None:
    game_id = pd.read_csv(input_path, usecols=["gameId"], dtype=str).iloc[0, 0].zfill(10)
    try:
        return client.get_game_info(game_id)
    except Exception as err:
        click.echo(f"  could not fetch game info: {err}", err=True)
        return None


@main.command("plot")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/shot_chart_page.html"),
    help="Where to save the PNG.",
)
def plot_cmd(input_path: Path, output_path: Path):
    """Plot a 3D shot chart: game time x player x shot distance, made/missed colored."""
    game_info = _load_game_info(input_path)
    saved_path = plotting.plot_shots(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


@main.command("grid")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/shot_grid.html"),
    help="Where to save the PNG.",
)
def grid_cmd(input_path: Path, output_path: Path):
    """Plot every shot (both teams) on a 2D game-time x shot-distance grid, colored by player."""
    game_info = _load_game_info(input_path)
    saved_path = plotting.plot_time_height_grid(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


@main.command("plusminus")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/plus_minus_chart.html"),
    help="Where to save the PNG.",
)
def plusminus_cmd(input_path: Path, output_path: Path):
    """Plot each player's on-court plus/minus over game time (one 2D chart per
    team, players as colored lines/legend). Reconstructed from substitution
    events in the play-by-play feed — an approximation, not the official stat."""
    game_info = _load_game_info(input_path)
    saved_path = plotting.plot_plus_minus(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


@main.command("plusminus-players")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/plus_minus_by_player_chart.html"),
    help="Where to save the PNG.",
)
def plusminus_players_cmd(input_path: Path, output_path: Path):
    """Same plus/minus chart as `plusminus`, but one small subplot per player
    (grouped by team) instead of every player overlaid on one axes per team."""
    game_info = _load_game_info(input_path)
    saved_path = plotting.plot_plus_minus_by_player(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


@main.command("plusminus-players-html")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/plus_minus_by_player.html"),
    help="Where to save the HTML file.",
)
@click.option(
    "--tooltips/--no-tooltips",
    default=False,
    help="Hover targets (pure CSS, no JS): player titles, player stints, and "
         "lineup stints reveal box score lines. Off by default.",
)
def plusminus_players_html_cmd(input_path: Path, output_path: Path, tooltips: bool):
    """Same chart as `plusminus-players`, saved as a static, non-interactive
    standalone HTML file (SVG embedded directly, no JS/Plotly)."""
    game_info = _load_game_info(input_path)
    saved_path = plotting.plot_plus_minus_by_player_html(
        input_path, output_path, game_info=game_info, tooltips=tooltips,
    )
    click.echo(f"saved plot -> {saved_path}")


@main.command("plusminus-team")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/plus_minus_team_chart.html"),
    help="Where to save the PNG.",
)
def plusminus_team_cmd(input_path: Path, output_path: Path):
    """One chart per team: the team's overall game plus/minus traced
    continuously over the whole game, with every event by every player on
    that team plotted at the team's margin at that moment."""
    game_info = _load_game_info(input_path)
    saved_path = plotting.plot_team_events(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


@main.command("plusminus-team-html")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/plus_minus_team.html"),
    help="Where to save the HTML file.",
)
def plusminus_team_html_cmd(input_path: Path, output_path: Path):
    """Same chart as `plusminus-team`, saved as a static, non-interactive
    standalone HTML file (SVG embedded directly, no JS/Plotly)."""
    game_info = _load_game_info(input_path)
    saved_path = plotting.plot_team_events_html(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


@main.command("edge-report")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--at",
    "fraction",
    default=0.2,
    show_default=True,
    help="Game completion fraction for the live cutoff (0.2 = first 9.6 minutes).",
)
@click.option(
    "--games",
    "n_games",
    default=40,
    show_default=True,
    help="How many recent games feed each team's form ratings.",
)
@click.option(
    "--half-life",
    default=15.0,
    show_default=True,
    help="Recency half-life in games for the form weighting.",
)
def edge_report_cmd(input_path: Path, fraction: float, n_games: int, half_life: float):
    """Matchup edge report at a live cutoff: recency-weighted season form
    (net rating, pace, four factors) for both teams, the same factors
    read live from the play-by-play through the cutoff, the last
    head-to-head meetings, and where the live game diverges from the
    matchup expectation. Stage 1 of the win-probability project."""
    from nba_pbp.edge import edge_report

    click.echo(edge_report(input_path, fraction=fraction, n_games=n_games, half_life=half_life))


@main.command("winprob-build")
@click.option("--season", "seasons", multiple=True, required=True,
              help="Season(s) to harvest, e.g. 2025-26. Repeatable.")
@click.option("--at", "fraction", default=0.2, show_default=True,
              help="Game completion fraction for the live snapshot.")
@click.option("--games", "n_games", default=40, show_default=True)
@click.option("--half-life", default=15.0, show_default=True)
@click.option("--limit", default=None, type=int,
              help="Only the most recent N games per season (pipeline test).")
@click.option("--output", "output_path", type=click.Path(path_type=Path),
              default=Path("outputs/winprob_dataset.csv"), show_default=True)
def winprob_build_cmd(seasons, fraction, n_games, half_life, limit, output_path):
    """Build the win-probability training dataset: one row per historical
    game with pregame form + live-at-cutoff features and the final
    outcome. Play-by-play is disk-cached, so re-runs are resumable and
    only new games hit the network."""
    from nba_pbp.winprob import build_dataset

    df = build_dataset(list(seasons), fraction=fraction, n_games=n_games,
                       half_life=half_life, limit=limit, progress=click.echo)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    click.echo(f"saved {len(df)} games -> {output_path}")


@main.command("winprob-train")
@click.option("--dataset", "dataset_path", required=True,
              type=click.Path(exists=True, path_type=Path))
@click.option("--test-fraction", default=0.2, show_default=True,
              help="Chronological tail held out for testing.")
@click.option("--at", "fraction", default=0.2, show_default=True,
              help="Recorded in the model file (must match the build).")
@click.option("--games", "n_games", default=40, show_default=True)
@click.option("--half-life", default=15.0, show_default=True)
@click.option("--output", "model_path", type=click.Path(path_type=Path),
              default=Path("outputs/winprob_model.json"), show_default=True)
def winprob_train_cmd(dataset_path, test_fraction, fraction, n_games, half_life, model_path):
    """Fit and evaluate the win-probability models on a strictly
    time-ordered split, print the baseline comparison, and save the
    coefficients."""
    from nba_pbp.winprob import save_model, train

    df = pd.read_csv(dataset_path)
    result = train(df, test_fraction=test_fraction)
    click.echo(
        f"train {result['n_train']} games {result['train_span'][0]}..{result['train_span'][1]}  |  "
        f"test {result['n_test']} games {result['test_span'][0]}..{result['test_span'][1]}"
    )
    click.echo(f"{'set':16}{'log loss':>10}{'brier':>8}{'acc':>7}{'margin RMSE':>13}{'MAE':>7}")
    for name, m in result["sets"].items():
        click.echo(
            f"{name:16}{m['log_loss']:>10.4f}{m['brier']:>8.4f}{m['accuracy']:>7.3f}"
            f"{m['margin_rmse']:>13.2f}{m['margin_mae']:>7.2f}"
        )
    click.echo(f"selected: {result['selected']}")
    from nba_pbp.edge import _season_for_game_id
    seasons = sorted({_season_for_game_id(str(g).zfill(10)) for g in df["game_id"]})
    save_model(result, model_path, fraction, seasons, n_games, half_life)
    click.echo(f"saved model -> {model_path}")


@main.command("winprob")
@click.option("--input", "input_path", required=True,
              type=click.Path(exists=True, path_type=Path),
              help="Play-by-play CSV produced by `fetch`.")
@click.option("--model", "model_path", type=click.Path(exists=True, path_type=Path),
              default=Path("outputs/winprob_model.json"), show_default=True)
def winprob_cmd(input_path, model_path):
    """Home win probability and expected final margin for one game,
    evaluated at the model's snapshot fraction, with the baselines for
    context."""
    from nba_pbp.winprob import predict_live

    out = predict_live(input_path, model_path)
    click.echo(
        f"{out['away']} @ {out['home']} ({out['game_id']}), at {out['fraction']:.0%}: "
        f"live margin {out['features']['live_margin']:+.0f} ({out['home']}), "
        f"form edge {out['features']['net_diff']:+.1f}"
    )
    for name, p in out["sets"].items():
        mark = "  <- selected" if name == out["selected"] else ""
        click.echo(
            f"  {name:16}{out['home']} win prob {p['win_prob']:.1%}, "
            f"expected final margin {p['margin']:+.1f}{mark}"
        )


@main.command("statline")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Save as CSV instead of printing to the terminal.",
)
def statline_cmd(input_path: Path, output_path: Path | None):
    """Short statline per player: player, min, pts, reb, stocks (stocks =
    steals + blocks + assists). Parsed from the cumulative counts already
    embedded in play descriptions, plus minutes from `compute_stints`."""
    from nba_pbp.plusminus import compute_statline

    lines = compute_statline(input_path)
    if lines.empty:
        click.echo("No data found.")
        return

    if output_path:
        storage.save_dataframe(lines, output_path, "csv")
        click.echo(f"saved {len(lines)} statlines -> {output_path}")
        return

    for team in sorted(lines["teamTricode"].unique()):
        click.echo(team)
        team_lines = lines[lines["teamTricode"] == team]
        click.echo(f"  {'PLAYER':<20}{'MIN':>5}{'PTS':>5}{'REB':>5}{'STOCKS':>8}")
        for _, row in team_lines.iterrows():
            click.echo(
                f"  {row['displayName']:<20}{row['MIN']:>5}{row['PTS']:>5}{row['REB']:>5}{row['STOCKS']:>8}"
            )


@main.command("lineups")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Save as CSV instead of printing to the terminal.",
)
@click.option(
    "--min-minutes",
    default=1.0,
    show_default=True,
    help="Only include lineups used for more than this many minutes.",
)
@click.option(
    "--stints",
    is_flag=True,
    default=False,
    help="One row per individual lineup stint (not aggregated), rather than "
         "per lineup. Filtered by --min-seconds.",
)
@click.option(
    "--min-seconds",
    default=30.0,
    show_default=True,
    help="With --stints, only include stints longer than this many seconds.",
)
def lineups_cmd(
    input_path: Path, output_path: Path | None, min_minutes: float,
    stints: bool, min_seconds: float,
):
    """Box score by 5-man lineup, per team. By default one row per lineup used
    more than --min-minutes (its totals across all appearances); with
    --stints, one row per individual stint (contiguous stretch on the floor)
    longer than --min-seconds. Lineups are named by the first two letters of
    each player's last name (sorted). Columns: MIN, PTS, REB, AST, STL, BLK,
    TO, PF, +/- — the team's totals while that lineup was on the floor."""
    from nba_pbp.plusminus import compute_lineup_box_score, compute_lineup_stints

    if stints:
        box = compute_lineup_stints(input_path, min_seconds=min_seconds)
        label = f"stints (>{min_seconds:g} sec)"
    else:
        box = compute_lineup_box_score(input_path, min_minutes=min_minutes)
        label = f"lineups (>{min_minutes:g} min)"
    if box.empty:
        click.echo("No lineups found.")
        return

    if output_path:
        storage.save_dataframe(box, output_path, "csv")
        click.echo(f"saved {len(box)} rows -> {output_path}")
        return

    if stints:
        # full box score per stint, with "P MM:SS" start/end and MM:SS MIN
        stat_cols = [c for c in box.columns if c not in ("teamTricode", "lineup", "players")]
        def _w(c):
            return 10 if c in ("start", "end") else 7 if c == "MIN" else 5

        header = f"{'Lineup':<12}" + "".join(f"{c:>{_w(c)}}" for c in stat_cols)
        for team in sorted(box["teamTricode"].unique()):
            click.echo(f"{team} {label}")
            click.echo(header)
            for _, r in box[box["teamTricode"] == team].iterrows():
                cells = "".join(f"{str(r[c]):>{_w(c)}}" for c in stat_cols)
                click.echo(f"{r['lineup']:<12}{cells}")
            click.echo("")
    else:
        header = (
            f"{'Lineup':<12}{'MIN':>5}{'PTS':>5}{'REB':>5}{'AST':>5}"
            f"{'STL':>5}{'BLK':>5}{'TO':>4}{'PF':>4}{'+/-':>5}"
        )
        for team in sorted(box["teamTricode"].unique()):
            click.echo(f"{team} {label}")
            click.echo(header)
            for _, r in box[box["teamTricode"] == team].iterrows():
                pm = r["PLUS_MINUS"]
                pm_str = f"+{pm}" if pm > 0 else f"{pm}"
                click.echo(
                    f"{r['lineup']:<12}{r['MIN']:>5.1f}{r['PTS']:>5}{r['REB']:>5}{r['AST']:>5}"
                    f"{r['STL']:>5}{r['BLK']:>5}{r['TO']:>4}{r['PF']:>4}{pm_str:>5}"
                )
            click.echo("")


@main.command("subs")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Save as CSV instead of printing to the terminal.",
)
def subs_cmd(input_path: Path, output_path: Path | None):
    """List every substitution (player in / player out) in chronological order."""
    from nba_pbp.plusminus import extract_substitutions

    subs = extract_substitutions(input_path)
    if subs.empty:
        click.echo("No substitutions found.")
        return

    if output_path:
        storage.save_dataframe(subs, output_path, "csv")
        click.echo(f"saved {len(subs)} substitutions -> {output_path}")
        return

    for _, row in subs.iterrows():
        click.echo(
            f"{row['period']:>2}  {row['clock']:<12} {row['teamTricode']:<3}  "
            f"{row['player_in']:<16} IN  /  OUT {row['player_out']}"
        )


@main.command("stints")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Save as CSV instead of printing to the terminal.",
)
@click.option(
    "--clock-format",
    "clock_format",
    type=click.Choice(["elapsed", "countdown"]),
    default="elapsed",
    help="Terminal display only — CSV exports (--output) always use the broadcast "
    "countdown clock. 'elapsed' (default): time elapsed since the period started, "
    "e.g. 'Q1 07:42'. 'countdown': broadcast-style game clock, e.g. 'Q1 04:18'.",
)
def stints_cmd(input_path: Path, output_path: Path | None, clock_format: str):
    """List each player's on-court stints (entry/exit times), playing time per
    stint, and total playing time. Reconstructed from substitution events."""
    from nba_pbp.plusminus import compute_stints, format_broadcast_clock, format_duration

    stints = compute_stints(input_path)
    if stints.empty:
        click.echo("No stints found.")
        return

    clock_fn = format_broadcast_clock if clock_format == "countdown" else None
    if clock_fn:
        stints = stints.copy()
        stints["entry_clock"] = (stints["entry_minutes"] * 60).map(clock_fn)
        stints["exit_clock"] = (stints["exit_minutes"] * 60).map(clock_fn)

    if output_path:
        # CSV exports always use the broadcast countdown clock (12:00/5:00 -> 0:00),
        # regardless of --clock-format, since that's the convention people expect
        # in a saved stint file.
        stints = stints.copy()
        stints["entry_clock"] = (stints["entry_minutes"] * 60).map(format_broadcast_clock)
        stints["exit_clock"] = (stints["exit_minutes"] * 60).map(format_broadcast_clock)

        total_minutes = stints.groupby(["teamTricode", "displayName"])["duration_minutes"].transform("sum")
        stints = stints.assign(_total=total_minutes).sort_values(
            ["teamTricode", "_total", "displayName", "entry_minutes"], ascending=[True, False, True, True]
        )
        simple = stints[["teamTricode", "displayName", "entry_clock", "exit_clock"]].rename(
            columns={"teamTricode": "team", "displayName": "player", "entry_clock": "start_time", "exit_clock": "stop_time"}
        )
        simple["length_of_stint"] = stints["duration_minutes"].map(format_duration)
        simple["cum_playing_time"] = (
            stints.groupby(["teamTricode", "displayName"])["duration_minutes"].cumsum().map(format_duration)
        )
        simple["total_playtime"] = stints["_total"].map(format_duration)
        storage.save_dataframe(simple, output_path, "csv")
        click.echo(f"saved {len(simple)} stints -> {output_path}")
        return

    for team in sorted(stints["teamTricode"].unique()):
        click.echo(team)
        team_stints = stints[stints["teamTricode"] == team]
        players_by_minutes = (
            team_stints.groupby("displayName")["duration_minutes"].sum().sort_values(ascending=False)
        )
        for name in players_by_minutes.index:
            player_stints = team_stints[team_stints["displayName"] == name]
            click.echo(f"  {name}")
            for _, row in player_stints.iterrows():
                dur = format_duration(row["duration_minutes"])
                click.echo(f"    {row['entry_clock']} -> {row['exit_clock']}   ({dur})")
            total = format_duration(player_stints["duration_minutes"].sum())
            click.echo(f"    TOTAL: {total} across {len(player_stints)} stint(s)")
        team_total = format_duration(team_stints["duration_minutes"].sum())
        click.echo(f"  TEAM TOTAL: {team_total} across {len(team_stints)} stint(s)")


@main.command("player-stints")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Save as CSV instead of printing to the terminal.",
)
@click.option(
    "--min-seconds",
    default=0.0,
    show_default=True,
    help="Only include stints longer than this many seconds.",
)
def player_stints_cmd(input_path: Path, output_path: Path | None, min_seconds: float):
    """Box score per player stint: one row per contiguous on-court stretch
    with the player's own counting stats during it — the same numbers the
    stint hovers on the plus/minus page show (each player's stints sum to
    their official box score line). Columns lead with MIN/PTS/+/- like the
    page's box scores; start/end use the broadcast countdown clock."""
    from nba_pbp.plusminus import (
        compute_player_stint_stats,
        format_broadcast_clock,
        format_duration,
    )

    stats = compute_player_stint_stats(input_path)
    if stats.empty:
        click.echo("No stints found.")
        return
    stats = stats[stats["MIN"] * 60 > min_seconds]

    def pct(made, att):
        return [round(m / a * 100) if a else 0 for m, a in zip(made, att)]

    out = pd.DataFrame({
        "team": stats["teamTricode"],
        "player": stats["displayName"],
        "start": (stats["entry_minutes"] * 60).map(format_broadcast_clock),
        "end": (stats["exit_minutes"] * 60).map(format_broadcast_clock),
        "MIN": stats["MIN"].map(format_duration),
        "PTS": stats["PTS"],
        "+/-": stats["PLUS_MINUS"],
        "FGM": stats["FGM"], "FGA": stats["FGA"], "FG%": pct(stats["FGM"], stats["FGA"]),
        "3PM": stats["FG3M"], "3PA": stats["FG3A"], "3P%": pct(stats["FG3M"], stats["FG3A"]),
        "FTM": stats["FTM"], "FTA": stats["FTA"], "FT%": pct(stats["FTM"], stats["FTA"]),
        "OREB": stats["OREB"], "DREB": stats["DREB"], "REB": stats["REB"],
        "AST": stats["AST"], "STL": stats["STL"], "BLK": stats["BLK"],
        "TO": stats["TO"], "PF": stats["PF"],
    })

    if output_path:
        storage.save_dataframe(out, output_path, "csv")
        click.echo(f"saved {len(out)} stints -> {output_path}")
        return

    stat_cols = [c for c in out.columns if c not in ("team", "player")]

    def _w(c):
        return 9 if c in ("start", "end") else 6 if c == "MIN" else 5

    header = f"{'Player':<18}" + "".join(f"{c:>{_w(c)}}" for c in stat_cols)
    for team in sorted(out["team"].unique()):
        click.echo(team)
        click.echo(header)
        for _, r in out[out["team"] == team].iterrows():
            cells = "".join(f"{str(r[c]):>{_w(c)}}" for c in stat_cols)
            click.echo(f"{r['player']:<18}{cells}")
        click.echo("")


@main.command("stint-plot")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/stint_chart.html"),
    help="Where to save the PNG.",
)
def stint_plot_cmd(input_path: Path, output_path: Path):
    """Gantt-chart style plot of each player's on-court stints over game time."""
    game_info = _load_game_info(input_path)
    saved_path = plotting.plot_stints(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


@main.command("interactive")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/shot_chart.html"),
    help="Where to save the HTML file.",
)
def interactive_cmd(input_path: Path, output_path: Path):
    """Interactive HTML shot chart: hover a player's legend entry to highlight their shots."""
    game_info = _load_game_info(input_path)
    saved_path = interactive.plot_interactive(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


@main.command("plusminus-players-interactive")
@click.option(
    "--input",
    "input_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Play-by-play CSV produced by `fetch`.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("outputs/plus_minus_by_player.html"),
    help="Where to save the HTML file.",
)
def plusminus_players_interactive_cmd(input_path: Path, output_path: Path):
    """Interactive HTML version of `plusminus-players`: one subplot per player, hover any point for details."""
    game_info = _load_game_info(input_path)
    saved_path = interactive.plot_plus_minus_players_interactive(input_path, output_path, game_info=game_info)
    click.echo(f"saved plot -> {saved_path}")


if __name__ == "__main__":
    main()


@main.command("season-events-3d")
@click.option("--season", default="2025-26", show_default=True)
@click.option("--team", default=None,
              help="Only this team's games and events (tricode, e.g. OKC).")
@click.option("--smooth", default=2, show_default=True,
              help="Centered rolling average over this many game days (1 = raw).")
@click.option("--output", "output_path", type=click.Path(path_type=Path),
              default=Path("outputs/season_events_3d_chart.html"), show_default=True)
def season_events_3d_cmd(season: str, team: str | None, smooth: int, output_path: Path):
    """Static 3D ridge plot of the whole season: every +/- event kind's
    count per game (both teams combined), one ridge per kind across the
    season's games. Reads play-by-play from the disk cache (run
    winprob-build for the season first to populate it)."""
    saved = plotting.plot_season_events_3d(season, output_path, smooth=smooth, team=team)
    click.echo(f"saved plot -> {saved}")


@main.command("season-events-3d-html")
@click.option("--season", default="2025-26", show_default=True)
@click.option("--team", default=None,
              help="Only this team's games and events (tricode, e.g. OKC).")
@click.option("--smooth", default=2, show_default=True,
              help="Centered rolling average over this many game days (1 = raw).")
@click.option("--output", "output_path", type=click.Path(path_type=Path),
              default=Path("outputs/season_events_3d.html"), show_default=True)
def season_events_3d_html_cmd(season: str, team: str | None, smooth: int, output_path: Path):
    """Same plot as season-events-3d, saved as a standalone HTML page
    where hovering an event kind's axis label highlights its ridge
    (pure CSS, no JavaScript)."""
    saved = plotting.plot_season_events_3d_html(season, output_path, smooth=smooth, team=team)
    click.echo(f"saved plot -> {saved}")


def _resolve_team(t: str) -> str:
    """Resolve a tricode / city / nickname / full name to a tricode."""
    from nba_api.stats.static import teams as _teams

    t = t.strip()
    if _teams.find_team_by_abbreviation(t.upper()):
        return t.upper()
    for finder in (_teams.find_teams_by_full_name,
                   _teams.find_teams_by_nickname,
                   _teams.find_teams_by_city):
        res = finder(t)
        if res:
            return res[0]["abbreviation"]
    return t.upper()


def _seasons_for_range(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    """Every NBA season string (YYYY-YY) the date range touches. A season
    runs Oct->June, so a date's season year is its calendar year in
    Aug-Dec, else the previous year."""
    def season_year(ts: pd.Timestamp) -> int:
        return ts.year if ts.month >= 8 else ts.year - 1

    return [f"{y}-{str(y + 1)[2:]}"
            for y in range(season_year(start), season_year(end) + 1)]


@main.command("fetch-games")
@click.option("--start", required=True, help="Start date, inclusive (e.g. 2026-01-01).")
@click.option("--end", required=True, help="End date, inclusive (e.g. 2026-01-31).")
@click.option("--team", "teams", multiple=True, required=True,
              help="Team tricode / city / nickname; repeat for several teams.")
@click.option("--season", default=None,
              help="Season YYYY-YY. Derived from the dates when omitted.")
@click.option("--output", "output_path", type=click.Path(path_type=Path),
              default=Path("outputs"), show_default=True,
              help="Directory for the pbp_<game_id>.<fmt> files.")
@click.option("--format", "fmt", type=click.Choice(["csv", "json"]), default="csv")
@click.option("--no-box-scores", is_flag=True,
              help="Skip pre-fetching the traditional box scores.")
@click.option("--render", is_flag=True,
              help="Also build the plusminus-players-html game page per game "
                   "(with hover tooltips/highlighting enabled).")
@click.option("--delay", default=0.6, show_default=True,
              help="Seconds between network fetches (politeness).")
def fetch_games_cmd(start, end, teams, season, output_path, fmt,
                    no_box_scores, render, delay):
    """Fetch every game the listed teams played between --start and --end
    (inclusive) and make the files the team and player apps consume: one
    play-by-play file per game, plus (unless --no-box-scores) the cached
    box score. A game where two listed teams meet is fetched once. With
    --render, also generate the plusminus-players-html page per game.

    Example:
      nba-pbp fetch-games --start 2026-01-01 --end 2026-01-31 --team OKC --team SAS
    """
    import time
    from nba_pbp.edge import league_history

    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    if end_ts < start_ts:
        raise click.UsageError("--end is before --start")
    want = {_resolve_team(t) for t in teams}
    seasons = [season] if season else _seasons_for_range(start_ts, end_ts)

    games: dict[str, pd.Series] = {}
    for s in seasons:
        try:
            hist = league_history(s)
        except Exception as err:
            click.echo(f"  season {s}: {err}", err=True)
            continue
        sel = hist[hist["TEAM_ABBREVIATION"].isin(want)
                   & (hist["GAME_DATE"] >= start_ts)
                   & (hist["GAME_DATE"] <= end_ts)]
        for _, g in sel.iterrows():
            games.setdefault(str(g["GAME_ID"]), g)

    if not games:
        click.echo(f"No games for {', '.join(sorted(want))} in "
                   f"{start_ts.date()}..{end_ts.date()}")
        return

    output_path.mkdir(parents=True, exist_ok=True)
    ordered = sorted(games.items(), key=lambda kv: kv[1]["GAME_DATE"])
    click.echo(f"{len(ordered)} games for {', '.join(sorted(want))} "
               f"({start_ts.date()}..{end_ts.date()})")
    for gid, g in ordered:
        was_cached = client.has_cached_play_by_play(gid)
        try:
            df = client.get_play_by_play_cached(gid)
        except Exception as err:
            click.echo(f"  {gid} play-by-play failed: {err}", err=True)
            continue
        target = storage.save_dataframe(df, output_path / f"pbp_{gid}.{fmt}", fmt)
        note = ""
        if not no_box_scores:
            try:
                client.get_box_score_traditional(gid)
            except Exception as err:
                note += f"  (box score failed: {err})"
        if render:
            try:
                plotting.plot_plus_minus_by_player_html(
                    Path(target), output_path / f"pm_players_{gid}.html",
                    game_info=client.get_game_info(gid), tooltips=True,
                )
                note += f"  + pm_players_{gid}.html"
            except Exception as err:
                note += f"  (render failed: {err})"
        click.echo(f"  {g['GAME_DATE'].date()}  {g['MATCHUP']}  -> {Path(target).name}{note}")
        if not was_cached and delay:
            time.sleep(delay)


@main.command("flush-cache")
@click.option("--all", "flush_all", is_flag=True, help="Delete the entire cache.")
@click.option("--pbp", is_flag=True, help="Delete cached play-by-play.")
@click.option("--box-scores", is_flag=True, help="Delete cached box scores.")
@click.option("--league-logs", is_flag=True,
              help="Delete cached season game logs (refresh a season in progress).")
@click.option("--game-id", "game_ids", multiple=True,
              help="Delete every cached file for these game IDs; repeatable.")
@click.option("--yes", is_flag=True, help="Skip the confirmation prompt.")
def flush_cache_cmd(flush_all, pbp, box_scores, league_logs, game_ids, yes):
    """Delete cached NBA data so it re-fetches next time (outputs/ is not
    touched). With no flags, just report the cache size."""
    cache = client.CACHE_DIR
    if not cache.exists():
        click.echo(f"No cache at {cache}")
        return

    all_files = sorted(cache.glob("*.pkl"))
    if not any([flush_all, pbp, box_scores, league_logs, game_ids]):
        total = sum(f.stat().st_size for f in all_files)
        click.echo(f"{len(all_files)} files, {total / 1e6:.1f} MB at {cache}")
        click.echo("Flush with --all, --pbp, --box-scores, --league-logs, "
                   "or --game-id <id>.")
        return

    targets: set[Path] = set()
    if flush_all:
        targets.update(all_files)
    if pbp:
        targets.update(cache.glob("pbp_*.pkl"))
    if box_scores:
        targets.update(cache.glob("box_score_traditional_*.pkl"))
    if league_logs:
        targets.update(cache.glob("league_games_*.pkl"))
    for gid in game_ids:
        targets.update(cache.glob(f"*{gid}*.pkl"))

    targets = sorted(targets)
    if not targets:
        click.echo("Nothing matched.")
        return
    size = sum(f.stat().st_size for f in targets)
    click.echo(f"Deleting {len(targets)} files ({size / 1e6:.1f} MB) from {cache}")
    if not yes and not click.confirm("Proceed?"):
        click.echo("Aborted.")
        return
    for f in targets:
        f.unlink()
    click.echo(f"Deleted {len(targets)} files.")
