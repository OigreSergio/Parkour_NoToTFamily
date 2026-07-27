#!/usr/bin/env sh
# Ripubblica la web app nello spazio di test nascosto su gh-pages.
#
# Uso: scripts/deploy_test_web.sh <cartella-export-expo>
#   es: scripts/deploy_test_web.sh mobile/dist
#
# Prende un export web di Expo (con percorsi assoluti basati su
# /Parkour_NoToTFamily), lo sposta sotto /t/$TOKEN/ riscrivendone la base,
# aggiunge meta noindex, e ricrea placeholder root + robots.txt.
# Vedi docs/WEB_TEST_SPACE.md.
set -eu

TOKEN="2fe095ecfaa79a73"
BASE="/Parkour_NoToTFamily"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$1"
WORK="$(mktemp -d)"

[ -f "$DIST/index.html" ] || { echo "index.html non trovato in $DIST"; exit 1; }

git -C "$REPO_ROOT" fetch origin gh-pages
git -C "$REPO_ROOT" worktree add "$WORK/ghp" -B gh-pages origin/gh-pages

# ripulisce tutto tranne .git e ricostruisce il layout
find "$WORK/ghp" -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
mkdir -p "$WORK/ghp/t/$TOKEN"
cp -R "$DIST"/. "$WORK/ghp/t/$TOKEN/"
touch "$WORK/ghp/.nojekyll"

# base dei percorsi -> /t/$TOKEN/ in HTML e bundle JS
find "$WORK/ghp/t/$TOKEN" -name '*.html' -o -name '*.js' | while read -r f; do
  sed -i "s|$BASE|$BASE/t/$TOKEN|g" "$f"
done
# meta noindex su tutte le pagine dell'app
find "$WORK/ghp/t/$TOKEN" -name '*.html' | while read -r f; do
  sed -i 's|<head>|<head><meta name="robots" content="noindex, nofollow">|' "$f"
done

# patch modalità test (satellite, spot fissi, gratis, pk-route.js)
python3 "$REPO_ROOT/scripts/patch-gh-pages-test-free.py" \
  "$WORK/ghp/t/$TOKEN"/_expo/static/js/web/entry-*.js

printf 'User-agent: *\nDisallow: /\n' > "$WORK/ghp/robots.txt"
cat > "$WORK/ghp/index.html" <<'EOF'
<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PkFAMILY</title>
<style>
  body { margin: 0; display: grid; place-items: center; min-height: 100vh;
         font-family: system-ui, sans-serif; background: #111; color: #eee; }
  main { text-align: center; padding: 2rem; }
  p { color: #999; }
</style>
</head>
<body>
<main>
  <h1>PkFAMILY</h1>
  <p>Anteprima privata — l'accesso avviene solo tramite invito (QR code).</p>
</main>
</body>
</html>
EOF
sed "s|Anteprima privata — l'accesso avviene solo tramite invito (QR code).|Pagina non trovata.|" \
  "$WORK/ghp/index.html" > "$WORK/ghp/404.html"

git -C "$WORK/ghp" add -A
git -C "$WORK/ghp" commit -m "chore: rideploy anteprima privata web app"
git -C "$WORK/ghp" push origin gh-pages
git -C "$REPO_ROOT" worktree remove --force "$WORK/ghp"
rm -rf "$WORK"
echo "Deploy ok: https://oigresergio.github.io$BASE/t/$TOKEN/"
