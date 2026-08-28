#!/usr/bin/env bash
# Sostituisce il branch `gh-pages` con la pagina che rimanda a pkfamily.app.
#
#   ./scripts/publish_gh_pages_redirect.sh          # mostra cosa farebbe
#   ./scripts/publish_gh_pages_redirect.sh --fallo  # lo fa davvero
#
# ⚠️ **Da lanciare solo dopo che https://pkfamily.app risponde.**
#
# Oggi `gh-pages` serve ancora l'anteprima Expo sotto /t/<token>/, ed è l'unica
# cosa che funziona per chi ha il QR stampato. Pubblicare il redirect prima che
# il dominio nuovo sia online non «prepara il terreno»: spegne l'unica versione
# raggiungibile e manda tutti su un dominio che non esiste. Lo script controlla
# da sé che il sito nuovo risponda, e si ferma se non lo fa.
#
# Perché un branch orfano e non un commit sopra: quel branch ha in pancia la
# storia del bundle Expo, e non serve più a niente. Il codice vero sta in
# `mobile/`, dove è sempre stato dal BLOCCO 1.

set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SORGENTE="$RADICE/deploy/gh-pages"
FALLO=false
[ "${1:-}" = "--fallo" ] && FALLO=true

echo
echo "Redirect di gh-pages verso pkfamily.app"
echo

# --- Il sito nuovo è online? --------------------------------------------------

echo "→ Controllo che https://pkfamily.app risponda…"
# `tail -c 3`: dietro un proxy curl può stampare un codice per ogni salto, e
# quello che conta è l'ultimo.
codice=$(curl -sL -o /dev/null -w '%{http_code}' --max-time 20 https://pkfamily.app/ 2>/dev/null | tail -c 3)
codice=${codice:-000}

if [ "$codice" != "200" ]; then
  cat <<FINE

✗ https://pkfamily.app ha risposto $codice, non 200.

  Non pubblico il redirect. Finché il dominio nuovo non è online, gh-pages è
  l'unica versione raggiungibile: sostituirla adesso vorrebbe dire mandare su
  una pagina morta chiunque abbia il QR o il vecchio link.

  Prima: registra il dominio, collega Cloudflare Pages, pubblica un tag.
  Poi torna qui.

FINE
  exit 1
fi
echo "  200. Il sito nuovo c'è."

# --- Cosa succederebbe --------------------------------------------------------

echo
echo "→ Cosa verrà pubblicato su gh-pages:"
(cd "$SORGENTE" && find . -type f | sed 's|^\./|    |')

echo
echo "→ Cosa sparisce: tutto il resto, storia del branch compresa."
echo "    (il bundle Expo sotto /t/<token>/, che non è più aggiornabile)"

if [ "$FALLO" != true ]; then
  echo
  echo "Prova a vuoto. Per farlo davvero:"
  echo "    $0 --fallo"
  echo
  exit 0
fi

# --- Fallo --------------------------------------------------------------------

temporanea="redirect-gh-pages-$$"
attuale=$(git -C "$RADICE" rev-parse --abbrev-ref HEAD)

echo
echo "→ Costruisco il branch orfano…"
git -C "$RADICE" checkout --orphan "$temporanea"
git -C "$RADICE" rm -rf --cached . >/dev/null
git -C "$RADICE" clean -fdx --exclude=deploy >/dev/null

cp "$SORGENTE"/*.html "$RADICE/"
# Senza questo file GitHub Pages passa tutto da Jekyll, che ignora le cartelle
# che cominciano con `_` e a volte riscrive l'HTML.
touch "$RADICE/.nojekyll"

git -C "$RADICE" add index.html 404.html .nojekyll
git -C "$RADICE" commit -m "chore: gh-pages rimanda a pkfamily.app

L'anteprima privata sotto /t/<token>/ non c'è più: il sito è pubblico.
Chi ha il QR stampato o il vecchio link atterra sull'app, non su un 404."

echo
echo "→ Push forzato su gh-pages…"
git -C "$RADICE" push --force origin "$temporanea:gh-pages"

git -C "$RADICE" checkout "$attuale"
git -C "$RADICE" branch -D "$temporanea"

cat <<FINE

Fatto.

  Verifica fra qualche minuto (GitHub Pages ci mette un po'):
    curl -sL https://oigresergio.github.io/Parkour_NoToTFamily/ | grep canonical

  Da segnare in docs/OPS_TODO.md: lo «Scenario C» di 📲/README.md — tornare
  indietro sul sito con un revert su gh-pages — adesso non ha più una storia su
  cui tornare. Il rollback è ripubblicare il tag precedente.

FINE
