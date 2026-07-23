"""A small, fixed set of games for manual visual review / regression
testing. Rebuild every page with ``nba-pbp rebuild-test-games`` (say
"refresh test games") and eyeball the results, or use it as a quick
consistent sample after a change to the game-page code.

Add or remove entries freely — each is ``(game_id, note)``. The note is
just documentation (why this game is in the set). A game only builds if
its ``outputs/pbp_<id>.csv`` is present; missing ones are skipped with a
log line, so it is safe to list games you have not fetched yet.
"""

# Chosen for coverage: schedule-nav edge cases (season opener / final
# game), overtime, one-possession finishes, blowouts, and the two known
# data bugs kept as regression cases.
TEST_GAMES = [
    ("0022500001", "OKC vs HOU - season opener, 1-pt, 2OT (nav: next only)"),
    ("0022500005", "IND vs OKC - 2OT"),
    ("0022500047", "GSW @ SAS - 1-pt nailbiter"),
    ("0022500095", "NOP vs SAS - 1OT"),
    ("0022500004", "DAL vs SAS - 33-pt blowout"),
    ("0022500015", "OKC @ CLE - 32-pt blowout"),
    ("0022500455", "Wallace cross-team surname - stint misattribution case"),
    ("0022500568", "OKC vs SAS - primary hand-checked game"),
    ("0022500641", "Bradley zero-length stints - unlinkable-band case"),
    ("0042500317", "OKC vs SAS - Finals, last game (nav: prev only)"),
    # a spread of ~20 more across the season (both teams, all months,
    # regular season + playoffs) for broader manual review
    ("0022500010", "SAS @ OKC - W 15pt 2025-12-25"),
    ("0022500105", "SAS vs BKN - W 11pt 2025-10-26"),
    ("0022500180", "OKC @ POR - L 2pt 2025-11-05"),
    ("0022500247", "NOP vs OKC - L 17pt 2025-11-17"),
    ("0022500326", "SAS @ ORL - W 2pt 2025-12-03"),
    ("0022500399", "WAS vs SAS - L 11pt 2025-12-21"),
    ("0022500490", "SAS vs POR - L 5pt 2026-01-03"),
    ("0022500553", "OKC vs MIA - W 12pt 2026-01-11"),
    ("0022500653", "TOR @ OKC - W 2pt 2026-01-25"),
    ("0022500738", "SAS @ DAL - W 12pt 2026-02-05"),
    ("0022500808", "BKN @ OKC - L 19pt 2026-02-20"),
    ("0022500876", "OKC @ DAL - W 13pt 2026-03-01"),
    ("0022500942", "BOS @ SAS - L 9pt 2026-03-10"),
    ("0022501013", "PHX @ SAS - L 1pt 2026-03-19"),
    ("0022501094", "CHI @ SAS - L 15pt 2026-03-30"),
    ("0022501161", "SAS vs POR - W 11pt 2026-04-08"),
    ("0042500142", "PHX @ OKC - playoffs, L 13pt 2026-04-22"),
    ("0042500222", "OKC vs LAL - playoffs, W 18pt 2026-05-07"),
    ("0042500312", "OKC vs SAS - Finals, W 9pt 2026-05-20"),
    ("0042500405", "SAS vs NYK - Finals, L 4pt 2026-06-13"),
]
