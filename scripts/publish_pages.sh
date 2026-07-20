#!/bin/zsh
# Stage outputs/*.html for GitHub Pages on the local `gh-pages` branch.
#
# Builds an index.html entry page (from the season page's box-score
# headers: date, matchup, result per game), then writes the staged set
# as a SINGLE parentless commit on the local gh-pages branch, so the
# ~400MB of generated pages never accumulates in git history.
#
# This script does not touch the network. To deploy, push the branch:
#     git push origin +gh-pages
#
# One-time repo setting: Settings -> Pages -> Deploy from a branch ->
# gh-pages / (root). Site: https://<user>.github.io/<repo>/
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

cp "$ROOT"/outputs/*.html "$STAGE"/
python3 - "$STAGE" <<'PY'
import html
import re
import sys
from pathlib import Path

stage = Path(sys.argv[1])
seasons = sorted(p.name for p in stage.glob("season_events_*.html"))

# game list from the season page's box-score card headers:
# "<span class="bx-head">2025-10-21  OKC vs. HOU  <span..>W</span> ...
#  <a href="pm_players_<id>.html">..."
games = {}
for sp in seasons:
    text = (stage / sp).read_text()
    for m in re.finditer(r'<span class="bx-head">(.*?)</span>\n', text, re.S):
        head = m.group(1)
        link = re.search(r"pm_players_(\w+)\.html", head)
        if not link:
            continue
        label = html.unescape(re.sub(r"<[^>]+>", "", head)).strip()
        games[link.group(1)] = label
# pages with no season-page entry still get listed, by id
for p in sorted(stage.glob("pm_players_*.html")):
    games.setdefault(p.stem.replace("pm_players_", ""), p.stem)


def title(name):
    text = (stage / name).read_text()[:400]
    return text.split("<title>")[1].split("</title>")[0]


season_links = "\n".join(
    f'<li><a href="{s}">{html.escape(title(s))}</a></li>' for s in seasons)
game_links = "\n".join(
    f'<li><a href="pm_players_{gid}.html">{html.escape(label)}</a></li>'
    for gid, label in sorted(games.items(), key=lambda kv: kv[1]))

(stage / "index.html").write_text(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>nba-dataview pages</title>
<style>
body{{background:#000;color:#ddd;font-family:'DejaVu Sans Mono',monospace;
  max-width:720px;margin:40px auto;padding:0 16px;}}
h1{{font-size:20px;color:#eee;font-weight:normal;}}
h2{{font-size:15px;color:#aaa;font-weight:normal;margin-top:28px;}}
ul{{list-style:none;padding:0;}}
li{{margin:3px 0;}}
a{{color:#6ca0ff;text-decoration:none;}}
a:hover{{text-decoration:underline;}}
</style></head><body>
<h1>nba-dataview</h1>
<h2>Season</h2><ul>{season_links}</ul>
<h2>Games</h2><ul>{game_links}</ul>
</body></html>""")
print(f"index.html: {len(seasons)} season page(s), {len(games)} games")
PY

# write the staged files as one parentless commit on the local
# gh-pages branch, without disturbing the current worktree
export GIT_INDEX_FILE="$STAGE/.gitindex"
cd "$STAGE"
git --git-dir="$ROOT/.git" --work-tree="$STAGE" add -Af .
TREE="$(git --git-dir="$ROOT/.git" write-tree)"
COMMIT="$(git --git-dir="$ROOT/.git" commit-tree -m "publish pages $(date +%Y-%m-%d)" "$TREE")"
git --git-dir="$ROOT/.git" branch -f gh-pages "$COMMIT"
echo "gh-pages -> $COMMIT ($(ls *.html | wc -l | tr -d ' ') pages)"
echo "deploy with: git push origin +gh-pages"
