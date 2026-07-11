# Guide: the plus/minus players page

This is the reference for the interactive game page produced by
`nba-pbp plusminus-players-html` — what's on it, how to read each panel,
and every interaction. For the other commands (shot charts, 3D plots,
CSV reports), see the [README](README.md).

## Generating a page

```bash
# one-time setup
python3 -m venv .venv && source .venv/bin/activate && pip install -e .

# find the game id, fetch its play-by-play, render the page
nba-pbp games --date 2026-05-18
nba-pbp fetch --game-id 0042500311 --output outputs/sas_okc_g1.csv
nba-pbp plusminus-players-html --input outputs/sas_okc_g1.csv \
    --output outputs/sas_okc_g1_pm_players.html --tooltips
```

`--tooltips` enables all the hover interactions described below (pure
CSS — the page never runs JavaScript). Without it you get the same page
with no hovers.

The page is fully self-contained (charts embedded as base64 PNGs), so
you can open the file directly, or serve `outputs/` with the
`outputs-server` entry in `.claude/launch.json`.

Per-game NBA endpoint data (official box score, rotation data, recap,
wall-clock times) is cached in `~/.cache/nba_pbp/`, so re-rendering a
game after the first time is much faster and works offline.

## Page structure

Everything below the always-visible header is behind native
`<details>` toggles:

| Section | Default | Contents |
|---|---|---|
| Title block + linescore | always visible | matchup, date, arena, game id; points per period |
| `Summary` | closed | the AP game recap (via ESPN; omitted if none exists) |
| `OKC` / team name | **open** | the team +/- panel and team box score |
| `Players` | closed | one small plus/minus chart per player |
| `Lineups` | closed | the lineup stints plot and lineup box score |

Each team gets its own `team name` / `players` / `lineups` trio.
Open toggles read `Less` (the team toggle keeps the team name).

## The team panel

One panel per team, four layers:

- **Gray line** — the team's score margin (its +/-) over game time.
- **Letter markers** riding the margin line — every event by every
  player on the team, at the moment it happened: `1 2 3` made shots by
  value (a `1` is a made free throw), `R` rebound, `A` assist, `S`
  steal, `B` block. Green = good; **red** = missed shots, fouls (`F`),
  turnovers (`T`).
- **Dashed blue line** (right axis) — the team's cumulative score.
- **The rotation band** (dim color blocks) — each player's on-court
  stints as one horizontal lane, stacked in box-score order (top row of
  the box score = top lane), spread over the full plot height. Colors
  match the player charts and box-score names.

The x-axis is game time (`Q1…END`), with the actual local wall-clock
time each period started printed underneath.

## Box scores

The team box score (under the panel) is the NBA's official box score.
Player names are colored to match that player's charts. Stat cells are
highlighted per column:

- **goldenrod** — the column's best value: the max in most columns; the
  *min* in TO and PF, where fewer is better
- **red** — the column's worst value: the smallest non-zero in most
  columns; the *max* in TO and PF
- **gray dash** — a shot group (3P or FT) with zero attempts

The lineup box score uses the identical rules.

**`Show per 32` / `Show per game`** — the switch on the team box
score's label line converts it to per-32-minute rates: each player's
counting stats and +/- become `value / MIN × 32` (rounded; MIN becomes
a dash), the totals row becomes the team's rate per 32 minutes of game
time, and the highlighting is recomputed on the rates. The team plot
above is unaffected. As with any rate view, low-minute players produce
noisy numbers.

## Player charts (`Players` toggle)

One chart per player, ordered by minutes played, title in the player's
color. Within each chart:

- **Shaded spans** — the player's on-court stints (their color).
- **Black line** — the *team's* margin shape while they were on court,
  rebased to the player's own running plus/minus (flat while benched).
- **Black dots** — stint entry/exit, at the +/- they entered/left with.
- **Markers** — that player's own events, same letter code as the team
  panel; missed shots / fouls / turnovers in red.

All player charts share the same time axis; each chart's y-axis
auto-ranges to its own data, snapped to multiples of 5 with ticks every
5 — so compare y-values by reading the scale, not by eyeballing heights
across charts.

## Lineups (`Lineups` toggle)

The **lineup plot** shows every 5-man unit's stints (longer than 30
seconds) as translucent colored planes, one distinct color per lineup,
with a **diamond** at each stint's horizontal center marking the
stint's net +/-. The team's cumulative score rides the right axis.

The **lineup box score** below lists every lineup used for more than a
minute, one row per lineup, sorted by name. Lineup names are the first
two letters of each player's last name, alphabetized (`CaGiHoWiMi`),
colored to match the plot, with `(N)` = how many separate stints it
had. Hover a lineup name to see the full player names.

**`Show per 8` / `Show per game`** — the switch on the box score's
title line converts the view to per-8-minute rates: every counting stat
and +/- becomes `value / MIN × 8` (rounded; MIN becomes a dash since it
no longer means anything), *and the lineup plot swaps too* — the
diamonds and y-axis rescale to per-8 rates. Rates for very short
lineups are noisy by nature (a +3 minute goes to ±24 per 8).

## Hovers (with `--tooltips`)

Every readout is a box-score-formatted line pinned near the relevant
title, column-aligned with the box scores. The data row is always in
the entity's color.

| Hover target | Shows |
|---|---|
| a player chart's **title** | that player's full-game box-score row |
| a **stint span** in a player chart | that stint's own stats (they sum exactly to the full-game row) |
| a **lane segment** in the team panel's rotation band | that stint's stats, **plus** a highlight bar over the player's row in the team box score |
| a **lineup plane** in the lineup plot | the lineup's box-score line (in the lineup color) and its players (each in their color), plus a highlight on its row in the lineup box score |
| a **lineup name** in the lineup box score | the lineup's full player names |

## Data notes

- On-court stints come from the NBA's own `GameRotation` tracking when
  available, falling back to reconstructing them from substitution text
  in the play-by-play (which occasionally has gaps — see the docstrings
  in `src/nba_pbp/plusminus.py`).
- The team box score is the official `BoxScoreTraditionalV3`. Per-stint
  and lineup stats are reconstructed from play-by-play descriptions;
  offensive/defensive rebounds are inferred (a rebound by the team that
  just missed is offensive).
- The recap is the AP story from ESPN's public API, matched by game
  date and team names.

## Where things live in the code

- `src/nba_pbp/plusminus.py` — all computation: stints, plus/minus,
  per-stint stats, lineup segments and box scores.
- `src/nba_pbp/plotting.py` — figure building
  (`_build_plus_minus_by_player_figure`), panel drawing, the HTML
  assembly with slices, toggles, and hover overlays
  (`plot_plus_minus_by_player_html`).
- `src/nba_pbp/client.py` — NBA/ESPN endpoint wrappers with disk
  caching.
