# Response log

Each entry: the request, when it was answered, a one-line summary,
and the final response as given.

---

## 2026-08-02 10:15 — "make the controls.md, start logging your final response to a request with date time and summary and the response"

**Summary:** Wrote CONTROLS.md (full guide to both pages' controls) and started this response log; both committed, practice saved to memory.

Both done.

**[CONTROLS.md](CONTROLS.md)** now documents every control on both pages — the filter chips and their dim/lit language, the two-stage SHOW/SHRINK contract, the PLOTS card, single-stat and group label lines (member toggles, per-member sorts, packs), the W/L band's rows and its four color-coded sorts + readout, tracking/pinning, the box score's views and records, the season page's team hiding and NONE mode, and the frozen 900px canvas.

**Response logging is on:** this file (LOG.md, repo root) records each request's final response with a timestamp and summary — this entry is the first. I've saved the practice to memory so future sessions keep appending, and both files are committed to the repo so you can read them anytime (they don't affect the published site).

---

## 2026-08-02 10:40 — "did I see anything about flag poles and flags on mouse over, i.e. what are they"

**Summary:** Explained the pole/flags (tracking line + per-plot value|rank pairs, rank 1 = best, direction-aware) and expanded CONTROLS.md's tracking section.

Yes — briefly, in CONTROLS.md's "Tracking and pinning" section. What they are: the pole is the vertical tracking line through every plot at the hovered game's date (grey hover / white pinned). The flags at each plot's pole tip show, left of the pole, that game's value for the stat and, right of it, the value's rank among the season's games — rank 1 is always best, direction-aware (most assists, fewest fouls/turnovers). Group plots stack one value|rank row per member in the member's color; the mm-dd date hat rides above them; everything follows the mouse and rests on the pinned game. CONTROLS.md's section now spells this out.

---

## 2026-08-02 11:05 — "change the controls.md to help.html and link it to the upper right corner on all pages" (+ "add index page after help")

**Summary:** CONTROLS.md became a dark-styled help.html at the site root; HELP and INDEX links sit in the upper-right corner of every page (team, season, and all 1,398 game pages).

Done. CONTROLS.md is retired; its content now lives in help.html, styled to match the site (dark, colored accents, a back link). Every page carries HELP INDEX in the upper-right corner: the team and season generators emit the links, the 1,398 existing game pages were patched in place (their generator also emits them for future builds), and the staging script now carries help.html to the published root next to index.html. Verified the links land: HELP opens the guide, INDEX goes to the site root. Both seasons rebuilt and staged — local until "push and publish".

---

## 2026-08-02 11:20 — "stack help/index. index only for gh_pages subset"

**Summary:** Corner links stacked vertically (HELP over INDEX, right-aligned) on all pages; the index page now exists only in the published gh-pages subset, not in outputs.

Done — the corner links stack (HELP above INDEX, right-aligned) on the team and season pages, in the game-page generator, and re-patched across the 1,398 existing game pages. The local outputs/index.html is gone: index.html is generated only into the gh-pages staging, so the INDEX link resolves on the published site (locally it 404s by design). Both seasons rebuilt and staged — local until "push and publish".

---

## 2026-08-02 11:55 — "the traveling date doesn't track moused over games for sorted plots"

**Summary:** The date hat now lives per-lane and takes its x from the hovered cell's own lane-scoped position, so it tracks exactly under every sort and pack.

Fixed — the hat was reading the page-level calendar position (a CSS subtlety: var() inside a custom property resolves where it is declared, so the sorted lane's positions never reached it; the unsorted look was right only by construction). Each lane now carries its own hat, and per-game rules set its x from the hovered cell's own variable, which resolves inside the lane — sorted, member-sorted, packed, filtered, and strip-band hovers all verified at exactly 0px offset. The hat also inherits lane behavior for free: it disappears with a shrunk lane. Both seasons rebuilt and staged — local until "push and publish".

---

## 2026-08-02 12:20 — "stacking does not work"

**Summary:** Stacking is now always available (faces no longer hidden without a filter) and works on member-sorted group lanes (per-member count trees compose pack with each sort).

Fixed — two things were biting. The stack arrows only existed while a filter was active, so with nothing filtered there was nothing to click; they now always show, and packing an unfiltered lane uniformizes the calendar spacing. And the group lanes (DR, FT%, 3P%, 2P%) had no pack rules for their per-member sorts, so stacking a member-sorted lane did nothing; each member now has its own count tree and the stack packs in that member's order, keeping the sort, with or without filters. Verified: no-filter pack (97 games uniform), FTM-sorted pack (order kept, uniform), and the same under EAST. Both seasons rebuilt and staged — local until "push and publish".

---

## 2026-08-02 13:00 — "on the player pages: hide/show lineup box score by clicking on the team's lineups box score title"

**Summary:** Each lineup box score title is now a fold — click hides/shows that team's table (details/summary, no JS); generator updated and all 1,398 built game pages patched (2,796 boxes).

Done — on the player (game) pages, each team's "XXX Lineups box score" title now toggles its table: click to hide, click again to show, with a hover highlight on the title. It works alongside the per-8 switch, starts open, and needs no JavaScript (a details/summary fold with explicit hiding, since the pre-formatted context defeats the native collapse). The generator emits it for future builds and all 1,398 existing game pages were patched in place. Staged — local until "push and publish".

---

## 2026-08-02 13:15 — "remove one line gap below NOP Lineup box score in player page"

**Summary:** The blank line below the lineup box score titles (a leftover newline after the fold's summary) is gone across generator and all 1,398 built pages.

Fixed — the fold I added kept a newline after the clickable title, and since the title now breaks its own line, that newline rendered as a blank line below every "Lineups box score" title. Removed in the generator and re-patched across all 1,398 game pages; title-to-table spacing is back to the normal single-line flow (34px -> 7px, verified on the LAL/NOP page). Staged — local until "push and publish".

---

## 2026-08-02 13:40 — "lower top Lineups box score ... show per 32/8 line closer to the Lineups plot by two lines"

**Summary:** The top lineup box (title + per-8 switch included) rides two lines lower, closing the gap to the combined Lineups plot; the box layers above the slice so no rows are covered.

Done — the first team's Lineups box score (with its title and Show-per-8 line) sits two lines lower, closing the blank toward the combined Lineups plot: margin-top grows two lines while a negative bottom margin keeps the plot in place, and the box now layers above the image slice so the overlap lands on the slice's blank top band (first attempt covered the table's last rows — caught and fixed). Generator updated and all 1,398 built pages patched; verified on the LAL/NOP page. Staged — local until "push and publish".

---

## 2026-08-02 14:10 — "no gap between upper lineups box score title and upper lineup mouse over shown lineup detail; gap should match lower title/detail" (with the OKC/HOU layout walkthrough)

**Summary:** Restored the 4-line hover-readout band between the upper lineup box and the Lineups plot (the earlier two-line pull had eaten it); the box keeps its lowered position.

Fixed — the section layout is: upper box, a reserved 4-line band where the upper team's stint hover readout appears, the combined Lineups plot, the lower readout, the lower box. My earlier "two lines closer" change consumed two lines of that reserved band, so the upper readout landed with no gap. The negative bottom margin is gone: the band is back at full height (upper title-to-detail spacing matches the lower side again) and the box itself stays two lines lower as requested. Generator + all 1,398 built pages. Staged — local until "push and publish".

---

## 2026-08-02 14:30 — "the gap between end of HOU lineups box score and start of HOU lineup popup does not match the end of OKC popup and start of OKC lineups boxscore"

**Summary:** Evened the readout gaps: upper box-to-popup now equals lower popup-to-box (21px both), via a 0.58cqw bottom margin on the upper box.

Fixed — measured with the readouts force-shown: the upper gap (HOU box end to HOU popup) was 14px against the lower side's 21px (OKC popup end to OKC box title). A small bottom margin on the upper box pushes the plot and its popup down the difference; both gaps are now exactly 21px. Generator + all 1,398 built pages, verified on the OKC/HOU page. Staged — local until "push and publish".

---

## 2026-08-02 14:45 — "did not fix" / "top gap too big"

**Summary:** The first pass matched box RECTANGLES, but the upper box carries 21px of trailing padding — visually the top gap was still double. Re-measured text-to-popup and set -1.17cqw: both visual gaps are now 21px.

Right — my first match used the box rectangle, which hides 21px of trailing padding, so the visible gap (last table row to popup) was still 42px against the lower side's 21. Corrected the margin by that padding: last-row-to-popup and popup-to-title now both measure 21px. Generator + all 1,398 pages re-patched. Staged — local until "push and publish".

---

## 2026-08-02 15:10 — "the bottom of hou last lineups row to the top edge of the hou popup is bigger than the bottom edge of OKC popup to top edge okc lineups title"

**Summary:** Scanned all 84 popups; the sides differed by ~1.5px. The lower box now carries a tiny top margin and both gaps sit at ~21.5px, within half a pixel of each other.

Done — measured every stint popup on both sides (they all anchor identically per side): the upper row-to-popup gap was ~22.3px against the lower popup-to-title's ~20.8px. The lower box gained a hair of top margin; the true values now read 21.33 vs 21.75 — equal to well under a pixel. Generator + all 1,398 pages. Staged — local until "push and publish".

---

## 2026-08-02 15:25 — "what is the vertical distance between bottom edge of OKC popup to top edge of OKC Lineups box score title? ... HOU last row to HOU popup top?"

**Summary:** Measured: OKC popup-to-title 21.75px; HOU last-row-to-popup 21.33px — a 0.42px subpixel difference.

On the OKC/HOU page: OKC popup bottom to OKC title top is 21.75px; the fully open HOU box's last row bottom to the HOU popup top is 21.33px. The 0.42px difference is subpixel residue from the cqw math — below what a display renders. If the gaps still read differently by eye, the popup drop shadow is the likely culprit (it softens the edges by a couple of pixels); it can be trimmed on request.

---

## 2026-08-02 15:35 — "get rid of shadows"

**Summary:** Removed the drop shadows from the hover popups (stint readouts and lineup-name popups) — crisp edges, true gaps.

Done — the box shadows are gone from the stint readout popups and the lineup-name popups on the player pages (the marker ring's glow stays, it is a highlight rather than a shadow). Popup edges are crisp now, so the matched 21px gaps read as they measure. Generator + all 1,398 pages. Staged — local until "push and publish".

---

## 2026-08-02 15:45 — "remove the background behind the pop ups"

**Summary:** The #222 panels behind the popups are gone (stint readouts and lineup-name popups); the text floats on the black page.

Done — the grey panel behind the hover popups is removed on the player pages: the stint readouts and lineup-name popups render as bare text on the page black. Generator + all 1,398 pages, verified on the OKC/HOU page. Staged — local until "push and publish".

---

## 2026-08-02 15:55 — "log as not resolved, then push and publish"

**Summary:** UNRESOLVED (parked): the perceived mismatch between the upper (HOU last row → popup) and lower (OKC popup → title) gaps in the player pages' lineups section. Measured 21.33px vs 21.75px after several passes (margins tuned, shadows and backgrounds removed), but it still reads unevenly to the eye. Minor visual irritation — to be revisited.

Logged as not resolved and published. The gap work so far: reserved readout band restored, box lowered two lines, margins tuned to sub-pixel equality, popup shadows and backgrounds removed. Whatever remains is perceptual or anchored in the baked image bands — parked for a later look.

---

## 2026-08-02 16:05 — "on the player pages what plots use images?"

**Summary:** All charts are image slices of one rendered figure (Karma panel, team summary/rotation panels, player plus-minus grids, combined Lineups plot); box scores, recap, popups and controls are HTML overlaid on them.

Every chart is an image: the page renders one big matplotlib figure to full-page SVGs (data URIs), and slice divs crop horizontal bands of it — the Karma/event panel, each team's summary panel with the rotation band, each team's player plus-minus grid (Players toggle), and the combined Lineups plot (Lineups toggle). The HTML parts are the header, player and lineup box scores, the recap, and all interactivity (popups, readouts, highlights, toggles). Charts need re-rendering to change; text/spacing can be patched in place.

---

## 2026-08-02 16:20 — "why can't the Karma panel be html/css?" / "just drawing the karma lines on the plot area"

**Summary:** It can. The karma lines specifically are the easiest part: a score margin is a step function, so ~2 divs per scoring event (team-page bar machinery) draws it in pure CSS; alternatives are a single clip-path polygon (filled area) or an inline SVG polyline (exact smooth stroke, no image, no JS). The catch is anchoring onto the baked panel's coordinates, which the hover overlays already do.

Answered: the panel is an image for historical reasons (the page began as one matplotlib figure). For just the lines: (1) pure-CSS steps — one horizontal sliver per interval plus a vertical at each score, a few hundred divs from the CSV, crisp and patchable; (2) one div with a clip-path polygon for a filled margin area; (3) an inline SVG polyline for the exact current look, markup not image. Offered to prototype the step version over the existing Karma slice.

---

## 2026-08-02 16:30 — "how about the stints as an html layer?"

**Summary:** Yes — stints are rectangles and their geometry already exists as the invisible hover boxes; a visible HTML layer is mostly "give those boxes a background." Clean version re-renders once with baked planes omitted (avoids double-tint) and minds paint order vs the baked line/markers.

Answered: stints as an HTML layer are even more natural than the karma lines — the hover boxes (and the rotation band's self-painting segments) already carry exact stint geometry. Benefits: CSS-patchable styling, native hover, crisp edges, smaller SVGs once planes leave the render. Considerations: double-tinting over the baked planes (fix: one pipeline re-render with planes off) and paint order (planes must stay translucent under the baked line, or the line goes HTML too). Framed as step one of peeling the combined Lineups plot fully out of the image.

---

## 2026-08-02 17:00 — "scores and +/- are a line segment for game, can we do that"

**Summary:** Prototyped on the OKC/HOU page: the Karma panel's +/- margin and both score lines now render as HTML step segments (505 divs) instead of baked strokes — exact axis alignment, wired into the Hide +/- and Hide Scores toggles. Generator done; full fleet needs a ~20min re-render pass (pending decision).

Done as a working prototype on game 0022500001 (OKC/HOU): the generator skips the baked margin/score strokes and emits them as HTML step segments in figure coordinates (steps are the honest shape — the margin only moves when the score does). Verified: segments land exactly on the panel's axes over the bars/stints/events, and the existing Hide +/- / Hide Scores toggles control them. The other 1,397 pages keep their baked lines until a fleet re-render (~20 minutes parallel) — say the word and I will run it.

---

## 2026-08-02 17:20 — "add html stints to showcase"

**Summary:** The combined Lineups plot's stint planes are now HTML on the showcase page (42 rects from the pin/hover geometry, band-split per team, render-matched colors/alpha); the baked planes are skipped there. Karma lines + stint planes both live as HTML on game 0022500001.

Done — the showcase page (OKC/HOU) now draws the combined plot's stint planes as HTML: the generator skips the baked axvspans (html_planes) and emits per-stint rects in figure coordinates through the same overlay pipeline as everything else, band-split per team with the render's wheel colors at 30% alpha. Hover/pin highlights and the lineup box-score row links keep working. Together with the step lines, the Karma margin/scores and the stint planes are now live HTML on this page; the fleet re-render remains the pending step to roll both out everywhere.

## 2026-08-02 19:20 — "do the karma bars and markers"

**Summary:** Karma bars (343 rects) and the combined plot's +/- markers (42 diamond/circle divs) are now HTML on the showcase page; a transform-timing bug (rects computed before the panel's x-range was set) was found and fixed; layering matches the render, and markers no longer get tinted by the HTML stint planes.

Done — the karma bars and the combined plot's +/- markers are now HTML on the showcase page (OKC/HOU, game 0022500001).

- **Karma bars**: the generator skips the four baked bar series and emits 343 translucent rects (brand color + dimmed-tip stacking, alpha .55) through the overlay pipeline. The first build had them wildly wrong — the rects were computed before the panel set its x-range, so the whole game mapped into the first minute; moving the computation after the axis setup fixed it, and the panel now matches the published baked version bar-for-bar. They sit above the margin/score lines exactly as the render layered them, and Hide Karma hides them.
- **Markers**: the 42 stint +/- diamonds/circles are divs (rotated square / border-radius) in team brand colors, centered on the same transform the hover rings use — the pin/hover ring lands dead-center on them. They now sit above the stint planes, as matplotlib drew them; the published page had been tinting the baked markers pink under its HTML planes, which this fixes.

With the earlier step lines and stint planes, all Karma/combined content except the event glyphs is now live HTML on the showcase. Rebuilt 2024-25, shipped (not pushed).

## 2026-08-02 19:30 — "is anything not html/css in karma plot"

**Summary:** Q&A — inventoried what's still baked in the Karma panel: all four event layers (stint lanes, event markers, vEvent columns, hEvent rows), the axes furniture (grid, zero line, tick labels, +/- and Score scales), the HOU/OKC corner tricodes, and the frame. HTML now: title, margin line, score lines, karma bars.

Yes — four things in the Karma panel are still baked into the SVG image:

1. **All the event content** — the translucent player stint lanes in the background, the per-player event markers, the per-minute event columns (vEvents), and the left-packed event rows (hEvents). Everything the No Events cycler switches between is still image swaps.
2. **The axes furniture** — grid lines, the white zero line, the Q1...END tick labels and wall-clock times, the left +/- scale, and the right red Score scale with its label.
3. **The two corner tricodes** (HOU / OKC) — they're drawn on the bars layer, so they ride the same baked overlay that Hide Karma toggles, even though the bars themselves are now HTML.
4. The panel frame/spines, as part of the base image.

Now HTML/CSS: the title, the margin step line, both dashed score lines, and the karma bars.

The events are by far the biggest remaining piece — four separate layers with their own draw helpers — and the corner tricodes would be a trivial conversion. The furniture (grid/ticks/scales) is static, so baking costs nothing interactively.

## 2026-08-02 19:55 — "corner tricodes, event layers go html"

**Summary:** The Karma stint lanes, all three event-glyph layers, and the corner tricodes are now HTML on both karma panels of the showcase page; the four baked layer SVGs per panel are gone (page 1.65MB -> 1.22MB); verified glyph-for-glyph against the published page in all three event states.

Done — the Karma corner tricodes and all four event layers are now HTML on the showcase page (both panels, HOU and OKC).

- **Stint lanes** (94 rects): the translucent player bands render as divs from the same lane geometry, hidden by Hide Stints as before.
- **Event glyphs** (1,563 text divs): pEvents / vEvents / hEvents are per-glyph text divs — italic letters, upright digits, player colors, bold to match the baked stroke weight — positioned by the same transforms as the old scatters; the No Events cycler now switches the HTML sets per panel.
- **Corner tricodes** (4): HTML text riding the Hide Karma toggle, exactly where the bars layer drew them.
- The four baked layer SVGs per panel are gone: the page dropped from 1.65MB to 1.22MB.
- Verified in WebKit against the published page: glyph positions/colors/sizes match in all three event states on both panels, the cycler and Hide toggles work per panel, and the karma-band stint hovers are unchanged (94 hit areas, readouts reveal).

Still baked in the Karma panels: only the axes furniture (grid, zero line, tick labels, +/- and Score scales, frame) — and, on the second (OKC) panel, the margin/score lines and bars, which are HTML only on the game-level panel so far.

Rebuilt 2024-25, shipped (not pushed).

## 2026-08-02 20:15 — "okc panel lines and bars go html"

**Summary:** The second (OKC) karma panel's margin/score lines and karma bars are now HTML too — 1,010 line segments and 686 bar rects across both panels; the empty bars layer image is gone (the pm/scores layer images stay: they carry the +/- and Score scale numbers).

Done — the OKC Karma panel's margin line, score lines, and karma bars are now HTML, matching the game-level panel.

- The line emission now runs once per panel, each margin from that panel's team's perspective on that panel's own axes — 1,010 step segments and 686 bar rects page-wide.
- The baked bars layer image (now empty on both panels) is dropped from the page; the +/- and Score layer images remain because they carry the axis scales, so Hide +/- and Hide Scores still take the scale numbers with them — verified per panel, along with Hide Karma hiding bars + tricodes.
- With this, every karma layer that draws data is HTML on both panels; only furniture and scales are baked.

## 2026-08-02 20:15 — "make the OKC/HOU box scores click to hide like the lineups box scores"

**Summary:** The team box scores now fold on title click like the lineup box scores — the "TRI box score" title is a fold summary; the table title moved out of the .bx render (hover-row offsets auto-adjusted), per-32 switch stays put, row-hover stint highlights unchanged.

Done — clicking "HOU box score" / "OKC box score" now hides/shows that table, exactly like the Lineups box scores.

- The title moved out of the table render into a fold summary wearing the same .bx/.bx-head classes — pixel-identical position and color, with the same white hover cue as the lineup titles.
- The per-32 switch stays on the title line while folded; row hovers still light the player's karma stints (the hover-strip offsets adjusted automatically when the baked title line left the table).
- Verified with real mouse clicks in WebKit: fold closes, reopens, per-32 swaps, hover highlights fire.

## 2026-08-02 20:30 — "event characters are same font as box score but sized correctly"

**Summary:** The karma event glyphs now use the box score's face — DejaVu Sans Mono, upright, normal weight — at the plot-calibrated glyph size (not the box score's size); the mathtext italic/bold styling is gone.

Done — the event characters now wear the box score's font: DejaVu Sans Mono, upright, normal weight, at the same glyph size as before (calibrated to the plot, not inherited from the box score). The italic letters and bold weight from the mathtext look are gone, so R/A/1/2/3/F/T/S/o read as the same face as the tables below. Verified in WebKit on the showcase page across the event states; positions and colors unchanged.

## 2026-08-02 20:40 — "HOU/OKC Karma plot title - should be HOU/OKC set team on team name"

**Summary:** The karma panel titles are now the matchup — panel team first, each tricode in its brand color: "HOU/OKC Karma" and "OKC/HOU Karma".

Done — the Karma titles now read as the matchup with the panel's team first and team colors on the names: the game-level panel says "HOU/OKC Karma" (HOU in red, OKC in blue) and the second panel "OKC/HOU Karma", with "Karma" in the usual title color. Verified both panels in WebKit.

## 2026-08-02 20:45 — "HOU or OKC on different plots. top is HOU"

**Summary:** Correction to the previous title change — each karma plot names only its own team, tricode in team color: top plot "HOU Karma", second "OKC Karma" (no matchup pair).

Done — back to one team per title: the top plot reads "HOU Karma" with HOU in its red, the second "OKC Karma" with OKC in its blue, "Karma" in the normal title color. Verified both in WebKit.

## 2026-08-02 20:55 — "delete HOU/OKC in plot area"

**Summary:** Removed the in-plot corner tricodes from both karma panels (emission, extraction, and CSS all deleted) — the brand-colored plot title names the team now.

Done — the HOU/OKC corner labels inside the karma plot areas are gone from both panels; the team-colored title carries the identification. The generator no longer emits them at all (the .ktc machinery is fully removed), so nothing rides the Hide Karma toggle but the bars themselves. Verified zero corner labels on the showcase page.

## 2026-08-02 21:00 — "both box score title lines carry team color on team name"

**Summary:** The two team box score fold titles now color the tricode in the team's brand color ("HOU box score" red, "OKC box score" blue), with "box score" staying in the normal head color.

Done — both box score titles now carry the team color on the team name: HOU in its red, OKC in its blue, the words "box score" unchanged. The titles stay clickable folds; verified both on the showcase page.

## 2026-08-02 21:10 — "same thing for line up box score"

**Summary:** The Lineups box score titles (both teams, per-game and per-8 variants, in the combined section) now carry the team color on the tricode, matching the team box score titles.

Done — the Lineups box score titles now color the team name too: "HOU Lineups box score" with HOU in red, "OKC Lineups box score" with OKC in blue, including the "(per 8)" title variants the switch swaps in. The titles remain clickable folds; verified both teams' titles on the showcase page.

## 2026-08-02 21:20 — "whats left in image format"

**Summary:** Q&A — remaining baked SVG content on the game page: the per-player +/- plots (fully baked, biggest piece), the combined Lineups plot base (axes/grid/rolling lines/legend, raw + per-8 variants), and the karma furniture (grid/ticks/frame) plus the +/- and Score scale strips.

Still in image (SVG) format on the game page, top to bottom:

1. **The player plots** — each team's per-player +/- section (the page's namesake chart) is entirely baked: stint bars, cumulative +/- step lines, player name labels, and axes. This is the biggest remaining image content.
2. **The Lineups (combined) plot base** — the axes, gridlines, the two teams' rolling +/- lines, and the corner legend glyphs. Its per-game and per-8 variants are separate baked images the switch swaps. (The stint planes and the diamond/circle +/- markers over it are already HTML.)
3. **Karma panel leftovers** (both panels) — the furniture base (grid, white zero line, Q1...END tick labels with wall-clock times, frame) plus two thin layer images per panel: the +/- scale strip and the Score scale strip, kept as images so Hide +/- and Hide Scores can take the scale numbers along with their lines.

Everything else is HTML/CSS now: the header and linescore, karma titles, margin/score lines, karma bars, stint lanes, all three event-glyph layers, the combined plot's planes and markers, both team box scores, both lineup box scores, and every control, tooltip, and readout.

## 2026-08-02 21:45 — "do the player plots"

**Summary:** The per-player +/- charts are now HTML: on-court spans (94), the stint +/- polylines as rotated pill-capped segments (1,387), event glyphs (503, box score face), entry/exit dots (188), and the player-name titles (20, DejaVu Sans stack). Only the axes furniture stays baked. Page height byte-identical (4040px); page 1.18MB -> 1.11MB.

Done — the player plots' content is HTML now, on every chart of both teams:

- **On-court shading**: the player-color spans are divs at the exact axvspan geometry.
- **The +/- curves**: each stint's jagged polyline renders as rotated segments with pill caps (the page scales uniformly, so angles computed in figure pixels hold at any width) — 1,387 segments reproducing matplotlib's 3.2pt black line, round joins included.
- **Event glyphs**: the R/A/B/S/F/T/1/2/3 markers are text divs in the box score face, same positions (declutter nudges included), player-color/red with the baked alphas.
- **Entry/exit dots**: black circle divs at matplotlib's inscribed-circle size (first attempt was 13% oversized — sqrt(s), not 2*sqrt(s/pi)).
- **Player names**: HTML text at the measured title positions in the karma title's font stack. The title Text artists stay on the axes for measurement and hide only after the slice cuts are computed — first attempt hid them too early and every player section shifted ~20px; the fix keeps the page height byte-identical (4040px old and new).
- Verified in WebKit against the published page: shapes/positions/colors match, title hover and stint hover readouts fire, sections toggle as before. Page dropped 1.18MB -> 1.11MB.

Still baked on the page: only axes furniture everywhere (grids, ticks, scales, frames) and the combined Lineups plot's base (its rolling lines and legend).

## 2026-08-02 21:55 — "why can't we use fonts for out event characters"

**Summary:** Q&A — we can. The CSS already names DejaVu but macOS/Windows don't have it installed, so browsers fall back (box scores fall back identically, so they still match). Baked SVGs dodged this by writing text as paths. Guaranteed DejaVu = @font-face embed (pure CSS): ~2-4KB per-page subset of the 13 event glyphs, or one shared ~15-25KB site font cached across all pages.

We can — nothing technically blocks it. The event characters (and box scores) already name 'DejaVu Sans Mono', but CSS only uses installed fonts; DejaVu ships with Linux and inside matplotlib, not macOS/Windows, so browsers fall back to the generic monospace (Menlo on a Mac) — for both events and box scores alike, which is why they still match each other. The baked SVGs never had the problem because matplotlib writes text as vector paths. For guaranteed DejaVu: @font-face with the font embedded (pure CSS, no JavaScript) — either a ~2-4KB per-page data-URI subset of the ten event glyphs, or one shared subsetted dejavu.woff2 (~15-25KB, box score charset included) published next to help.html and cached once for all pages.

## 2026-08-02 22:20 — "do the shared site font"

**Summary:** Published subsetted DejaVu woff2 faces (mono + sans, regular + bold, 46KB total) at the site root; game pages and help.html now declare @font-face for them, so every 'DejaVu Sans (Mono)' rule resolves to the real face on any OS. Cached once for all pages.

Done — the site now ships its own DejaVu:

- **fonts/** at the repo/site root holds four subsetted faces (ASCII + the site's few symbols): dejavu-mono.woff2 (10.6KB), dejavu-mono-bold (9.8KB), dejavu-sans (13.7KB), dejavu-sans-bold (12.5KB) — 46KB total, built from matplotlib's bundled TTFs with fontTools, downloaded once and cached for all 1,398 game pages.
- **Game pages** declare the four @font-face rules (font-display:swap, ../../../fonts/ like the HELP link); every existing 'DejaVu Sans Mono'/'DejaVu Sans' family now resolves to the genuine face instead of Menlo/Helvetica — box scores, event characters, readouts, titles. The event glyphs now truly match the baked-SVG letterforms, which were DejaVu paths.
- **help.html** references the sans faces the same way; **stage_gh_pages.py** copies fonts/ into the publish stage.
- Verified in WebKit: both regular faces load and apply (bolds sit lazy until requested), the box score and karma glyphs render in DejaVu, and layout is unaffected (page height moved 8px from real-font metrics in the flowed tables — the image geometry is untouched).

Note: the team/season pages also name DejaVu but don't declare the @font-face yet — say the word and I'll wire those two generators the same way.

## 2026-08-02 22:35 — "wire the team/season pages the same way"

**Summary:** team2.py and nba_season.py now declare the four @font-face rules for the shared site fonts (team pages at ../../../fonts/, season page at ../../fonts/) — every DejaVu family on those pages resolves to the real face; verified both load in WebKit with layout intact at the frozen 900px.

Done — the team and season generators now declare the same @font-face rules as the game pages, at their own depths (team pages three levels up, the season page two). All the 'DejaVu Sans'/'DejaVu Sans Mono' text on them — headers, filter chips, plot labels, flags, box charts — now renders in genuine DejaVu on any OS instead of the system fallback. Verified in WebKit on the OKC team page and the season page: both faces load (two woff2 requests each, from the shared cached files) and the frozen-900px layout is unchanged. Both seasons rebuilt with the wired generators and shipped.

## 2026-08-02 22:45 — "whats left in image format"

**Summary:** Q&A — remaining baked: the combined Lineups plot base (axes/grid, the two rolling +/- lines, legend; per-game + per-8 variants) and axes furniture (player-chart grids/ticks/scales/frames; karma furniture base + the +/- and Score scale strips). The rolling lines are the last baked data content.

On the game page, two things remain in image format:

1. **The combined Lineups plot's base** — its axes and grid, the two teams' rolling +/- lines, and the corner legend glyphs, baked in two variants (per-game and per-8) that the switch swaps. The stint planes and the diamond/circle markers over it are already HTML.
2. **Axes furniture** — on the player charts: the grid, zero line, Q1...END tick labels, the y scales and the "+/-" label, and the frames; on the karma panels: the furniture base (grid, zero line, tick labels with wall-clock times, frame) plus the two thin scale strips (+/- and Score) kept as layer images so their Hide toggles take the scale numbers along.

Everything that represents data is HTML now except the combined plot's rolling lines — that's the last baked data content on the page. The furniture is static decoration; converting it would mean rebuilding matplotlib's axis layout in CSS for little gain, though it's doable if you want the pages fully image-free.

## 2026-08-02 22:50 — "what do you mean by the combined plot?"

**Summary:** Q&A — "the combined plot" = the single "Lineups" chart between the two Lineups box scores, where both teams share one +/- axis (stint bands split top/bottom per team, diamond/circle markers, two rolling +/- lines). Named after _draw_combined_lineup_stint_panel; its planes/markers are HTML, its base image (axes, rolling lines, legend, per-game + per-8 variants) is the remaining baked part.

The plot titled "Lineups" on the page — the single chart sitting between the two Lineups box scores (behind the Lineups section toggle). It's the one where both teams share one +/- axis: the full-height colored bands are each lineup's stint (HOU's lineups tinting the top half, OKC's the bottom), the red diamonds (HOU) and blue circles (OKC) mark each stint's +/-, and two rolling lines trace each team's +/- through the game. Hovering it pops the lineup detail readouts, and clicking pins a stint.

I call it "combined" after its function in the code (_draw_combined_lineup_stint_panel) because it merges what used to be two separate per-team lineup panels into one shared plot. Its planes and markers are already HTML — what's still baked there is the background image: the axes/grid/frame, the two rolling +/- lines, and the little corner legend ("HOU / OKC" glyphs), in two variants since the per-8 switch swaps a rescaled render.

## 2026-08-02 23:00 — "do the combined plot lines"

**Summary:** The combined Lineups plot's margin line is now HTML — 250 step segments on its own .khl-c class (2px floor to match the baked 1.6pt). One correction: it's ONE game-margin line (top team's perspective), not the "two rolling lines" earlier answers claimed. The plot's remaining baked content is furniture only (axes, grid, legend, title).

Done — the combined Lineups plot's line is HTML now. It turned out to be one line, not two: the olive game-margin from the top team's perspective (my earlier "two rolling +/- lines" description was wrong). The generator skips the baked plot and the builder emits 250 step segments through the same pipeline as the karma lines, on a .khl-c class with a 2px thickness floor to match the baked 1.6pt weight; it sits above the stint planes and below the markers, exactly as the render layered it. No toggle wiring — the plot has no Hide switch. Verified against the published page in WebKit: same path, same color, steps in place of the sample-connected polyline (the same convention the karma lines shipped with). With this, the last baked DATA on the page is gone — every image left is axes furniture, scales, the legend, and panel titles.

## 2026-08-02 23:15 — "combined plots corner legend to html"

**Summary:** The combined plot's legend entries ("HOU diamond" / "OKC circle") are HTML text divs in brand colors; the site fonts were re-subsetted to include the diamond/circle glyphs (U+25C6/U+25CF). Also fixes the old page's tint: the baked legend sat under the HTML planes, the HTML one rides above them as the render's zorder intended.

Done — the corner legend is HTML: each entry a .ppt-based div in the team's brand color, with the diamond/circle glyphs added to the site font subset so they render in true DejaVu. The baked texts are skipped (html_legend flag). Side effect fixed: on the published page the baked legend was tinted by the HTML stint planes above it; the HTML legend sits over the planes as matplotlib layered it.

## 2026-08-02 23:15 — "combined plots panel titles to html"

**Summary:** The "Lineups" panel title is HTML through the player-title machinery (measured, then hidden pre-render). Gotcha: loc="left" titles live on ax._left_title — ax.title is the empty center object, and the first attempt anchored the div there.

Done — the "Lineups" title now renders as HTML at the measured baked position, same font stack as the other titles. It rides the same machinery as the player names (measure extents, emit .ppt div, hide the Text before the SVG render, after all layout measurement). One gotcha: matplotlib keeps loc="left" titles on ax._left_title, not ax.title — the first attempt measured the empty center title and floated the div mid-plot.

## 2026-08-02 23:15 — "stuff in legend should be centered horizontally"

**Summary:** The legend entries are now horizontally centered on the plot — "HOU diamond" top-center, "OKC circle" bottom-center (anchor at 0.5 transAxes + translateX(-50%)).

Done — both legend entries center horizontally on the combined plot: HOU's at the top edge, OKC's at the bottom, each still in its brand color and vertical anchor. Verified in WebKit.

## 2026-08-02 23:25 — "how we gonna get the furnutire"

**Summary:** Q&A — plan for converting the remaining axes furniture: a shared helper walks each axes and emits grid/zero/spine rects + tick-label/ylabel text divs (~700 divs page-wide); karma scale numbers wire to their Hide toggles, retiring the last layer images. End state: no SVG at all (~1.1MB -> ~300-400KB), matplotlib kept as layout engine only. Order: combined plot, karma panels, player grid, then drop the render machinery.

The same way everything else went — furniture is just rects and text, and every position is computable from the axes: frame spines, grid lines at the tick positions, the zero line, tick labels, the +/- and Score axis labels, and the karma wall-clock times. A shared helper walks any axes and emits (a) 1px rect divs for lines through the same transform pipeline as the karma steps, and (b) text divs for labels — pixel-true now that the site font makes HTML text measure identically to the baked SVG text. The karma scale strips become tick-number divs wired to the existing Hide +/- / Hide Scores toggles, killing the last two layer images. Volume ~700 divs page-wide, smaller than the event-glyph conversion. The payoff: with furniture HTML, the baked images contain nothing — the SVG data-URIs (most of the remaining ~1.1MB) go away, img-boxes keep their aspect-ratio to hold layout, matplotlib stays as the layout engine but never renders, and the fleet re-render gets much faster. End state ~300-400KB pure HTML/CSS. Order: combined plot first, then karma panels (+ retire scale strips), then the player grid, then drop the render machinery.

## 2026-08-02 23:40 — "go, start with the combined plot" (furniture)

**Summary:** The combined Lineups plot's furniture is HTML — grid lines (under the planes, per axisbelow), zero line, left/bottom spines, tick marks (35 rects), and the tick labels + rotated "+/-" ylabel (17 text divs at measured positions, per-artist font sizes). The axes then hides entirely: its baked image is now empty. Layout and hovers unchanged (page height 4032, popups fire).

Done — the combined plot's furniture is HTML, emitted at builder end from the live axes: vertical grid + tick marks at each x tick, horizontal grid + marks at each in-range y tick, the white zero line, the gray left/bottom spines (35 rects via the line_rect pipeline, grid on a below-data z-level to honor axisbelow), plus every tick label and the rotated "+/-" ylabel as text divs at their measured window extents with each artist's own font size (17 divs). With planes, markers, line, legend, and title already converted, the axes carries nothing baked — it hides whole before the render, leaving that slice's image empty. Verified in WebKit: scale values/positions match the published page, grid sits under the planes, minus signs render from the site font, page height and the hover/pin machinery are unchanged. Next: the karma panels (and retiring their scale-strip layer images), then the player grid.

## 2026-08-03 00:00 — "do the karma panels" (furniture)

**Summary:** Both karma panels' furniture is HTML — grid/zero/spines/tick marks as rects, x tick labels + wall-clock times as text divs, and the +/- and Score scales as .fnm/.fns divs wired to Hide +/- / Hide Scores (line and scale hide together). The per-layer render machinery is gone entirely (_layer_band_render, layer_groups, kb-ov images and rules); the karma base image renders empty, kept only for the band's aspect-ratio.

Done — the karma panels' furniture is HTML on both panels:

- **Rects**: vertical grid + tick marks at each x tick, the white zero line, gray left/bottom spines — through the same line_rect pipeline, grid on the below-data z-level.
- **Text**: Q1...END labels and the wall-clock times (from the annotation artists, own colors/sizes), each at its measured position.
- **Scales**: the +/- scale (olive, left) and Score scale (team color, right) — tick marks, numbers, and the rotated ylabels — as .fnm/.fns divs; the existing Hide +/- and Hide Scores switches now hide line AND scale together, exactly like the old layer images did.
- The layer-render machinery is deleted: _layer_band_render, the layer loop, the kb-ov slice divs and CSS are gone. The karma base axes hide before the SVG pass, so the -k image renders empty and survives only to hold the band's aspect-ratio.
- Verified in WebKit: scales match the published page (values, colors, positions), both Hide toggles take the scale along, page height unchanged (4032), hovers intact.

Next: the player-chart grid, then dropping the empty renders altogether.

## 2026-08-03 00:20 — "do the player plots furniture"

**Summary:** All ~20 player charts' furniture is HTML via a shared _emit_furniture helper (also now used by the combined plot and karma bases): grid, zero lines, spines, tick marks, tick labels, and the "+/-" ylabel — 616 rects + 307 text divs page-wide. Every chart axes hides; all base renders are now empty. Bonus fidelity fix: the grid paints over the on-court spans again (matplotlib's axisbelow layering), which the interim HTML spans had been covering.

Done — the player charts' furniture is HTML on every chart of both teams, through one shared helper that now serves the combined plot, the karma bases, and the player grid alike: grid lines and tick marks at the x/y ticks, the zero line (when 0 is in range), gray left/bottom spines, tick labels at measured positions, and the rotated "+/-" label on each team's first chart. Each player axes then hides whole — with that, EVERY rendered band on the page is empty; the SVGs survive only as aspect-ratio placeholders. A small fidelity bonus: the y-grid lines show over the on-court spans again, as matplotlib layered them (the interim HTML spans had been painting over the baked grid). Verified in WebKit: furniture matches the published look, title and stint hovers fire, page height unchanged (4032). Page size 1.10MB -> 1.03MB; the big drop comes next, when the empty renders are dropped altogether.

## 2026-08-03 00:45 — "drop the render machinery"

**Summary:** The SVG pipeline is gone from the game pages: no renders, no data URIs, no band/crop machinery — slice divs are empty boxes keeping their aspect-ratios, matplotlib is layout-engine only. Zero images on the page (verified), layout byte-identical (4032px), page 1.03MB -> 921KB, and the build dropped to ~1.7s/page (the fleet re-render just got an order of magnitude faster).

Done — the render machinery is deleted:

- **Removed**: the _render/_fig_svg call, _apply_band, _crop_svg, _band_render, the band-render loops, the rate-view render pass, the karma pre-hide loop, the renders dict, and the :root data-URI block. _slice_svg became _slice_box: an empty div carrying only the band's aspect-ratio, so the stacked boxes reproduce the figure's vertical layout and every %-positioned overlay lands where it always did.
- **The page now contains zero images** — confirmed by scanning the served page for data URIs. Everything is HTML/CSS text: overlays, furniture, tooltips, box scores.
- matplotlib remains as the layout engine only (gridspec, transforms, extents) — the figure is built, measured, and closed without ever rendering. Page build time fell to ~1.7s.
- Verified in WebKit: karma, players, and Lineups sections pixel-consistent with the previous build, page height unchanged (4032), Hide toggles and the event cycler work, hovers fire. Page size 1.03MB -> 921KB.

## 2026-08-03 01:50 — "fix the rebuild script and do the fleet re-render"

**Summary:** Fixed scripts/rebuild_game_pages.py for the season/team tree (it assumed a flat outputs root) and re-rendered the whole fleet: 2,624 game pages (both seasons — more than the 1,398 quoted earlier), 0 failures, ~3h wall (dominated by ~1,100 cold game-info fetches from the NBA API, now cached forever; the cached stretches ran at ~100+ pages/min). Spot-checked 2024-25 regular season, 2024-25 playoffs, and 2025-26 pages: zero images, site fonts, full HTML overlays, hovers fire.

Done — the fleet is fully re-rendered on the pure-HTML pipeline:

- **Script fix**: rebuild_game_pages.py now walks outputs/<season>/<tri>/csv/pbp_*.csv and writes each page next door in ../html/ (it previously looked for a flat outputs/pbp_*.csv that no longer exists), with the docstring updated for the ~1.7s/page no-render builds.
- **The run**: 2,624 pages across 2024-25 (regular season + playoffs) and 2025-26, 8 workers, 0 failures. The fleet turned out to be nearly double the 1,398 figure quoted earlier. Most of the wall time went to ~1,100 games whose game-info (matchup/date/venue header) wasn't in the local cache yet — each hit the NBA API once and is now cached in ~/.cache/nba_pbp, so the next full re-render runs at CPU speed end to end (~15 min).
- **Spot checks in WebKit**: OKC/DEN (2024-25), BOS/ORL (2024-25 Finals-format playoff id), CHA/GSW (2025-26) — no data URIs on any page, DejaVu site fonts load, karma/player/lineups overlays present in full, hover popups fire.
- Every game page on the site now ships the complete conversion: HTML data layers, HTML furniture, zero images, shared site fonts.

## 2026-08-03 01:55 — "push and publish"

**Summary:** Pushed main (ac60da3a..55388137) and force-pushed gh-pages (c35ce1ec) — the fully image-free site is live: all conversions, site fonts, and the 2,624-page fleet re-render.

Pushed and published. main ac60da3a..55388137; gh-pages force-updated to c35ce1ec with the rebuilt stage. Live: the complete HTML conversion (karma lines/bars/lanes/events, player plots, combined plot, furniture and scales everywhere), the shared DejaVu site fonts, box-score folds and team-colored titles, and all 2,624 game pages re-rendered with zero images.

## 2026-08-03 02:00 — "whats left in image format"

**Summary:** Q&A — nothing. Zero images site-wide: all 2,624 game pages are pure HTML/CSS (matplotlib is layout-only at build time), team/season pages never had images, help/index are text. Only non-site entry points still use the old SVG helpers.

Nothing. As of this publish, no page on the site contains a single image: the game pages (all 2,624) have no data URIs, no img tags, and no background images — every panel's data, furniture, scales, and labels is HTML/CSS, with matplotlib surviving only as an invisible layout engine at build time. The team and season pages were born pure HTML/CSS, and help/index are text. The only image-producing code left in the repo is the old _fig_svg/data-URI helper pair, used by non-site entry points.

## 2026-08-03 02:20 — "stop rebuilds for now, only build OKC/HOU 10/21/25 while we focus on games pages"

**Summary:** Killed the running fleet re-render (~555 of 2,624 pages had picked up the karma-title fold; the rest are one change behind). New routine while focused on game pages: rebuild only the showcase (0022500001), commit with plain git, no ship/staging. Before the next publish: full fleet re-render (~15 min, cache warm) + both seasons' team/season pages + stage.

Stopped — the fleet rebuild is killed and rebuilds are paused. While we focus on game pages, each change rebuilds only OKC/HOU 10/21/25 (game 0022500001, the showcase). Note the fleet is now MIXED: about 555 pages carry the karma-title fold, the other ~2,070 are one change behind; before the next push and publish I'll run the full fleet re-render (warm cache, ~15 minutes), rebuild both seasons' team/season pages, and restage. Logged in memory so the routine sticks.

## 2026-08-03 02:22 — "the karma plots use the first line as a show/hide for the plots"

**Summary:** The karma titles are folds now — clicking "HOU Karma" / "OKC Karma" collapses that panel to its title strip (controls stay on the line, the box score below slides up); click again restores. Verified with real mouse clicks both ways, panels independent. Showcase only (fleet paused per the focus-phase routine).

Done — clicking a karma plot's first line (the "TRI Karma" title) now hides/shows that plot: the title became a fold summary, and closing it collapses the panel to its title strip — the title and the No Events / Hide switches stay on their line, and the page reflows so the box score slides up underneath. Clicking again restores the plot. Each panel folds independently. Verified in WebKit with real clicks; built on the showcase page only.

## 2026-08-03 02:35 — "get rid of the show/hide for OKC/HOU"

**Summary:** Removed the team section toggles ("▼ HOU" / "▼ OKC" headers) — redundant now that each karma title folds its own plot. The team sections always show; Summary, Players, and Lineups keep their toggles. Showcase only.

Done — the OKC/HOU section show/hide headers are gone: the team sections always display, since clicking the karma title now does the per-plot folding. The page flows from the linescore into Summary and straight into the HOU Karma panel. The Summary, Players (x2), and Lineups section toggles are untouched, and both karma title folds still work. Built on the showcase page only, committed without staging per the focus-phase routine.

## 2026-08-03 02:50 — "karma plot should not drop down one line when clicked, remove score,+/- axis label"

**Summary:** Fixed the fold jump — the title line was %-anchored to the collapsing kbox, so it moved one line per click; it now sits at a fixed cqw offset (and the closed strip sizes per panel via --kbmh), title pixel-stable across open/close/reopen. Removed the karma panels' rotated "Score" and "+/-" axis labels; the scale numbers stay. (A suspected lane-color regression in a screenshot turned out to be the player-stint hover highlight under the resting test mouse.)

Done — both fixes on the showcase page:

- **No more one-line jump**: the title line (title, Hide switches, event cycler) was positioned as a percentage of the kbox height, which collapses when the fold closes — so everything shifted a line on each click. The line now anchors at a fixed cqw offset computed from the band geometry, and the folded strip takes its height from the same number (per-panel --kbmh), so the title stays pixel-identical through open -> closed -> reopened (measured 416/416/416).
- **Axis labels removed**: the karma panels' rotated "+/-" (left, olive) and "Score" (right, team color) labels are gone; the tick numbers keep working and still hide with their Hide switches. The combined plot's and player charts' "+/-" labels are untouched.

## 2026-08-03 03:00 — "box score plot title line font/size should match karma plot size"

**Summary:** The team box score fold titles now wear the karma title's face — DejaVu Sans at the shared title size/weight instead of the table's mono; computed styles verified identical (19.68px, weight 300) on both titles.

Done — the "HOU box score" / "OKC box score" title lines now use the same font and size as the karma plot titles: DejaVu Sans at the shared title cqw and weight, replacing the box score's monospace. Verified in WebKit that the karma and box titles compute to identical font, size, and weight; the fold click, team-colored tricode, hover cue, and per-32 switch are unchanged. Showcase only, committed without staging.

## 2026-08-03 03:05 — "same thing for lineup box score titles"

**Summary:** No change needed — the Lineups box score titles already use the shared title CSS (DejaVu Sans + title cqw/weight); computed styles measure identical to the karma title (19.68px, 300). All three title kinds now match.

Nothing to change — the "TRI Lineups box score" titles were already built on the shared title style (.lineup-box-title carries DejaVu Sans plus the same _TITLE_FONT_CSS the karma title uses), and WebKit measures them pixel-identical to the karma title: same face, 19.68px, weight 300. With the team box score titles fixed in the previous request, every title line on the page — karma, box score, lineups — now shares one font and size.

## 2026-08-03 03:12 — "make +/- axis ticks font size match score"

**Summary:** The karma +/- scale's tick numbers dropped from 9pt to 7pt to match the Score scale — changed at the source (ax_m tick_params), so the measured HTML emission followed; both scales compute to 14.58px on the page.

Done — the karma panels' +/- tick numbers now match the Score scale's size: the axis declares 7pt like the Score axis, and since the HTML furniture takes each label's measured size, both scales render identically (14.58px computed on the page, minus signs intact). Showcase only, committed without staging.

## 2026-08-03 03:25 — "stretch karma plot to start at left edge"

**Summary:** The karma panels now span from the page's left edge to the Score scale — the axes reposition to x0=0 before any twin is created, the +/- tick numbers moved inside the plot (direction in, ha left), and their tick marks point inward; every HTML layer followed automatically via the live transforms.

Done — the karma plots stretch to the left edge: the panel axes detach from the gridspec margin and reposition to x0=0 before the twins are built, so every overlay axis (and therefore every HTML layer — lanes, bars, lines, glyphs, grid, spines) inherits the wider geometry with no further changes. The +/- scale lives inside the plot now: labels left-aligned just right of the spine (olive, same 7pt-derived size as Score), tick marks pointing inward — nothing hangs off-page. The Score scale, title line, fold, and readouts are unchanged, and the Q1 tick label with its wall-clock time still renders fully at the edge. Showcase only, committed without staging.

## 2026-08-03 03:40 — "stretch karma plot to start at left edge of axis tick label, +/- tick labels outside plot areas, left edge aligns with box score left edge"

**Summary:** Reworked the stretch: the +/- tick labels are back OUTSIDE the plot, their left edge aligned to the box score's left margin (pixel-exact: both at 87px), and the plot spine starts just right of the label block. The panel computes the widest label analytically (renderer text metrics, no draw) and repositions before the overlay twins are created, so every HTML layer follows.

Done — the karma panels now start at the box score's left edge: the +/- tick numbers sit outside the plot with their left edge on the box score margin (measured pixel-identical, 87px both), the spine begins just right of the widest label plus tick pad, and the plot runs from there to the Score scale. The label-block width comes from renderer text metrics at build time — no extra draw — and the repositioning happens before ax_p and the overlay twins exist, so lanes, bars, lines, glyphs, and furniture all inherited the geometry untouched. Tick marks point outward again. Showcase only, committed without staging.

## 2026-08-03 03:50 — "karma plot title line left edge aligns with left axis"

**Summary:** The "TRI Karma" title now left-aligns with the panel's left spine — the spine fraction rides the slice dict into the title's inline left, replacing the stale 7.6% class default. Measured pixel-identical (134.8px both).

Done — the karma title lines align with the left axis: each panel records its repositioned spine x, and the title summary uses it as an inline left, overriding the old fixed 7.6% (which matched the pre-stretch gridspec). WebKit measures title and spine at the same 134.8px on both panels. Showcase only, committed without staging.

## 2026-08-03 03:58 — "karma plot title line left edge aligns with left edge of axis labels"

**Summary:** The karma title moved from the spine to the axis labels' left edge (the box score margin the +/- numbers align to) — title and label block measure identical at 87.2px.

Done — the "TRI Karma" titles now left-align with the +/- axis labels instead of the spine: the title's inline left is the box score margin the labels sit on, and WebKit measures title and label-block left edges pixel-identical (87.2px). So the title, the axis numbers, and the box scores below all share one left edge. Showcase only, committed without staging.

## 2026-08-03 04:10 — "box score has an additional line before it that separates kearm /box score"

**Summary:** Tightened the karma-to-box-score gap by one line: .bx-flow margin dropped from two box lines to one (55.4px -> 27.7px) and the fold title's line box tightened (line-height 1.15, 29.5px -> 22.6px). The removed line turned out to be the hover-readout clearance, so the karma readouts got a solid black backdrop — they now paint legibly over the title when a lane hover fires, and the title returns when the hover ends.

Done — the extra line between the karma plot and the box score is gone: the box score now sits one box line under the panel (was two), and the enlarged fold title no longer inflates its line box. Investigating first paid off — that second line was originally clearance for the karma stint-hover readouts that hang below the panel, and removing it made them collide with the title mid-hover. The fix keeps the tight layout and gives the readouts a black backdrop, so during a hover the readout paints cleanly over the title line and everything returns when the pointer leaves. Verified in WebKit: gap halved, readouts legible over the fold title, box score undisturbed. Showcase only, committed without staging.

## 2026-08-03 04:18 — "get rid of hide/show for lineups"

**Summary:** Removed the Lineups section toggle — the combined Lineups section (box scores + plot) always shows now; remaining section toggles are Summary and the two Players. The lineup box score titles keep their own folds.

Done — the Lineups show/hide is gone: the section renders directly (combined plot visible, "Lineups" plot title in place), with only Summary and the two Players sections still behind toggles. The lineup box score title folds are untouched for per-table collapsing. Showcase only, committed without staging.

## 2026-08-03 04:35 — "change Lineups title line to HOU vs/@ OKC Lineups, make it hide just show/hide title like others, hidden area is start of first pop up area to end of last pop up area"

**Summary:** The combined plot's title is now a flow-line fold reading "HOU @ OKC Lineups" (tricodes in brand colors, vs/@ by home court) sitting between the upper lineup table and the popup band; clicking it hides exactly the img-box — first popup area through last popup area — leaving both tables and the title. Fix along the way: the upper .lineup-box (relative, z2, negative margin) overlapped the title and ate clicks until the title got z3.

Done — the Lineups title line reads "HOU @ OKC Lineups" (HOU red, OKC blue; it would say "vs" if the first team were home) and folds like the karma and box score titles: clicking hides the stretch from the start of the first popup area to the end of the last one — precisely the section's img-box, which holds the upper readout band, the plot, and the lower readout band — while the two lineup box scores and the title itself stay put. The old in-plot "Lineups" title is gone (its baked Text was already hidden with the axes). One catch fixed during verification: the upper lineup table's container overlays the title line (relative z-index:2 with a negative bottom margin from the popup-gap work), so the title needed position:relative;z-index:3 before real clicks landed. Verified in WebKit: fold closes/reopens by mouse, the hidden region is exactly the popup-to-popup band, pins and popups work while open. Showcase only, committed without staging.

## 2026-08-03 04:42 — "the OKC@HOU title should sit on the left edge"

**Summary:** The "HOU @ OKC Lineups" title now sits on the container's left edge — the stray offset was .ktitle's left:7.6% still applying once the summary went position:relative; left and margin both zeroed, measured flush (title 50 == container 50).

Done — the Lineups section title sits on the left edge: it had inherited .ktitle's left:7.6% (which acts as a relative shift once the summary became position:relative for the z-order fix), plus the box-margin indent I'd given it. Both zeroed; WebKit measures the title's left edge exactly at the chart container's left edge. Showcase only, committed without staging.

## 2026-08-03 04:52 — "place the blue hide/show arrows like on Summary to all openable/closable title lines"

**Summary:** Every foldable title line now carries the Summary-style blue disclosure arrow (open/closed states) — karma titles, team box score titles, lineup box score titles, and the Lineups section title.

Done — all four foldable title kinds show the blue arrows the Summary line uses: down-arrow while open, right-arrow when folded, in the Summary blue, rendered from the site font's own glyphs. Applied via ::before rules per fold class (karma, box score, lineup box score — scoped so the box fold doesn't double up from its shared class — and the Lineups section title). Verified all four on the showcase page. Committed without staging.

## 2026-08-03 04:58 — "hou @ okc Lineups should start on the left side same place as OKC box score"

**Summary:** The "HOU @ OKC Lineups" title moved from the container edge to the box score margin — its left edge now measures identical to the box score titles (87.2px both).

Done — the Lineups section title starts where the box score titles do: its margin is the shared box score left margin, and WebKit measures the title and the "OKC box score" title at the same 87.2px. Showcase only, committed without staging.

## 2026-08-03 05:15 — "the player plots axis range is +15/-15. the plots go in a tabbed display where each tab name is the player last name and the plot is in the tab content" + "plot height should be the same for all players"

**Summary:** Player charts now share a fixed +/-15 y-range (HTML layers clamp the curve and skip out-of-range glyphs/dots, matching matplotlib clipping), and each team's players section is a pure-CSS tabbed display: a last-name tab bar (dim, active lit) over one fixed-height pane — a window shifted across the full chart grid, every pane the same height (the tallest band).

Done — both changes on the showcase page:

- **Fixed range**: every player chart runs -15..+15 (ticks every 5); the stint +/- curve clamps to the range and out-of-range event glyphs and entry/exit dots are skipped, mirroring what matplotlib's clipping did.
- **Tabs**: the players sections are tabbed — hidden radios hold the active player, the bar lists the players (the chart names, e.g. Sengun / Durant / Smith Jr.), and the pane is an overflow-hidden window slid over the chart grid by generated per-tab margins. Pane height is uniform across all players (the tallest mid-gap band). Hover readouts and stint hovers ride along inside the window. Verified with real clicks in WebKit: default Sengun, switching to Durant swaps the pane and lights the tab, both team sections tabbed.

## 2026-08-03 05:25 — "change tab same size plot as player, players name in tab is player color in plot, axis fonts are same as karma"

**Summary:** Player tabs polished: names at the plot-title size (19.68px, same as the in-plot player name), each tab in its player's chart color (dim 55% until active), and the player charts' y tick labels dropped to the karma scale's 7pt.

Done — the tab bar now mirrors the plots: each name renders at the same size as the player title inside the chart, in that player's chart color (Sengun cyan, Durant red, ...), dimmed to 55% until selected and full-strength when active. The player charts' y-axis numbers now match the karma +/- scale size (7pt; the x ticks were already karma's 8pt). Verified computed styles in WebKit: tab font == title font, tick font == karma tick font. Showcase only, committed without staging.

## 2026-08-03 05:32 — "change players to HOU Players as the collapse title for the players plot"

**Summary:** The Players section collapse titles now name the team — "HOU Players" / "OKC Players", tricode in brand color, same text whether open or closed (previously "Players" closed / "Less" open).

Done — the players sections collapse under team-named titles: "HOU Players" and "OKC Players", each tricode in its brand color with "Players" in the section blue, and the text no longer flips to "Less" while open (the arrow alone shows the state). Verified both sections on the showcase page. Committed without staging.

## 2026-08-03 05:40 — "okc players hide/show should left align with OKC boxscore"

**Summary:** The Players section summaries indent to the box score margin (padding-left override on a .pmore class; first attempt lost the cascade to the base .more rule and moved after it) — the blue arrows of "HOU/OKC Players" now start at the same 87px as the box score and karma title arrows.

Done — the Players collapse lines align with the box score titles: the players sections' details carry a .pmore class whose summary padding is the shared box score margin, so their arrows start in the same column as the karma and box score title arrows (87px measured). One cascade fix on the way: the override initially sat before the base .more>summary rule and lost at equal specificity. Verified both team sections on the showcase page. Committed without staging.

## 2026-08-03 05:50 — "unnessacry gap between OKC Players and HOU should have uniform pad between closed plots/boxes"

**Summary:** Measured all closed-state gaps between title lines (34/0/23/34/0/116/8/5) — the 116px band between the closed Players section and the Lineups block was the upper lineup table's 4-box-line margin left over from the pre-tab layout; reduced to one box line, bringing it to 32px and in rhythm with the rest.

Done — with everything folded the page reads as a compact index: Karma line, box score line, Players line per team, then the Lineups block, at near-uniform pads (34/23/32/34 between sections). The offender was the upper lineup box score's margin-top of four box lines, clearance designed for the old stacked player grid; it's one box line now, matching the karma-to-box-score spacing. Verified by measuring every consecutive title-line gap in the fully-collapsed state. Showcase only, committed without staging.

## 2026-08-03 06:05 — "remove +/- from player plot, make box score lines popup always on by initial tab selection is player 1 in player list" + "make OKC Players team colors"

**Summary:** Player charts lose the "+/-" ylabel; the active tab's player shows their box score line (header + row, player color) permanently under the tab bar — suppressed while a pane hover shows another readout — with tab 1 the default as before; and the "TRI Players" section titles are fully team-colored ("Players" included).

Done — three changes on the showcase:

- **No "+/-" label** on the player charts (the ylabel is gone; the tick numbers remain).
- **Always-on box score line**: whichever player's tab is selected shows their full box score line (the header and their row, in their chart color) pinned above the plot — no hover needed. Hovering a stint still swaps in that stint's readout cleanly (the always-on line steps aside while any pane readout is hovered), and the initial selection stays player 1. Wired per tab via a ptt-{team}-{i} class on the title readouts.
- **Team-colored section titles**: "HOU Players" / "OKC Players" render entirely in the team's brand color.

## 2026-08-03 06:20 — "panels in Players tabs clipped at top on every panel"

**Summary:** The tab panes clipped the always-on readout — the pane bands started at the chart mid-gap while the readout block lifts itself a full two box lines above its anchor. Bands now start above each chart's readout anchor by the readout's own height (2 box lines + air); header, player row, title, and chart all render on every tab.

Done — the pane windows no longer clip: each tab's band starts above that chart's readout anchor by the readout's height (the .tt-line block anchors its BOTTOM at label_top and rises two box lines above it, which the mid-gap band tops cut off). Verified on the default Sengun tab and Thompson: the stats header, the player's row, the title, and the full +/-15 chart all show. Showcase only, committed without staging.

## 2026-08-03 06:30 — "durant's box score lines in player panel start one line lower than panels for all other HOU players"

**Summary:** The inconsistency was tab 0, not Durant — the first chart's band reached above the slice's content start, so Sengun's readout sat one line higher (and 8px clipped) than everyone else's. The players slice top now extends to the first chart's readout headroom; measured all 20 tabs across both teams at exactly +13px.

Done — the panels are uniform: the odd one out was actually the first tab (Sengun), whose band started above the slice content (his readout rode 21px higher and lost 8px to the window edge), making every other player's panel look one line lower. The players slice now begins at the first chart's readout headroom, so band offsets clamp cleanly; every tab on both teams measures the readout at exactly 13px from the pane top. Showcase only, committed without staging.

## 2026-08-03 06:50 — "plot order game page: HOU Karma, HOU Box score, HOU Players, HOU Lineups Box score, HOU @/vs OKC Lineups, OKC Lineups Box score, OKC players, OKC Box score, OKC Karma"

**Summary:** The page now mirrors around the Lineups block: HOU (Karma, box score, Players), the Lineups section (HOU table, combined plot, OKC table), then OKC reversed (Players, box score, Karma — box above karma). Slices assemble as pairs (second team reversed, box_first flag flips the section internals); the figure-band geometry is untouched, only the stacking order changed.

Done — the game page reads in the requested mirror order: HOU Karma, HOU box score, HOU Players, HOU Lineups box score, HOU @ OKC Lineups, OKC Lineups box score, OKC Players, OKC box score, OKC Karma. The team slices now assemble as per-team pairs with the second team's pair reversed and its karma/box section emitted box-first; since every slice carries its own figure-band fractions, reordering the stack changes nothing inside the panels. Verified the collapsed index reads top-to-bottom in the exact order and the open OKC section renders box score over a fully-working karma panel. Showcase only, committed without staging.

## 2026-08-03 07:05 — "default to hide/show controls is closed, visual separation for all closed title lines is uniform"

**Summary:** Every fold (karma, box scores, lineup box scores, Lineups section) now defaults CLOSED — the page loads as the compact title-line index — and the closed-state gaps were normalized: the three outliers (0, 8, 5px) moved to 18/27/27 via a margin above the first team's Players section and uniform margins around the Lineups title; the full set now reads 34/18/32/27/27/22/28/23.

Done — the page opens as the folded index: all hide/show controls start closed (karma plots, team box scores, lineup box scores, and the Lineups section; the Players sections and Summary already defaulted closed). The separations between consecutive closed title lines are even now — the flagrant ones were the zero gap between a folded box score and the Players line and the 5-8px squeezes around the Lineups title, fixed with a 1.4cqw margin above the first Players section and 1.65/1.9cqw margins around the Lineups title line. Measured the full run of gaps top to bottom: 34/18/32/27/27/22/28/23. Showcase only, committed without staging.

## 2026-08-03 07:20 — "no bright whites, align Summary with other titles, Summary becomes ESPN Update"

**Summary:** Title-line whites muted to #9BA3AD (the karma/lineups title gray, the box score fold titles, and all fold hover cues — no more #fff flashes); the Summary section renamed "ESPN Update" (same text open/closed) and indented to the shared title column via the pmore class.

Done — three changes: every title line's non-team text now sits at the muted #9BA3AD (the "Karma"/"Lineups" words already used the panel gray, the box score fold titles dropped their bright #e0e0e0 via a .bx-head override, and the hover cues went from white to a soft #c9ced4); the Summary toggle reads "ESPN Update" in both states; and it aligns with the rest of the title column (its arrow in the same 87px column as the karma/box/players lines). Verified on the folded index. Showcase only, committed without staging.

## 2026-08-03 07:35 — "all bright white through out the document" / "get rid of"

**Summary:** Document-wide muting: the header/linescore mono block (#d3d3d3), box score body (#c0c0c0) and header rows (#e0e0e0), hover readout text, the recap, and the marker highlight ring (white -> soft #c9ced4) all moved to the muted #9BA3AD family. Translucent furniture (the 30%-alpha zero/grid lines) stays; another page's pinned-line white in the same file was left alone.

Done — no bright whites remain on the game page: the matchup/date/linescore header, every box score's body and header text, the hover readouts, the ESPN recap text, and all fold titles now sit in the muted gray, and the marker highlight ring softened from pure white to a gentle silver. The colored content — tricodes, player names, gold/red stat highlights, the control blues — now carries the contrast hierarchy alone. Showcase only, committed without staging.

## 2026-08-03 07:45 — "team name + description on hidden plot/box is all that show when in closed mode"

**Summary:** Folded plots/boxes now show only their title line — the karma Hide switches and event cycler hide with the plot, and the per-32 / per-8 switches hide with their tables; all controls return when the fold opens.

Done — closed mode is titles-only: a folded karma plot shows just "TRI Karma" (the No Events cycler and the four Hide switches go with the plot), a folded box score shows just "TRI box score" (Show per 32 hides), and a folded lineups box score likewise drops its Show per 8. The controls reappear the moment a fold opens (verified both ways in WebKit). The all-folded page is now purely the title index. Showcase only, committed without staging.

## 2026-08-03 07:50 — "how big is this page"

**Summary:** Q&A — the showcase page is 922KB raw but 79KB gzipped (GitHub Pages serves compressed); pure-markup pages compress ~12:1. Plus the 46KB shared fonts, cached once site-wide. Down from 1.65MB (with far worse compression) before the HTML conversion.

The showcase page is 922 KB on disk but only 79 KB over the wire — it's repetitive HTML/CSS markup that gzips about 12:1, and GitHub Pages serves it compressed. The shared DejaVu fonts add 46 KB, downloaded once and cached for all 2,624 game pages. Before the image-to-HTML conversion the page was 1.65 MB of SVG data URIs, which compress far worse, so the real transfer dropped from roughly 1 MB to under 100 KB.

## 2026-08-03 07:55 — "whAT DOES 79K delivered mean?"

**Summary:** Q&A — "delivered" = bytes actually sent over the network: GitHub Pages gzips the file before sending (browsers request and unpack compression automatically), so the 922KB file travels as 79KB; download time follows the 79, memory/rendering the 922.

"Delivered" means what actually travels over the network. Browsers tell the server they accept compressed responses; GitHub Pages runs the file through gzip before sending, and the page's highly repetitive markup squeezes 922 KB down to 79 KB — that's what crosses the internet and determines load time. The browser unpacks it back to 922 KB to render. Both ends do this automatically; nothing in the pages is involved. It's also why the old SVG pages were costlier: base64 image data barely compresses, while plain markup shrinks ~12x.

## 2026-08-03 — Sanity-critic verification of storage-reduction findings (subagent)
Re-verified the analysts' top claims against pm_players_0022500001.html (944,275 B raw / 77,315 B gz9). Confirmed: percent-rounding (1-dec: ~-46 to -55 KB raw, -9 to -10 KB gz, max err 0.60px @1200px; 2-dec: -32 KB raw, -3.9 KB gz, max 0.06px), color/background class-hoist (-84.4 KB raw, gz flat), top-10 decl extraction (-75.5 KB raw, gz +640 B WORSE). Flagged triple-counting of the class-hoist and decimal-trim levers across analysts, double-counting of the tooltip-header dedup, and a scope bug: 4 of the 212 "Player..." headers are visible .bxs box-score headers (plus 4 lu-table "Lineup..." headers) that must NOT be stripped. Built and browser-verified a conservative combined transform (header ::before dedup + drop zero-size decls + color hoist + ppl var(--r) + 2-dec + safe whitespace + semicolon trim): 944,275 -> 731,841 raw (-22.5%), 77,315 -> 71,614 gz (-7.4%); aggressive 1-dec variant: 709,372 raw (-24.9%) / 65,935 gz (-14.7%). Fleet extrapolation ~2.12 GB -> 1.64-1.70 GB. Layer claims spot-checked and confirmed (.git 305M, gh_pages_dist 303M, outputs 2.3G, 412 gh-pages reflog entries). Verified copies: scratchpad/critic_combined_safe.html, critic_combined_1dec.html.

## 2026-08-03 08:10 — "HOU players title line font does not match other title line fonts, space from line to line should be uniform."

**Summary:** The section summaries (ESPN Update, TRI Players) now use the shared title font (19.68px weight 300, was 1.8cqw normal), and the line-to-line spacing was tuned to genuine uniformity — all nine closed-state gaps now measure 27-28px (was 23/34/18/32/27/27/22/28/23) via per-contributor margins (kbox top margin, folded-strip tail trim, per-team players margins, lineup-table margin).

Done — every title line shares one font (face, size 19.68px, weight 300; the section summaries had been 10% larger at normal weight), and the vertical rhythm is uniform: measuring each consecutive closed title-line gap top to bottom now gives 27/28/28/27/27/27/27/28/27. Each deviation was fixed at its own source: +4px above both karma sections, the folded karma strip's tail trimmed, the two players sections' margins set per team, and the lineup table margin eased. Showcase only, committed without staging.

## 2026-08-03 08:25 — "how can we make the storage per game lower?"

**Summary:** Ran a 5-agent measured audit (byte profile, micro-markup, structure, storage layers, sanity critic; every claim tested on transformed copies, the combined file browser-verified). Ranked plan: (1) free local wins ~580MB (gh-pages reflog gc ~280MB + drop the gh_pages_dist duplicate ~300MB); (2) generator bundle, verified -22.5%/page (2-decimal coords, color class-hoist, var(--r) rotations, scoped ::before stats header, zero-decl drop) -> fleet 2.12GB -> ~1.65GB, needs a ~15min re-render; optional 1-decimal variant -25% disk/-15% transfer after a seam check; (3) APFS transparent compression (~2GB allocated) OR tar.gz the frozen season + gzip CSVs. Not worth it: per-32/per-8 duplicate tables (required by pure CSS — verified) and the SVG-layer rewrite (unproven, high effort). The critic flagged analyst double-counting and a header-strip scope bug that would have corrupted box scores.

The page is ~80% geometry divs (karma lines 23%, event glyphs 17%, player segments 17%, bars 8%); inline styles are 51% of the file and coordinate digits are what gzip can't squeeze. Ranked: (1) ~580MB free — expire the gh-pages reflog (305MB .git -> ~25MB) and stop keeping gh_pages_dist; (2) plotting.py bundle, browser-verified at -22.5% per page (944 -> 732KB; fleet ~1.65GB): 2-decimal coordinates, ~40 inline colors hoisted to value-classes, rotate(var(--r)), the 100-byte stats header as a scoped ::before (212 copies -> 1), zero-size declarations dropped; 1-decimal opt-in reaches -25% disk/-15% transfer pending a seam check at 900px; (3) APFS decmpfs on outputs/ (~2GB) or archive 2024-25 + gzip CSVs — one path, not both. No savings exist in the per-32/per-8 duplicate tables without JavaScript, and the inline-SVG idea stays parked until a one-layer prototype proves its ~350KB estimate.

## 2026-08-03 08:50 — "do low risk generator bundle"

**Summary:** Implemented the audit's verified storage bundle in plotting.py: 2-decimal overlay coordinates, ~40 repeated inline colors/sizes hoisted to generated value-classes (emitted last in <style> to win order ties), ppl rotations via one rotate(var(--r)) rule, the 100-byte stats header emitted once as a ::before scoped to tooltip readouts (real table headers untouched), and zero-size width/height dropped on line segments. Showcase: 922KB -> 734KB raw (-20.4%), 79KB -> 70KB gzipped (-11%). Verified in WebKit: hoisted colors resolve, rotations compute, headers align, tables intact, hovers/pins/folds all working.

Done — the low-risk generator bundle is in, matching the audit's browser-verified numbers: the showcase page dropped from 922KB to 734KB on disk (-20.4%) and 79KB to 70KB gzipped (-11%). The changes, all in the single writer plotting.py: overlay coordinates emit at 2 decimals (max drift 0.06px at the frozen layout); every repeated inline background/color/font-size registers a short value-class through a page-level registry whose rules are appended at the end of the style block; the player-curve segments carry only --r custom properties with one shared rotate(var(--r)) rule; the box score column header — previously repeated verbatim in over 200 hover readouts — is one CSS ::before content string scoped to the tooltip classes (the critic's scope warning heeded: the real box score tables keep their header rows); and zero-width/height declarations vanish behind the .khl 1px floors. Verified in WebKit: colors, rotations, readout headers, table headers, hovers, pins, tabs, and folds all behave identically. Fleet projection once re-rendered: 2.12GB -> ~1.69GB. Showcase only per the focus phase — the fleet re-render (now several changes behind) stays queued for before the next publish.

## 2026-08-03 09:30 — "build locally"

**Summary:** Full local fleet re-render: 2,624 pages, 0 failures, ~22 min at 8 workers (warm game-info cache, ~110 pages/min). Fleet now carries every focus-phase change including the storage bundle: avg 640KB/page (was 788), total 1.72GB (was 2.12GB, -19%). Spot-checked a 2024-25 regular-season page, the ORL playoff page, and a 2025-26 page in WebKit: zero images, hoisted colors resolve, rotations compute, readout headers render, folds and tabs present. (One probe initially hit a wrong hardcoded path and read a 404 as an empty page — the real file was fine.) Local only: no staging, no publish; memory updated to fleet-current.

Done — the local build is complete: all 2,624 game pages rebuilt with the current generator in ~22 minutes (the game-info cache made it pure CPU work), zero failures. The fleet-wide effect of the storage bundle matches the showcase projection: average page 788KB -> 640KB, total 2.12GB -> 1.72GB on disk. Spot checks across seasons and game types confirm the pages render with the full focus-phase feature set. Nothing was staged or published; before the next push and publish only the team/season page rebuilds and staging remain.

## 2026-08-03 09:50 — "back to our spot light page ... light stint background color 75%"

**Summary:** The player plots' on-court stint background alpha raised from 30% to 75% (player color, BF) — the band reads bright behind the black +/- curve. Showcase only.

Done — back on the showcase: the player charts' on-court stint background now renders at 75% alpha in the player's color (was 30%), making the on-court band bright and unmistakable behind the black curve. Note the glyphs in the player's own color sit on a same-hue background now — say the word if they need an outline or darker tone. Showcase only, committed without staging.

## 2026-08-03 09:55 — "make it 15%"

**Summary:** Player on-court stint background alpha dialed from 75% down to 15% — a subtle tint behind the curve; glyphs and grid read clearly again. Showcase only.

Done — the on-court stint background now sits at 15% alpha (player color, was briefly 75%): a quiet tint marking the on-court stretches while the curve, glyphs, and grid stay fully readable. Showcase only, committed without staging.

## 2026-08-03 10:20 — "change to 8%, allow multi select on tabs so you can plots on top or another and you can see through them"

**Summary:** On-court stint tint to 8%; the player tabs are MULTI-SELECT now — checkboxes instead of radios, each player's chart lives in its own absolutely-positioned group shifted to the shared pane, so checked players overlay in one viewport. Curves render in the player's color at 80% alpha (black would be indistinguishable overlaid), furniture is one shared base layer from chart 0, and with 2+ selected the in-chart names and always-on box lines step aside (tab colors identify the curves). Single-select view unchanged apart from the colored curve.

Done — three things: the on-court background dropped to 8% alpha; the tab bar multi-selects (click more names to add their plots; click again to remove — the first player starts checked); and selected plots overlay in the same pane, see-through: each player's spans, curve, glyphs, and dots live in a per-player layer aligned to one viewport, with curves now in the player's color at 80% alpha so overlapping lines read distinctly and blend where they cross. The chart furniture renders once as a shared base (every chart's geometry is identical), and when two or more players are selected the in-chart name and the standing box-score line hide — the lit tab colors name the curves — while stint hovers still pop their readouts. Storage note: emitting furniture once per team instead of per chart also trims the page further. Showcase only, committed without staging.

## 2026-08-03 10:45 — "on players multi select box score player lines should grow to stack when more than one are selected, thinner line for player"

**Summary:** The standing box-score lines moved from the pane's absolute headroom into a normal-flow stack between the tab bar and the pane: one shared header plus one row per checked player, packing with the selection (grows/shrinks, no gaps). Player curves thinned 3.2pt -> 2pt, which also reads better in overlays.

Done — selecting players now grows a compact box-score stack under the tab bar: the column header appears once and each checked player contributes their row in their color, with hidden rows leaving no hole (normal document flow does the packing that absolute positioning couldn't). The old absolute standing-line machinery and its multi-select suppression are gone — the stack IS the multi behavior, and it works identically with one player. The player +/- curves are thinner (2pt, was 3.2pt), which sharpens the multi-select overlays. Verified with real clicks: one row for Sengun alone, four stacked rows and four distinguishable translucent curves with Durant, Thompson, and Adams added. Showcase only, committed without staging.

## 2026-08-03 11:05 — "the adding player box score list should update when stint is moused over"

**Summary:** The flow stack is live: hovering a stint swaps that player's row from the full-game line to the stint's own line (and back on mouse-out) via per-stint hover keys on the pane cells and swap rules on the stack; the old floating stint readout inside the pane is retired for player charts — the stack is the single readout surface.

Done — mousing over a stint now updates the box score list: the hovered player's row in the stack switches from their full-game line to that stint's line, in their color, and reverts when the pointer leaves; other selected players' rows stay put. Each hover cell carries a per-stint key and the stack holds hidden per-stint alternates that the hover reveals, so it's all pure CSS. The old floating readout that used to pop inside the pane headroom is gone for player charts — the stack above the pane is now the one readout surface, in single and multi select alike. Verified with a real hover: Sengun's 49-minute game line swapped to the 6-minute stint line and restored on mouse-out. Showcase only, committed without staging.

## 2026-08-03 11:15 — "non standard gap between last players box score extract and plot"

**Summary:** The pane's top headroom (two box lines reserved for the retired floating readouts) was the dead gap between the stack and the chart — the band pad shrank to a small air gap, and the plot now sits directly under the last stacked row.

Done — the odd gap between the box score extract and the plot was the pane's leftover readout headroom: each band reserved two box lines above the chart for the floating hover readouts that moved into the flow stack. The pad is now just a sliver of air, so the chart follows the last stacked row at the page's standard spacing. Showcase only, committed without staging.

## 2026-08-03 11:40 — "thinner line, mouse over any stint thats shown, not just top, full or partial, updates shown box lines"

**Summary:** Player curves thinned to 1.2pt, and the pane hover reworked: a shared interval layer partitions the timeline at every stint edge, each cell carrying the key of EVERY stint crossing it — so one hover swaps every shown player's row at once (full or partial overlap), instead of only the topmost stacked cell winning. The retired per-player pane cells are gone entirely.

Done — two changes: the player +/- curves are thinner still (1.2pt), and hovering anywhere in the pane now updates every shown player's box line, not just the top layer's. The old per-player hover cells stacked on top of each other, so only one could receive the pointer; they're replaced by one shared interval layer — the timeline partitions at every stint boundary and each interval cell lists all the stints that cross it, firing every matching row swap through the same pure-CSS keys. Verified with a real hover on the opening-lineup interval with Sengun and Durant shown: both rows swapped to their stint lines simultaneously and restored on mouse-out. Showcase only, committed without staging.

## 2026-08-03 11:55 — "if stints not covered show darkish gray '-'s not summary for game"

**Summary:** During any pane hover, a shown player whose stints don't cover the hovered interval now reads as their name plus dark-gray dashes in every column (derived from the header layout so alignment is exact), instead of falling back to their full-game line; covered players still swap to their stint lines, and everything restores on mouse-out.

Done — hovering the pane now distinguishes on-court from off-court among the shown players: whoever's stint covers the hovered stretch swaps to that stint's line, and whoever's doesn't shows dashes — name in their color, dark-gray '-' right-aligned under each stat column, generated from the header's own spacing so the columns line up exactly. Mouse-out restores the full-game lines. Verified with Sengun on / Durant off at the same instant: stint line and dash line side by side. Showcase only, committed without staging.

## 2026-08-03 12:05 — "game header shrunk to standard label size"

**Summary:** The game header block (matchup, date, venue, linescore) shrank from ~2.08cqw to the page's standard mono label size (the box score font, 1.22cqw) — the whole header now reads at the same size as the tables.

Done — the header block renders at the standard label size: the matchup line, date/time, venue/game-id line, and the linescore all use the box score font size now (14.6px at the design width, down from ~25px), keeping the monospace linescore alignment intact and giving the page a quieter top. Showcase only, committed without staging.

## 2026-08-03 12:12 — "upper left hand corner change Next to right arrow, Prev to left arrow"

**Summary:** The corner schedule nav labels swapped words for arrows: "Prev" is now a left arrow, "Next" a right arrow (both corners; the arrow glyphs are already in the site font subset).

Done — the corner navigation reads with arrows now: "← --" and "→ OKC @ IND 10/23/25" upper-left, "→ HOU vs DET 10/24/25" upper-right. One label change at the nav builder; the arrow glyphs ship in the site font. Showcase only, committed without staging.

## 2026-08-03 12:18 — "more the triangle pointer style"

**Summary:** The corner nav arrows switched to the triangle pointer style matching the fold arrows — "◂" for previous, "▸" for next (left triangle added to the site font subset).

Done — the corner navigation uses the triangle pointers now: "◂ --" and "▸ OKC @ IND 10/23/25" upper-left, "▸ HOU vs DET 10/24/25" upper-right, matching the page's fold-arrow style. The left-pointing triangle joined the site font subset alongside its existing right/down siblings. Showcase only, committed without staging.

## 2026-08-03 12:30 — "add okc 10/23 to our showcase and make…" (message cut off)

**Summary:** Built OKC @ IND 10/23/25 (game 0022500005) into the showcase set: its CSV was written from the play-by-play cache (649 events) and the page built with the current generator — double-OT IND home game, "IND vs OKC Lineups" (the vs/@ logic picked "vs" correctly), full feature set, zero images. The corner nav round-trips: the showcase's ▸ link opens it, its ◂ link returns to OKC vs HOU 10/21. The user's "and make…" continuation never arrived.

Done — OKC @ IND 10/23/25 is now a second showcase page: the pbp CSV materialized from the cache into outputs/2025-26/okc/csv/, and pm_players_0022500005.html built with every current feature (folds, tabs, multi-select stack, triangle nav, muted grays). Verified by clicking the showcase's own "▸ OKC @ IND 10/23/25" corner link: the new page loads, reads "Oklahoma City Thunder @ Indiana Pacers" with the 141-135 double-OT linescore, and links back. The request's second half ("and make…") was cut off — awaiting the rest.

## 2026-08-03 12:45 — "the left upper link 1: chases the team 1... link2 chases team 2 on the right edge..."

**Summary:** The corner nav edges now follow the page's team order instead of home/away: the left edge carries team 1's schedule (prev game above, next game below), the right edge team 2's — verified on both showcase pages (HOU left / OKC right on 10/21; IND left / OKC right on 10/23).

Done — each upper corner chases its own team: the left edge belongs to the page's first team with its previous game on the top line and its next game below, and the right edge does the same for the second team. Sides were previously assigned by home/away, which put the top team's links on the wrong side; they now key off the page's team order. Verified on both showcase pages: 10/21 reads HOU left (prev --, next vs DET) and OKC right (prev --, next @ IND); 10/23 reads IND left and OKC right with its previous-game link back to 10/21. Showcase pages only, committed without staging.

## 2026-08-03 12:55 — "navigation tools in the upper corners... follow a team's prev game and the opponent's prev game. How can I do this with no page duplicates?"

**Summary:** Q&A — measured: the fleet already stores each of 2,624 games exactly once (1 accidental dup from adding 0022500005 to okc/). The fix is canonical-path + cross-directory RELATIVE hrefs in the corner nav (../../<owner>/html/pm_players_<gid>.html): both teams' chains converge on the one file, and every page's four-link nav lets you keep following either team. Option A: owner lookup by glob at build time, zero migration. Option B: one-time migration to a flat <season>/games/ dir. Flagged: the parked per-team rename scheme (2024-okc-{gameid}) would force duplication; a shared 2024-{gameid} scheme keeps one copy.

Each game needs exactly one page; the corner links just have to point at it wherever it lives. Cross-directory relative hrefs do that on GH Pages and local preview alike, and since every page carries both teams' prev/next links, the chains stay followable from anywhere with zero duplication. Adopt via owner-lookup at build time (no migration) or a one-time move to a flat games dir; fix the single existing duplicate either way.

## 2026-08-03 13:05 — "don't skip link if missing just place what it should have been"

**Summary:** The corner nav never dims a game anymore: every prev/next entry is a link to the game's canonical page wherever its CSV lives in the season tree (cross-directory relative href via a build-time owner glob — Option A from the design discussion), and when the page isn't built anywhere yet the link points where it SHOULD be (the chain team's directory). Only schedule boundaries ("--") stay as text. Verified: OKC@IND's "OKC @ ATL" link resolved into atl/'s collection and a real click landed on that page; the HOU chain resolved into hou/.

Done — the nav links are unconditional now: each prev/next game links to its one canonical page, found by globbing the season tree for the game's CSV at build time and emitting a cross-directory relative href (../../TRI/html/pm_players_GID.html, or the bare filename in-directory). If a game isn't built anywhere, the href still points at the path it should have — the chain team's directory — so the link starts working the moment that page gets built, with no page duplicated anywhere. The stale cache-based existence check is gone. Verified on both showcase pages and with a real click hopping from the okc directory into atl's OKC @ ATL page. Note: this nav change means the fleet re-render before the next publish is required (already queued in memory). Showcase pages only, committed without staging.

## 2026-08-03 13:20 — "lets make our gh_pages set like this. Its the first 5 pages for each team... season and teams pages act like the full season is there with data and links. 404 when needed."

**Summary:** The gh-pages staging rule is now "each team's first five games" (was first four + last), deduped across teams, resolved at each game's ONE canonical location by owner glob (the old code assumed home-team dirs and silently skipped games stored elsewhere). Staged set: 2 season pages + 60 team pages + 157 game pages = 277MB. Season/team pages keep full-season data and links; unstaged games 404 by design.

Done — the staging script curates the requested set: for every team, its first five games per season (a shared early game stages once and serves both teams), found wherever each game's single page actually lives in the tree rather than an assumed home-team path. The season and team pages stage in full — complete data, links to every game — and links to games outside the first-five set simply 404, as specified. A dry run stages 219 files: 2 season pages, 60 team pages, 157 deduped game pages, 277MB total. Note for publish: the staged game pages come from the morning fleet build, which predates today's tab/nav work — the standing pre-publish fleet re-render covers that. Committed without staging to gh-pages (dry-run only).

## 2026-08-03 14:15 — "make a new help file and include game pages" + "push and publish and what ever might need to do"

**Summary:** Full publish run: new help.html (Game pages documented first — nav, karma, box scores, multi-select players, lineups), fleet re-render (2,625 pages, 0 failures, ~20 min), removed the one duplicate game copy (okc's 0022500005; IND is canonical) and rebuilt its three linking neighbours, both seasons' team+season pages rebuilt, staged the first-five-per-team subset (2 season + 60 team + 157 game pages, 271MB), then pushed main and force-pushed gh-pages.

Published. The new help page leads with Game pages: the per-team corner navigation, the karma panel (what the bars measure, the lines and scales, stint lanes, the four-state event cycler, the Hide switches), box scores with per-32 rates and row-to-stint highlighting, the Players section's multi-select tabs with overlaid translucent plots and the live box-score stack that follows the mouse (dashes for benched players), and the shared Lineups plot with its diamond/circle markers, hover-and-pin readouts, and per-8 tables — then the team and season pages as before, closing with a note that season and team pages are complete while game pages are the first-five sample.

Everything else the publish needed: the fleet re-rendered so all 2,625 pages carry today's work (multi-select tabs, live stack, interval hovers, always-on nav links, muted grays, triangle nav, the storage bundle); the single duplicate game page was deleted so every game has exactly one canonical page (2,624 games, 2,624 pages) with its three linking neighbours rebuilt to point at IND's copy; both seasons' team and season pages rebuilt; and the gh-pages set restaged under the new rule — each team's first five games, deduped — at 271MB.

## 2026-08-03 14:35 — "title and by Qs start at top of page + margin or pad if used. all the show/hiders follow along"

**Summary:** The header block's top padding dropped from clamp(52-76px) to a flat 14px, so the matchup/date/venue lines and the by-quarter linescore start at the top of the page and every title line below follows up in flow (first fold line 285px -> 223px at 1300px, 157px at 800px). The corner nav sits beside the centred text, no collision at either width.

Done — the title and the by-quarter linescore now start at the top of the page with a 14px pad, and all the show/hide title lines follow up with them: the first fold line moved from 285px to 223px at full width (157px at 800px). The old clamp(52-76px) padding was clearance for the header's original larger type; with the header at label size the corner nav tucks beside the centred block instead of below it — verified clean at 1300px and 800px. Noticed while checking: in the top-right corner the HELP/INDEX links and the right-edge game nav overlap each other (pre-existing, unrelated to this change) — say the word and I'll separate them. Showcase only, committed without staging.

## 2026-08-03 14:45 — "separate them" (HELP/INDEX vs right-edge game nav)

**Summary:** The right-hand game nav column now starts at 46px, below the fixed HELP/INDEX links that share the top-right corner (left column still starts at 8px); measured no overlap at 1300px and 800px.

Done — the two top-right stacks no longer collide: HELP and INDEX keep the corner, and the right-edge team nav (◂ prev / ▸ next / season page) begins just below them. The left-edge nav is unchanged at the top. Verified by geometry at both widths — corner links end at 40px, nav starts at 46px, zero overlap — and visually. Showcase only, committed without staging.

## 2026-08-03 14:52 — "how about on the game page"

**Summary:** Q&A/verification — the corner separation WAS the game page (plotting.py); measured all three page types at 1300px: game page clean (HELP/INDEX end 40px, right nav starts 46px, left nav top-left), team and season pages never collided (their nav is top-LEFT, HELP/INDEX top-right). Published site still shows the old overlap until the next publish.

The separation I made was on the game page — verified: HELP/INDEX hold the corner, the right-edge team nav starts below them, the left-edge nav sits at the top-left, and the collision detector reports zero overlaps. Checked the other page types too: team and season pages put their navigation in the opposite (top-left) corner, so they never had the problem. All three are clash-free locally; the live site still shows the old game-page overlap because the last publish predates the fix.

## 2026-08-03 15:00 — "on our show case pages?"

**Summary:** The second showcase page (OKC @ IND 0022500005, canonical under ind/) was still on the fleet build, predating the header-to-top and corner-separation changes — rebuilt it; both showcase pages now measure header at 14px, right nav at 46px, zero corner overlap.

Right — the second showcase page was a build behind: OKC @ IND lives under ind/ now and was last written by the fleet render, before the header and corner changes. Rebuilt both showcase pages; each now starts its title at 14px with the right-edge nav below HELP/INDEX at 46px and no overlap. The IND page's corners read cleanly: IND's chain on the left (▸ IND @ MEM 10/25/25), OKC's on the right (◂ OKC vs HOU 10/21/25 back to the other showcase, ▸ OKC @ ATL 10/25/25).

## 2026-08-03 15:10 — "lets add OKC first 5 to our show case"

**Summary:** OKC's first five 2025-26 games are now the showcase set, all rebuilt with the current generator: 0022500001 vs HOU (okc/), 0022500005 @ IND (ind/), 0022500101 @ ATL (atl/), 0022500119 @ DAL (dal/), 0022500126 vs SAC (okc/). Each verified — header at 14px, right nav at 46px, no corner overlap, tabs present, zero images — and a click-through of the ▸ chain walks all five in order across four team directories.

Done — the showcase is OKC's opening five: HOU 10/21, @ IND 10/23, @ ATL 10/25, @ DAL 10/27, and SAC 10/28. All five are freshly built with today's generator, and each carries one canonical page in its own team's directory (okc, ind, atl, dal, okc) — no duplicates. Clicking the right-edge ▸ link from game one walks the whole chain in order, hopping directories as it goes. These are exactly the five OKC pages the staging rule publishes, so the showcase and the published OKC set are now the same thing. Committed without staging.

## 2026-08-03 15:25 — "color Qs similar with R/G based on result, team names get team colors"

**Summary:** The linescore is coloured: team names in brand colours, each period's points green for the team that won that period and red for the one that lost (ties stay neutral), and the final by the game result — same green/red the W/L bands use. Built as HTML spans with all padding inside them, so the monospace columns keep their exact positions. _build_header now returns the coloured block alongside the plain prose. All five showcase pages rebuilt.

Done — the by-quarter table now reads at a glance: OKC in its blue and HOU in its red, then each quarter green for whoever won it and red for whoever lost (OT1's 11-11 tie stays neutral), with the final score green for the winner and red for the loser. It uses the same green/red as the team pages' W/L bands. The colouring lives in HTML spans whose padding sits inside the span, so the monospace column alignment is untouched; the header builder now hands back the coloured block next to the plain-text prose the figure path still needs. All five OKC showcase pages rebuilt and verified. Committed without staging.

## 2026-08-03 15:40 — "lower intensity on quarter colors, uneven gaps between closed titles on game page"

**Summary:** Period colours dropped to 60% alpha (the Final keeps full strength, so the result still reads first). The uneven closed-title rhythm was invisible in box measurements — the section summaries (ESPN Update, TRI Players) carried 6px of internal vertical padding while the karma/box/lineup titles carried none, so the VISIBLE ink gaps ran 26-34px; removing that padding evens them to 26-27.8px. All five showcase pages rebuilt.

Done — the quarter numbers are quieter now (green/red at 60% alpha) while the Final column stays full-strength, so the eye lands on the result first and the period detail sits behind it. On the gaps: box-to-box the closed titles measured a uniform 27-28px, which is why this looked fine before — but the section summaries carry 6px of padding above and below their text and the other title types don't, so the gaps you actually SEE ran from 26px to 34px depending on which kinds of titles were adjacent. Dropping that vertical padding brings the visible rhythm to 26-27.8px across all nine transitions. Showcase pages rebuilt, committed without staging.

## 2026-08-03 16:00 — "gap after lineups box score"

**Summary:** The Lineups section reserved a full readout band above AND below the plot (189/186px of blank at rest, for readouts only 143px tall that only appear on hover). Dropped the reservation to the page's standard gap and gave the lineup readouts the karma panel's black backdrop, so they paint over the neighbouring tables when shown: bands now 118/114px, readout verified intact (5 lines, marker ring, no clipping).

Done — that gap was a reserved hover-readout band: the section held ~190px of blank above and below the plot so the lineup popups had somewhere to land, even though they only appear on hover and are 143px tall. The reservation is now the page's standard gap, and the readouts carry a solid backdrop like the karma panel's — when one appears it simply paints over the table above (or below) it. At rest the blank is down to ~118px above and ~114px below (the latter including the plot's own tick labels), and a hover test confirms the full five-line readout with its marker ring still renders uncut. This also resolves the popup-gap item parked earlier in the session. All five showcase pages rebuilt; committed without staging.

## 2026-08-03 16:30 — "lineups box score drop-down overwrites next line: heavy shading; remove additional space after first Lineups box score"

**Summary:** (1) The per-row lineup-details drop-down (.lu-players, full player names on hover) now sits on a solid black backdrop extended 3px past its padding (box-shadow ring, z-index 6), so the next row it lands on is fully covered and the names read cleanly. (2) The ~146px dead band between the Lineups title and the plot was the hover-readout zone the figure's tightbbox reserved (the hidden mpl title area the readouts anchor in); the combined slice's top edge now hugs the axes (+10px headroom) — title-to-plot is 23px on all five pages. The readouts instead overlay the first lineup table when shown (black backdrop, .clbox z-index 3 over the table's z2) — verified: 5-line readout paints over the table uncut, hover/ring/highlight all work. Closed-state rhythm unchanged.

Both fixed. The drop-down that shows a lineup's full player names now lays a heavy solid-black shade under itself, extended a few pixels beyond its text, so the row it covers disappears behind it instead of bleeding through — the names read cleanly and the row's remaining stats continue past the shade's edge. And the extra space after the first Lineups box score is gone: it was a ~146px band the layout reserved so the hover readout had somewhere to appear; since the readouts now carry their own backdrop, they simply paint over the lineup table when summoned, and the plot starts 23px under its title — the page's normal rhythm — on all five showcase pages. Hover-verified: the five-line stint readout overlays the table fully readable, the marker ring and plane highlight still track, and the closed-state title spacing is untouched. Committed without staging.

## 2026-08-03 16:40 — "what is the gap between closed IND Lineups box score and IND vs OKC Lineups / closed OKC Lineups box score and OKC Players"

**Summary:** Measurement only (IND page 0022500005, 1300px, closed, no hover): IND Lineups box score -> IND vs OKC Lineups = 27.1px ink gap (50.0 top-to-top); OKC Lineups box score -> OKC Players = 26.8px (49.7). Page-wide closed range 26.0-27.8px; spread is letterform descenders, not margins.

The two gaps are 27.1px and 26.8px of visible whitespace — within a third of a pixel of each other. Full-page context: every closed gap sits between 26.0 and 27.8px (title-top to title-top 48.9-50.7), and the variation tracks which glyphs end each line (descenders eat into the measured white) rather than the section margins.

## 2026-08-03 16:45 — "where are my showcase files"

**Summary:** Listed the five showcase pages (OKC first five, canonical dirs): okc/0022500001, ind/0022500005, atl/0022500101, dal/0022500119, okc/0022500126 — local under outputs/2025-26/{tri}/html/, live under jackjohnson-sd.github.io/nba-dataview/2025-26/{tri}/html/. Noted live copies predate today's later fixes until next publish.

Your showcase is OKC's first five games, one canonical page each: vs HOU under okc/, @ IND under ind/, @ ATL under atl/, @ DAL under dal/, and vs SAC under okc/ — locally at outputs/2025-26/{team}/html/pm_players_{gameid}.html and live at the same paths on the site. The live copies are from this afternoon's publish, so today's later polish (coloured linescore, header at top, corner separation, drop-down shading, readout-band removal) is local-only until we publish again.

## 2026-08-03 16:50 — "OKC/HOU 10-21-25 game page, all closed: vertical offsets from top of page to HOU Lineups box score / HOU @ OKC Lineups / OKC Lineups box score"

**Summary:** Measurement only, 1300px viewport: HOU Lineups box score 423.5px, HOU @ OKC Lineups 473.5px, OKC Lineups box score 522.6px (text-ink tops; element boxes 425/473/524). Steps of 50.0 and 49.1px — uniform pitch.

At a 1300px window the three titles sit 423.5px, 473.5px and 522.6px from the top of the page (measuring to the visible text). The steps between them are 50.0px and 49.1px — the page's standard closed-title spacing, with sub-pixel variation from glyph extents. Game pages scale with window width, so the absolute numbers scale proportionally at other widths.

## 2026-08-03 16:55 — "OKC/HOU 10-21-25, all closed: vertical offset from top of page to top of ALL collapsable items"

**Summary:** Measurement only, 1300px viewport, text-ink tops: ESPN Update 223.4, HOU Karma 273.6, HOU box score 323.9, HOU Players 374.6, HOU Lineups box score 423.5, HOU @ OKC Lineups 473.5, OKC Lineups box score 522.6, OKC Players 572.2, OKC box score 622.8, OKC Karma 672.7. Steps 48.9-50.7px, mean 49.9.

The ten fold titles sit at 223.4 / 273.6 / 323.9 / 374.6 / 423.5 / 473.5 / 522.6 / 572.2 / 622.8 / 672.7 pixels from the top of the page at a 1300px window, a near-uniform ~50px pitch (48.9-50.7) whose sub-pixel wobble comes from glyph extents and slice rounding. The header block and linescore occupy the space above the first fold.

## 2026-08-03 17:20 — "make all 40 exactly."

**Summary:** Closed-title pitch is now EXACTLY 40px. Mechanism: every closed section renders as a fixed 40px cell (title flush at cell top) — details.more/kbox/bx-flow/lineup-box/clbox all get height:40px when their fold is closed, trailing margins zeroed, the karma title's inline top overridden to 0, the lineup-box's 18px bottom padding dropped (vertical only; the left-padding scoping bug caught in a mixed-state screenshot and fixed). A row's top margin drops only when the row ABOVE is also closed (pair-scoped :has() sibling rules), so open sections keep their normal gaps. Line boxes unified (bx title line-height:normal instead of 1.15, lu summary display:block at the shared title font, cl-title display:block) so the ink offset in every cell is identical. Verified: cell-box pitch [40,40,40,40,40,40,40,40,40] exact at 1300; text-ink pitch 40.00 across all nine steps at 900/1100 on all five showcase pages, 40±0.04 at 1300/1600 (sub-rendering-pixel font-metric rounding); mixed states (karma open, box open) keep proper gaps and alignment.

Done — all nine steps between the ten closed titles are now exactly 40px, top to top. Each closed section renders as a fixed 40-pixel cell with its title flush at the top, and the cells stack flush when their neighbours are closed too; open a section and it keeps its normal breathing room, with the closed rows around it still on the grid. The title line boxes were also unified (the box score title carried a different line-height, the lineup titles a different font context) so the text sits at the same offset inside every cell — measured 40.00 for every step at 900 and 1100 wide, and within four hundredths of a pixel (font rasterization, not layout) at 1300 and 1600, on all five showcase pages. The element grid itself measures a flat [40 x 9] everywhere. Committed without staging.

## 2026-08-03 17:35 — "the first line up pop up should have the starting lineup as in and nothing as out."

**Summary:** The first drawn stint's popup previously showed in: --- / out: --- (no predecessor to diff against). Now the whole starting lineup lists as "in" (sorted, each name in its chart colour) and out stays ---. Verified on both halves: HOU first stint -> in: Adams, Durant, Sengun, Smith Jr., Thompson / out: ---; OKC first stint -> in: Dort, Gilgeous-Alexander, Hartenstein, Holmgren, Wallace / out: ---. All five showcase pages rebuilt.

Done — each team's first lineup popup now reads the starting five as "in" and nothing as "out": hovering HOU's opening stint shows in: Adams, Durant, Sengun, Smith Jr., Thompson with out: ---, and OKC's shows in: Dort, Gilgeous-Alexander, Hartenstein, Holmgren, Wallace with out: ---. Every later stint still diffs against the previous drawn stint as before. Committed without staging.

## 2026-08-03 17:55 — "stack all the nav on the left side, add link to team page as last stack item with triangle pointing up"

**Summary:** The corner nav is now ONE left column: team 1's ◂ prev / ▸ next, team 2's pair below, and last "▴ TRI 2025-2026" linking up to the team page of the collection the game lives in (okc page -> team_okc.html, ind page -> team_ind.html). The old right-edge column is gone (HELP/INDEX keep the top right). The ▴ glyph (U+25B4) was added to all four DejaVu woff2 subsets (rebuilt from matplotlib's TTFs with the full site unicode list). The old per-side team link had checked the wrong directory (csv/ instead of html/) and never showed — the up-link replaces it unconditionally. help.html's Corner navigation section rewritten to match. Verified on both showcase corner variants: 5-item stack at 8/28/47/67/86px, correct cross-directory hrefs, triangle renders (fonts.check U+25B4 true).

Done — all the game navigation now lives in one upper-left column: the first team's previous and next games, the second team's below them, and at the bottom "▴ OKC 2025-2026" (or the page's own team), pointing up to the team page the game belongs to. The right edge is clear except HELP/INDEX. The up-triangle needed a font update — U+25B4 wasn't in the site's subsetted DejaVu faces, so all four were rebuilt with it. It also turned out the old team-page link had been checking the wrong directory and never actually appeared, so this is the first time the corner reaches the team page at all. Help updated to describe the new corner. Committed without staging.

## 2026-08-03 18:10 — "make a new help, talks about navigate. start with season, team, then page."

**Summary:** help.html rewritten as a navigation guide, top-down: a "The map" panel (SEASON -> click a tricode -> TEAM -> click a game column then LINK -> GAME) plus the corner convention (▴/^ up, ‹›/◂▸ sideways, HELP/INDEX top right), then Season page, Team page, Game page — each opening with its own NAVIGATING block before its controls. Navigation paths verified live first: season page tricodes link to team_TRI.html everywhere (ring, conference rows, plot labels); team page carries ^ 25/26, ‹ TRI / › TRI, and a per-game LINK in the pinned info line (cross-directory hrefs for games owned by other teams); game page's new five-line left stack. Content otherwise carried over, updated for today's changes (coloured linescore, starting five as "in", lineup code drop-down). Verified: no horizontal overflow, fonts load, section order correct.

Done — the help is now a navigation guide that reads top-down. It opens with a map panel: SEASON, then "click any tricode" down to TEAM, then "click a game column, then LINK" down to GAME — followed by the corner convention that holds at every level (▴ or ^ climbs, ‹ › or ◂ ▸ steps sideways, HELP and INDEX top right). Then each page gets its own section in that order — Season, Team, Game — and each one leads with a NAVIGATING block explaining how to go down, up and sideways from there, before its controls. I verified the paths against the live pages first rather than describing them from memory: on the season page every tricode really does link to that team (ring, conference rows and plot lanes alike), the team page carries the up-link, the alphabetical team steppers and a per-game LINK that resolves across directories, and the game page has the new five-line left stack. The control documentation carried over with today's changes folded in — the coloured linescore, the opening stint listing the starting five as "in", and the lineup-code drop-down. Committed without staging.

## 2026-08-03 18:30 — "push and publish"

**Summary:** Full publish: fleet re-render (2,624 pages, 0 failed, ~19 min) so every game page carries today's evening work, both seasons' team+season pages rebuilt (60 + 2), staged the first-five-per-team subset (157 game pages, 271MB), verified the STAGED copies before pushing (40px pitch [40,39.96,40.04,40,40,40,40,39.96,40.04], 5-item left-only nav with "▴ OKC 2025-2026", coloured linescore spans, new navigation-first help, team page up-link resolving), then pushed main and force-pushed gh-pages.

Published. The fleet re-rendered clean — 2,624 game pages, zero failures — so everything from this evening is now live: the exact 40-pixel grid between closed titles, the single left-hand navigation column ending in the ▴ link up to the team page, the colour-coded linescore, the first lineup popup listing the starting five as "in", the shaded lineup drop-down, and the reclaimed space around the Lineups plot. Both seasons' team and season pages were rebuilt alongside, and the new navigation-first help ships with them. I checked the staged copies rather than the source ones before pushing — the grid, the nav stack, the linescore colouring and the help's section order all verified in the exact files that went out.

## 2026-08-03 18:45 — "get rid of the gnav-r css rule"

**Summary:** Dropped ".gnav-r{right:12px;}" from the game-page stylesheet (dead since the nav moved to one left column). Zero gnav-r references remain in the output; nav verified unchanged — 5 items, all at left:12px, tops 8/28/47/67/86, ending "▴ OKC 2025-2026". All five showcase pages rebuilt.

Gone — the rule is out of the stylesheet and the built pages contain no gnav-r reference at all. The nav is unchanged: five items in one column at the left margin, evenly stacked, ending in the up-link to the team page. It'll reach the live site with the next publish. Committed without staging.

## 2026-08-03 19:05 — "make the player plots same line style Karma +/-"

**Summary:** The player +/- was a sloped polyline (rotated divs, --r angle var, rounded caps); it's now a STEP line built exactly like the karma panel's margin line — a horizontal run at each value plus a vertical riser at each change, emitted as axis-aligned rects. .ppl dropped its rotation/transform-origin/border-radius for .khl's min-width/min-height:1px floors; pp_seg entries became pp_step (x, y, w, h, color, team, idx). Verified: zero rotation transforms remain, segments split 139 H / 161 V, thickness matches the karma margin line (1px both), multi-select overlay intact (3 tabs -> 3 groups, 216/169/206 line elements, each in its own player colour). Cost: 765KB vs 702KB per page (+9%, ~2 rects per point pair instead of 1 segment). All five showcase pages rebuilt.

Done — the player plots now draw their plus/minus the same way the Karma panel draws its +/- line: a flat run at each value with a vertical riser where it changes, instead of the old diagonal polyline. It's literally the same construction and the same 1-pixel weight, so the two read as one family; the lines keep each player's own colour, since that's what the multi-select overlay depends on. Checked that the rotation machinery is fully gone, that the step segments come out balanced (139 horizontal, 161 vertical on the first chart), and that selecting three tabs still overlays three separate coloured step lines. It costs about 9% more page weight (765KB vs 702KB) because a step needs two rectangles where a slope needed one. Committed without staging.

## 2026-08-03 19:20 — "merge the risers into the runs"

**Summary:** Each step is now ONE element instead of two: an L drawn with borders on a single box — the run is the top or bottom border (whichever edge the step sits on), the riser is that same box's right border. Three variants: .ppl-u (bottom+right, step up), .ppl-d (top+right, step down), .ppl-h (top only, flat run). Colour moved from background to border-color class hoisting; box-sizing:border-box so the borders land exactly on the box edges. Element count 2,518 -> 1,394 (-45%); page 765KB -> 707KB, back to the sloped version's weight (702KB) while keeping the step shape. Verified: variant split 664 up / 659 down / 71 flat, borders resolve 1px on the right edges, multi-select overlay intact (3 groups, per-player colours). All five showcase pages rebuilt.

Done — each step is a single element now. The trick is drawing the L with borders instead of fill: one box per step whose top-or-bottom border is the flat run and whose right border is the riser, so the two pieces come from the same div. The step line looks identical; the count of drawn elements dropped 45% (2,518 to 1,394) and the page went from 765KB back to 707KB — essentially the old sloped-line weight, with the karma-matching step shape. Verified the variants come out balanced (664 stepping up, 659 down, 71 flat runs), the borders resolve to a clean 1px, and the multi-select overlay still draws each player's line in their own colour. Committed without staging.

## 2026-08-03 19:45 — "on players no color for stint background, mouse overs still work, events are moved to a y above the max for the segment"

**Summary:** (1) The 8%-alpha on-court tint (pp_span/.pps) is no longer emitted — zero .pps elements. (2) Mouse-overs verified intact: the hover layer is a separate 65-cell interval grid (.psh in .pgrp-hov), never the tint; hovering at 15%/50%/80% of the game swaps the flow-stack row to that stint (6min +4 / 11min +2 / 5min 0) and leaving the plot restores the full-game line (49min +9). (3) Each event now sits at its STINT's max +/- plus 6% of the range, so glyphs band above the curve instead of scattering along it; events outside every stint keep their own value. Caught during verification: declutter bumps walked 25 of 503 glyphs (5%) past +15 where the range check silently dropped them — added a post-declutter clamp into [-15, +15], so all 503 render (0 above the frame). Page 707KB -> 698KB. All five showcase pages rebuilt.

All three done. The on-court tint is gone — the stints now read from the step line and the entry/exit dots alone. Mouse-overs are untouched, as expected: the hover layer was always a separate grid of interval cells sitting above the plot, not the tint itself, and I confirmed it by hovering across the game and watching the box-score row swap to each stint's stats and snap back to the full-game line on the way out. Events now ride in a band above each stint's own peak rather than sitting on the curve where they happened. One thing worth flagging: lifting the glyphs pushed some against the top of the frame, and the declutter pass that separates overlapping ones was walking about 5% of them (25 of 503) clean off the chart, where the range check dropped them without a trace — I clamped the final positions back inside, so every event renders even if a few crowd the ceiling on high-plus/minus stints. Committed without staging.

## 2026-08-03 20:05 — "on players stack events vs overlap"

**Summary:** Root cause found by measuring the glyph in the browser: the declutter assumed a footprint of 5% of the y-range (1.5 units) and nudged collisions by 40% of that (0.6 units), while a glyph is actually 3.15 data units tall — so "decluttered" glyphs still overlapped by ~80%. Rewrote _declutter_marker_rows to take the glyph's REAL footprint (w, h) and, on a collision, jump to the hit glyph's top + one full height (tight stacking, no drift). Second bug: the whole band/declutter block ran BEFORE ax.set_xlim/set_ylim, so transData still had default 0-1 limits and the measured footprint was meaningless (first rebuild still showed 32 overlapping pairs at 97%) — moved the block after the limits are set, where transData is exact (by_kind holds references to the same row dicts, so emission is unaffected). Per-stint columns that outgrow the frame shift down as a unit. Verified across 8 player charts on 2 games: 0 overlapping pairs, 0 glyphs outside the frame (was 32 pairs at 97% overlap on Sengun alone). Page 698KB.

Done — events stack cleanly now, no overlaps anywhere. The cause was a bad assumption in the declutter pass: it treated a glyph as 1.5 data units tall when the real box is 3.15, and nudged collisions by 0.6 units — a fifth of a glyph — so things it considered "resolved" were still sitting on top of each other. It now measures the glyph's true size and, when two collide, lifts the later one to sit exactly one glyph above the one it hit, so clusters stack tight instead of drifting. Finding that exposed a second problem: the whole placement pass was running before the axis limits were set, so the measurement it was based on was meaningless — my first attempt still had 32 overlapping pairs at 97%. Moving the pass to after the limits fixed it. Where a stack outgrows the top of the frame, that stint's whole column drops as a unit rather than clipping. Verified on eight player charts across two games: zero overlapping pairs, zero glyphs outside the frame. Committed without staging.

## 2026-08-03 20:20 — "is everything cached needed to make all pages?"

**Summary:** Yes — verified by building with the network hard-blocked at the socket layer (not just a proxy), not by inspecting the cache alone. Cache is 982MB at ~/.cache/nba_pbp: game_info / game_rotation / box_score_traditional / live_actions / pbp all cover 2,624 of 2,624 buildable games (0 missing); league_games pickles cover both seasons (regular + playoffs), so league_history returns instantly offline (2,628 / 2,630 rows). Offline builds succeeded: game page 700KB/1.9s with its ESPN recap, both season pages 3.5MB/8.0s, team pages 0.2-0.3s each. ONE gap: game_recap is cached for 2,609 of 2,624 — 15 games (14 in 2024-25, 1 in 2025-26) have no recap; those pages build fine offline, just without the ESPN Update section (verified: 0022400034 built 558KB, recap section absent). Exactly 1 of the 157 staged games is affected.

Yes — everything needed is cached, and I confirmed it by actually building pages with the network blocked at the socket layer rather than by reading the cache listing. A game page built in 1.9 seconds with its recap intact, both season pages in 8 seconds each, and team pages in a fraction of a second; league history comes straight from its pickles. The cache is 982MB and covers all 2,624 buildable games for play-by-play, game info, rotations, box scores and live actions — no gaps.

One exception worth knowing: ESPN recaps are cached for 2,609 games, so 15 (14 from 2024-25, 1 from this season) have none. Those pages still build offline without error — they just come out without the ESPN Update section, which I verified on one of them. Only one of the 157 currently published game pages is affected. If you want that closed, fetching those 15 recaps online once would do it.

## 2026-08-03 20:35 — "get the 15 missing recaps"

**Summary:** Attempted all 15; ZERO are retrievable — the data doesn't exist upstream, it isn't a cache or lookup failure. Diagnostics per game: ESPN's scoreboard finds each game by exact matchup name on the right date and returns a valid event id (e.g. 0022400034 -> 401703403), but the summary endpoint has NO "article" key at all for these events, while a working game (0022500001 -> 401809243) does. Checked the alternate path too: the "news" block on the empty events carries only generic league articles (free agency previews, Knicks front-office news) with story=False — no game recap under a different key. _cached never stores None, so every rebuild retries them for free; if ESPN backfills, they'll appear on the next render. Net: 2,609 of 2,624 games have recaps; the other 15 render without the ESPN Update section by design.

I tried all 15 and none of them can be fetched — the recaps don't exist on ESPN, so there's nothing to cache. This isn't a lookup bug: for every one of the 15, ESPN's scoreboard finds the game by exact matchup on the right date and hands back a valid event id, but the summary for that event has no article at all, where a game that works has a full one. I also checked whether the recap had simply moved to a different field — the "news" block on those events carries only generic league stories (free-agency previews and such), nothing game-specific.

So the 15 pages will keep rendering without an ESPN Update section, which they already do cleanly. One upside of how the cache works: it never stores a null, so every future rebuild silently retries them — if ESPN ever backfills those recaps, they'll appear on the next render with no action from us.

## 2026-08-03 20:55 — "start getting data for 23/24 season page, team pages, then game pages 1 each 15 seconds report every 5 minutes"

**Summary:** Probed each page type's real dependency before fetching. Findings: 2023-24 play-by-play is ALREADY fully cached (1,312/1,312) — so TEAM pages build offline right now (verified: OKC 2023-24 rendered 2,758KB with the network blocked at the socket layer, nothing to fetch). The SEASON page needs boxscoretraditionalv3 for every game (0/1,312 cached) and cannot render until the last one lands. GAME pages need that box score plus game info, rotation, live actions, ESPN recap, and the play-by-play written out as CSV (0 CSVs on disk for 2023-24). Because the season page needs ALL box scores either way, a split box-scores-first pass would reach it no sooner than a combined pass while costing a second 5.5h sweep — so wrote scripts/fetch_season_data.py to complete one game fully per 15s tick (calls spaced 1.2s inside the tick), resumable (cached calls are free), PROGRESS line every 300s. Dry-run on 3 games: 3 complete, 0 partial, CSVs in the right team dirs. Full run launched: 1,312 games, ~5.5h, background task byhcya4ak with monitor bnnqz6id1.

Started. First, what each page actually needs, checked rather than assumed: 2023-24 play-by-play turns out to be fully cached already, so the TEAM pages need nothing — I built OKC's 2023-24 page with the network blocked and it rendered fine. The SEASON page is the real gap: it needs the traditional box score for all 1,312 games and none are cached. Game pages need that same box score plus game info, rotations, live actions and recaps, and the play-by-play written out as CSV, which doesn't exist on disk for that season yet.

One judgement call on ordering: since the season page can't render until the last box score arrives, fetching box scores alone first wouldn't get you the season page any sooner — it would just add a second five-hour sweep for the game data. So each 15-second tick now completes one game entirely. The season page unlocks at the end either way, and every game page is finished at that same moment instead of five hours later. It's resumable, so stopping and restarting picks up where it left off rather than refetching.

Running now: 1,312 games, about 5.5 hours, with a progress report every five minutes.

## 2026-08-03 21:20 — "increase the season page event bar size for 1 member groups to take up 50% of unused space" + "add PM to you list"

**Summary:** Measured the geometry first: every lane on the season page carries an identical 102px pad below it (tricode row + label line + next pole head), of which ~50px is labels and ~52px is blank — the same blank whether the lane is a 1-member stat or a 3-member trio. But lane height is 13*members + 19, so singles got 32px against the trios' 58px. Singles now take back half that blank (+26px), landing on 58px: _LH2 = 13*_m + 19 + (26 if _m == 1 else 0). Six lanes grow — PF, TO, BLK, STL, AST and PM (PM is a 1-member lane, so the user's addition is covered by the same rule). Peak bar heights went 27/28/28/27/30/32 -> 49/51/50/49/55/58. Everything downstream (_T2 tops, _BANDS collapse offsets, _H2 plot height) derives from _LH2, so it followed automatically: verified 0 overlapping lanes in the resting view, with a lane collapsed, and in sort mode; pitch is a uniform 160px (147 at the DR/OR pair, which stays 45px as a 2-member group). Rebuilt the 2025-26 season page only.

Done — the six single-member plots now stand 58px instead of 32px, the same height as the shooting trios. The reasoning behind the number: every lane on that page reserves the same 102px strip beneath it for its tricode row and label line, and about 52px of that is simply blank, no matter how many members the lane has. So a one-member plot was wasting exactly as much space as a three-member one while drawing a third of the bars. Taking half that blank back adds 26px, which happens to land the singles on the trios' height — a tidy result rather than a coincidence I engineered. Peak bars roughly doubled: PF went from 27px to 49, PM from 32 to 58.

PM came along for free — it's a one-member lane, so the same rule catches it. Everything that positions the page (lane tops, the collapse offsets that reclaim space when you close a plot, the total plot height) is derived from that one height value, so it all followed; I checked the resting view, a collapsed lane and sort mode, and there are no overlaps in any of them.

One thing to confirm: I read "OKC 25/26 Season page" as the 2025-26 league season page, which is where these single-member lanes live and where OKC leads the resting order. If you meant OKC's own team page, its single-stat lanes are already 45px rather than 32px — say the word and I'll give them the same treatment. Rebuilt the season page only; committed without staging.

## 2026-08-03 22:10 — "collect all possessions in a game: research the definition, then determine all in a game (team, date, start/end game time, duration, scored Y/N)"

**Summary:** New module src/nba_pbp/possessions.py. Definition used (NBA / Basketball-Reference standard): a possession runs from gaining control to giving it up, ending ONLY on a made field goal, a made LAST free throw, a defensive rebound, a turnover, or the period end — and NOT on an offensive rebound (same team keeps it), a non-final free throw, or a technical free throw. And-1s are one possession (the bonus FT is absorbed onto the made basket at the same clock). Data notes discovered by probing: rebound subType is "Unknown" so offensive/defensive is decided by whether the rebounder is the team already in possession; team rebounds AND team turnovers carry no tricode and are resolved from the description nickname ("Rockets Rebound"); free-throw makes/misses come from the description ("MISS") since shotResult is null on FTs; technicals are subType "Free Throw Technical".

Validation caught three real bugs before the result was trusted: teamless team-turnovers produced a phantom extra possession for the wrong side; the turnover hand-off was inverted (ball given back to the team that lost it); and 2 points went unattributed. Post-fix, across 6 games: consecutive same-team possessions 0/0/0/0/0/0, max per-period team gap exactly 1 in every game, mean possession 13.6-15.3s (NBA pace ~14s), and possession points + technical FT points == the actual final score in ALL SIX games. Showcase game 0022500001: 227 possessions (HOU 115, OKC 112), 50.2% scored, 1.097 points per possession, mean 15.3s.

Here's the definition and the result. A possession runs from the moment a team gains control to the moment it gives it up, and it ends on exactly four things: a made field goal, a made last free throw, a defensive rebound, or a turnover (plus the period ending). Critically it does NOT end on an offensive rebound — the same team still has the ball, the possession just runs longer — which is what separates possessions from shot attempts. An and-1 is one possession, not two, so the bonus free throw and its point are absorbed onto the basket.

Three things in the data needed care. Rebounds don't say whether they're offensive or defensive (the field literally reads "Unknown"), so that's decided by whether the rebounder already had the ball. Team rebounds and team turnovers carry no team code at all, only a nickname in the text. And free throws don't carry a made/missed flag — that's in the description.

I validated rather than assumed, which caught three genuine bugs: teamless turnovers were inventing an extra possession for the wrong side, the turnover hand-off was giving the ball back to the team that just lost it, and two points were falling through the cracks. After fixing those, across six games: zero consecutive same-team possessions, the two teams' counts differ by at most one in every single period, average possession 13.6-15.3 seconds against a league pace of about 14, and possession points plus technical free throws equal the actual final score in all six.

For the showcase game: 227 possessions, HOU 115 and OKC 112, half of them scoring, 1.097 points per possession.

## 2026-08-03 23:05 — "new test_page.html: possessions plot (2 team rows on the game clock, scored, duration = length), no collisions, linked box score, karma-style axes, hide/show title" + "What are smallest gaps"

**Summary:** New scripts/possessions_page.py -> outputs/test_page.html (144KB, pure HTML/CSS, no JS/images), built on possessions.py. Two rows on the game-clock axis in team colours, rect left/width = possession start/duration, karma-style furniture (period grid lines, Q1..END x ticks, team tricodes as y labels), a "Possessions" ▾ fold hiding the plot, and a possessions box score below in the game page's own table classes (.bx/.bxs/.bx-head/.mx-gold/.mx-red, imported constants — not a copy).

TOO SMALL TO LABEL — resolved with measurements, not a guess: the axis runs 0.312 px per second, so the WIDEST possession in the game (41s) is 12.8px and the median (15.3s) is 4.8px, while a digit needs ~10px. Text would therefore land on 1-2 rects out of 227. Points are encoded as HEIGHT instead — 0/1/2/3+ points = 15/33/55/82px tiers — which reads at any width; the exact line stays one hover away.

NO COLLISIONS — enforced and verified: each row is walked in time order and every rect is trimmed against the NEXT one's start. First attempt still showed 1 overlap because CSS min-width:1px was re-widening trimmed rects after the geometry pass; dropping that floor gives 0 overlapping pairs (3 rects end up sub-pixel, which is honest at 0.3px/s).

SMALLEST GAPS (the user's question), same game: same-team consecutive possessions have a MINIMUM gap of 0.0s — three of them, two at period boundaries plus one real 0.0s (OKC P2 9:33, defensive rebound straight back). Next smallest 0.1s (0.03px), 0.7s (0.22px), then three at 1.0s (0.31px). Medians are 13.0s (HOU) and 17.0s (OKC). Durations: min 0.0s, median 15.3s, max 41.0s; 6 possessions under 2s, 18 under 5s. So a one-second gap is a third of a pixel — which is exactly why a minimum-width floor could not survive and had to be clamped.

Both-way hover verified live: hovering a rect lights its box score row and pops the readout ("HOU 1:54 - 1:37 17s scored 3"); hovering a row outlines its rect in white.

## 2026-08-03 23:30 — "go vertical with plot"

**Summary:** Rotated the possessions plot: the game clock now runs DOWN the page (period rules across, Q1..END labels down the left margin) and the two teams are side-by-side columns headed by their tricodes. Duration is bar HEIGHT, points are bar WIDTH (0/1/2/3+ = 18/40/68/100% of the column), scored still solid vs dim outline. The .img-box went from 0.2x to 3.0x the container width (3,600px tall at 1200 wide).

THE PAYOFF IS MEASURED: vertical gives 1.03 px per second instead of 0.31, so the median possession is a 15.2px-tall bar instead of a 4.8px-wide sliver — and 72 of 114 scored possessions now carry their point label, where the horizontal version could fit ZERO. The remaining 42 are still too short and fall back to width + hover, as before.

Overlap guarantee re-verified after the rotation (trim against the next bar DOWN in the same column): 0 overlapping pairs, 3 clamped. Two fixes found by checking rather than assuming: the hover readout had been positioned at 97% left, i.e. off the right edge of the plot — it now sits just above its bar on a black backdrop like the karma readouts (verified inside the box on both edges); and the left margin was 12% of dead space for clock labels, trimmed to 6.5% with the columns widened to 43.5% each. Both-way hover still verified live.

## 2026-08-03 23:50 — "put box and plots in scroll bars"

**Summary:** Both blocks now scroll in their own window instead of running down the page: the plot in a 62vh window (558px onto 3,558px of timeline) and the box score in a 34vh one (306px onto 6,301px of rows). Page height drops from ~4,600px to 1,015px with no horizontal overflow. Scrollbars wear the season page's own treatment (14px, gradient thumb, lit on hover, translucent track).

Two things kept OUT of the scrolling so they stay readable: the HOU/OKC column heads sit in a pinned strip above the plot window, and the box score's column header row sits above its window — so you always know which column is which and which team a bar belongs to. Verified after scrolling the plot 1,500px that the both-way hover link still works (bar -> box row lit + readout shown). Also fixed while checking: the hover readout was anchored to the left spine for BOTH columns, so hovering an OKC bar popped its readout over in HOU's half; it now sits over its own column (measured HOU readout at 127px, OKC at 690px).

## 2026-08-04 00:20 — "possession mouse over: game time, duration, last event code, green for success" + "success or failure they will be a conclusion to defensive and offensive possession"

**Summary:** The readout now reads "Q1  11:02 - 10:50  12s  M2  OFF +2" — period, clock range, duration, and the LAST event code inside that window (M2/M3 made, X2/X3 missed, FT/XFT, OREB/DREB, TOV, FOUL, VIOL, JUMP; added _event_code + a last_event column to possessions.py).

The second message reframed the model, so the page was rebuilt on it: every possession window concludes TWO possessions at once — the offensive one for the team with the ball and the defensive one for the team without it — and the same event decides both in opposite directions. So each window now draws TWO bars: the offensive one in its team's column (anchored left, solid) and the mirrored defensive one in the other team's column (anchored right, outline only so it never reads as scoring). 227 possessions -> 454 bars, both pointing at the same box score row, which stays one row per possession.

Success is judged per side: offence succeeds by scoring, defence succeeds with a stop. That produces a clean invariant, which is also the validation — exactly 227 of the 454 readouts are green, one per possession, because every window is a success for exactly one side. Verified live: hovering the offensive bar gives "OFF +2" in green while its mirrored defensive bar gives "DEF scored on" in grey, and either one lights the same box row. Zero overlaps within each side after the split. Page 148KB -> 241KB.

Earlier single-sided reading (green = scored OR gained-by-own-defensive-rebound) is superseded and gone.

## 2026-08-04 00:45 — "make the plot and x-axis labels, line, tick and plot label font sizes large enough" + "just place on small possessions at the possession base"

**Summary:** The plot's type was roughly half the karma panels'. Everything is now derived from the SAME point sizes the karma panels use (a _pt() helper converting matplotlib points at 150dpi on the 1200px page into cqw) rather than hand-picked numbers: tick labels 0.78cqw -> 1.389cqw (9.4px -> 16.7px, karma's 8pt x ticks), team column heads -> the panel-title size 1.644cqw (19.7px), in-bar point labels 0.86cqw -> 1.215cqw (14.6px, karma's 7pt). The head strip grew with the type so nothing clips (verified).

The bigger label font cut the bars that could hold a digit from 72 to 44 — which the second message then solved: a possession too short to centre its number now hangs it at the possession's BASE, the left edge it grows from, in white with a dark halo so it reads over the dim fill. Result: ALL 114 scoring possessions now carry their points (44 centred inside, 70 at the base), up from 72 before the type change and 44 after it — and a full pairwise check across every label found 0 colliding pairs.

## 2026-08-04 01:15 — "each offensive possession begins when we get the ball (opponent scored, turnover, foul, jump ball, rebounded a missed 2P/3P/last FT, awarded...) — the plots butt up against each other"

**Summary:** Two changes. (1) HOW EACH POSSESSION BEGAN is now derived and carried: possessions.py records the terminating event's detail (turnover subtype, 2PT/3PT) and maps the previous possession's ending into a gain reason — opponent score, defensive rebound, turnover, offensive foul, shot clock, violation, period start, retained, or "other" for anything the data cannot place rather than guessing. Showcase game: opponent score 111, defensive rebound 72, turnover 18, violation 10, period start 6, offensive foul 5, shot clock 4, other 1. Across 5 games only the same small taxonomy appears, no unexplained bucket growth.

(2) THE PLOTS NOW BUTT AGAINST EACH OTHER: dropped the two separated columns for a shared centre line at 52% — the first team's bars grow leftward from it, the second's rightward, so at every moment of the game the two teams' bars meet in the middle. Verified: all 454 bars touch the centre (227 each side), none crosses it. The team heads sit either side of the centre line, the base labels moved to whichever edge each bar actually grows FROM (right edge for the left team, left edge for the right team), and both readouts now name the origin — "Q1 11:31 - 11:26 5s M2 OFF +3 from defensive rebound" and its mirror "DEF scored on they got it from defensive rebound".

Three patch attempts failed on stale/whitespace-mismatched anchors before this landed; each aborted before writing, so no half-applied edits.

## 2026-08-04 02:00 — "use DR,OR for rebounds; one side = things attributed to our players, their side = theirs; show both sides at once" + "the date time do not need to be repeated, print them out for one team to the left edge" + "center the bar on the mid of poss"

**Summary:** (1) Rebound codes shortened to DR / OR. (2) EVERY event is now credited to the team it belongs to: possessions.py accumulates a per-team code list inside each window, so a single possession reads "HOU OFF FOUL X3 OR M2 +2" on HOU's side and "OKC DEF -" on OKC's — each side showing only its own players' work. (3) Hovering either bar (or the box row) reveals BOTH sides at once, plus (4) the shared time printed ONCE in a widened 18% left gutter: "Q1 9:04-8:49 15s". Layout re-proportioned for it — centre 52%->57%, halves 44%->39%.

(5) Bars are now centred on the possession's MIDPOINT rather than grown down from its start, so a bar widened to the minimum height still sits over the moment it happened.

That change exposed a real bug in the no-overlap pass, caught by measurement: it was clamping each team's possessions separately, but every window is drawn in BOTH halves (a team's own offence on its side, the same window mirrored as the other's defence), so neighbouring windows were free to collide — 1.59px of overlap. Rewritten as ONE pass over the whole timeline in time order, clamping against each bar's real drawn bottom rather than its raw end time: overlap now 0.05px (sub-pixel rounding) across all 454 bars. Clamp count rose 4 -> 60, which is the honest cost of centring: more short bars now touch a neighbour and get trimmed.

Readout geometry verified on 3 sample possessions: 3 elements shown (gutter time + both sides), 0px overlap between them, 0px outside the plot; the left side is right-anchored so it reads INTO the centre line and long ones wrap inside their own half instead of spilling across.

## 2026-08-04 02:15 — "get rid of team names on bar lines, offensive rebound -> OR, defensive DR. What the black numbers on the bars?"

**Summary:** Dropped the leading tricode from both side readouts — the side a readout sits on already names the team (the heads are pinned above each half), so "HOU OFF ..." became "OFF ...". Added a _GAIN map so the origin reads in the same codes as the events: "defensive rebound" -> DR, "offensive rebound" -> OR, plus "opponent score" -> "opp score", "offensive foul" -> "off foul", "period start" -> "tip". A readout now reads "OFF X3 OR M2 +2 <- DR".

ANSWER to the question: the numbers on the bars are the POINTS that possession scored. Black ones (44) sit inside bars tall enough to hold the digit, where they read against the solid team-colour fill; white ones (70) hang at the bar's base for possessions too short to fit a digit inside, haloed so they read against the dim fill. Values run 1-4 (a 4 is a three plus an and-1 free throw). Only scoring possessions carry a number — the other 113 have none, which is what tells them apart at a glance.

## 2026-08-04 02:35 — "all events stacked starting in middle"

**Summary:** The bar no longer encodes points by width — each possession now draws ONE BLOCK PER EVENT, stacked outward from the centre line in the order they happened, so the first event of a possession sits against the centre and the sequence reads centre-outward on each side. 227 possessions -> 596 blocks. Codes: M2 M3 FT (solid, a score) and X2 X3 XFT OR DR TOV FOUL VIOL JUMP (outline). A side with no events of its own keeps a small nub so the row still registers. Block width 4.2% holds the widest code; verified 0 blocks run outside the plot and all 454 possession-sides still touch the centre.

Lettering: a first pass lettered every block and measurement caught 119 colliding label pairs (worst 14.5px) — the text box is 17px tall while most bars are only a few pixels, so codes were overflowing onto neighbouring possessions. Now the block is always drawn and the CODE is lettered only where the bar is tall enough to hold it: 87 lettered of 596, 0 colliding pairs. The readouts dropped the event list (the blocks carry it) and keep only the outcome — "+2 <- DR" / "stop" — with the time still printed once in the gutter.

## 2026-08-04 02:55 — "i need to see FL, TO, AST events on our plot others?"

**Summary:** Added the three asked for plus the two that were hiding in the same places, and renamed to the site's own vocabulary: FOUL -> FL, TOV -> TO. Assists live INSIDE the made-shot text ("(Dort 1 AST)") and are credited to the shooter's own team just before the basket; steals and blocks are credit rows carrying NO actionType at all ("Sengun STEAL (1 STL)"), which the walker previously skipped — both now attributed to the crediting team. Every count cross-checked against the raw play-by-play and exact: AST 52/52, STL 18/18, BLK 9/9, FL 53/53, TO 37/37, DR+OR 122/122.

Blocks per game rose 596 -> 673; lettered 109, 0 colliding labels, 0 outside the plot. A possession now reads e.g. "STL AST M2" (stole it, assisted, scored) or "FL X3 OR M2".

Full vocabulary now on the plot: M2 M3 FT (scores, solid) and X2 X3 XFT OR DR TO FL AST STL BLK VIOL JUMP (outline).

ANSWER to "others?" — what else exists in the play-by-play and is NOT plotted, all available if wanted: Substitution (274 rows per 5 games, by far the biggest), Timeout (55), Instant Replay (8), Heave (3). Those are the only remaining action types; everything else in the feed is already represented.

## 2026-08-04 03:10 — "no substitutions, timeouts TM, offensive foul OF, ends poss"

**Summary:** Substitutions stay out. Timeouts added as TM — they carry NO tricode (the club is named in the text, "Rockets Timeout: Regular"), so they resolve through the same nickname lookup the team rebounds use, and they explicitly do NOT end a possession (the ball stays where it was). Offensive fouls split out of FL into their own OF code and DO end the possession.

The offensive foul needed care: the feed records it TWICE, once as a Foul row (subType "Offensive"/"Offensive Charge") and once as the paired "Offensive Foul Turnover" at the same clock. Recording both would have double-counted it, so the turnover row now contributes no separate code while still terminating the possession. Cross-checks, all exact: TM 21/21 timeouts, OF 5/5 offensive fouls, FL 48 (= 53 fouls - 5 offensive), TO 32 (= 37 turnovers - 5 now read as OF). Every OF possession confirmed to end, end_reason "turnover", 0 points.

Nothing upstream shifted: possession counts still HOU 115 / OKC 112, total points still 249 = the actual final score. Blocks 673 -> 688, lettered 114, 0 colliding labels, 0 outside the plot.

## 2026-08-04 03:25 — "why are the first 3 boxes in the plot empty"

**Summary:** A real bug, not missing data. The blocks had events all along — the opening possession is HOU's X3 with OKC's JUMP and DR beside it — but the lettering rule still read `show_label = points > 0`, left over from when the label WAS the point total. So no scoreless possession ever lettered its codes, and the defensive rects were hardcoded `"inside": False`, meaning no defensive block was ever lettered at all. The plot was silently showing only the codes of scoring offensive possessions.

Lettering now depends on the bar's height alone (can the block hold the text?), for both sides: lettered blocks 114 -> 292 of 688, still 0 colliding labels, and a fresh check for "block tall and wide enough to letter but blank" returns 0. Codes now visible across the plot: AST BLK DR FL FT JUMP M2 M3 OF OR STL TM TO VIOL X2 X3 XFT — previously only 11 of the 17 ever appeared.

## 2026-08-04 03:45 — "if you mouse over a not tall enough poss, display poss centered in the same location tall enough to show all events and then collapse on exit"

**Summary:** Short possessions now OPEN on hover. Every block carries its own geometry as CSS variables (--t top, --h height) and always carries its label in the DOM; a block too short to letter gets .psb-tiny, which hides the text at rest. Hovering any block of a possession — or its box score row — grows EVERY block of that possession to --eh (one line of the code type) and re-tops it to `calc(--t - (--eh - --h)/2)`, i.e. it grows about its own middle, then collapses on exit. Measured: 4.9px -> 21.1px -> 4.9px, all 3 blocks of the possession together, centre drift 0.0px, labels none -> block -> none. Pure CSS, no JS.

Two bugs found by measuring rather than eyeballing. The expansion silently did nothing at first — the rule sets height/top but each block carries them INLINE, which out-ranks a stylesheet rule; needed !important. And the first working version lit up the codes on EVERY short block in the plot whenever any one was hovered (a generic `:has(.psb-hit:hover) .psb-tiny .pslab` reveal), which the screenshot showed as stray text scattered over unrelated rows — now scoped per possession, verified 2 labels shown while hovered rather than all of them. Page 367KB -> 533KB for the per-possession open rules.

## 2026-08-04 04:00 — 2023-24 season data fetch COMPLETE

**Summary:** 1,312 games in 338 min (5.6h) at the requested 1 game / 15s: 1,297 complete, 15 partial. All 1,312 play-by-play CSVs written (95MB under outputs/2023-24/); cache now 1.2GB. Every partial is the SAME endpoint failing the SAME way — GameRotation returning JSONDecodeError — and every one of the 15 is a 2024 PLAYOFF game (game ids 004230xxxx, 2024-04-20 through the 2024-06-17 Finals closer).

Checked what that costs rather than assuming: GameRotation is used in exactly one place, plusminus.py's _fetch_game_rotation, which is already written to return None on failure so callers fall back to reconstructing stints from the play-by-play substitution text. Verified by building two of the 15 with the network blocked at the socket layer — 0042300405 (the Finals closer) and 0042300151 — both render fully, 578KB and 559KB, with their ESPN recaps and player tabs intact.

So the season is fully usable: season page, all 30 team pages and all 1,312 game pages can be built offline. The 15 playoff games take the play-by-play stint reconstruction instead of the NBA's tracking data, which is the documented fallback path, not a defect.

## 2026-08-04 04:15 — "mouse over causes the poss under the mouse to expand from the center until it is large enough to display. delete all other non event mouse over text"

**Summary:** All floating hover text is gone — both side readouts and the gutter timestamp, plus their CSS and per-possession reveal rules (0 .psro/.psst elements remain, and the dead styling was removed from the stylesheet too, not just the markup). The event codes inside the blocks are now the ONLY thing hovering reveals.

The expansion also stopped being a fixed height. It was setting height:var(--eh) outright, which grew short possessions but would SHRINK any possession already taller than one line of code type — a real defect the wording exposed. It now grows to max(var(--h), var(--eh)), i.e. "until it is large enough to display" and no further. Measured both directions: a short possession goes 4.9 -> 21.1 -> 4.9px with its labels appearing, and a tall one holds at 28.5px throughout with its labels already up. Centre drift 0.0px in both cases, so a possession still opens about its own middle. Page 533KB -> 386KB with the readouts gone.

## 2026-08-04 04:30 — "make your threshold for showing lower"

**Summary:** Pulled the resting-label threshold from 1.15 label-heights down to 1.05, which letters 317 blocks instead of 292 with still ZERO colliding labels. Chosen by sweeping it against measured collisions rather than picking a number: 1.10 and 1.05 both collide 0; 1.00 letters 338 but 5 pairs touch (worst 2.3px); 0.95/0.90 letter 372 with 12 pairs; 0.85 letters 397 with 20; 0.70 gives 438 with 40; 0.50 gives 497 with 71. So 1.05 is exactly the floor before labels start overlapping — anything lower trades a clean resting plot for stray text sitting on its neighbours. The threshold is now a named constant (LABEL_FIT) with that sweep recorded beside it.

The remaining 324 blocks are not lost: they open and letter on hover, which is what that mechanism is for. Say the word if you want to go below the collision floor anyway — 0.85 would letter 80 more at the cost of 20 overlapping pairs.

## 2026-08-04 04:40 — ".3"

**Summary:** LABEL_FIT set to 0.3 as asked — a code is now lettered at rest whenever its block is at least 30% of a label height. Lettered blocks 317 -> 525 of 688; only 55 blocks stay hidden until hovered (was 324).

The cost, measured not guessed: 94 colliding label pairs, worst overlap 9.7px. That is the trade the sweep predicted — at this threshold most short possessions letter, and where two of them sit within a label height of each other the text overlaps, visible in the plot as codes like "AST/M2" and "FL/DR" printing across their neighbours. The hover expansion still opens any possession cleanly, so the overlapped pairs are always readable on demand.

If the overlap reads badly in use, 1.05 is the last collision-free value (317 lettered) and 0.85 is a middle setting (397 lettered, 20 pairs, worst 3.7px) — one constant either way.

## 2026-08-04 05:05 — "show periods one at a time stacked. period labels across the top select the period to show, 2x period right to show more events" + "larger vertical period"

**Summary:** The plot is now ONE PERIOD at a time. Q1 Q2 Q3 Q4 OT1 OT2 sit across the top as tabs (hidden radios + labels, pure CSS as ever); the selected one underlines in blue and everything tagged to another period — blocks, clock rules, AND box score rows — hides. Each period is laid out on its own canvas, positioned within its own start/end rather than on the game-long axis, so a period fills the whole plot instead of a sixth of it. Canvas raised to 2.6x the container width (3,084px for one period, against ~745px a period used to get on the shared axis).

The gutter changed with it: the Q1..END markers are gone, replaced by the game clock inside the selected period every two minutes (12:00, 10:00, ...), which is the axis that means something once a single period fills the view.

The payoff is exactly the point of the request — with that much vertical room per period, lettering at rest went 525 -> 557 blocks AND colliding label pairs went 94 -> 0. So the plot now letters more events than the 0.3 threshold managed on the game-long axis, and does it without a single overlap. Verified by clicking through to Q3: 145 blocks visible, all of them from Q3, 49 box score rows, labels intact.

## 2026-08-04 05:30 — "get rid of the squares, keep background, mousing over events puts event start mm:ss and duration extending from the center"

**Summary:** The outlines are gone — every block is fill only now (solid for a score, translucent otherwise), verified 0 of 147 visible blocks carry a box-shadow. And each event carries its OWN clock: possessions.py now records a timestamp beside every code it appends (including the assist it infers from the shot text and the steal/block credit rows), checked against the code lists — 0 rows where the two disagree in length.

Hovering an event hangs "11:31  29s" — that event's own start and the possession's length — on the centre line, running outward on that event's side. First cut keyed the reveal on the possession side, so hovering one event lit EVERY readout on that side and they stacked on top of each other at the same y (measured 2-3 shown at once). Each block now carries its own key, so exactly one readout appears: DR -> "11:31 29s", M2 -> "11:26 5s", TO -> "10:24 26s", each verified anchored on the centre.

## 2026-08-04 05:40 — "popup starts outside the last event"

**Summary:** The hover popup was anchored on the centre line, so it printed straight over the possession's own event blocks. It now starts just past the OUTERMOST event of that possession — offset by the stack's full width (event count x block width, plus a small gap) — and runs further outward from there. Verified on four different event types (DR, M2, TO, OR): 0px overlap with any block of their own possession in every case, and every popup still lands inside the plot.

## 2026-08-04 06:00 — "whats in thin empty bar"

**ANSWER:** a possession in which that side's team recorded nothing at all — the nub is drawn so the possession still registers on their side of the timeline. Overwhelmingly it is the DEFENCE: 121 of 227 in the showcase game (53%), and legitimately so — 80 of them are the other team simply making a field goal (no rebound to grab, no foul, no steal), 34 are unforced turnovers with no steal credited, 6 are period ends.

Checking the RARE case — a blank on the OFFENSIVE side — turned up two real bugs:

1. EVENTS WERE BEING LOST ON A RESYNC. The event code was appended to the team's list and only then did close() fire and wipe the lists, so the very shot that revealed a possession change vanished from the possession it belonged to. Resync now happens BEFORE the code is recorded. Proof: X2 (45) + X3 (67) now equals the play-by-play's 112 missed shots exactly; before the fix one was missing.

2. AWAY-FROM-PLAY FOULS INVENTED A PHANTOM POSSESSION. That foul awards a free throw but NOT the ball — the shooting team keeps it. The walker was ending the possession on the made free throw and handing over, creating an empty possession for the other team that only collapsed when the real owner shot again (showing up as a "possession change" desync). Now the ball stays put. Desyncs 1 -> 0, possessions 227 -> 225.

Everything else held: points still 249 = the actual final score, per-period team gap still max 1, zero consecutive same-team possessions. Re-validated across 5 games — desyncs 0 in four of them (one remaining in 0022500064), points reconcile in all five.

Offence-side blanks are now down to 1 in the showcase game: HOU with 2.2 seconds left in OT1, no shot taken. That one is real.

## 2026-08-04 06:10 — "get rid of empty line marker"

**Summary:** The nub is gone — a side with no recorded events now draws nothing at all instead of a 0.7%-wide stub. Verified: 0 blocks without a code and 0 narrow stubs remain; visible blocks in the shown period drop 147 -> 116, which is exactly the empty-side count. Lettering and collisions unaffected (558 lettered, 0 colliding). Page 450KB -> 430KB.

## 2026-08-04 06:25 — "get rid of End column in box score, every line in with box score, append list of events for poss"

**Summary:** End column dropped — the header is now "#  Team  Per  Start  Dur  Pts  Sc  Events" (the start plus the duration already say when a possession ran). Each line now ends with that possession's own event list: the offence's codes in the offence's team colour, then the defence's in theirs, e.g. "1 HOU 1 12:00 29s 0 N  X3   JUMP DR" and "3 HOU 1 11:26 24s 2 Y  FL X3 OR M2". A side with nothing recorded contributes nothing, matching the plot.

"Every line in" — the rows were double-spaced, and the cause was mine: the period reveal sets display:block, which is right for the plot's divs but turned every box row into a block while newlines still separated them in the white-space:pre table, so each row printed with a blank line under it. Rows are now joined without newlines and the blocks supply the line breaks: row pitch is a uniform 28px with no gaps, header sits flush on the first row.

## 2026-08-04 06:35 — "get rid of End column in box score, every line with events add events after timing"

**Summary:** End had already gone in the previous commit (86a7d47c) — confirmed absent from the header — so this landed as the refinement: the events now sit immediately after the timing. Header is "#  Team  Per  Start  Dur   Events" and a line reads "3 HOU 1 11:26 24s  FL X3 OR M2", offence codes in the offence's colour then the defence's in theirs.

Pts and Sc went with the move rather than being stranded after a ragged Events column: M2 / M3 / FT already state what a possession scored, and their absence states that it scored nothing, so those two columns only repeated what the codes say. Say the word if you want them back — they would need to sit before Start to keep their alignment.

## 2026-08-04 06:50 — "dates from initial event start date don't match box score"

**Summary:** Confirmed and fixed. Checked first whether the times were actually wrong: no event in the game predates its own possession's start (0 of 224), so nothing was mis-ordered. The disagreement was one of MEANING — the popup showed each EVENT's own clock while the box score line shows when the POSSESSION began, and those differ by a median of 11s (max 29s; only 31 of 224 possessions have their first event on the same tick as their start, because a possession begins when the team gets the ball and the first recordable event is usually the shot at the end of it).

The popup now leads with the possession's start and length, matching its box score line exactly, and appends the event's own clock after a separator when it differs: "12:00  29s   · 11:36" against box row "1 HOU 1 12:00 29s X3 JUMP DR". Verified across five event types — 5/5 popups agree with their box score line, and the per-event timing is still there rather than being thrown away.

## 2026-08-04 07:05 — "why HOU and OKC on the same line at the first event?"

**ANSWER:** because that line is ONE possession window, and both teams act inside it. HOU had the ball 12:00-11:31; on their side sit the events they produced (the tip they won, their missed three), and on OKC's side sits the defensive rebound that ENDED it. Every line works that way — one possession, the offence's work on its side, the defence's on theirs, meeting at the centre. Verified by grouping the blocks: possession 0 offence = JUMP + X3 on the LEFT, defence = DR on the RIGHT, all at the same y.

But the question exposed a REAL bug, now fixed. The jump ball was sitting on OKC's side when HOU won it. The play-by-play files a jump ball under the JUMPER's tricode — every tip row in this game reads teamTricode OKC because Holmgren/Dort/Hartenstein jumped — while the description says who actually came away with it ("Tip to Thompson"). All four tips in this game went to HOU and were being credited to OKC. The walker now reads the name after "Tip to" and attributes the JUMP to that player's team, using a player->team map built from the game's own rows.

Nothing else moved: possessions still HOU 114 / OKC 111, points still 249 = the actual final score, 0 consecutive same-team possessions, 0 desyncs.

## 2026-08-04 07:25 — "first line in plots has blue and red events"

**Summary:** Flagged twice, so the model changed rather than being re-explained. The defensive rebound is how the NEXT team GETS the ball — exactly as the user defined a possession's start ("we rebounded a missed 2P, 3P or last FT") — so it now opens THEIR possession instead of being filed as a defensive footnote on the possession it ended. (A steal already behaved this way: its credit row follows the turnover that closed the previous possession.)

First line is now HOU alone — "JUMP X3", all one colour — and the rebound leads the next line as "DR AST M2" in OKC's blue. Lines mixing both teams' colours dropped from 49 of 49 to 7 of 49, and the 7 that remain are the genuinely simultaneous cases: a foul, block, violation or timeout by the defence DURING the possession, which really did happen inside that window and nowhere else (31 FL, 5 BLK, plus a few combinations).

DR count unchanged at 72, OR 50, together the play-by-play's 122 rebounds. Possessions still HOU 114 / OKC 111, points still 249 = the actual final score.

## 2026-08-04 07:55 — "the VIOL belongs to the next poss"

**Summary:** Generalised into a rule rather than special-casing the one violation: an event committed by the team WITHOUT the ball is that team's own doing, so it is held and recorded on THEIR next possession instead of on the possession it happened during. That covers kicked balls, fouls, blocks and timeouts by the defence — the defensive rebound already worked this way, and a steal needs no holding because the turnover it belongs to has already handed that team the ball.

The first VIOL now reads exactly as asked: HOU's possession at 10:50 is "X2 OR TO" alone, and OKC's next possession at 10:24 opens "VIOL TO".

Blocks needed a second pass — they arrive as credit rows with no actionType and took a different code path that bypassed the new rule, leaving 8 mixed lines after the first fix. Routed through the same hold.

Result: EVERY line now shows exactly one team. 0 of 225 possessions carry the other team's events, and 0 of the 49 drawn possessions mix the two team colours (measured per possession — an earlier "22 mixed" reading was my own check comparing rgb() against rgba() strings and grouping by pixel row, not a real defect). Nothing was lost in the move: VIOL 3/3, FL 48/48, OF 5/5, BLK 9/9, STL 18/18, TM 21/21, AST 52/52, TO 32/32 against the play-by-play, possessions still HOU 114 / OKC 111, points still 249 = the actual final score.

## 2026-08-04 08:05 — "on the mouse line for 1st OKC event has start dur + parts of the end time which we no longer use. get rid of end part"

**Summary:** The popup was "11:31  5s   · 11:26" — the trailing figure was the event's own clock, appended back when the popup and the box score disagreed, and it reads as an end time. Dropped. The popup is now just the possession's start and length: "11:31  5s" against box row "2 OKC 1 11:31 5s DR AST M2". Checked on four events (DR, AST, M2, VIOL) — every popup is two fields and matches its box score line exactly.

## 2026-08-04 08:20 — "make events thickness less"

**Summary:** Blocks are drawn thinner: a new BAR_THICK = 0.45 gives each block 45% of its possession's span, centred in the band, so relative durations stay proportional but the plot reads far lighter. Median bar height 65.7px -> 29.6px (max 132 -> 59, min 2.7 -> 1.2). Swept 0.55 / 0.40 / 0.30 first — all held 556 lettered and 0 colliding labels — and settled on 0.45 between them.

Also corrected while doing it: the "can this block hold its code" test was measuring the possession's FULL span, not the thinner block actually drawn, so it would have lettered blocks that no longer had the room. It now tests the drawn height.

One honest consequence: 23 labels extend past their block. That is the 0.3 label threshold at work — it letters a code whenever the block is at least 30% of a label height, so on the thinner bars the text overhangs. Nothing collides (0 pairs) and everything stays readable, but raising LABEL_FIT would trade some lettering for tidier blocks if you want it.

## 2026-08-04 08:35 — "move Q1..OT2 selectors to left margin"

**Summary:** The period selectors moved off the bar above the plot and into the LEFT MARGIN, stacked down beside the canvas: Q1 Q2 Q3 Q4 OT1 OT2 with the selected one lit and marked by a blue rule on its right edge (was an underline when they sat horizontally). Verified: all six in the margin, one per row, none overlapping the plot area; clicking Q2/Q3 still shows only that period's blocks and lights only that label.

First placement put them at the same x as the clock labels — "Q1" printed straight over "12:00". Narrowed the selector column so it sits at the far left with the clock labels keeping the inner gutter: selectors now end at x=146, clock labels start at x=204, measured 0 overlaps between them.

## 2026-08-04 08:50 — "Qs should be one line stuck on left margin, move center line of plot to the left. Make plot overall thinner without crowding"

**Summary:** Three changes. The period selectors are back on ONE line, hard against the left margin (x=50, all six on the same row, verified single-row). The plot's centre line moved from 57% to 42%. And the drawn band is narrower: each half's reach cut 39% -> 23.5% (the longest possession in a game is 6 events) and block width 4.2% -> 3.8%, so the whole plot now occupies x=228..814 of an 1186px canvas instead of spanning nearly all of it.

Crowding checked rather than eyeballed: the widest code, "JUMP", measures 35.1px inside a 45.1px block, and across every visible label 0 spill their block horizontally (worst overhang 0.0px). Lettering unchanged at 556.

Note on the check itself: a first pass reported 441 codes overflowing, which was my test being wrong, not the layout — it compared labels in HIDDEN periods against their zero-width parents, since getComputedStyle on an element inside a display:none ancestor reports its own display, not none. Measuring actual edges gives 0.

## 2026-08-04 09:05 — "set 'P time dur' on top of event, add period as 'P' compress 30% vertically"

**Summary:** The readout now reads "P1  12:00  29s" — period, possession start, duration — and rides directly on top of the event block it belongs to, left-aligned with it, instead of hanging off past the end of the stack. Canvas compressed 30%: 3,084px -> 2,158px for a period.

One thing measurement caught: the readout first sat 7px INSIDE its block. Short possessions expand on hover, so the block's top moves up while the readout was still positioned at the unexpanded top. The readout now carries the same --t/--h variables and resolves its top with the same max(--h,--eh) expression the block uses, so the two move together — verified on four events, gap above the block exactly 0px and left edges aligned to 0px in every case.

## 2026-08-04 09:25 — "no mouse over, P TIME DUR always setting on Events anchored to center line, start end of session anchored to middle"

**Summary:** Hover is gone from the plot entirely. Every possession now carries its "P1  12:00  29s" stamp permanently, straddling the CENTRE LINE and vertically centred on its own possession — 49 stamps on the shown period, all measured centred on the line. The events stack outward from either side of the stamp instead of from the bare centre, so nothing sits under it: 0 stamp/block overlaps measured. Geometry moved to suit — centre 42% -> 47%, each half's reach 23.5% -> 29% to fit the stamp plus the longest possession (6 events). All the per-event reveal CSS came out with the hover, taking the page 436KB -> 372KB.

One honest defect: 4 stamps collide with a neighbour's. They are consecutive short possessions whose stamps are taller than the possessions themselves (e.g. "P1 10:11 4s" against "P1 10:07 15s"). With the stamps always on there is nowhere for them to go — suppressing the stamp on very short possessions, or shortening it to "12:00 29s", would clear them if you want that.

## 2026-08-04 09:40 — "poss number per team colored and anchored to left edge of ticker table"

**Summary:** Every possession now carries its team's OWN running count in the far-left column, in that team's colour and level with the possession: HOU counts 1..25 in red and OKC 1..24 in blue through the shown period, interleaved down the page. 49 numbers, colour split verified 25/24.

Anchored on the box score table's left edge rather than eyeballed — the numbers start at x=87 and the table's rows start at x=87, so the plot's first column lines up with the table's below it. A first attempt anchored them to the clock column instead, which put them 7px off its edge and collided one number with a clock label; measured 0 clock overlaps after the move.

## 2026-08-04 09:55 — "date duration sits on top of not beside the event list. the score should be in the middle and extending out"

**Summary:** Two moves. The "P1 12:00 29s" stamp now rides ON TOP of the event list — centred over the centre line and lifted clear above its own blocks — instead of sitting beside them on the line. And the POSSESSION'S SCORE takes the middle: the points it produced sit on the centre line in the team's colour (values 1/2/3, blank when it scored nothing), with the events extending outward past it. The centre reservation shrank from 11.6% (the old stamp) to 3.6% (the score), so each half's reach came down 29% -> 26% and the whole band is tighter. Verified: 49 stamps, 49 scores, every score measured centred on the line.

Honest defect: 14 of 49 stamps overlap a neighbouring possession's blocks. A stamp is lifted a full line above its own row, and where two possessions sit close together that line lands on the one above (visible around "P1 10:11 4s"). Shortening the stamp to "12:00 29s", or suppressing it on short possessions, would clear it — say which you prefer.

## 2026-08-04 10:10 — "get rid of the score in the middle. game time sets on the upper outer edge of the event list, remove all p1s, p2s, etc"

**Summary:** The centre score is gone (0 .pscore elements) and the events start on the centre line again, so each half's reach came down 26% -> 24%. The game time now hangs on the UPPER OUTER corner of its event list — off the far end of the stack, on the side the stack grows toward, lifted a line above the row — and reads "12:00  29s" with the period prefix dropped (verified: 0 stamps begin with P).

A useful side effect of moving it outward: stamps overlapping a neighbouring possession's blocks fell from 14 to 3, since the outer corner is empty space where the centre was crowded. The 3 that remain are consecutive short possessions on the same side.

## 2026-08-04 10:25 — "undo last"

**Summary:** Reverted 55655691 (clock times flush on both edges of the event list) with git revert, so the history keeps both the change and its undo. Back to one clock label per rule, sitting right-aligned in the gutter just left of the band: 7 labels, 0 doubled edge labels, label ends at x=311 with the rule starting at 323. Page rebuilt.

## 2026-08-04 10:35 — "the left side clock time aligns set left side and above of the events. the right side aligns with the right edge of the events over the right top of the right side events"

**Summary:** The time flipped from hanging OUTSIDE the stack to aligning WITH it. A left-side possession now starts its time on its events' left edge; a right-side possession ends its time on its events' right edge — both sitting a line above the row, over the top corner of their own events. (It previously anchored at the outer end and ran outward, away from the events.)

Alignment is exact by construction — the anchor is CENTRE -/+ (event count x block width), the same expression that places the outermost block. Measured 36 stamps that could be matched to their row: 35 exact to the pixel. The one 20px outlier is in the crowded pair near 10:11/10:07 where two possessions nearly share a row, so the geometric matcher picked up the neighbour's blocks rather than its own.

## 2026-08-04 10:50 — "the right side aligns with the right edge of the events ... unless the date time string is longer than the length of events then align to left edge to left edge"

**Summary:** The time now flips when it cannot fit its own events. Normal case unchanged — a right-side possession ends its time on its events' right edge, a left-side one starts on their left edge. When the string is wider than the event stack (measured from the character count at the label's own size, with a 0.4% margin so a borderline fit does not round over the line), it flips to hang off the CENTRE and run outward instead, away from the other team's half. Applied to both sides for the same reason, though only the right was asked about: a left-side stamp that overruns would otherwise cross the centre just the same. 9 of 36 possessions take the flip — mostly single-event possessions, where one 45px block cannot hold an 88px string.

Verified: all 36 stamps touch one of their own edges or the centre, and 0 genuinely cross the middle. One case flagged as crossing turned out to be a zero-length possession's "0:00 0s" stamp, correctly flipped outward — my check had matched it against a neighbouring possession's block at almost the same height and so judged it from the wrong side.

## 2026-08-04 11:00 — "reverse events lists"

**Summary:** The plot's stacks are reversed: a possession's LAST event now sits against the centre line and its FIRST at the outer edge, so each row reads outside-in in the order it happened — the same direction the time stamp anchors from. Left side reads left-to-right "JUMP X3" and "FL X3 OR M2"; right side reads "M2 AST DR" left-to-right, i.e. DR (first) at its outer right edge inward to M2 (last) at the centre.

The box score list is left as it was, chronological left-to-right ("DR AST M2"), since a table reads that way — say the word if you want it flipped to match the plot.

## 2026-08-04 11:10 — "move time/dur to extend from the centered end of the events"

**Summary:** The time now starts at the CENTRED end of its event list — the end touching the centre line — and runs outward from there, above the row. All 49 stamps measured anchored on the centre, 0 crossing it.

That also retired the fit test added two changes ago: when the anchor was the outer edge, a stamp wider than its own events ran back across the middle into the other team's half, so it had to measure itself and flip. Anchored at the centre it always runs the right way and the special case is gone.

## 2026-08-04 11:25 — "time stamp moves to the end of the events line and extends. right side extend right and left side extends left"

**Summary:** The time came down onto the event line itself — vertically centred on the row rather than lifted above it — and now sits at the outer END of the events, running away from the middle: the right side extends right, the left side extends left. Verified all 49: every stamp on its own event row, 0 overlapping their blocks, 0 extending the wrong way.

Note: the edit had already been written when the run was interrupted, so this landed from the same patch rather than being redone.

## 2026-08-04 11:55 — "aligned horizontally for the left and right time events. left pair and right pair butted together in the middle"

**Summary:** Reverted the centring (65b3fc29) — that description is the arrangement it replaced. Each side is now a horizontal pair on one line, time then events, with the two pairs meeting in the middle: [time][events] | [events][time]. Verified all 49 — every stamp on its own event row, every one butting its list with a gap measured at 0.0px, and all 49 lists touching the centre line.

## 2026-08-04 12:10 — "the left side time/events pair are not vertically centered"

**Summary:** Real bug, and it was mine. The period-reveal rule sets display:block on EVERYTHING carrying a period class, which clobbered the display:flex that the time stamps and the possession numbers use to centre their text in the row — both were computing to block and rendering top-aligned inside a 37px box. The reveal now restores flex for those two, so they centre again.

Measured after: stamp and number both compute flex, and the vertical offset between a stamp and its own events is 0.0px on BOTH sides — 25 left, 24 right, worst case 0.

Worth noting the earlier check missed this: it matched a stamp to its blocks BY vertical proximity, so a vertical offset could not show up. Matching on horizontal adjacency instead exposed it immediately.

## 2026-08-04 12:25 — "the first position at 12:00 should be vertically aligned with 12:00. next at 11:31 vertically aligns over 11:31 and so on"

**Summary:** Rows anchor on their START time now instead of their span's midpoint: each time/events pair is vertically centred on where its start falls on the clock axis, so the 12:00 possession sits ON the 12:00 rule and the 11:31 one at 11:31's height. Duration still shows as bar height (45% of the span) and the sequential clamp still stops a row backing into the one above.

Verified from the stamps themselves — every row's centre compared against where its own declared start time falls on the axis: 45 of 49 exact (0.0px), worst deviation 4.4px on the 4 rows the no-overlap clamp had to nudge (consecutive possessions whose rows physically collide, e.g. 11:26 pushed 4.4px below a row that ends where it begins). Width-clamp count fell 50 -> 14 as a side effect: start-anchoring spreads neighbouring rows apart more naturally than midpoint-centring did.

## 2026-08-04 12:40 — "align left time with left edge of key label, align right time right edge with end of right time grid"

**Summary:** The times moved into fixed outer columns. Left side: every stamp's LEFT edge aligns with the clock key labels' left edge (measured "12:00" at the tick font = 4.05% wide, anchor baked as CENTRE - COL_W - 1 - 4.05 = 17.95%). Right side: every stamp's RIGHT edge ends flush with the right end of the time grid (CENTRE + COL_W = 71%). Verified: 25 left stamps at 0.0px off the tick edge, 24 right stamps at 0.0px off the grid end.

Two collisions surfaced and were handled with a backdrop rather than moved: a possession that starts ON a tick (every period opens at 12:00) puts its stamp exactly over the tick label — they printed over each other as "12:0029s" — and a 6-event stack reaches into the time column (4 rows). The stamp now carries the black backdrop + ring the karma readouts use, so it prints cleanly over both; it repeats the time the tick showed anyway.

## 2026-08-04 12:55 — "if our left side time is over the scale move it to the right so it clears the grid scale"

**Summary:** A left-side time whose row lands on a 2-minute scale label now shifts right by one stamp width (4.55%) so the scale stays readable beside it — the first row reads "12:00" (the scale) then "12:00  29s" (the possession) side by side instead of overprinting. The test is done in game seconds (a ~1.1%-of-plot band around each 120s multiple), so it follows the period's own span. Verified: 6 left stamps shifted, 19 stay at the column, and 0 overprint a scale label — the backdrop from the previous change now only ever covers event blocks, never the scale.

## 2026-08-04 13:05 — "are all fonts the same?"

**ANSWER:** Two families at four sizes, all mapped to game-page constants rather than invented: DejaVu Sans 19.7px for titles/heads/period selectors (= _TITLE_FONT_CQW), Sans 16.7px for the clock scale (= karma's 8pt ticks), DejaVu Sans Mono 18.5px for the box score header+body (= _BOX_FONT_CQW), Mono 14.6px for event codes / time stamps / possession numbers (= karma's 7pt). Convention: labels are Sans, data is Mono so digits align — the same split the karma panels use.

## 2026-08-04 13:20 — "all fonts on possessions the same"

**Summary:** The whole possessions plot now uses ONE font: DejaVu Sans Mono at the box score's own size (_BOX_FONT_CQW, 18.5px at 1200) — period selectors, team heads, clock scale, possession numbers, time stamps and event codes all measure identical (a single distinct family@size across every probe). The plot and its box score now read as one piece of type.

The size change (14.6 -> 18.5 for the small elements, and the scale/heads dropping from their old sizes) moved every text-derived anchor, so those were re-derived rather than left stale: the tick label "12:00" is now 5 mono chars at the shared size (TICK_W, computed not hardcoded), the left time column starts where the ticks start (19 at the column, 0 measured off it), and the on-a-tick shift uses TICK_W + 0.5 (6 shifted, 0 overprinting the scale). Codes still fit their blocks (0 spilling, 0 collisions; lettered 110 at rest, down 4 from the bigger glyphs).

## 2026-08-04 13:30 — "move colored count to right side past time stamp"

**Summary:** The team-coloured possession count moved from the far-left column to the RIGHT side, one slot past the right time column — at CENTRE + COL_W + 1, just beyond where the right stamps end flush with the grid. Verified: all 49 numbers sit past the grid's right end, 0 collide with a time stamp, all inside the plot, colours still 25 red / 24 blue.

## 2026-08-04 13:40 — "align left outer edge timestamps"

**Summary:** All 25 left-side times now share ONE left edge. The uniform column sits just past the scale labels (TIME_L = CENTRE - COL_W - 0.5, i.e. half a percent left of the grid's left rule), which also made the per-row near-tick shift unnecessary — deleted, along with the two-edge raggedness it caused (the previous build measured left edges at 256 AND 317; now a single edge at 317, 0 stamps overprinting the scale). The scale labels keep the outermost strip to themselves.

## 2026-08-04 13:50 — "decrease event width for 2 char events"

**Summary:** Block width now follows the code: 2-character events (M2, X3, DR, OR, TO, FL, FT, OF, TM) draw at 2.6% (31px) while 3-4 character ones (AST, STL, BLK, XFT, VIOL, JUMP) keep 3.8% (45px). The stacking offset became a running sum of the actual widths instead of n x fixed, so mixed rows still butt exactly. Verified: exactly two block widths on the page (31px for 2ch, 45px for 3+), 0 codes spilling their block, 0 gaps or overlaps within any row. Rows read visibly tighter — "FL X3 OR M2" went from 4 uniform slots to 4 snug ones.

## 2026-08-04 13:58 — "XFT is X1"

**Summary:** The missed free throw renamed XFT -> X1, completing the family: X1/X2/X3 are the missed 1/2/3-point attempts alongside M2/M3 (and FT for the made free throw). Verified 9 X1 on the page = 9 missed free throws in the play-by-play, 0 XFT remaining, and as a 2-character code it picked up the narrow 31px block automatically.

## 2026-08-04 14:10 — "align the Q1 with possessions, move time grid to the left aligned with Q1"

**Summary:** The whole axis hangs off the page's own left margin now. The Q1..OT2 row left-aligns with the Possessions title (both at 87px, exact), and the time grid moved left so its scale labels start at that same edge (86px, within a pixel — the ticks are right-aligned in their column so the widest label "12:00" defines the edge). CENTRE stopped being a hand-picked 47% and is now derived: page margin + tick width + gap + half-reach = 32.75%, so the left-margin alignment survives any future font or reach change. The whole band moved ~14% left, leaving the free space on the right where the counts now sit. GUTTER, dead since the stamp column replaced it, deleted.

## 2026-08-04 14:20 — "move everything but time grid bit to right"

**Summary:** The content stepped right while the time grid stayed put. New split: GRID_L (rule start + scale column) keeps the page's left margin exactly where it was — scale still at 86px, still flush with Q1 — and the content centre now derives as GRID_L + SHIFT + COL_W with SHIFT = 4%, so the stamps, event stacks, and counts all sit ~50px further right (stamp column 148 -> 195px, a clear 54px of water between the scale and the content). The grid rules were widened to span from their unchanged left edge under the shifted band, so the rightmost event still sits on a rule; the counts remain inside the plot.

## 2026-08-04 14:28 — "time stamp '1:10m SSs' remove extra space between them"

**Summary:** The stamp's double space between time and duration is now a single space: "12:00 29s" instead of "12:00  29s". Verified on the rendered page.

## 2026-08-04 18:36 — "copy the Possession plot with hide/show controller to the player page at the end."

**Summary:** The possessions plot and its box score now close every game page, both folded shut by default. The section moved into a shared module (`src/nba_pbp/possessions_section.py`) that the game page and `test_page.html` both render, so the two can't drift — verified byte-identical markup apart from the `open` attribute. An audit before any code changed found six ways a naive copy would have broken the page, all fixed by making the block's CSS private (`ps-canvas`, `ps-fnt`, `ps-fnl`, `ps-xtick/ytick`, `psp{N}`, `pp{i}`, `--ps-*`) and borrowing only `.kbox`/`.kb-fold`/`summary.ktitle`/`.bx-flow`/`.bx-fold` from the page's own furniture. Regrouping the hover links into three selector lists cut the section's CSS from 208 KB to 32 KB. Cost per page ~+205 KB raw / ~+21 KB gzip; at fleet scale that is ~+540 MB raw across 2,624 pages, which is worth a decision before a full rebuild.

Verified on the rebuilt showcase page against a pre-change copy: every pre-existing section identical in height, karma titles still absolute at left 7.6%, no `.img-box` gained an aspect-ratio, `.fnt` furniture unchanged, karma grid lines gained no border, fonts resolve with zero failed requests, no duplicate ids, and closing any one of the 17 folds blanks no other section. All-closed pitch is exactly 40.00px across all 12 titles now (the seam into the new section came in at 43.95px first — the previous wrap ends on a closed karma box, a case the adjacency rules didn't cover — fixed with two more rules). Section behaviour intact on the game page: all six period tabs, thin-block hover expansion (5.2 -> 26.8px), label reveal, and both-way block/row highlighting. A forced section failure prints a skip line and still writes the page. All five showcase pages rebuilt.

## 2026-08-04 19:24 — "trim the decimals and drop the redundant top"

**Summary:** Each possession block wrote its top and height twice — once as `--ps-t`/`--ps-h` and again as `top:`/`height:` — so the CSS rule now reads the geometry off the custom properties the hover rule already depends on, and the inline pair is gone. Vertical percentages went from 3 decimals to 2. Together that is **−14,934 raw / −2,672 gzip per page** (mean over the five showcase pages); the showcase game is 927,250 → 910,658 raw, 91,317 → 88,482 gzip. The section's cost over a page without it drops from +210,790 to +194,198 raw, so a full 2,624-page fleet is ~509 MB rather than ~540 MB.

The audit found a latent bug worth more than the bytes. Rounding `top` and `height` **independently** lets each drift by its own rounding unit, which silently un-flushes block pairs the no-overlap clamp made exactly flush. Measured over all 3,936 cached play-by-plays: **68,444 exactly-flush pairs, 6,173 of them (9.02%) broken by the `.3f` scheme that shipped this morning.** The fix is to round the block's two EDGES on the emitted grid and let the height fall out of them (`_q(bottom) - _q(top)`), so a block's drawn bottom is byte-identical to the next block's drawn top. Rounding is monotone, so this holds at any precision: **0 broken at `.2f`**, zero non-positive heights, minimum rendered height 0.12%. The clamp itself still compares exact floats — only what is emitted gets snapped.

Verified by capturing every mark's rendered rect in WebKit, before and after, keyed by DOM index so a moved block can never be matched to a neighbour: 1,083 marks over 6 periods. Horizontal geometry is **exactly** unchanged (max dl and dw both 0.0000px — no horizontal value was touched); vertical moved at most 0.110px (top) and 0.188px (height), both inside the analytic one-rounding-unit bound, on a canvas that measures 1186 × 2158.3px (the scrollbar gutter takes 14px — it is not 1200 wide). Zero overlapping block pairs in every period. Box score text, `.psb-tiny` count (39), and `build_section(...).info` including `clamped: 14` all identical. Hover, the six period tabs, both folds, and the 40px pitch still pass on both pages, and nothing already on the game page moved.

`!important` stays on the hover rule: it is no longer needed for specificity, but it costs 20 bytes and is the only thing that keeps hover alive if an inline `top`/`height` is ever put back.

Two notes for later. The label-at-rest test now reads the rounded height rather than the exact one — 0 verdicts flip on the showcase game, ~182 across the fleet (1 per 22 games), and deciding on the height that actually renders is the more correct behaviour. And the big remaining raw levers are wire **losses**: hoisting the four repeated background fills to classes saves 9,812 raw but costs +604 gzip, and hoisting `--ps-t`/`--ps-h` into per-possession rules saves 18,674 raw for +123 gzip — long identical runs are what gzip is best at. The cheapest real win left is stripping the section CSS's own comments (−1,132 raw / −579 gzip), which trades the built page's self-explanation for half a kilobyte.

## 2026-08-04 20:55 — "the docstring of `plot_plus_minus_by_player_html` is stale and actively misleading"

**Summary:** Documentation only — the rebuilt showcase page is byte-identical with and without the change (verified by building it twice across a `git stash`). The docstring claimed the figure was rendered to SVG, embedded once per render as a data URI in a CSS custom property, and cropped into page slices via `background-size`/`background-position` to dodge a Chrome bug with tall inline SVGs. None of that survives: the page has zero `data:image`, `<svg>`, `<img>`, `background-image`, `.png` or `.svg`, and its only four `url()` are the `@font-face` rules. matplotlib is a LAYOUT ENGINE now — the figure is closed without a single `savefig`, and every mark ships as an absolutely positioned div (`.ppl-u/.ppl-d/.ppl-h` steps, `.ppd` dots, `.ppt` names, `.khl` grid, `.khb` bars, `.kev` glyphs, `.fnt` text) inside empty `.simg` boxes that carry only each band's aspect-ratio.

Two claims in the same docstring that the brief expected to keep turned out to be stale as well, and were rewritten from the built page rather than preserved. The toggle structure is no longer "three toggles per team": the karma title folds its own panel, there is ONE combined lineups section between the teams with the second team's blocks mirrored, and a Possessions section closes the page. And **nothing is open by default** — the page emits no `<details open>` at all (24 folds, all closed), so the old "open by default … reading Less while open" was wrong twice over. The recap toggle is labelled "ESPN Update", not "Summary".

The bigger find is what `tooltips` now means. `_overlays_for_slice` early-returns on `not tooltips`, and that same pass is what emits the chart marks — so `--no-tooltips` does not produce "the same page with no hovers", it produces a page with **empty plot bands**: measured 0 `.ppl`, 0 `.khl`, 0 `.fnt` vs 1394 / 1415 / 97 with tooltips on (314,471 vs 910,658 bytes). The CLI flag still defaults to False. Behaviour left alone; the docstring, the `--tooltips` help text and GUIDE.md now say so.

Also corrected across `plotting.py`: the module header (no chart it emits contains an image; the SVG helpers survive only for `_save_fig_html`, which nothing calls), the slice-cut comment, the karma/box-score cut comments, `_overlays_for_slice` (it draws the charts, not just tooltips), the `.chart-wrap`/`.img-box`/`.lineup-box`/`.gnav` CSS comments, the event-cycler "layer image" comments, and the karma-title comment in `_draw_event_sum_panel`. `redraw_rate_views` is documented as CURRENTLY UNUSED — it is built and returned but never called, so the per-8 switch swaps only the HTML table and the lineup plot is identical in both views. Comments that describe history in the past tense ("replaces the SVG-baked box score", "the aspect-ratio its SVG band used to have") were judged accurate and left. Roughly 25 comments still say "image" as shorthand for a slice box; instead of a risky mass rename, a vocabulary note at the top of the module says what the word means there. `cli.py` also lost "(SVG embedded directly, no JS/Plotly)". GUIDE.md's two claims ("no images beyond embedded SVG", "charts embedded as SVG data URIs") are fixed but not staged, per the brief's `git add src scripts LOG.md`.

Not touched, flagged instead: README lines 129 and 151 still describe charts "embedded as SVG", but they sit inside blocks documenting `nba-pbp plot`, `season-events-3d`, `winprob` and `games` — commands the CLI no longer registers (it has fetch, plusminus-players-html, season-events-2d-html, nba-season-html, rebuild-test-games, fetch-games, flush-cache). Fixing the SVG wording there would polish sections that are wrong at a deeper level. README line 123 is accurate. Separately: the page still ships an `img{...}` CSS rule for a tag it never emits (now commented as dead), and rebuilding the showcase game reproduced the shipped file except for one tab-window height, 23.445 vs 23.448cqw — same byte length, a pre-existing sub-pixel non-determinism, present before this change too.

## 2026-08-04 21:12 — "do all font size choices in Possession match those in OKC Players" / "do all four"

**Summary:** They didn't — 4 of 8 shared roles matched, 4 didn't. Everything that matched was page chrome (fold title, fold arrow, box-score header, box-score body), and it matched because both sections read the same two host constants. Everything that mismatched was plot furniture, where Players inherits matplotlib point sizes and Possessions had collapsed onto one body size. All four are now aligned role for role, verified by getComputedStyle in WebKit:

| role | Players | Possessions before | after |
|---|---|---|---|
| selector tabs | 19.680px sans | 18.480px mono | **19.680px sans** |
| x tick (team heads) | 16.668px | 18.480px | **16.668px** |
| y tick (game clock) | 14.580px | 18.480px | **14.580px** |
| in-plot glyph | 16.368px | 18.480px | **16.368px** |

The intention was already in the file and never wired: `TICK_CQW = _pt(8)` computes **exactly** the Players x-tick size and was referenced nowhere, and `HEAD_CQW` said "panel-title size, for the team heads" but only ever set a height. Added `YTICK_CQW = _pt(7)` and `GLYPH_CQW = _pt(sqrt(32)/0.72)` — the latter being the same marker footprint the karma panel's own declutter pass spaces its glyphs by — so every constant now names the karma artist it mirrors.

Three coupled constants had to move with them, and each would have been a silent defect on its own. `TICK_W` is literally 5 mono character advances of "12:00" and feeds `GRID_L`, so the clock gutter followed the clock label down (55.66 -> 43.93px, and the whole content band shifted ~12px left with it). `label_h_pct` is the test that decides which blocks letter at rest, so it reads `GLYPH_CQW` now — psb-tiny blocks fall 39 -> 32, i.e. seven more codes are permanently legible, which is what `LABEL_FIT = 0.3` was swept for. `--ps-eh` is one line of the code type but `.evr`/`.pnum` open to the same height carrying the larger tabular face, so it is now `max(GLYPH_CQW * 1.45, LAB_CQW * 1.25)`. `.pshead`'s reserved height follows `TICK_CQW`, the size it actually holds.

One miss caught by measuring rather than computing: the tabs first came out 19.728px against Players' 19.680px, because `_TITLE_FONT_CSS` rounds the shared constant to 2 decimals and I emitted 3. Emitting at the host's own 2dp lands it exact.

Verified: all six comparable roles now agree to <0.01px; 0 event labels collide at rest (113 shown); 0 time stamps collide; 0 possession blocks overlap; the clock column keeps 53.23px of water before the content. Hover, six period tabs, both folds and the exact 40px pitch all still pass, and nothing already on the game page moved. Deliberately left alone: mono stays on the clock scale and the event codes, because `TICK_W`'s gutter arithmetic depends on a fixed pitch and Players' own glyph face is mono too — only the tabs and heads, whose Players counterparts are sans and which carry no alignment dependency, changed face.

**Pre-existing defect found, not introduced and not fixed here:** 9 pairs of possession-count digits (`.pnum`) overlap vertically, worst 11.1px. Measured identically before (11.12px) and after (11.15px) this change; the flex boxes actually improved 13 -> 11 overlapping pairs. It comes from `--ps-eh` expanding short possessions' count boxes past their own span. Worth a separate look.

## 2026-08-04 21:41 — "change +/- to PM in game page"

**Summary:** All 59 rendered occurrences on the game page now read `PM`, from 4 sites / 5 line edits in `plotting.py` plus 3 in the hand-maintained `help.html`. This brings the game page into the convention the team and season pages already use (`nba_season.py:73` pairs label `"PM"` with key `"+/-"`; `team2.py` and `nba_season.py` both carry `_DN` maps doing the same). Sites: the box-score header (52 occurrences, via `_box_score_header_line`), the karma panel's Hide/Show switch (2+2), the event cycler's `PM Events` state (2), and the combined-lineup panel's y-axis label (1).

The hazard was that `+/-` is 3 characters and `PM` is 2, in whitespace-aligned monospace tables whose colour overlays are positioned from character offsets. Keeping the `:>4` makes it width-neutral: both header lines are 101 chars, only indices 32/33/34 change glyph, the field boundary at 35 does not move, and `PM` right-aligns on exactly the two columns the values' last two digits already use. From column 24 onward the game header is now byte-identical to the shipped team page header.

Roughly two dozen `"+/-"` in `plotting.py` are internal KEYS (`view["+/-"]`, `order.index("+/-")`, `NOSEL` members, colour-map keys), all inside `plot_season_events_2d_html`, which does not execute for a game page — renaming any is a KeyError, not a relabel. Two `ax.set_ylabel("+/-", color="gray")` lines are byte-identical to each other and only ONE emits (the other panel's axes are never harvested), so the edit was anchored on the following line to disambiguate. A blanket `sed s/+\/-/PM/g` would have hit both traps. Left deliberately: `<title>Plus/minus by player</title>` and 3 `aria-label`s — "PM by player" reads badly as a page title and screen-reader text is better spelled out.

Verified against a pre-change copy. The strongest check was reverse substitution: replacing the five new strings back in the rebuilt page reproduces the baseline **byte for byte** (0 bytes differ), page exactly 7 bytes shorter, exactly 56 lines changed, residual `+/-` = 0. Since every offset on this page is emitted as literal text, that one check proves nothing else moved — corroborated by the 21,514 emitted offset tokens being identical in document order. Rendered in WebKit at 1400×1000: all 2,300 measured box-score header character cells at **max Δ 0.0000px**, all 16 colour overlays unmoved, all 96 `::before` header twins identical once the label field is normalised, element count identical at 10,673. The y-label shrinks 32→30.55px with x and width unchanged; `Hide PM` is right-anchored so its right edge stays pinned at 1083.313 and it shrinks 1.359px — matching the 1.36px predicted from the font metrics — with 0 collisions. Isolation: of 2,688 built HTML files, the 2,624 carrying this header are all `pm_players_*`; no other page type contains it.

Two checks of mine failed before the page did: a census pattern requiring `class="fnt fnr"` to close exactly (the div is `class="fnt fnr v0 v87"`), and a twin comparison that stripped `PM` and so mangled `3PM`. One check failed for a real reason worth recording — the baseline copy was rendered from the scratchpad, where `../../../fonts/*.woff2` cannot resolve, so it silently fell back to Helvetica and inverted the width comparison. A font-sanity gate (`document.fonts.check` plus asserting the `'+/-':'PM'` canvas width ratio is 1.048, not 0.80) caught it; the same trap produced a wrong "PM is wider, add compensation" recommendation in two of the analysis passes, which was rejected.

**Flagged, not fixed:** the game page now has a mild semantic collision the sibling pages do not — 14 x-axis tick labels are wall-clock times ending in "PM" (`7:43 PM` … `10:59 PM`) and the header prints `7:30 PM ET`, so `Hide PM` and `PM Events` sit in a panel whose x-axis reads in PM. Mitigating: `Hide PM` sits in a row of stat-name toggles (`Hide Stints`, `Hide Karma`, `Hide Scores`), which reads it as a stat name.

Note: `plotting.py` in this commit also carries the concurrent docstring task's rewrite of `plot_plus_minus_by_player_html` (documentation only — it now correctly states the page has no images and lists the exact tag set). Its `cli.py` and `GUIDE.md` changes are left uncommitted for that session.

## 2026-08-04 22:12 — "push and publish"

**Summary:** Publishing everything since `3fbf316b` — four changes to the game page, all landed today: the possessions plot and box score merged in as a folding section at the foot of every page; that section's inline geometry deduplicated and snapped to the emitted grid (which also fixed 6,173 flush block pairs the old independent rounding was breaking); its plot type aligned to the karma panels role for role; and the plus/minus column relabelled `PM`, matching the team and season pages. Plus a documentation-only rewrite of `plot_plus_minus_by_player_html`'s docstring, which had described the page as SVG data-URI background slices — it has had no images for a long time.

Fleet rebuilt: **3,936 game pages, 0 failures**. That is 1,312 more than the 2,624 of the last publish, because the 2023-24 play-by-play fetched on 2026-08-04 is now in `outputs/` and builds pages automatically. Those 2023-24 pages are NOT published — `stage_gh_pages.py` hardcodes `SEASONS = ["2024-25", "2025-26"]` — so they cost build time and disk only, with no dangling links. `outputs/` is now 3936 pages / 3.4 GB on disk, up from ~1.7 GB, which is the possessions section's ~195 KB per page plus the new season. Verified across a 9-page sample spanning all three seasons and confirmed fleet-wide: every page carries exactly one possessions section, all 3,936 carry the `PM` header, and **0** still carry `+/-`.

**Published and verified live.** Pushed 74 commits (`3fbf316b..15f8f4de`) to main and force-updated `gh-pages` to a fresh parentless commit (`7476cd74`, 221 pages / 299 MB, up from ~150 MB — the possessions sections). Pages served the previous build for the first ~30s, then flipped. Verified against the live CDN, not the local staging copy: the showcase game page is 910,778 bytes with exactly one possessions section, 52 PM tables and zero `+/-`; a 2024-25 game page likewise; help.html carries the rename; both season pages, the OKC team page and the index all serve; and `2023-24/html/nba_season.html` correctly 404s, confirming the unpublished season is not reachable. Every page still image-free.

Left uncommitted deliberately: the concurrent docstring session's `cli.py` and `GUIDE.md`. Neither affects page generation, so nothing published depends on them.

## 2026-08-05 04:29 — "rename titles to HOU @ OKC, heads at Q1 size, Big/Normal switch"

**Summary:** Four possessions-section changes. Both title lines now carry the matchup in team colours — "HOU @ OKC Possessions" and "HOU @ OKC box score". The play-by-play never says who is home, so home comes from the canonical csv path (`outputs/<season>/<home>/csv/…`, the convention the CLI and the season fetcher both file games under), with a first-possession-order "vs" fallback for unconventional paths; verified correct across all five showcase games (HOU @ OKC, OKC @ IND, OKC @ ATL, OKC @ DAL, SAC @ OKC). The team column heads at the plot centre went from the karma x-tick size to Q1's size (16.67 -> 19.68px, `HEAD_CQW`, emitted at the host's own 2dp so they land identical to the tabs), their strip re-reserving `HEAD_CQW*1.5`; `TICK_CQW` is now unreferenced and deleted. And the title line gained a Big/Normal switch — a borrowed `.lu-toggle` (the karma panels' own switch furniture, so the arrow, blue, font and fold-hide come from the host), reading "Big" closed and "Normal" open — whose open state holds EVERY possession at the height hover would give it (`max(--ps-h, --ps-eh)`) and letters every code, so a whole period reads without the mouse. Thin neighbours overlap in that view by construction; that is the trade the switch buys. Hover keeps working in both modes (its rules carry `!important` and win the tie with identical geometry).

Verified in WebKit on the game page and the standalone: titles and colours exact; heads == Q1 tab to <0.01px and unclipped; Big takes the thinnest visible block 2.6 -> 23.7px with 116/116 blocks lettered; Normal restores 2.6px; the switch hides when the section folds and the all-closed 40px pitch holds. Two check corrections along the way: `textContent` concatenates both switch labels regardless of CSS (use `innerText`), and the standalone shell was missing the host's closed-adjacency rule (`.kbox+.bx-flow` margin-top:0), which showed as a 58px pitch on the test page only — added to SHELL_CSS, both pages now [40]. The `.lu-toggle` borrow is documented in the module docstring and its rules copied into the standalone shell like the other borrowed furniture.

## 2026-08-05 04:38 — "box title HOU @ OKC Possessions box score; HOU OKC line before the Q selectors"

**Summary:** Two refinements. The box-score fold title now reads "HOU @ OKC Possessions box score" (was "HOU @ OKC box score") — with the matchup coloured, so the page's last title names both the game and the table. And the HOU OKC column heads moved to a line of their own BEFORE the Q1..OT2 selectors — the markup order swap of .pshead and .pdside — so the section reads title, teams, period tabs, plot. Verified in WebKit on the game page and the standalone: box title exact, heads line above the tabs (653.0 vs 682.6px on the game page), heads still at Q1's 19.68px and unclipped. Showcase pages and test_page.html rebuilt.
