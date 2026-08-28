#!/usr/bin/env bash
# Mette in un file solo le migration ancora da applicare, nell'ordine giusto.
#
#   ./scripts/migrazioni_da_applicare.sh > /tmp/pkfamily.sql
#
# Poi si incolla in **Dashboard → SQL Editor → New query** e si preme Run.
#
# Perché non lo fa uno script: applicare uno schema è DDL, e la secret key non
# ne fa. Passa dal SQL Editor con la tua identità, oppure dalla CLI Supabase
# con la password del database — che è giusto così, perché è l'operazione che
# può rompere tutto.
#
# Prima di premere Run, due cose:
#
#   1. **Fai un backup.** `📲/backup.mjs`, o lo snapshot dalla dashboard.
#   2. **Attiva le sessioni anonime**, se non l'hai già fatto. La 0010 nega gli
#      spot a chi non ha una sessione: applicarla con le sessioni anonime spente
#      svuota la mappa a tutti quelli che non hanno un account.
#
# Le migration sono append-only e ognuna è scritta per essere rieseguibile
# (`if not exists`, `drop policy if exists`), quindi rilanciare il blocco non
# fa danni. Ma un backup prima resta la cosa da fare.

set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DA=${1:-0004}

cat <<'INTESTAZIONE'
-- ============================================================================
-- PkFAMILY — migration da applicare, in ordine.
--
-- Generato da scripts/migrazioni_da_applicare.sh. Non modificare qui: le
-- correzioni vanno nei file sotto supabase/migrations/, o si perdono alla
-- prossima generazione.
--
-- Da incollare in Dashboard → SQL Editor → New query → Run.
-- ============================================================================

begin;

INTESTAZIONE

trovate=0
for file in "$RADICE"/supabase/migrations/*.sql; do
  nome=$(basename "$file")
  numero=${nome%%_*}

  # 0001 e 0002 descrivono uno schema mai esistito in produzione: sono marcate
  # come storiche nei file stessi, e vanno saltate qui in modo esplicito perché
  # eseguirle creerebbe tabelle che nessuno usa.
  [[ "$numero" < "$DA" ]] && continue

  trovate=$((trovate + 1))
  printf -- '-- ----------------------------------------------------------------\n'
  printf -- '-- %s\n' "$nome"
  printf -- '-- ----------------------------------------------------------------\n\n'
  cat "$file"
  printf '\n\n'
done

cat <<'CHIUSURA'
commit;

-- ============================================================================
-- Dopo il Run, verifica da fuori invece di fidarti del «Success»:
--
--   SUPABASE_URL=https://<ref>.supabase.co \
--   SUPABASE_PUBLISHABLE_KEY=sb_publishable_… \
--   node scripts/audit_rls.mjs --sessione
--
-- Deve sparire la ricorsione sulla chat (niente più HTTP 500) e deve comparire
-- «il gate è applicato dal database».
-- ============================================================================
CHIUSURA

printf -- '\n-- %d migration incluse, da %s in poi.\n' "$trovate" "$DA" >&2
