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
