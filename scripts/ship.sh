#!/bin/bash
# Rebuild, commit, restage in one call:
#   ./scripts/ship.sh "commit message" [all|season|TRI ...]
set -e
cd "$(dirname "$0")/.."
MSG="$1"; shift
./scripts/rebuild.sh "${@:-all}" >/dev/null
git add src scripts
git commit -q -m "$MSG

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
./scripts/publish_pages.sh >/dev/null 2>&1
echo "shipped: $MSG"
