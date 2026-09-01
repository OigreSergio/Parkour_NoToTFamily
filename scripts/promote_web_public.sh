#!/usr/bin/env sh
# Passaggio al pubblico: sposta la web app già online da /t/<token>/ alla root
# di gh-pages, toglie noindex/robots restrittivo e pubblica.
#
# Non richiede un nuovo export Expo: riusa il bundle già pubblicato.
# Vedi docs/WEB_TEST_SPACE.md.
#
# Uso:
#   scripts/promote_web_public.sh --dry-run   # prova a vuoto, non tocca il remoto
#   scripts/promote_web_public.sh             # pubblica su gh-pages
#
# Prima di pubblicare salva lo stato attuale sul branch `gh-pages-anteprima`,
# così il passaggio è reversibile:
#   git push -f origin gh-pages-anteprima:gh-pages
set -eu

SITE_URL="https://oigresergio.github.io/Parkour_NoToTFamily/"
BACKUP_BRANCH="gh-pages-anteprima"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

WORK="$(mktemp -d)"
trap 'git -C "$REPO_ROOT" worktree remove --force "$WORK/ghp" 2>/dev/null || true; rm -rf "$WORK"' EXIT

git -C "$REPO_ROOT" fetch origin gh-pages
git -C "$REPO_ROOT" worktree add "$WORK/ghp" -B gh-pages origin/gh-pages

python3 "$REPO_ROOT/scripts/gh_pages_public.py" "$WORK/ghp" --site-url "$SITE_URL"

git -C "$WORK/ghp" add -A
git -C "$WORK/ghp" status --short
git -C "$WORK/ghp" commit -m "feat: pubblica la web app sulla root di gh-pages (fine anteprima privata)"

if [ "$DRY" = 1 ]; then
  echo
  echo "--dry-run: niente push. Commit preparato in $WORK/ghp"
  echo "Per pubblicare davvero rilancia senza --dry-run."
  exit 0
fi

# rete di sicurezza: lo stato attuale resta su $BACKUP_BRANCH
git -C "$REPO_ROOT" push -u origin "origin/gh-pages:refs/heads/$BACKUP_BRANCH" 2>/dev/null \
  || git -C "$REPO_ROOT" push -u origin "+origin/gh-pages:refs/heads/$BACKUP_BRANCH"
git -C "$WORK/ghp" push -u origin gh-pages

echo
echo "Pubblicato: $SITE_URL"
echo "Backup dell'anteprima privata: branch $BACKUP_BRANCH"
