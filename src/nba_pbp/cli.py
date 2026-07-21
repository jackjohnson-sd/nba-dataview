"""Command-line interface for collecting NBA play-by-play data."""
from __future__ import annotations

from pathlib import Path

import click
import pandas as pd

from nba_pbp import client, plotting, storage


@click.group()
def main():
    """Collect NBA play-by-play data from stats.nba.com."""


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


@main.command("season-events-2d-html")
@click.option("--season", default="2025-26", show_default=True)
@click.option("--team", default=None,
              help="Only this team's games and events (tricode, e.g. OKC).")
@click.option("--smooth", default=2, show_default=True,
              help="Centered rolling average over this many game days (1 = raw).")
@click.option("--output", "output_path", type=click.Path(path_type=Path),
              default=Path("outputs/season_events_2d.html"), show_default=True)
def season_events_2d_html_cmd(season: str, team: str | None, smooth: int, output_path: Path):
    """The season event plot FLAT: the same lanes as the 3D page stacked
    as horizontal strips over one shared date axis — same hover/click
    interactions, pure CSS, no JavaScript."""
    saved = plotting.plot_season_events_2d_html(season, output_path, smooth=smooth, team=team)
    click.echo(f"saved plot -> {saved}")


@main.command("nba-season-html")
@click.option("--season", default="2025-26", show_default=True)
@click.option("--output", "output_path", type=click.Path(path_type=Path),
              default=Path("outputs/nba_season.html"), show_default=True)
def nba_season_html_cmd(season: str, output_path: Path):
    """League-wide season page: the same lanes as a team's season page,
    but columns are the 30 teams and every value is that team's season
    per-game average (reads the cached box scores). Includes a
    season-average box table for all teams and columns."""
    from nba_pbp.nba_season import plot_nba_season_2d_html

    saved = plot_nba_season_2d_html(season, output_path)
    click.echo(f"saved plot -> {saved}")


@main.command("rebuild-test-games")
@click.option("--dir", "out_dir", type=click.Path(path_type=Path),
              default=Path("outputs"), show_default=True,
              help="Directory holding pbp_<id>.csv and the pm_players pages.")
def rebuild_test_games_cmd(out_dir: Path):
    """Rebuild the game pages for the fixed test set in
    `nba_pbp.test_games.TEST_GAMES` (say "refresh test games"). Games
    without a cached CSV are skipped, not fatal."""
    from nba_pbp.test_games import TEST_GAMES

    n = len(TEST_GAMES)
    for i, (gid, note) in enumerate(TEST_GAMES, 1):
        csv = out_dir / f"pbp_{gid}.csv"
        if not csv.exists():
            click.echo(f"[{i}/{n}] SKIP {gid} (no CSV) :: {note}", err=True)
            continue
        try:
            plotting.plot_plus_minus_by_player_html(
                csv, out_dir / f"pm_players_{gid}.html",
                game_info=_load_game_info(csv), tooltips=True)
            click.echo(f"[{i}/{n}] OK   {gid} :: {note}")
        except Exception as err:
            click.echo(f"[{i}/{n}] FAIL {gid} :: {err}", err=True)


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
