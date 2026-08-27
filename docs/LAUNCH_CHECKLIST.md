# Checklist di lancio — PkFAMILY su pkfamily.app

Stato di avanzamento dei blocchi di [`LAUNCH_PROMPT.md`](LAUNCH_PROMPT.md).
Il piano completo è in [`LAUNCH_PLAN.md`](LAUNCH_PLAN.md).

Legenda: `[ ]` da fare · `[~]` in corso · `[x]` fatto · `[→]` sta all'umano (vedi
[`OPS_TODO.md`](OPS_TODO.md))

---

## BLOCCO 0 — Messa in sicurezza

- [x] 0.1 `gh-pages` ricreato come branch orfano senza `invito/` (IBAN fuori dal sito **e**
      dalla storia pubblica); l'anteprima sotto `/t/<token>/` resta accessibile
- [x] 0.2 Backup pubblico ridotto ai soli contenuti della community; `profiles` e le altre
      tabelle con dati personali escluse, con controllo che fa fallire lo script
- [x] 0.3 Questa checklist
- [x] 0.4 `OPS_TODO.md` con le azioni non automatizzabili

## BLOCCO 1 — Fondamenta

- [x] 1.1 Piattaforma web generata; manifest PWA e `index.html` PkFAMILY, senza tracker
- [x] 1.2 `supabase_flutter` al posto di `api_client.dart` (rimosso), chiavi da `--dart-define`;
      modelli riscritti sullo schema **reale** — `lat`/`lng`, `skill_level`, `crowd_level`,
      `has_fountain`, foto da `spot_photos` con autore e licenza
- [~] 1.3 `0003_production_baseline.sql` come **ricostruzione**, non un dump. `0001`/`0002`
      marcate storiche e mai applicate. Il dump vero richiede la secret key:
      `scripts/dump_schema.sh` → [OPS_TODO](OPS_TODO.md)
- [x] 1.4 Migration `0004` che corregge la **ricorsione infinita** nelle policy della chat
      (`42P17`, oggi HTTP 500 in produzione) — da applicare, vedi [OPS_TODO](OPS_TODO.md)
- [x] 1.5 `web-admin` riparato: `src/lib/supabase.ts` al posto del mancante `@/lib/api`,
      Supabase Auth + RLS, nessuna secret key nel client. Lint e build verdi
- [x] 1.6 `ci.yml`: format, analyze, test e build web per Flutter; lint e build per web-admin
- [x] 1.7 Script di patch del bundle Expo rimossi, con `sync-map.yml`;
      `WEB_TEST_SPACE.md` → [`DEPLOY.md`](DEPLOY.md)

## BLOCCO 2 — Accessi e account

- [ ] 2.1 Auth Supabase con conferma email obbligatoria
- [ ] 2.2 Age gate 16 anni
- [ ] 2.2bis Accesso tramite genitore: account `supervised`, chat spenta di default
- [ ] 2.3 Livelli anonimo / user / instructor / admin
- [ ] 2.4 Profilo: export dati ed eliminazione account
- [ ] 2.5 Gate PkPASS e registrazione dispositivo via `mailto` rimossi
- [ ] 2.6 `admin-desktop` deprecato, secret key fuori dal browser
- [ ] 2.7 Gate di sicurezza all'ingresso, con accettazione registrata (versione + hash)
- [ ] 2.8 Modalità informativa senza spot per chi rifiuta, applicata **anche lato server**
- [ ] 2.9 Avvertenza breve in ogni scheda spot

## BLOCCO 3-bis — Spot fuori Roma (gate di lancio)

- [ ] 3b.1 Attributi inventati → `NULL` (`skill_level`, `crowd_level`, `has_fountain` su 1.680)
- [ ] 3b.2 Rimossi i nomi delle 23 persone dalle descrizioni, con test di regressione
- [ ] 3b.3 Toponimo reale via Nominatim al posto di «Spot Athens 3»
- [ ] 3b.4 Contesto OSM via Overpass, incluso `has_fountain` reale
- [ ] 3b.5 Foto da Mapillary (CC-BY-SA) e Wikimedia, con autore e licenza in `spot_photos`
- [ ] 3b.6 Stato di completezza: `da_completare` / `arricchito` / `verificato`
- [ ] 3b.7 «Ci sei stato? Aggiungi una foto e raccontalo» → moderazione
- [ ] 3b.8 `scripts/spot_coverage.mjs`: copertura per paese e città

## BLOCCO 3 — Mappa e spot

- [ ] 3.1 Dataset ripulito: via gli hotlink non-Wikimedia e le immagini Street View
- [ ] 3.2 Import degli spot in Supabase (non nel bundle)
- [ ] 3.3 Mappa con clustering e rendering del viewport
- [ ] 3.4 Scheda spot con crediti foto e `access_type`
- [ ] 3.5 Geolocalizzazione solo su richiesta, mai salvata
- [ ] 3.6 "Proponi uno spot" → `pending`

## BLOCCO 4 — Chat

- [ ] 4.1 Conversazioni private e di gruppo su Realtime
- [ ] 4.2 Solo utenti con email confermata, rate limit
- [ ] 4.3 Blocco utente e segnalazione messaggio
- [ ] 4.4 Assenza di cifratura end-to-end dichiarata
- [ ] 4.5 Pseudonimizzazione dei messaggi alla cancellazione dell'account

## BLOCCO 5 — Video

- [ ] 5.1 Gating premium rimosso lato server, non solo in UI
- [ ] 5.2 `is_starter` e `order_index` su `videos`
- [ ] 5.3 Percorso "Inizia da qui"
- [ ] 5.4 Embed `youtube-nocookie.com` con placeholder fino al consenso
- [ ] 5.5 Riga di sicurezza in ogni scheda
- [ ] 5.6 Percorso iniziale popolato

## BLOCCO 6 — Moderazione e DSA

- [ ] 6.1 Segnalazioni su spot, messaggi, commenti, profili
- [ ] 6.2 Code di moderazione in `web-admin`
- [ ] 6.3 Statement of reasons (art. 17 DSA)
- [ ] 6.4 Log di moderazione, 12 mesi
- [ ] 6.5 Punto di contatto `abuse@pkfamily.app`

## BLOCCO 7 — Legale e privacy

- [ ] 7.1 `/legale/privacy` (IT + EN)
- [ ] 7.2 `/legale/termini`
- [ ] 7.3 `/legale/cookie`
- [ ] 7.4 `/legale/note-legali`
- [ ] 7.5 `/legale/sub-responsabili`
- [ ] 7.6 Documenti interni: registro, DPIA, procedura breach, LIA
- [ ] 7.7 Checkbox separate e non pre-spuntate in registrazione
- [→] Revisione legale professionale di informativa, Termini e DPIA

## BLOCCO 8 — Infrastruttura e deploy

- [ ] 8.1 `_headers` con CSP, HSTS, Permissions-Policy
- [ ] 8.2 `_redirects` per il routing SPA
- [ ] 8.3 Workflow di deploy staging e produzione
- [ ] 8.4 Redirect 301 da `gh-pages` a `pkfamily.app`
- [ ] 8.5 `security.txt` e `SECURITY.md` allineato
- [ ] 8.6 Error tracking (o rinuncia documentata)
- [ ] 8.7 `robots.txt` permissivo, sitemap, meta OG
- [→] Dominio registrato, DNS, DPA accettati, caselle email

## BLOCCO 9 — Verifica prima del tag

- [ ] 9.1 `scripts/audit_rls.mjs` in CI
- [ ] 9.2 Percorsi utente provati a mano su staging
- [ ] 9.3 Header di sicurezza verificati
- [ ] 9.4 Restore di prova dal backup
- [ ] 9.5 Checklist e OPS_TODO aggiornati
