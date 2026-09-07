#!/usr/bin/env sh
# Pubblica il contesto visivo della scheda spot (pk-scheda.js +
# pk-scheda-spots.json) sulla web app già online, nella root di gh-pages,
# senza rifare l'export Expo.
#
# Uso: scripts/deploy_pk_scheda.sh [--no-push]
#   1. rigenera i due file (docs/demo/tools/build_pk_scheda.py);
#   2. li copia nella root di gh-pages (worktree temporaneo);
#   3. si assicura che index.html e 404.html carichino gli script innestati
#      con percorso ASSOLUTO: con "./pk-scheda.js" un deep link o un refresh
#      su /spot/<id> cercava lo script in /spot/ e non lo trovava;
#   4. commit e push su gh-pages (con --no-push si ferma al commit locale).
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="/Parkour_NoToTFamily"
WORK="$(mktemp -d)"

python3 "$REPO_ROOT/docs/demo/tools/build_pk_scheda.py"

git -C "$REPO_ROOT" fetch origin gh-pages
git -C "$REPO_ROOT" worktree add "$WORK/ghp" -B gh-pages origin/gh-pages

cp "$REPO_ROOT/docs/demo/pk-scheda.js" "$REPO_ROOT/docs/demo/pk-scheda-spots.json" "$WORK/ghp/"

for f in "$WORK/ghp/index.html" "$WORK/ghp/404.html"; do
  [ -f "$f" ] || continue
  BASE="$BASE" python3 - "$f" <<'EOF'
import os, re, sys
base = os.environ["BASE"]
path = sys.argv[1]
html = open(path, encoding="utf8").read()
for name in ("pk-route.js", "pk-scheda.js"):
    tag = f'<script src="{base}/{name}" defer></script>'
    html, n = re.subn(rf'<script src="(?:\./)?(?:{re.escape(base)}/)?{re.escape(name)}" defer></script>', tag, html)
    if n == 0:
        html = html.replace("</body>", tag + "\n</body>")
open(path, "w", encoding="utf8").write(html)
print(f"ok: script innestati con percorso assoluto in {os.path.basename(path)}")
EOF
done

git -C "$WORK/ghp" add -A
if git -C "$WORK/ghp" diff --cached --quiet; then
  echo "gh-pages è già aggiornato: niente da pubblicare"
else
  git -C "$WORK/ghp" commit -m "chore: contesto visivo e Instagram nella scheda di tutti gli spot (pk-scheda)"
  if [ "${1:-}" = "--no-push" ]; then
    echo "commit pronto su gh-pages (non pushato): git push origin gh-pages"
  else
    git -C "$WORK/ghp" push origin gh-pages
    echo "Deploy ok: https://oigresergio.github.io$BASE/"
  fi
fi

git -C "$REPO_ROOT" worktree remove --force "$WORK/ghp"
rm -rf "$WORK"
