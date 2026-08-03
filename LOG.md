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
