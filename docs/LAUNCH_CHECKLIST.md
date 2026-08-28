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

- [x] 4.1 Conversazioni private e di gruppo su Supabase Realtime, elenco con anteprima,
      creazione, ricerca persone, uscita
- [x] 4.2 Email confermata e rate limit **imposti dal database** (policy RESTRICTIVE +
      trigger a 20 messaggi/minuto), non solo dal client
- [x] 4.3 Blocco utente applicato **anche lato server** (`can_write_to_chat()`) e
      segnalazione messaggio con categorie DSA → `reports`
- [x] 4.4 Assenza di cifratura end-to-end dichiarata in cima all'elenco chat, non solo
      nell'informativa
- [x] 4.5 `pseudonymise_deleted_accounts()`: alla scadenza dei 30 giorni `sender_id`
      diventa NULL e il messaggio resta nella conversazione degli altri

> Le migration `0004` e `0007` **non sono applicate**. Finché non lo sono, la chat risponde
> HTTP 500 (`42P17`) e l'app lo dice esplicitamente invece di sembrare rotta.

## BLOCCO 5 — Video

- [x] 5.1 Gating premium rimosso **dove è davvero applicato**: policy su `videos`
      (migration `0008`), modello Dart (`is_premium`/`locked` non esistono più) e
      `video_service.py`. Il vecchio bundle lo forzava solo nel JavaScript, e il server
      continuava a rifiutare
- [x] 5.2 `is_starter`, `order_index` (0006) + `stage`, `description`, `safety_note`,
      `author` (0008)
- [x] 5.3 Percorso «Inizia da qui»: 7 tappe curate, in cima alla sezione video
- [x] 5.4 **Nessuna richiesta verso Google prima del tocco** — nemmeno per l'anteprima,
      che è disegnata in locale. Il video si apre fuori dall'app su `youtube-nocookie`,
      dopo una spiegazione mostrata una volta sola
- [x] 5.5 Riga di sicurezza **per tappa**, non un banner generico: quello che serve sapere
      prima di una rullata non è quello che serve prima di un salto di precisione
- [x] 5.6 **Le sette tappe hanno i loro video**, dal catalogo `docs/TUTORIAL_CATALOG.md`
      che ha portato l'utente. Scelti sul contenuto, non sul titolo: la tappa «Quadrupedia»
      prende *10 Parkour Moves on Flat Ground*, che nella sua scheda è descritto come
      «movimento quadrupedale, base spesso saltata dai principianti»
- [x] 5.7 **Il catalogo completo**: 117 video oltre ai 7 del percorso, in
      `scripts/data/tutorial_catalog.json`, caricabili con `scripts/seed_videos.mjs`.
      **Tutti e 124 verificati via oEmbed**: esistono e i loro autori consentono
      l'incorporamento — che è la loro autorizzazione esplicita, non una nostra
      interpretazione. Nessuno scartato
- [x] 5.8 Migration `0011`: `url` diventa chiave unica, così rilanciare il caricamento
      aggiorna invece di duplicare 117 righe
- [x] 5.9 **Le anteprime restano vuote di proposito.** Il catalogo porta i
      `thumbnail_url` di `i.ytimg.com`: caricarli significherebbe una richiesta a Google
      appena si apre la lista, mentre l'informativa dice che non ne parte nessuna. Il
      segnaposto è disegnato in locale
- [x] 5.10 Tradotte le stringhe inglesi rimaste nella sezione video: «Search tricks»,
      «Mark as landed», «Suggestion Generator», «Easier»/«Harder»

## BLOCCO 6 — Moderazione e DSA

- [x] 6.1 Segnalazione su spot, messaggi, commenti, post e **profili** (`profile_id` mancava:
      un utente molesto si poteva segnalare solo attraverso un suo messaggio). Vincolo che
      impone un solo bersaglio, e nessuno segnala sé stesso
- [x] 6.2 Console: code segnalazioni, contributi, spot, utenti — con sospensione a tempo
      (3/7/30 giorni) oltre al ban, perché fra «niente» e «per sempre» ci vuole qualcosa
- [x] 6.3 Statement of reasons: `record_moderation()` scrive registro e motivazione
      **insieme**, e la motivazione arriva all'utente nel profilo. Una decisione senza
      motivazione viene rifiutata dal database
- [x] 6.4 `moderation_events` — non esisteva affatto in produzione (404): il registro della
      migration 0001 non era mai stato creato. 12 mesi, con funzione di pulizia
- [x] 6.5 `abuse@pkfamily.app` citato dove serve; le pagine legali sono il BLOCCO 7
- [x] **`scripts/audit_rls.mjs`**, in CI: verifica da fuori cosa vede un estraneo, e
      dichiara «non concludente» invece di «passato» quando la tabella è vuota

> 🔴 **Trovato sondando la produzione: `reports` era leggibile da chiunque.** La tabella è
> vuota, ma alla prima segnalazione di molestie chi l'aveva scritta sarebbe stato leggibile
> dalla persona segnalata — e nessuno segnala più, se segnalare espone. Stessa lettura aperta
> su `post_saves` ed `entitlements`. Chiuse dalla migration `0009` con policy RESTRICTIVE.

## BLOCCO 7 — Legale e privacy

- [~] 7.1 Informativa artt. 13-14, **solo in italiano**: la versione inglese del piano non
      c'è, e la scelta è motivata in `docs/OPS_TODO.md` §6-ter. Descrive quello che il codice
      fa davvero — la sessione anonima crea una riga in `auth.users`, la chat non è cifrata
      end-to-end, la posizione non arriva mai al server
- [x] 7.2 Termini: gratuità, 16 anni e account del genitore, servizio **informativo e non
      organizzativo**, foro del consumatore. Il paragrafo sul rischio dice che il disclaimer
      **non è una rinuncia ai tuoi diritti** e cita art. 1229 c.c. e artt. 33/36 Cod. Consumo:
      una clausola nulla non protegge, e fingere il contrario peggiora la posizione
- [x] 7.3 Cookie: nessun banner perché non c'è nulla da consentire, con l'elenco di cosa
      finisce in `localStorage` e perché è tecnico
- [~] 7.4 Note legali: recapiti, provenienza dei dati della mappa, licenze.
      **Manca il nome del titolare** — segnaposto deliberato, vedi `docs/OPS_TODO.md` §6-bis
- [x] 7.5 Sub-responsabili: Supabase (Francoforte, con le clausole contrattuali standard),
      Cloudflare, GitHub. E YouTube dichiarato **non responsabile**, perché non incorporiamo
- [x] 7.6 Documenti interni in `docs/privacy/`, non pubblicati: `registro-trattamenti.md`
      (11 trattamenti), `dpia.md` (7 rischi con mitigazione e residuo),
      `procedura-data-breach.md` (le prime due ore, quando notificare, il registro),
      `lia-legittimo-interesse.md` (il test in tre passi per i quattro trattamenti su
      art. 6.1.f, con **cosa lo farebbe cadere** per ciascuno)
- [x] 7.7 Checkbox separate e non pre-spuntate, ciascuna con «Leggi» che apre il documento
      prima di spuntarla
- [x] `LegalLinks` raggiungibile **prima di qualsiasi decisione**: sta sul gate di sicurezza
      sotto il pulsante di rifiuto, e nel profilo anche da non registrati
- [x] `mobile/test/legal_texts_test.dart` — 10 controlli: i documenti esistono, sono datati e
      versionati, coprono quello che l'art. 13 richiede, e **non contengono formule d'esonero**
      («manleva», «declina ogni responsabilità», «in nessun caso saremo responsabili»…)
- [→] Revisione legale professionale di informativa, Termini e DPIA

> **Deviazione dal piano, dichiarata.** Il piano chiedeva le pagine legali in italiano *e
> inglese*. Ci sono solo in italiano. Una traduzione non revisionata di un'informativa afferma
> cose leggermente diverse dall'originale in un documento su cui l'utente fa affidamento:
> peggio di non averla. Quando l'app prende una seconda lingua, le pagine legali la prendono
> con lei — e la revisione legale copre entrambe.

## BLOCCO 8 — Infrastruttura e deploy

- [x] 8.1 `deploy/_headers.template` → CSP senza `'unsafe-eval'`, HSTS con preload,
      `frame-ancestors 'none'`, `Permissions-Policy` che nega tutto tranne la
      geolocalizzazione. `connect-src` nomina l'host Supabase **reale**, sostituito al deploy:
      un `*.supabase.co` lascerebbe parlare con qualsiasi progetto Supabase del mondo
- [x] 8.2 `deploy/_redirects` → www → apex con 301 vero, `/t/*` → `/` per chi ha il vecchio
      link, e la rewrite `200` per il routing SPA (un 301 verso `/` perderebbe il percorso)
- [x] 8.3 `deploy-staging.yml` (push su `main`) e `deploy-prod.yml` (tag `v*`). In produzione
      analyze, test e **audit RLS** rigirano prima di pubblicare — un tag si può mettere su
      qualsiasi commit — e dopo il deploy il workflow **interroga il sito vero** e fallisce se
      gli header non ci sono: Cloudflare ignora un `_headers` malformato senza dirlo
- [~] 8.4 Pagina di redirect pronta in `deploy/gh-pages/`, **non pubblicata**: finché
      `pkfamily.app` non risponde, `gh-pages` è l'unica versione raggiungibile e sostituirla
      manderebbe su una pagina morta chi ha il QR. `publish_gh_pages_redirect.sh` lo verifica
      da sé. **GitHub Pages non può fare un 301 vero**: la pagina usa `rel=canonical`, meta
      refresh e un link visibile — è meno, e va detto
- [x] 8.5 `security.txt` generato a ogni deploy con `Expires` ricalcolato (RFC 9116 lo rende
      obbligatorio, e una data scaduta è peggio del file assente). `SECURITY.md` riscritto:
      tempi che una persona sola può tenere, e via le voci spuntate che descrivevano il
      backend FastAPI mai deployato
- [x] 8.6 **Si lancia senza error tracking**, come decisione motivata in `docs/OPS_TODO.md`
      §12: un error tracker è un responsabile del trattamento in più su un progetto che ne ha
      tre. Al suo posto una schermata d'errore leggibile che dice a chi la vede cosa scrivere
      e dove — perché senza telemetria l'unico sensore sono gli utenti
- [x] 8.7 `robots.txt` e `sitemap.xml` generati (permissivi in produzione, `Disallow: /` su
      staging), meta OG e `canonical` in `index.html`. Nessun `noindex` residuo nell'app
- [x] **CanvasKit servito da noi, non da `gstatic.com`.** Il build predefinito lo scarica dal
      CDN di Google a ogni apertura — cioè esattamente la richiesta che l'informativa dichiara
      di non fare. `--no-web-resources-cdn` la elimina, e `prepare_deploy.mjs` si rifiuta di
      pubblicare un build che non ce l'abbia
- [x] `scripts/prepare_deploy.mjs` — l'ultima rete prima della pubblicazione: rifiuta un
      bundle con dentro una secret key, un host Supabase diverso da quello nella CSP, un
      segnaposto non sostituito. Gira anche in CI, così si rompe lì e non a tag già spinto
- [→] Dominio registrato, DNS, progetti Cloudflare, i quattro secret, DPA, caselle email

> **31 MB.** È quanto pesa il build, e il service worker di Flutter se li porta giù tutti per
> l'uso offline. Alla prima apertura il browser ne scarica ~10 MB (un motore di rendering
> solo), il resto arriva dopo, in background, su rete mobile. Non l'ho cambiato: per un'app
> che si apre davanti a un muro dove il campo non prende, l'offline vale quei megabyte. Ma è
> una decisione da prendere sapendo il numero — opzioni in `docs/OPS_TODO.md` §12-bis.

## BLOCCO 9 — Verifica prima del tag

- [x] 9.1 `scripts/audit_rls.mjs` in due fasi. **Fase 1** (in CI): cosa vede chi non ha fatto
      login. **Fase 2** (`--sessione`, a mano prima di un tag): cosa può fare chi *un account
      ce l'ha* — non può nominarsi admin, non tocca il profilo di un altro, non vede la
      corrispondenza altrui, non si autoverifica uno spot. La fase 2 non è in CI perché
      lascia dietro un utente anonimo per esecuzione
- [x] 9.1-bis Il controllo del gate è **conclusivo**, non «non concludente»: guarda gli spot
      prima e dopo aver registrato la presa d'atto. Se prima niente e dopo sì, la policy della
      `0005` funziona davvero — l'unico controllo dello script che dimostra qualcosa anche su
      una tabella piena
- [x] 9.3 `scripts/check_headers.mjs` — non guarda solo se un header c'è, guarda cosa dice:
      una CSP con `'unsafe-eval'` è presente e inutile, un HSTS con `max-age=60` è presente e
      non protegge. Controlla anche che `connect-src` non usi `*.supabase.co`, che
      `security.txt` non sia scaduto, e che lo staging non sia indicizzabile
- [~] 9.2 / 9.4 `docs/COLLAUDO.md` — la sequenza da provare a mano su staging, passaggio per
      passaggio, con dentro il ripristino del backup su un progetto vuoto. **Da eseguire:**
      serve staging online, le migration applicate e un secondo account
- [x] 9.5 Checklist e `docs/OPS_TODO.md` aggiornati

> 🔴 **Trovato eseguendo la verifica: il gate di sicurezza non regge per chi non fa login.**
> Con la sola chiave pubblica e nessuna sessione, `GET /rest/v1/spots` restituisce i 24 spot
> con le coordinate. La policy della `0005` è `to authenticated` e non tocca il ruolo `anon`;
> il disegno teneva perché il client apre una sessione anonima all'avvio — ma quella è una
> riga di Dart, e in produzione **le sessioni anonime sono spente**
> (`"anonymous_users": false`). Chiuso da `0010_gate_anche_senza_login.sql`, che nega gli spot
> ad `anon` in modo esplicito. Va applicata **dopo** aver attivato le sessioni anonime:
> `docs/OPS_TODO.md` §0.

> **Cosa questo blocco non ha potuto verificare.** La fase 2 dell'audit è scritta ma **mai
> eseguita fino in fondo**: in produzione le sessioni anonime sono spente, quindi non c'è modo
> di aprire la sessione che le serve, e lo script si ferma dichiarandolo «non concludente»
> invece di fingere. La prima esecuzione vera sarà su staging, ed è il primo passo di
> `COLLAUDO.md`.
