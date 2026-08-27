# Prompt operativo — dal privato al pubblico

Prompt pronto da incollare in una sessione Claude Code su questo repo. Mette in pratica
[`docs/LAUNCH_PLAN.md`](LAUNCH_PLAN.md): mappa con gli spot, gate di sicurezza all'ingresso,
chat in gruppi e private, sezione video per chi inizia, gestione degli accessi, dominio,
deploy e adempimenti legali/privacy UE.

Undici blocchi (0 → 9, più il 3-bis). **Lanciane uno alla volta**: ogni blocco chiude con
codice verificabile, e l'esito di uno cambia il contesto del successivo. Avanzamento in
[`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md).

---

# PkFAMILY — dall'anteprima privata al lancio pubblico su pkfamily.app

Lavori sul monorepo `Parkour_NoToTFamily`. Leggi prima `docs/PROJECT_RULES_AND_ROADMAP.md`,
`docs/WEB_TEST_SPACE.md`, `📲/README.md` e `supabase/migrations/0001_initial.sql`.

## Contesto e decisioni già prese (non rimetterle in discussione)

- Titolare del trattamento: **persona fisica, senza P.IVA**. Il servizio è e resta
  **gratuito**: nessun pagamento, nessun abbonamento, nessun paywall.
- La web app si **builda da Flutter** (`mobile/`), non più da Expo. Il bundle su `gh-pages`
  e tutta la catena di patch su JS minificato vanno in pensione.
- Backend di produzione: **Supabase**. `backend/` (FastAPI) si congela come riferimento.
- Dominio pubblico: **pkfamily.app**, hosting su **Cloudflare Pages**.
- Età minima: **16 anni**, autodichiarata.
- Nessuna cifratura end-to-end in chat: va dichiarato, non nascosto.

Regole di lavoro: branch `feat/<x>` da `main`, Conventional Commits, un cambiamento logico
per commit, `flutter analyze` + `flutter test` verdi prima di ogni push. Nessun segreto nel
repo. Le migrazioni sono append-only.

---

## BLOCCO 0 — Messa in sicurezza immediata

0.1 **`gh-pages`: ricrea il branch come orfano, senza `invito/index.html`.** Quella pagina
    espone un IBAN personale e il nome del titolare, ed è incompatibile con il servizio
    gratuito. Cancellarla con un commit normale non basta: la storia del branch è pubblica e
    l'IBAN resterebbe recuperabile. Quindi: prendi l'albero attuale, togli `invito/`, togli il
    link "Richiedi un invito" da `index.html`, e ricrea `gh-pages` come branch **orfano** con
    un solo commit, force-push. L'anteprima sotto `/t/<token>/` resta accessibile a chi ha il
    QR. Avvisa in `docs/OPS_TODO.md` che lo "Scenario C" di `📲/README.md` (rollback del sito
    via `git revert` su gh-pages) è temporaneamente senza storia su cui tornare.
0.2 Modifica `📲/backup.mjs` e `.github/workflows/backup-quotidiano.yml`: **escludi `profiles`
    e ogni tabella con dati personali** dal backup pubblicato sul branch pubblico `backup`.
    Restano solo `spots`, `videos`, `fountains`, `spot_photos`. Aggiorna `📲/README.md`, che
    oggi afferma che il backup pubblico "è pensato per essere pubblico": la premessa cambia.
0.3 Scrivi `docs/LAUNCH_CHECKLIST.md` con lo stato di ogni voce di questo prompt
    (da fare / in corso / fatto), così il lancio è tracciabile.
0.4 Genera `docs/OPS_TODO.md` con le azioni **non automatizzabili** che restano all'umano:
    registrare pkfamily.app, verifica di anteriorità EUIPO/UIBM sul nome, verificare che il
    progetto Supabase sia in regione UE (se non lo è: creare progetto UE e migrare),
    accettare i DPA di Supabase e Cloudflare, creare privacy@/abuse@/security@pkfamily.app,
    far rivedere i testi legali a un professionista.

## BLOCCO 1 — Fondamenta

1.1 `cd mobile && flutter create --platforms web .` — genera `web/` con `manifest.json`
    (PWA installabile, nome "PkFAMILY", icone, `display: standalone`, tema scuro) e
    `index.html` senza tracker.
1.2 Aggiungi `supabase_flutter` a `pubspec.yaml`. Crea `lib/services/supabase_client.dart`
    che legge URL e **publishable key** da `--dart-define` (mai hardcoded). Sostituisci
    `lib/services/api_client.dart` (che punta a FastAPI) mantenendo le firme di
    `SpotRepository.fetchSpots()` e `VideoRepository.fetchTutorials()`, così
    `providers.dart` e le screen non cambiano.
    ⚠️ **I modelli non combaciano con la produzione.** `models/spot.dart` rispecchia lo schema
    FastAPI (`location: GeoPoint`, `photoUrls`, `difficulty` 1-5, `water`, `submittedBy`).
    La tabella `spots` reale ha invece: `id, name, lat, lng, description, skill_level,
    crowd_level, has_fountain, status, rejection_reason, author_id, verified_by, created_at,
    verified_at` — niente PostGIS, niente array di foto (stanno in `spot_photos`), e
    `skill_level`/`crowd_level` sono testo (`principiante|intermedio|avanzato`,
    `tranquillo|medio|affollato`), non numeri. Riscrivi `Spot.fromJson` sulla forma reale,
    tenendola **tollerante** come impone `docs/PROJECT_RULES_AND_ROADMAP.md` §3.
1.3 **Allinea le migration alla produzione, non viceversa.** `supabase/migrations/0001_initial.sql`
    descrive uno schema che **non esiste**: nomi di tabella diversi (`conversations`/
    `conversation_members` contro `chats`/`chat_members`) e colonne diverse su `spots`.
    La produzione ha dati reali e l'app ci parla, quindi è il repo a dover essere corretto.
    - Scrivi `scripts/dump_schema.sh` (wrapper su `supabase db dump --schema public`) e
      documentalo: **richiede la secret key, lo lancia l'umano** — vedi `docs/OPS_TODO.md`.
    - Nel frattempo scrivi `supabase/migrations/0003_production_schema.sql` come
      ricostruzione **dichiarata tale in testa al file**, basata sulle colonne osservate via
      REST e sull'elenco tabelle di `📲/backup.mjs`. Va sostituita dal dump reale appena
      disponibile: non fidarti di una ricostruzione per il disaster recovery.
    - Marca `0001_initial.sql` e `0002_instructor_role.sql` come **storici e mai applicati in
      produzione**, così nessuno li esegue per sbaglio.
    - Aggiorna `docs/DATA_MODEL.md` sulla forma reale.
1.4 **Correggi la ricorsione infinita nelle policy della chat.** In produzione
    `GET /rest/v1/chats` risponde **HTTP 500** con
    `42P17: infinite recursion detected in policy for relation "chat_members"`: la policy su
    `chats` interroga `chat_members` e viceversa. **La chat oggi è rotta a livello di
    database**, non solo priva di client. Migration nuova che introduce una funzione
    `SECURITY DEFINER` (`is_chat_member(chat_id)`) e riscrive le policy in termini di quella —
    è esattamente il pattern già usato in `0001_initial.sql:226`
    (`is_conversation_member()`), applicato però ai nomi di tabella reali.
1.5 Ripara `web-admin`: `src/app/login/page.tsx:6` e `src/app/spots/page.tsx:6` importano
    `@/lib/api`, che **non esiste**. Riscrivilo su Supabase Auth + RLS (niente secret key nel
    client), usando `is_admin()`.
1.6 Crea `.github/workflows/ci.yml`: su ogni PR `flutter analyze`, `flutter test`,
    `dart format --set-exit-if-changed`, e `npm run lint && npm run build` per `web-admin`.
1.7 Elimina `scripts/patch-gh-pages-test-free.py`, `scripts/update_deployed_spots.py`,
    `scripts/deploy_test_web.sh`. Aggiorna `docs/WEB_TEST_SPACE.md` per riflettere il nuovo
    flusso (o sostituiscilo con `docs/DEPLOY.md`).

## BLOCCO 2 — Accessi e account

2.1 Auth con Supabase: registrazione email+password con **conferma email obbligatoria**, login,
    reset password, logout. Password minimo 12 caratteri, con il controllo nativo Supabase
    contro password compromesse. Rate limit su login e registrazione.
2.2 **Age gate**: in registrazione, data di nascita o dichiarazione "ho almeno 16 anni".
    Sotto i 16 → registrazione bloccata con un messaggio che spiega il motivo (art. 8 GDPR).
    Salva `age_confirmed_at` sul profilo.
2.2.bis **Accesso tramite genitore.** Chi viene bloccato dall'age gate deve trovare una strada,
    non un muro: pulsante "Chiedi a un genitore di aprire l'accesso".
    - Il minore inserisce l'email di un adulto → tabella `parent_access_requests`
      (`email`, `token`, `created_at`, `expires_at`), **una sola** email inviata,
      cancellazione automatica dopo 7 giorni se non completata. Rate limit stretto: è un
      canale di invio email guidato da un input utente, va protetto dall'abuso.
    - L'adulto apre il link e crea **il proprio** account: dichiara ≥18 anni e di esercitare
      la responsabilità genitoriale sul minore che userà il servizio sotto supervisione,
      accetta Termini e gate di sicurezza anche per suo conto.
    - Profilo con `supervised = true` e `supervisor_confirmed_at`. Il minore **non ha un
      account proprio**: nessuna email di minore viene trattata.
    - **La chat nasce disattivata** (`chat_enabled = false`) su questi account. Il genitore
      può attivarla dalle impostazioni, dopo un avviso esplicito sul rischio di contatto con
      adulti sconosciuti. Applica il vincolo **anche nelle RLS**, non solo in UI: un profilo
      con `supervised = true` e `chat_enabled = false` non deve poter inserire in `messages`
      né in `conversation_members`.
    - Il flag `supervised` è visibile alla moderazione.
2.3 Livelli: **anonimo** (mappa spot `verified`, video, pagine legali — sola lettura),
    **user** (propone spot, commenta, chat), **instructor** (badge, concesso da admin — non è
    un tier a pagamento), **admin** (solo a livello DB). Non introdurre percorsi API che
    assegnino `admin`.
2.4 Schermata profilo: modifica display name, **"Scarica i miei dati"** (JSON con profilo,
    spot, commenti, messaggi) e **"Elimina account"** (conferma via email, 30 giorni di
    grazia, cancellazione di profilo e contenuti, **pseudonimizzazione** dell'autore nei
    messaggi già inviati).
2.5 Rimuovi ogni traccia del gate PkPASS: il segreto client-side, il path `/t/<token>/` e la
    registrazione dispositivo via `mailto` che spediva Device ID e user agent all'admin —
    era fingerprinting senza base giuridica.
2.6 Deprecare `admin-desktop/index.html`: la secret key non deve stare in un browser. Sposta
    l'export completo in una Supabase Edge Function che verifica il ruolo server-side.
2.7 **Gate di sicurezza all'ingresso.** Schermata bloccante alla prima apertura, per
    **chiunque** — registrato o anonimo — prima che la mappa mostri un solo spot, e di nuovo a
    ogni cambio di versione del testo. Contenuto: la mappa è **informativa** e raccoglie in un
    posto solo ciò che già circola nella community; PkFAMILY **non organizza, non supervisiona
    e non promuove** attività sportiva; gli spot **non sono ispezionati né certificati** e le
    condizioni cambiano; alcuni possono essere su **proprietà privata**; chi pratica **si
    assume consapevolmente il rischio** e valuta da sé livello e condizioni.
    - Scrivi il testo come **presa d'atto e assunzione del rischio**. **Non** scrivere mai
      «l'utente esonera PkFAMILY da ogni responsabilità»: verso un consumatore una clausola
      che limita la responsabilità per danni alla persona è nulla (artt. 33 e 36 Cod. Consumo;
      art. 1229 c.c. per dolo e colpa grave), e una clausola nulla non protegge.
    - Il testo di ogni versione vive in `assets/legal/safety_notice_<versione>.md`, versionato
      nel repo.
    - **Registra l'accettazione**, altrimenti il gate in giudizio vale zero: nuova tabella
      `safety_acknowledgements` (`user_id` o id anonimo di sessione, `version`,
      `text_sha256` del testo esattamente mostrato, `accepted_at`). Per gli anonimi tieni il
      flag in `localStorage` e consolidalo sul profilo al primo login.
    - Non è un banner cookie e non va costruito come tale: è presa d'atto contrattuale, non
      consenso al trattamento. Dichiara il flag `localStorage` come storage tecnico.
    - Revocabile in entrambe le direzioni dalle impostazioni.
2.8 **Modalità informativa senza spot** per chi rifiuta. Non buttarlo fuori: l'app resta
    utilizzabile con **mappa vuota** — nessun pin, nessuna coordinata, nessuna scheda spot —
    più sezione video e pagine legali. Un pulsante sempre visibile permette di accettare
    dopo. Applica il filtro **anche lato server**: senza acknowledgement valido le query sugli
    spot non devono restituire coordinate. Un rifiuto aggirabile disattivando JavaScript non
    è un rifiuto.
2.9 In ogni **scheda spot**, la versione breve della stessa avvertenza: è lì che si decide
    davvero se andarci.

## BLOCCO 3 — Mappa e spot

3.1 Ripulisci il dataset **prima** di importarlo. Su `scripts/data/webapp_fixed_spots.json`:
    - rimuovi ogni URL foto che non sia `upload.wikimedia.org` (oggi ci sono hotlink a
      `parkourbilbao.com`, `comune.roma.it`, `vistanet.it`, `abitarearoma.it`: rischio copyright);
    - rimuovi qualsiasi immagine Street View (`streetviewpixels-pa.googleapis.com`): fuori
      dalle API ufficiali è contrario ai ToS di Google;
    - per le immagini Wikimedia superstiti aggiungi **autore, licenza e link alla pagina**, e
      mostrali nella scheda spot;
    - **segnala** in `docs/OPS_TODO.md` che i 1.706 spot derivano da una lista Google Maps
      condivisa (`scripts/fetch_gmaps_list.py`) e che vanno ricostruiti da OpenStreetMap
      (ODbL, con attribuzione) o da segnalazioni della community: la lista come *selezione*
      può essere coperta dal diritto sui generis sulle banche dati.
3.2 Importa gli spot ripuliti **in Supabase**, non nel bundle. Script idempotente in
    `scripts/import_spots_supabase.mjs`; gli spot importati partono con status `community`,
    distinti dai `verified` della famiglia.
3.3 Mappa in `lib/screens/spots_map_screen.dart` (`flutter_map` già presente):
    tile OpenFreeMap (`tiles.openfreemap.org`) con attribuzione OSM visibile; **clustering**
    dei marker + rendering del solo viewport (a ~1.700 spot serve); pin distinti per
    family/community/proprio spot in attesa; filtri per difficoltà, acqua, livello.
    Non usare tile Esri senza aver verificato la licenza.
3.4 Scheda spot: nome, descrizione, difficoltà (riusa `widgets/difficulty_gauge.dart`), foto
    con crediti, acqua, commenti, like, distanza e percorso a piedi (porta la logica di
    `scripts/web/pk-route.js`, ma valuta un router meno fragile del server pubblico FOSSGIS).
    Aggiungi il campo `access_type` (pubblico / privato / con permesso) e mostralo.
3.5 **Geolocalizzazione**: chiedila **solo al tap** su "dove sono"/"percorso", mai all'avvio,
    preceduta da una schermata che spiega perché serve. La posizione resta nel device: non
    salvarla e non inviarla a Supabase. Gestisci il diniego senza rompere la mappa.
3.6 "Proponi uno spot": form → insert con `status = 'pending'` (le RLS esistenti lo impongono
    già). L'autore vede il proprio spot in attesa; nessun altro.

## BLOCCO 3-bis — Rendere utilizzabili gli spot fuori Roma (gate di lancio)

**Il problema, misurato.** I 1.680 spot `community` non sono spot descritti male: sono
**segnaposto**. Verificato su `scripts/data/webapp_fixed_spots.json`:

- **nomi generati**: «Spot Athens 3», «Spot Náfplio 1» — non dicono nulla;
- **descrizione = solo la città**: «Bologna, Italia. Dalla lista community Google Maps
  "Parkour spot"», su tutti e 1.680;
- **attributi identici e inventati**: `skillLevel = intermedio`, `crowdLevel = medio`,
  `hasFountain = false`, `rating = 0` su **tutti e 1.680**. Non sono dati mancanti: sono
  valori di default mostrati all'utente come se fossero valutazioni;
- **foto: 5 su 1.680**;
- **154 spot citano 23 persone reali** («segnalato da Davide Rizzi», «Andrea Valitutti»...),
  scrapate dalla lista Google Maps. Il commit `031db8e` doveva rimuovere le attribuzioni e
  il lavoro è rimasto a metà.

Confronto con i 26 di Roma: «Gradonate in marmo e muri alti: spot tecnico per salti di
precisione e passamuro. **Attenzione ai custodi.**» Quella è conoscenza di chi c'è stato.
Nessuna API la produce, e generarla automaticamente significa **inventare fatti su luoghi
fisici dove la gente si fa male** — l'esatto contrario della «mappa informativa» su cui si
regge il gate di sicurezza (§3.4).

Distribuzione: 555 Italia (283 località), 263 USA, 201 Spagna, 141 Regno Unito, 59 Germania,
poi coda lunga su 61 paesi. In Italia: Bologna 20, Bolzano 18, Milano 10, Salerno 9, Genova 8.

**La regola che governa tutto il blocco: ciò che non si sa si dichiara sconosciuto.**
Mai un default travestito da valutazione.

3b.1 **Togli i dati inventati.** `skill_level`, `crowd_level` e `has_fountain` diventano
     **nullable** e vanno a `NULL` su tutti gli spot `community`. In UI: «non ancora
     valutato», non «intermedio». Elimina `rating`/`ratingCount` fittizi: zero recensioni
     non è un punteggio.
3b.2 **Togli i nomi delle 23 persone** dalle descrizioni, e aggiungi un test che fa fallire
     la pipeline se il pattern «segnalato da» ricompare.
3b.3 **Toponimo reale al posto del nome generato.** Reverse geocoding via **Nominatim/OSM**
     (rispettando la usage policy: 1 req/s, User-Agent identificabile, risultati messi in
     cache nel repo) → «Spot Athens 3» diventa «Pedion tou Areos — Atene». Dove il reverse
     geocoding non dà nulla di meglio, il nome resta generico ma la scheda lo dichiara.
3b.4 **Contesto fattuale da OpenStreetMap** via Overpass, entro ~150 m: `leisure=pitch`,
     `sport=parkour`, `leisure=fitness_station`, `surface=*`, e soprattutto
     `amenity=drinking_water` → **`has_fountain` reale** al posto del `false` piatto su
     tutti. Sono fatti verificabili con una fonte citabile, non prosa inventata.
3b.5 **Foto legali e automatiche.** Nell'ordine:
     - **Mapillary** (API ufficiale, immagini **CC-BY-SA 4.0**): è la sostituzione lecita
       dello Street View in hotlink che il BLOCCO 3 rimuove. Cerca per coordinate, salva
       l'id immagine + autore + licenza, mostra l'attribuzione nella scheda.
     - **Wikimedia Commons** geosearch per i luoghi notevoli, con autore e licenza.
     - Nient'altro. Nessun hotlink da siti terzi, nessuna immagine senza licenza nota.
     Le foto vanno in `spot_photos` (oggi 0 righe) con `source`, `author`, `license`,
     `source_url` — non in un array di URL nel bundle.
3b.6 **Stato di completezza esplicito** su ogni spot: `da_completare` (solo coordinate),
     `arricchito` (toponimo + contesto OSM + almeno una foto), `verificato` (un umano c'è
     stato e l'ha descritto — oggi solo i 26 di Roma). Pin visivamente distinti sulla mappa,
     e la scheda dice a che punto è.
3b.7 **Il seme del crowdsourcing, non un contorno.** Su ogni spot incompleto, in evidenza:
     «Ci sei stato? Aggiungi una foto e raccontalo» → form con foto, descrizione, skill,
     affollamento, acqua. Va in moderazione come una proposta di spot (BLOCCO 6). È questo,
     non la pipeline, che nel tempo porta gli spot da `arricchito` a `verificato`.
3b.8 **Cruscotto di copertura**: `scripts/spot_coverage.mjs` stampa, per paese e città,
     quanti spot sono in ciascuno stato. È la misura del gate di lancio, e va in
     `docs/LAUNCH_CHECKLIST.md`.

**Gate di lancio (deciso):** nessuno spot pubblicato con attributi inventati o nomi di terzi;
tutti e 1.706 con toponimo reale e stato di completezza dichiarato; foto automatica dove
Mapillary o Commons ce l'hanno; contributo della community aperto dal giorno uno. Le
descrizioni «alla romana» arrivano dopo, dalle persone — non da una pipeline.

## BLOCCO 4 — Chat: gruppi e private

4.1 Implementa il client sulle tabelle esistenti (`conversations`, `conversation_members`,
    `messages`): lista conversazioni, chat 1-a-1 (`kind='direct'`), gruppi (`kind='group'`)
    con creazione, invito, uscita. Usa **Supabase Realtime** per i messaggi in tempo reale.
4.2 Solo utenti registrati con email confermata. Rate limit sull'invio.
4.3 **Blocco utente** (tabella `blocked_users`): l'utente bloccato non può scrivere in privato
    né vedere i tuoi messaggi. **Segnalazione messaggio** → `reports`.
4.4 Nell'informativa e in una nota visibile nella schermata chat: **non c'è cifratura
    end-to-end**, l'amministratore ha accesso tecnico al database. Non promettere il contrario.
4.5 Alla cancellazione dell'account, i messaggi già inviati vengono **pseudonimizzati**
    (autore → "utente eliminato") anziché rimossi dalle conversazioni altrui. Documentalo.

## BLOCCO 5 — Video per chi inizia

5.1 **Rimuovi il gating premium**, non nasconderlo: `backend/app/services/video_service.py:21`
    (`is_premium`) e le RLS corrispondenti su `videos`/`entitlements`. Con il servizio gratuito
    ogni video è accessibile a tutti, **anche agli anonimi**. Verifica che non resti nessuna
    scrittura che le RLS rifiutano in silenzio.
5.2 Aggiungi `is_starter` e `order_index` alla tabella `videos` (nuova migration).
5.3 Percorso **"Inizia da qui"** in cima alla sezione video, sequenza per chi non ha mai
    fatto parkour: riscaldamento e mobilità → atterraggio e rullata (*roulade*) → quadrupedia
    → precision jump → vault di base (safety, speed, kong) → progressione e gestione della
    paura → prevenzione infortuni e recupero. Poi le categorie esistenti
    (`practice` / `conditioning` / `recovery`) filtrabili per livello.
5.4 Video **embeddati**, non ospitati. Usa `youtube-nocookie.com`. Poiché l'embed carica
    risorse di terze parti, mostra un **placeholder cliccabile** finché l'utente non
    acconsente esplicitamente a caricare il player: senza consenso non deve partire alcuna
    richiesta verso Google.
5.5 In ogni scheda video, una riga di sicurezza: progressione graduale, superficie adatta,
    spotter, non superare il proprio livello.
5.6 Popola almeno il percorso "Inizia da qui" con video reali e liberamente embeddabili;
    in `docs/OPS_TODO.md` elenca quelli per cui serve conferma dall'autore.

## BLOCCO 6 — Moderazione e DSA

6.1 Segnalazione su spot, messaggi, commenti e profili (categorie: contenuto illecito,
    molestie, spot pericoloso, spam, proprietà privata) → tabella `reports`, con RLS che la
    rende leggibile solo agli admin.
6.2 In `web-admin`: coda spot `pending` con verifica/rifiuto (motivo obbligatorio), coda
    segnalazioni, gestione utenti (sospensione, ban, promozione a `instructor`).
6.3 **Statement of reasons** (art. 17 DSA): quando un contenuto viene rimosso o uno spot
    rifiutato, l'autore riceve la motivazione. Il campo `rejection_reason` esiste già in
    `spots`; estendi il pattern agli altri contenuti.
6.4 Log di moderazione su ogni azione (estendi `spot_moderation_events`), conservato 12 mesi.
6.5 Punto di contatto `abuse@pkfamily.app` pubblicato nei Termini e in una pagina dedicata.

## BLOCCO 7 — Pagine legali e privacy

Crea `lib/legal/` con pagine raggiungibili dal footer di **ogni** schermata, anche da
anonimo, in **italiano e inglese**, ciascuna con data di ultima modifica e versione.
Marca chiaramente i testi come **bozza da far validare a un legale** (nota in
`docs/OPS_TODO.md`, non nella pagina pubblica).

7.1 `/legale/privacy` — informativa artt. 13-14 GDPR con la tabella dei trattamenti:
    account (art. 6.1.b), spot proposti (6.1.b + 6.1.f), chat (6.1.b), geolocalizzazione
    (6.1.a, **non conservata**), moderazione (6.1.c + 6.1.f), log antiabuso (6.1.f, 30 gg),
    backup (6.1.f, 30 gg). Più: destinatari e responsabili (Supabase, Cloudflare, GitHub,
    YouTube), trasferimenti extra-UE e garanzie, diritti artt. 15-22 con istruzioni concrete,
    reclamo al Garante, assenza di cifratura end-to-end, contatto `privacy@pkfamily.app`.
7.2 `/legale/termini` — gratuità, età minima 16 **e account supervisionato da un genitore**
    (il titolare dell'account risponde dell'uso che ne viene fatto), natura **informativa e non
    organizzativa** del servizio in coerenza col gate 2.7, regole di condotta, licenza non esclusiva sui
    contenuti caricati (con dichiarazione dell'utente di averne il diritto e che non ci sono
    volti riconoscibili di terzi senza consenso), moderazione e sanzioni con possibilità di
    contestare, **disclaimer di sicurezza** (la pratica è a proprio rischio, gli spot non sono
    ispezionati né certificati), limitazione di responsabilità **nei limiti dell'art. 1229 c.c.**
    — non scrivere clausole di esonero totale, sarebbero nulle — legge italiana e **foro del
    consumatore** (residenza dell'utente), procedura di modifica con preavviso.
7.3 `/legale/cookie` — dichiara il `localStorage` di sessione come **tecnico** (nessun consenso
    richiesto) e l'assenza di cookie di profilazione. **Non integrare Google Analytics.** Se
    serve una misura d'uso, usa Plausible o Umami self-hosted in UE, cookieless.
7.4 `/legale/note-legali` — identificazione del titolare: nome e cognome + email di contatto
    (D.lgs 70/2003). **Non pubblicare l'indirizzo di casa.**
7.5 `/legale/sub-responsabili` — elenco dei responsabili esterni con finalità e sede, e
    impegno a notificare le variazioni.
7.6 Documenti **interni** in `docs/privacy/` (non pubblicati):
    `registro-trattamenti.md` (art. 30 — l'esenzione sotto i 250 dipendenti non si applica,
    il trattamento non è occasionale e include geolocalizzazione),
    `dpia.md` (art. 35, valutazione leggera: geolocalizzazione + community + minori),
    `procedura-data-breach.md` (notifica al Garante entro 72 ore, con registro delle violazioni),
    `lia-legittimo-interesse.md` per i log antiabuso e la mappa pubblica.
7.7 In fase di registrazione: checkbox **separate e non pre-spuntate** per Termini e presa
    visione dell'informativa. Nessun consenso raggruppato.

## BLOCCO 8 — Infrastruttura e deploy

8.1 `_headers` per Cloudflare Pages: CSP restrittiva (`default-src 'self'`, con i domini
    Supabase, i tile e `youtube-nocookie.com` esplicitati; niente `unsafe-inline` se il build
    Flutter lo consente, altrimenti documenta il motivo), `Strict-Transport-Security`
    con preload, `X-Content-Type-Options: nosniff`,
    `Referrer-Policy: strict-origin-when-cross-origin`,
    `Permissions-Policy` che nega tutto tranne `geolocation=(self)`.
8.2 `_redirects` per il routing SPA.
8.3 `.github/workflows/deploy-staging.yml` (push su `main` → `staging.pkfamily.app`) e
    `deploy-prod.yml` (tag `v*` → `pkfamily.app`). Chiavi Supabase e Cloudflare dai GitHub
    Secrets, mai nel repo.
8.4 Svuota `gh-pages` e lascia un **redirect 301** verso `https://pkfamily.app`: chi ha il QR
    o il link vecchio non deve trovare un 404.
8.5 `/.well-known/security.txt` con `security@pkfamily.app`. Allinea `SECURITY.md`, che oggi
    promette un SLA "48h ack / 14d fix" non sostenibile da una persona sola, e punta a
    `security@notot.family`.
8.6 Sentry (region UE) con scrubbing dei dati personali, o in alternativa documenta
    esplicitamente in `docs/OPS_TODO.md` che si lancia senza error tracking.
8.7 `robots.txt` permissivo, `sitemap.xml`, meta OG. Rimuovi ogni `noindex` residuo.

## BLOCCO 9 — Verifica prima del tag

9.1 **Audit RLS** — scrivi `scripts/audit_rls.mjs` che, usando la sola publishable key da
    client **non autenticato**, verifica che: `spots?status=eq.pending` torni vuoto,
    `messages` torni vuoto o 401, l'update di un `profiles` altrui fallisca, nessuna policy
    consenta di scrivere `role = 'admin'`, un profilo `supervised` con `chat_enabled = false`
    non possa inserire in `messages`, e senza acknowledgement valido gli spot non restituiscano
    coordinate. Deve uscire con exit code ≠ 0 al primo fallimento, e girare in CI.
9.2 Prova a mano su staging i percorsi: anonimo (mappa → scheda → video → pagine legali);
    registrazione con età < 16 → bloccata, ≥ 16 → conferma email → login; spot proposto →
    invisibile in pubblico → verificato dall'admin → compare; chat di gruppo e privata con
    blocco e segnalazione; export dati → JSON completo; eliminazione account → dati rimossi
    e messaggi pseudonimizzati.
9.3 `curl -sI https://staging.pkfamily.app` e verifica gli header di sicurezza.
9.4 Prova di restore dal backup su un progetto Supabase vuoto: se non funziona, lo "Scenario B"
    resta teorico.
9.5 Aggiorna `docs/LAUNCH_CHECKLIST.md` e chiudi le voci di `docs/OPS_TODO.md` che ti competono.

---

Se un blocco rivela un vincolo che rende una richiesta impossibile o rischiosa, **fermati e
segnalalo** invece di aggirarlo. Non inventare testi legali che affermino garanzie inesistenti
(cifratura end-to-end, esonero totale di responsabilità, conformità certificata): descrivi ciò
che il sistema fa davvero.
