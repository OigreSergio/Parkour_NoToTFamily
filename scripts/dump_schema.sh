#!/usr/bin/env sh
# Esporta lo schema REALE di produzione in supabase/migrations/.
#
# Serve per il disaster recovery: senza, lo "Scenario B" di 📲/README.md
# (ricostruire il progetto da zero) non è eseguibile — vedi la nota in testa a
# 0003_production_baseline.sql, che oggi è solo una ricostruzione.
#
# Richiede la Supabase CLI e le credenziali del progetto: lo lancia l'admin dal
# proprio PC, mai la CI (la secret key non deve stare in nessun runner).
#
#   1. npm i -g supabase          (o brew install supabase/tap/supabase)
#   2. supabase login
#   3. scripts/dump_schema.sh <project-ref>
#
# L'output SOSTITUISCE 0003_production_baseline.sql. Committalo: contiene solo
# struttura, nessun dato e nessun segreto — ricontrolla comunque prima del push.
set -eu

REF="${1:-}"
[ -n "$REF" ] || { echo "Uso: scripts/dump_schema.sh <project-ref>"; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/supabase/migrations/0003_production_baseline.sql"

command -v supabase >/dev/null || { echo "supabase CLI non trovata."; exit 1; }

supabase link --project-ref "$REF"
supabase db dump --schema public --file "$OUT"

echo
echo "Schema scritto in $OUT"
echo "Ora:"
echo "  1. togli l'intestazione che lo dichiara una ricostruzione;"
echo "  2. allinea docs/DATA_MODEL.md alle tabelle reali;"
echo "  3. spunta la voce corrispondente in docs/LAUNCH_CHECKLIST.md."
