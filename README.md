# nba-pbp

Command-line tool that collects NBA play-by-play data from stats.nba.com via
[nba_api](https://github.com/swar/nba_api) (PlayByPlayV3) and saves it as CSV
or JSON. Also renders a 3D shot chart (game time x player x shot distance)
from the fetched data.

The flagship output is the interactive plus/minus game page
(`plusminus-players-html`) — see [GUIDE.md](GUIDE.md) for how to generate
and read it.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Or use the setup script (does the same thing):

```bash
scripts/setup.sh
```

## Usage

**Find game IDs for a date:**

```bash
nba-pbp games --date 2024-01-15
```

**Find game IDs for a team's season (regular season and playoffs):**

```bash
nba-pbp team-games --team LAL --season 2023-24
```

**Fetch play-by-play for one game:**

```bash
nba-pbp fetch --game-id 0022300565 --output outputs/lal_okc.csv
```

**Fetch play-by-play for every game on a date (one CSV per game):**

```bash
nba-pbp fetch --date 2024-01-15 --output outputs/2024-01-15
```

Use `--format json` for JSON output instead of CSV. Game IDs come from
`nba-pbp games` or `nba-pbp team-games`. Season strings use the `YYYY-YY`
format (e.g. `2023-24`).

**Fetch a date range for a list of teams (one file per game, for the team/player apps):**

```bash
nba-pbp fetch-games --start 2026-01-01 --end 2026-01-31 --team OKC --team SAS
```

Finds every game the listed teams played on or after `--start` and on or
before `--end` (a game where two listed teams meet is fetched once), saves a
`pbp_<game_id>.csv` per game, and warms the traditional box-score cache — the
data the team and player apps (e.g. `plusminus-players-html`) read. `--team`
accepts a tricode, city, or nickname and repeats for several teams; the season
is derived from the dates (override with `--season`). Add `--render` to also
build the `plusminus-players-html` page per game, `--no-box-scores` to skip the
box-score fetch, or `--format json`.

**Matchup edge report at a live cutoff (Stage 1 of the win-probability project):**

```bash
nba-pbp edge-report --input outputs/lal_okc.csv --at 0.2
```

Recency-weighted season form for both teams (net/off/def rating, pace, and
the four factors on both ends, from each team's last `--games` box scores
with a `--half-life` games decay), the same factors read live from the
play-by-play through the `--at` completion fraction, the last head-to-head
meetings, and the biggest divergences between the live game and the
matchup expectation. League game logs are fetched once per season and
cached; run `nba-pbp flush-cache --league-logs` to refresh a season in
progress.

**Manage the disk cache (`~/.cache/nba_pbp`):**

```bash
nba-pbp flush-cache                       # report cache size, delete nothing
nba-pbp flush-cache --league-logs         # refresh season game logs
nba-pbp flush-cache --pbp --box-scores    # by type
nba-pbp flush-cache --game-id 0022500581  # everything for one game
nba-pbp flush-cache --all --yes           # wipe it (skip the prompt)
```

Anything deleted re-fetches automatically the next time it's needed;
`outputs/` is never touched. Every flush (except `--all --yes`) asks to
confirm and shows how much it will delete first.

**Win-probability model (Stage 2):**

```bash
# harvest one row per historical game: pregame form + live features at
# the 20% mark + final outcome (play-by-play is disk-cached; resumable)
nba-pbp winprob-build --season 2025-26 --output outputs/winprob_2025-26.csv

# fit + evaluate on a strictly time-ordered split, save the coefficients
nba-pbp winprob-train --dataset outputs/winprob_2025-26.csv

# win probability for one game at the model's snapshot fraction
nba-pbp winprob --input outputs/sas_okc_g1.csv
```

Three nested feature sets are always compared: pregame net-rating
difference only; plus the live score margin; plus the live four-factor
differentials. The saved model keeps all three, marks the best test
log-loss as selected, and `winprob` prints them side by side.

**Season 3D event chart (one lane per box-score stat, by calendar day):**

```bash
# interactive pure-HTML/CSS page (no JavaScript, no images)
nba-pbp season-events-3d-html --season 2025-26 --team OKC --smooth 7 \
    --output outputs/season_events_3d_okc.html

# static matplotlib render of the same data (an HTML page with the
# chart embedded as SVG — no raster output)
nba-pbp season-events-3d --season 2025-26 --team OKC --smooth 7 \
    --output outputs/season_events_3d_okc_chart.html
```

Each lane is a stat from the traditional box-score line (2PM through FL,
plus derived attempts/percentages, home/away, back-to-back fatigue, and
+/-), averaged per game day with an optional rolling average (`--smooth`)
and scaled to its own non-zero-based axis. In the HTML page, hover or
click a stat label to spotlight its lane (arrow keys step through lanes
after a click), and hover the HOM lane to see that date's official team
box score — click to pin it, and step games with the corner arrows.
Play-by-play and box scores come from the same disk cache the other
commands use, so a full season renders offline once fetched.

**Plot a shot chart from a play-by-play CSV:**

```bash
nba-pbp plot --input outputs/lal_okc.csv --output outputs/shot_chart_page.html
```

Saves a dark-mode HTML page with the figure embedded as SVG (every chart
command emits HTML — the package produces no raster files): one 3D subplot
per team, with game time on
the x-axis, player on the y-axis, and shot distance on the z-axis. Made shots
are solid, missed shots are semi-transparent, 3-pointers are drawn slightly
larger, and each player gets a consistent color across dots and axis labels.
The title block (matchup, date/time, arena, game ID) is pulled automatically
from `BoxScoreSummaryV3` using the game ID embedded in the CSV.

**Plot every shot on a flat 2D game-time x shot-distance grid (both teams, square markers):**

```bash
nba-pbp grid --input outputs/lal_okc.csv --output outputs/shot_grid.html
```

**Plot the same 3D layout, but with on-court plus/minus instead of shot distance:**

```bash
nba-pbp plusminus --input outputs/lal_okc.csv --output outputs/plus_minus_chart.html
```

The z-axis becomes each shooter's cumulative on-court point differential at
the moment of the shot (reconstructed from substitution events, starting
lineups, and the running score), instead of shot distance — so the plane at
z=0 is "breakeven" rather than the free-throw line. This is an approximation:
the NBA's public play-by-play feed occasionally has gaps or inconsistencies
in its substitution log (a player's entrance missing entirely, or logged as
entering while already tracked on court), so values can be off by a few
points from the official box score `+/-` for some players.

**Interactive HTML shot chart:**

```bash
nba-pbp interactive --input outputs/lal_okc.csv --output outputs/shot_chart.html
```

Same layout as `plot`, but rendered with Plotly so you can rotate/zoom in the
browser. Hover over a player's name in the legend to brighten their shots and
dim everyone else's.

### scripts/shot_chart.sh

Fetches play-by-play for a game and renders its shot chart in one step:

```bash
scripts/shot_chart.sh 0042500311
```

Optional second argument sets the output directory (defaults to `outputs/`).

## Data

Each row is one play-by-play event: clock, period, team, player, action type
(shot, rebound, foul, turnover, etc.), running score, and description. Columns
come straight from the NBA's PlayByPlayV3 endpoint.
