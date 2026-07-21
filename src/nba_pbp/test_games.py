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
]
