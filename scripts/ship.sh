#!/bin/bash
# Rebuild, commit, restage in one call:
#   ./scripts/ship.sh "commit message" [all|season|TRI ...]
set -e
cd "$(dirname "$0")/.."
MSG="$1"; shift
# commit BEFORE building: outputs aren't tracked on main, and the
# season page bakes git log into its commit box — building after
# the commit puts the shipping commit itself in the box
git add src scripts
git commit -q -m "$MSG

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
./scripts/rebuild.sh "${@:-all}" >/dev/null
./scripts/publish_pages.sh >/dev/null 2>&1
echo "shipped: $MSG"
