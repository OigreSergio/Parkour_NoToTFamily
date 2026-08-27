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

- [x] 2.1 Auth Supabase: registrazione con conferma email, login, reset password, logout
- [x] 2.2 Age gate 16 anni (`AgeCheck`, soglia art. 8 GDPR), `age_confirmed_at` sul profilo;
      la data di nascita **non** viene conservata
- [x] 2.2bis Accesso tramite genitore: `parent_access_requests` inaccessibile dal client,
      invio via Edge Function con rate limit, scadenza 7 giorni; profilo `supervised` con
      `chat_enabled = false` applicato **anche nelle RLS**
- [x] 2.3 Livelli anonimo / user / instructor / admin; nessun percorso assegna `admin`
- [x] 2.4 Profilo: "Scarica i miei dati" (JSON) ed "Elimina account" con 30 giorni di grazia
- [x] 2.5 Gate PkPASS e registrazione dispositivo via `mailto` rimossi (BLOCCO 0)
- [~] 2.6 `admin-desktop` da deprecare: `web-admin` è già senza secret key (1.5), resta da
      spostare l'export completo in una Edge Function
- [x] 2.7 Gate di sicurezza con accettazione registrata (versione + **hash del testo mostrato**,
      calcolato a runtime dall'asset); testo in `mobile/assets/legal/safety_notice_v1.md`
- [x] 2.8 Modalità senza spot per chi rifiuta, applicata **anche lato server** con una policy
      RESTRICTIVE su `spots` + sessione anonima per dare un'identità a chi non si registra
- [x] 2.9 Avvertenza breve in ogni scheda spot

> Le migration `0004` e `0005` sono scritte ma **non applicate**: servono le credenziali
> del progetto. Vedi [OPS_TODO](OPS_TODO.md).

## BLOCCO 3-bis — Spot fuori Roma (gate di lancio)

- [x] 3b.1 Attributi inventati → `null`: 5.040 valori rimossi (`skillLevel`, `crowdLevel`,
      `hasFountain` erano identici su tutti e 1.680), più 1.706 rating fittizi
- [x] 3b.2 154 attribuzioni a 23 persone reali rimosse, con test di regressione in CI
- [~] 3b.3 Toponimo reale: `enrich_spots.py` pronto, **non ancora eseguito** — Overpass è
      irraggiungibile da questo ambiente. Va lanciato dal PC dell'admin
- [~] 3b.4 Contesto OSM e `has_fountain` reale: stesso script, stessa condizione
- [~] 3b.5 Foto: **serve un `MAPILLARY_TOKEN`** (gratuito). Wikimedia da solo non basta —
      provato, restituiva foto di cavi in fibra e chiese a 150 m dallo spot
- [x] 3b.6 Stato di completezza (`da_completare` / `arricchito` / `verificato`) nel dataset,
      nella migration `0006`, nel modello e nella scheda spot
- [x] 3b.7 «Ci sei stato?» nella scheda, che chiede **esattamente ciò che manca**
- [x] 3b.8 `scripts/spot_coverage.mjs`, in CI

**Copertura oggi: 30 spot su 1.706 (1,8%) hanno qualcosa da mostrare.** In Italia 0 su 555.
È il numero che il gate di lancio deve muovere, e lo muovono il token Mapillary e la community
— non un'altra pipeline.

## BLOCCO 3 — Mappa e spot

- [x] 3.1 Dataset ripulito: hotlink verso siti terzi rimossi, e le foto Wikimedia
      superstiti ora portano **autore, licenza e link alla fonte**, recuperati dall'API di
      Commons (`scripts/resolve_photo_credits.py`, verificato in CI)
- [x] 3.2 `scripts/import_spots_supabase.mjs`: idempotente su `external_id`, a blocchi,
      con `--dry-run`. Gli spot escono dal bundle JS e vanno nel database
- [x] 3.3 Mappa riscritta: **tile OpenFreeMap** al posto di `tile.openstreetmap.org`
      (vietato dalla usage policy di OSM per un'app), clustering su griglia con rendering
      del solo viewport, pin distinti per stato di completezza, filtri, attribuzione ODbL
- [x] 3.4 Scheda spot: foto con crediti, località, distanza calcolata **sul dispositivo**,
      indicazioni che portano solo le coordinate dello spot
- [x] 3.5 Geolocalizzazione **solo al tocco**, preceduta da una schermata che dice a cosa
      serve e che non viene conservata. Prima veniva chiesta all'avvio
- [x] 3.6 «Proponi uno spot» → `status = 'pending'`, visibile solo all'autore

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
