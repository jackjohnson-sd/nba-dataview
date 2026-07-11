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

**Plot a shot chart from a play-by-play CSV:**

```bash
nba-pbp plot --input outputs/lal_okc.csv --output outputs/shot_chart.png
```

Renders a 2x1 dark-mode figure (one 3D subplot per team) with game time on
the x-axis, player on the y-axis, and shot distance on the z-axis. Made shots
are solid, missed shots are semi-transparent, 3-pointers are drawn slightly
larger, and each player gets a consistent color across dots and axis labels.
The title block (matchup, date/time, arena, game ID) is pulled automatically
from `BoxScoreSummaryV3` using the game ID embedded in the CSV.

**Plot every shot on a flat 2D game-time x shot-distance grid (both teams, square markers):**

```bash
nba-pbp grid --input outputs/lal_okc.csv --output outputs/shot_grid.png
```

**Plot the same 3D layout, but with on-court plus/minus instead of shot distance:**

```bash
nba-pbp plusminus --input outputs/lal_okc.csv --output outputs/plus_minus_chart.png
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
