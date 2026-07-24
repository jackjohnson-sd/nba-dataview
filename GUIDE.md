# Guide: the interactive pages

This is the reference for the three interactive page types — what's on
each, how to read the panels, and every interaction. All three are pure
HTML/CSS: no JavaScript, no images beyond embedded SVG.

| Page | Command | Output | Scope |
|---|---|---|---|
| **Game page** | `plusminus-players-html` | `pm_players_<gameid>.html` | one game, play-by-play detail |
| **Team season page** | `season-events-2d-html --team OKC` | `season_events_2d_<TEAM>.html` | one team's whole season, one column per game |
| **League page** | `nba-season-html` | `nba_season.html` | all 30 teams' season averages, one column per team |

They link to each other: the league page's tricodes open team pages,
and a team page's per-game box cards carry a `detail` link to that
game's page. The game page is documented first; the two season pages
follow. For the other commands (shot charts, CSV reports), see the
[README](README.md).

## Generating a page

```bash
# one-time setup
python3 -m venv .venv && source .venv/bin/activate && pip install -e .

# find the game id, fetch its play-by-play, render the game page
nba-pbp games --date 2026-05-18
nba-pbp fetch --game-id 0042500311 --output outputs/sas_okc_g1.csv
nba-pbp plusminus-players-html --input outputs/sas_okc_g1.csv \
    --output outputs/sas_okc_g1_pm_players.html --tooltips

# one team's season page (reads that team's cached games)
nba-pbp season-events-2d-html --season 2025-26 --team OKC \
    --output outputs/season_events_2d_OKC.html

# the league page (reads every team's cached games)
nba-pbp nba-season-html --season 2025-26
```

`--tooltips` enables all the hover interactions described below (pure
CSS — the page never runs JavaScript). Without it you get the same page
with no hovers.

The page is fully self-contained (charts embedded as SVG data URIs), so
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
| `OKC` / team name | **open** | the team's Karma panel and its box score |
| `Players` | closed | one small plus/minus chart per player |
| `Lineups` | closed | the lineup stints plot and lineup box score |

Each team gets its own `team name` / `players` / `lineups` trio.
Open toggles read `Less` (the team toggle keeps the team name).

## The Karma panel

Each team's block opens with its own Karma panel (`OKC Karma`,
`SAS Karma`) — the same chart drawn from that team's perspective, so
its good events always point up. Four layers:

- **Stacked bars** — weighted good/bad event counts per 20-second
  interval (made shots count their point value — 3P=3, 2P=2, FT=1;
  everything else counts 1). The upward stack is the block's team's
  good events in its bright team color, tipped with the opponent's bad
  events in the opponent's dimmed color; the downward stack mirrors it.
  Every segment wears the brand color of the team that produced it.
- **Dim yellow line** (left `+/-` axis) — the team's smoothed score
  margin (5-second samples, 1-minute moving average).
- **Event markers** (off by default — see the event cycler below) —
  every event by every player on the team as a letter glyph: `1 2 3`
  made shots by value (a `1` is a made free throw), `R` rebound, `A`
  assist, `S` steal, `B` block, each in the player's chart color;
  missed shots, fouls (`F`), turnovers (`T`), and opponent offensive
  rebounds (`o`) in red. Three arrangements: **pEvents** places each marker on its player's rotation
  lane at the moment it happened; **vEvents** collects the markers per
  game minute and stacks them at that minute's center (good events
  climb up from the zero line, bad hang below — here every marker tied
  to one of the team's players wears the player's color, so red means
  "not ours"); **hEvents** packs each
  player's events — good and bad mixed, in game order — to the left of
  their lane without overlap, so each row reads as that player's event
  tally. Opponent offensive rebounds (`o`) belong to no lane, so only
  vEvents shows them.
- **Dashed lines** (right `Score` axis) — both teams' cumulative
  scores, each in its brand color; the axis itself is colored like the
  block's team.
- **The rotation band** (dim color blocks) — each player's on-court
  stints as one horizontal lane, stacked in box score order (top row of
  the box score = top lane), spread over the full plot height. Colors
  match the player charts and box score names.

The x-axis is game time (`Q1…END`), with the actual local wall-clock
time each period started printed underneath.

**`Hide Stints` / `Show Stints`** — the switch on the panel's title
line removes the rotation-lane backdrop, leaving just the bars and
lines. While hidden, hovering the panel no longer pops stint readouts,
but hovering a box score row still lights up that player's stint spans
over the blank panel.

**`Hide +/-` / `Show +/-`** — next to the stints switch; removes the
smoothed margin line along with its left axis.

**`Hide Karma` / `Show Karma`** — removes the stacked event bars and
the corner team labels, leaving whatever other layers are shown.

**`Hide Scores` / `Show Scores`** — removes both teams' cumulative
score lines along with the right `Score` axis.

**The event cycler** — one button that steps through the event-marker
arrangements: `No Events` → `player Events` (pEvents) → `+/- Events`
(vEvents) → `total Events` (hEvents) → back to `No Events`. The label
always names the presentation currently shown; clicking advances to
the next one.

All five switches, the event cycler, and the box score's per-32 switch
are independent — any combination works.

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
time, and the highlighting is recomputed on the rates. The Karma panel
above is unaffected. As with any rate view, low-minute players produce
noisy numbers.

## Player charts (`Players` toggle)

One chart per player, ordered by minutes played, title in the player's
color. Within each chart:

- **Shaded spans** — the player's on-court stints (their color).
- **Black line** — the *team's* margin shape while they were on court,
  rebased to the player's own running plus/minus (flat while benched).
- **Black dots** — stint entry/exit, at the +/- they entered/left with.
- **Markers** — that player's own events: `1 2 3` made shots by value
  (a `1` is a made free throw), `R` rebound, `A` assist, `S` steal,
  `B` block, in the player's color; missed shots, fouls (`F`), and
  turnovers (`T`) in red.

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

Every readout is a box score-formatted line pinned near the relevant
title, column-aligned with the box scores. The data row is always in
the entity's color.

| Hover target | Shows |
|---|---|
| a player chart's **title** | that player's full-game box score row |
| a **stint span** in a player chart | that stint's own stats (they sum exactly to the full-game row) |
| a **lane segment** in a Karma panel's rotation band | that stint's stats (shown below the panel), **plus** a highlight bar over the player's row in the box score below |
| a player's **row in the team box score** | a highlight over the row and over all that player's lanes in the Karma panel's rotation band |
| a **lineup plane** in the lineup plot | the lineup's box score line (in the lineup color) and its players (each in their color), plus a highlight on its row in the lineup box score |
| a lineup's **row in the lineup box score** | a highlight over all that lineup's planes in the plot (and hovering the name cell also pops the full player names) |

## The team season page (`season-events-2d-html`)

Renders one team's whole season — one column per game on a shared date
axis, one lane per stat — as flat lanes stacked joyplot-style. The
title wears the team's brand color and centers on the box score card.

### Lane encodings

Lanes top to bottom: `FL TOV BLK STL AST DR/OR FT 3P 2P +/- B2B LOC
W/L`. Each stat lane draws one translucent vertical bar per game, on
its own non-zero-based scale so it spends its full height on its
actual range.

- **Simple stat lanes** (`FL TOV BLK STL AST`): one bar per game.
  Colors: turnovers/fouls reds, playmaking cool hues (AST cyan, STL
  green, BLK purple).
- **`DR`/`OR`**: defensive and offensive rebounds stacked in one lane
  (two blues), scaled to total rebounds.
- **Shooting trios** (`FT`, `3P`, `2P`): each lane overlays three bars
  per game — attempts (dark), makes (vivid), and percentage (pale, at
  half width on its own % scale). Each family holds one hue in three
  steps — 2P orange, 3P magenta, FT teal — and within a game the bars
  z-stack by value (taller behind, shorter in front) so all three stay
  visible.
- **`+/-`**: the game margin, green above zero and red below.
- **`B2B`**: one mark on the second night of each back-to-back,
  colored by the pair's venues — **yellow** home-home (`HH`), **hot
  pink** split (`HA`/`AH`), **red** away-away (`AA`). A **small green
  half-height mark** flags games after two or more full days off
  (`OFF`).
- **`LOC`**: one line per game — **full height in the opponent's
  (dimmed) brand color** for away games, **half height in the team's
  own color** at home, so road stretches stand tall.
- **`W/L`**: one line per game — **full-height red on a loss**,
  2/3-height green on a win, so losses poke above the green field.

### The value column

Hovering or pinning a game shows its numbers in the right-hand column,
each in its lane's color. The trio lanes show all three members
(`%`/attempts/makes rows); `+/-` shows the signed margin. The three
schedule rows read as left-justified phrases on the label column
instead of bare numbers:

- **B2B row**: `B2B HH` (venue code, or `OFF`) in the mark's color —
  hidden entirely when the game is neither a back-to-back nor
  rest-flagged.
- **LOC row**: the team's own tricode, then `vs`/`@`, then the
  opponent's tricode in the opponent's color — both tricodes turned
  vertical, centered on the lane.
- **W/L row**: the result letter in win/loss green/red, then the final
  score (`W 112-104`); there is no separate label.

### Interactions

One pointer position reads both axes: the x-position names the game
(columns tile at midpoints, so anywhere snaps to the nearest game) and
the y-position names the lane under the cursor.

- **Hover**: draws the date line at that game, previews its box score
  below the plot, spotlights the hovered lane at 2x height with its
  own value axis, and brightens that stat's column in the box score
  card (the column stays black; the digits under the highlight go
  white).
- **Click**: pins *both* — the game and the stat. Click the same spot
  again to toggle just the stat off (the game and date line stay);
  click a third time to re-select it; click a gap between lanes to
  release everything. Clicking a different lane or column switches the
  pin directly.
- **Lane labels** (right column): every stat label — each trio member
  (`FT%`/`FTA`/`FTM`, …) and `DR`/`OR` included — is its own control.
  Hovering outlines it and previews its lane at 2x. Clicking cycles
  three states: the first click **pins the 2x** (date order, survives
  mouse-out); the second **rank-sorts the season by that exact stat**
  — every lane's bars re-pack left-to-right, best first (FL/TOV fewest
  first), starting at day 1, and the date axis hides. While ranked,
  mousing across the 2x graph previews each game's box score with the
  sorted stat's value circled and its own box-score column striped;
  clicking a different member of the lane switches the sort to it. The
  third click restores the date layout and releases the lane. While a
  game is pinned, a label click swaps the pinned stat instead.
- **Arrows / keyboard**: the L R U D arrows by the title step games
  (left/right) and selectable lanes (up/down); the same arrow keys
  work directly after a click, via native radio-group stepping.
- **Box score card**: gold marks the column best, red the worst
  (inverted for TO/PF), dashes mark empty shot groups; player names
  are colored by minutes rank; the `detail` link opens that game's
  plus/minus page (present only for fetched games).

## The league page (`nba-season-html`)

The league-wide season page: the same stat lanes as a team page, but
the 30 columns are the 30 teams and every bar is that team's per-game
season average. The default column order is by `+/-`, best first. Each
tricode (and each team name in the box table) links to that team's
season page.

Lanes top to bottom: `FL TOV BLK STL AST DR/OR FT 3P 2P +/-`, encoded
exactly like the team page (stacked rebounds, shooting trios with
value-ordered z-stack, teal/magenta/orange families). Below the plot
sit the **Games** view buttons and a league box table.

### Selecting a team

- **Hover a team's column**: brightens its tricode, shows its full
  value column on the right (every stat, in lane colors, `+/-` as the
  combined `+/- +10.5` phrase), and highlights its row in the box
  table.
- **Click a column**: pins that team, so its values stay up while the
  pointer moves; click the pinned column again to release. The
  leftmost (best `+/-`) team starts pinned.

### Sorting — every stat label is a sort button

Every lane label is a click target that re-sorts the 30 team columns
left-to-right by that exact stat — best first (`FL`/`TOV` invert:
fewest first). Each trio member sorts separately: `FTA`, `FTM`, and
`FT%` each produce their own order, as do `DR` and `OR`. The value
column is display-only; clicking the `+/-` prefix of the combined
phrase (that lane's label) restores the default order.

While a sort is active:

- a **circle** rings the sorted stat's value in the pinned team's
  column (a passive indicator — the values take no clicks);
- the sorted lane grows to 2x height with its value axis, the other
  lanes dim, and the tricodes move up under the sorted lane's baseline
  so the ranking reads right at the bars;
- the box table's rows reorder to the same ranking, and a stripe
  highlights the sorted stat's own column (`OR` → `OREB`, `FT%` →
  `FT%`, …).

**Hovering** any label magnifies its whole lane group (all three trio
labels magnify their shared lane) with its axis, and dims the rest —
a preview of the sort without clicking.

### The Games view buttons

Six exclusive views recompute the whole page — every bar, value,
sort order, rank, and box-table row — from just those games:

`1:27` `28:54` `55:82` `Regular` `Playoffs` `All` (default)

The three ranges slice the regular season by game number. Teams with
no games in a view (non-playoff teams under `Playoffs`) show dimmed
dash rows in the box table and sort after everyone else.

### Rank mode

The **Rank** button (right of the tricodes) swaps values for
standings: the bars hide and each lane shows every team's league rank
as one level row of numbers, each in its team's color. Ranking is
competition-style (ties share a rank); `FL`/`TOV` rank 1 = fewest.
Rank mode respects the active Games view and combines with sorting.

### The box table

One row per team — `Team # W L` then the full per-game stat line
(`MIN PTS +/- FGM FGA FG% 3PM 3PA 3P% FTM FTA FT% OREB DREB REB AST
STL BLK TO PF`). Gold marks the column best, red the worst (inverted
for TO/PF). Rows follow the active sort; the hovered/pinned team's row
is highlighted; the table scrolls with the page (no inner scrollbar).

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
  (`plot_plus_minus_by_player_html`), and the team season page
  (`plot_season_events_2d_html`).
- `src/nba_pbp/nba_season.py` — the league page
  (`plot_nba_season_2d_html`): per-view season averages, the sort
  radios and per-team column variables, Rank mode, and the league box
  table.
- `src/nba_pbp/client.py` — NBA/ESPN endpoint wrappers with disk
  caching.
