# nba-dataview — page controls

Everything is pure HTML/CSS: every control is a label wired to a hidden
checkbox or radio. No JavaScript anywhere.

## Team pages

### Corner (top left)
- **^ 25/26** — up to that season's league page.
- **‹ TRI / › TRI** — previous / next team, alphabetical, circular.

### Tabs
- **GAMES** — the filter card. **PLOTS** — the plot show/shrink card.

### GAMES card (filters)
Chips are dim until selected, lit while active.
- **All** — lights whenever any filter is active; click to clear them.
- **1:26 / 27:56 / 57:82** — season thirds (game-number ranges).
- **Regular / Playoffs**, **East / West**, **OT / Clutch**,
  **W / L**, **H / A** — one of each pair at a time; click the other
  to switch, **All** to clear.
- Filters hide game columns everywhere: plots, averages, the box.
  Scales stay season-wide except PM, which re-ranges to shown games.

### PLOTS card
- Colored plot names — click to shrink/show that plot (dim = shrunk).
- **SHOW / SHRINK** — copies of the main controls (below).

### SHOW / SHRINK (main row, right side)
- **SHRINK** — shuts every plot. Your individually closed plots are
  remembered through it.
- **First SHOW after a SHRINK** — restores exactly what that SHRINK
  closed (your own closures stay closed).
- **Second SHOW** — shows everything (also the full reset: clears
  member toggles and, on the season page, hidden teams).
- After SHRINK, a PLOTS-card chip *peeks* that one plot open;
  its ✕ re-shuts it.

### Plot label lines (under each plot)
- **Single stats (PF, TO, BLK, STL, AST, PM)** — the label itself
  closes the plot. **↑↓** cycles none → sort-up → sort-down by that
  stat. **✕** closes. **←→** (appears under a filter) stacks the
  shown games against an edge, keeping the current order.
- **Groups (DR OR, FT% FTA FTM, 3P% …, 2P% …)** — each member name
  toggles that member: dimmed label, its bars and pole chips drop
  from the plot. Each member has its own **↑↓** sorting the lane by
  that member's values. **✕** closes the whole plot.

### The W/L band (bottom)
One shared plot area, three rows: **W/L** result on top (green/red),
**opponent** color mid, **B2B** bottom (venue-pair colors: yellow
HH, pink mixed, red AA; creme = 2D rest; nothing = ordinary gap).

Its controls line:
- **W/L** label, then four color-coded sorts that reorder all three
  rows together: **green** by result, **team color** by home/away,
  **gold** by the B2B value, **white** by opponent tricode.
- **←→** (under a filter) stacks the band, keeping the active sort.
- The **readout** shows the tracked game: W/L, H/A, opponent, B2B,
  each in its color. **✕** shrinks the whole band.

### Tracking and pinning
- Hovering a game column raises the **pole**: a vertical tracking
  line through every plot at that game's date (grey on hover, white
  when pinned).
- The **flags** sit at each plot's pole tip: left of the pole is
  that game's **value** for the stat, right of it the value's
  **rank** among the season's games — rank 1 is always *best*
  (most assists, but fewest fouls/turnovers). Group plots stack one
  value|rank row per member, in the member's color.
- The **date hat** (mm-dd) rides just above the hovered plot's
  flags.
- **Click a game column to PIN it** — its line, flags, readout, info
  line and box row stay lit. The pinned info (date, matchup,
  team-colored score, LINK to the game page) sits centered on the
  SHOW/SHRINK row. **PINNED** (left) unpins.
- Hovering another game temporarily takes over the readouts;
  box-score rows track and snap the same way.

### Box score
- **10 / 25 / ALL / HIDE** — visible rows.
- Filtered views add a status line: filter names, game count and the
  **W-L record** (green/red), then that view's averages.
- Per-opponent rows: **vs TRI**, count, record, averages.
- Hovering a box column stripes the matching plot; hovering a row
  tracks its game.

## Season page

Same plot management (SHOW/SHRINK, chips, member toggles, sorts,
packs) over the 30 teams instead of games.

- **Teams ring / East–West rows** — click a tricode to hide that
  team everywhere; **NONE** inverts (start empty, add one by one).
  Hiding teams lights **SHOW**, which restores them.
- Sorts order by displayed value (PF/TO/L sort by value, not rank).
- **←→** stacks visible teams keeping the current order.
- PM auto-ranges to the shown teams; conference masks re-scale
  every lane to the filtered field.
- The corner links circle through the published seasons.

## Layout

The pages are frozen at a 900px design canvas — identical at every
window size (small windows scroll).
