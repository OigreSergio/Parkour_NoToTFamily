-- ============================================================================
-- PkFAMILY — il gate di sicurezza vale anche per chi non ha una sessione
--
-- BLOCCO 9 del piano di lancio: trovata verificando, non leggendo.
--
-- ⚠️ Applicare DOPO la 0005, e leggere la nota sulle sessioni anonime in fondo
--    prima di eseguirla: cambia cosa vede un visitatore.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Il problema
-- ----------------------------------------------------------------------------
-- La 0005 nega gli spot a chi non ha registrato la presa d'atto:
--
--   create policy "spot solo dopo la presa d'atto"
--     on public.spots as restrictive for select
--     to authenticated                      -- ← qui
--     using (public.has_accepted_safety_notice() or ...);
--
-- `to authenticated` significa che la policy si applica al ruolo
-- `authenticated`. Chi arriva con la sola publishable key e non apre nessuna
-- sessione **non è** `authenticated`: è `anon`, e quella policy non lo tocca.
-- Le policy permissive esistenti gli servono gli spot con le coordinate.
--
-- Il disegno teneva per una ragione che non sta nell'SQL: il client apre una
-- sessione anonima al primo avvio (`_Root` in `main.dart`), e questo trasforma
-- ogni visitatore in `authenticated`. Ma quella è una riga di Dart, e la
-- difesa non può stare in un client che l'utente controlla.
--
-- Verificato sulla produzione con `scripts/audit_rls.mjs`, con la sola chiave
-- pubblica e senza fare login:
--
--   GET /rest/v1/spots?select=id,name,lat,lng  →  200, 24 spot con coordinate
--   GET /auth/v1/settings  →  "anonymous_users": false
--
-- Cioè: le sessioni anonime sono **spente**, quindi nessun visitatore diventa
-- `authenticated`, quindi la 0005 non si applica mai a chi guarda la mappa
-- senza registrarsi — che è la maggioranza. Il gate sarebbe rimasto una
-- schermata, aggirabile chiedendo gli spot all'API a mano. È letteralmente il
-- caso che il piano descrive come «un rifiuto aggirabile disattivando
-- JavaScript non è un rifiuto».

-- ----------------------------------------------------------------------------
-- Il rimedio: fallire chiuso
-- ----------------------------------------------------------------------------
-- Un ruolo `anon` non può avere una presa d'atto — non ha un `auth.uid()` a cui
-- legarla. Quindi per lui la risposta giusta non è «dipende»: è no.
--
-- La policy dice esplicitamente quello che il disegno già dava per scontato, e
-- toglie di mezzo la dipendenza silenziosa da un'impostazione della dashboard.
drop policy if exists "niente spot senza sessione" on public.spots;
create policy "niente spot senza sessione"
  on public.spots as restrictive for select
  to anon
  using (false);

comment on policy "niente spot senza sessione" on public.spots is
  'La presa d''atto si registra su un auth.uid(), e un ruolo anon non ne ha '
  'uno: per lui la risposta è no, non «dipende». Senza questa policy la '
  'RESTRICTIVE della 0005 — che è `to authenticated` — non tocca chi non apre '
  'una sessione, e il gate si aggira chiedendo gli spot all''API.';

-- ----------------------------------------------------------------------------
-- ⚠️ Cosa cambia il giorno che la applichi
-- ----------------------------------------------------------------------------
-- **Le sessioni anonime devono essere attive**, altrimenti la mappa è vuota per
-- tutti quelli che non hanno un account:
--
--   Dashboard → Authentication → Sign In / Providers → Anonymous sign-ins
--
-- Oggi sono spente. Accendile **prima** di applicare questa migration.
--
-- L'ordine conta, e nell'altro senso non fa danni irreparabili ma fa un danno:
-- applicare questa prima di accendere le sessioni anonime svuota la mappa a
-- chiunque non sia registrato, e nessuno capisce perché.
--
-- Se le sessioni anonime restano spente per scelta, l'alternativa è chiedere la
-- registrazione per vedere la mappa. È una decisione di prodotto, non tecnica —
-- ma va presa: la terza strada, quella in cui il gate c'è nell'interfaccia e
-- non nel database, non è una strada.
--
-- `scripts/audit_rls.mjs` controlla entrambe le cose insieme e dice quale delle
-- due manca.
