#!/usr/bin/env sh
# Pubblica un export web di Expo direttamente sulla ROOT di gh-pages, senza
# riscrittura della base e senza noindex (versione pubblica di
# scripts/deploy_test_web.sh).
#
# Uso: scripts/deploy_public_web.sh <cartella-export-expo>
#   es: scripts/deploy_public_web.sh mobile/dist
#
# L'export dev'essere generato con base /Parkour_NoToTFamily (quella di default
# per un project site di GitHub Pages). Vedi docs/WEB_TEST_SPACE.md.
set -eu

SITE_URL="https://oigresergio.github.io/Parkour_NoToTFamily/"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$1"
WORK="$(mktemp -d)"
trap 'git -C "$REPO_ROOT" worktree remove --force "$WORK/ghp" 2>/dev/null || true; rm -rf "$WORK"' EXIT

[ -f "$DIST/index.html" ] || { echo "index.html non trovato in $DIST"; exit 1; }

git -C "$REPO_ROOT" fetch origin gh-pages
git -C "$REPO_ROOT" worktree add "$WORK/ghp" -B gh-pages origin/gh-pages

find "$WORK/ghp" -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
cp -R "$DIST"/. "$WORK/ghp/"
touch "$WORK/ghp/.nojekyll"

# patch modalità test (mappa ricamo, spot fissi, gratis, pk-route.js)
python3 "$REPO_ROOT/scripts/patch-gh-pages-test-free.py" \
  "$WORK/ghp"/_expo/static/js/web/entry-*.js

# robots permissivo, sitemap, 404 SPA, meta SEO
python3 "$REPO_ROOT/scripts/gh_pages_public.py" "$WORK/ghp" --site-url "$SITE_URL"

git -C "$WORK/ghp" add -A
git -C "$WORK/ghp" commit -m "chore: rideploy web app pubblica"
git -C "$WORK/ghp" push -u origin gh-pages

echo "Deploy ok: $SITE_URL"
