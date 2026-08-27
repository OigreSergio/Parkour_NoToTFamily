# Piano di pubblicazione PkFAMILY — web app pubblica su `pkfamily.app`

## Context

Oggi PkFAMILY esiste come **anteprima privata**: un bundle Expo compilato pubblicato su
`gh-pages` sotto `https://oigresergio.github.io/Parkour_NoToTFamily/t/2fe095ecfaa79a73/`,
protetto solo da `robots.txt` + `noindex` + un gate JavaScript con segreto in chiaro
(`gh-pages:index.html`, `PK_SECRET = "pk_4f7934b9aed5ae01b547a0c1"`). Il documento
`docs/WEB_TEST_SPACE.md` lo dice già esplicitamente: *«È riservatezza, non autenticazione»*.

Vogliamo passare al pubblico. L'esplorazione del repo ha però fatto emergere che il salto
non è la checklist in 3 righe di `WEB_TEST_SPACE.md` ("sposta l'app in root, togli noindex,
rigenera il QR"), perché ci sono **cinque blocchi reali**:

1. **Il sorgente della web app pubblicata non esiste nel repo.** Su `gh-pages` c'è solo il
   bundle minificato; `mobile/` è un progetto **Flutter**, non Expo. L'unico modo attuale di
   modificare l'app è fare string-replace su JS minificato
   (`scripts/patch-gh-pages-test-free.py`, documentato come *«Non idempotente»* e che fallisce
   se un'ancora non si trova esattamente una volta). Non è una base su cui lanciare.
2. **Superficie legale pari a zero.** Nessuna informativa privacy, nessun termine d'uso,
   nessun age gate, nessuna cancellazione account, nessun imprint — contro un'app in italiano,
   rivolta all'UE, che raccoglie **geolocalizzazione precisa** (`watchPosition` in
   `scripts/web/pk-route.js`), email via Supabase Auth e contenuti generati dagli utenti.
3. **Una pagina che incassa denaro** (`gh-pages:invito/index.html`): 5,00 € via **IBAN
   personale** con nome e cognome in chiaro, ordine tracciato in `localStorage`, dati inviati
   per `mailto`. Incompatibile con la scelta "persona fisica senza P.IVA / tutto gratis".
4. **Un backup pubblico che espone dati personali**: il workflow `backup-quotidiano.yml`
   pubblica ogni notte `profiles` (display name, ruolo) sul branch pubblico `backup` — su un
   repository pubblico, con storia git permanente.
5. **Provenienza dei dati fragile**: 1.706 spot importati da una lista Google Maps condivisa,
   foto in hotlink da Street View e da siti terzi.

**Esito atteso:** una PWA pubblica su `https://pkfamily.app`, buildata da sorgente Flutter
versionato, con mappa spot, chat (gruppi + private), sezione video per chi inizia, e un
impianto legale/privacy conforme agli standard UE (GDPR, ePrivacy, DSA) coerente con
un titolare **persona fisica, servizio gratuito**.

### Decisioni prese (input utente)

| Ambito | Decisione | Conseguenza |
| --- | --- | --- |
| Titolare | **Persona fisica, no P.IVA** | Nessun incasso possibile. Imprint con nome + email, senza P.IVA/REA. Responsabilità patrimoniale illimitata → vedi §5.7. |
| Monetizzazione | **Tutto gratis al lancio** | Niente diritto di recesso, niente IVA/OSS, niente Stripe. Il paywall va spento *lato server*, non solo nel bundle. |
| Sorgente | **Riparto da Flutter** (`mobile/`), abbandono Expo | Il bundle `gh-pages` e tutta la catena di patch su JS minificato vanno in pensione. |
| Dominio | **`pkfamily.app` da registrare** | TLD Google: HTTPS obbligatorio, HSTS preload. Ottimo per PWA. WHOIS non schermato di default → usare la privacy del registrar. |

---

## 1. Logistica: dove vive l'app e come ci arriva

### 1.1 Un solo sorgente, versionato

Il monorepo oggi ha **due backend concorrenti**: `backend/` (FastAPI, descritto dai docs come
"source of truth") e Supabase (quello che l'app deployata usa davvero). Non esiste alcun
percorso di codice che colleghi il bundle a FastAPI.

**Scelta: Supabase è il backend di produzione.** Un titolare persona fisica con un servizio
gratuito non ha capacità operativa per gestire un'API self-hosted, Redis, PostGIS e le patch
di sicurezza relative. `backend/` va congelato (`docs/` aggiornati, README che lo dichiara
sperimentale/non deployato) — non cancellato, resta utile come riferimento di dominio.

Struttura target:

```
mobile/            Flutter — app unica: web (PWA) + iOS + Android dallo stesso codice
  web/             ← da creare: flutter create --platforms web .
  lib/legal/       ← nuove pagine legali in-app
supabase/migrations/  ← schema di PRODUZIONE, oggi non committato (TODO aperto in 📲/README.md)
web-admin/         Next.js — moderazione (oggi NON compila, vedi §1.4)
scripts/           pipeline dati spot (da ripulire, vedi §5.5)
```

Da rimuovere al passaggio a Flutter: `scripts/patch-gh-pages-test-free.py`,
`scripts/update_deployed_spots.py`, `scripts/deploy_test_web.sh`. Sono tutti strumenti per
manipolare il bundle Expo che non esisterà più.

### 1.2 Hosting: Cloudflare Pages, non GitHub Pages

GitHub Pages non può fare tre cose che servono al lancio:

- **header HTTP** — niente `Content-Security-Policy`, `Permissions-Policy`,
  `Strict-Transport-Security` reali (solo meta tag, più deboli);
- **staging protetto** — nessuna autenticazione a livello di edge;
- **redirect/rewrite** — servono per il routing SPA e per `/legale/*`.

**Cloudflare Pages** (piano free) li copre tutti, con `_headers` e `_redirects` versionati nel
repo, e Cloudflare Access per proteggere lo staging. Il DNS di `pkfamily.app` sta comunque su
Cloudflare.

| Ambiente | URL | Accesso |
| --- | --- | --- |
| Produzione | `https://pkfamily.app` | pubblico |
| Staging | `https://staging.pkfamily.app` | Cloudflare Access, lista email invitati |
| Legacy | `oigresergio.github.io/...` | `gh-pages` svuotato → redirect 301 a `pkfamily.app` |

`gh-pages` **non va cancellato**: chi ha il QR vecchio o il link `/t/<token>/` deve atterrare
sul nuovo dominio, non su un 404.

### 1.3 CI/CD: oggi non esiste

Ci sono solo `backup-quotidiano.yml` e `sync-map.yml`. Nessun workflow di lint, test o build —
nonostante `README.md` dichiari "CI workflows, issue/PR templates, dependabot" e `SECURITY.md`
spunti "CodeQL + Dependabot enabled". Vanno creati:

- `ci.yml` — su ogni PR: `flutter analyze`, `flutter test`, `dart format --set-exit-if-changed`;
  `cd web-admin && npm run lint && npm run build`.
- `deploy-staging.yml` — su push a `main`: `flutter build web --release --wasm` (o
  `--web-renderer canvaskit`) → deploy su Pages staging.
- `deploy-prod.yml` — su tag `v*`: stesso build → produzione. Deploy in produzione **solo da
  tag**, così un revert è un tag precedente.
- Allineare README/SECURITY.md alla realtà (o attivare davvero CodeQL/Dependabot in-repo).

### 1.4 Debiti tecnici bloccanti

| Debito | Dove | Perché blocca il lancio |
| --- | --- | --- |
| `web-admin` non compila | `web-admin/src/app/login/page.tsx:6` e `spots/page.tsx:6` importano `@/lib/api` — **`src/lib/` non esiste** | Il giorno 1 di spot pubblici serve la coda di moderazione. Senza, ogni spot inviato resta invisibile. |
| Schema di produzione non committato | `supabase/migrations/` ha 8 tabelle; produzione ne ha 17 (`📲/backup.mjs:32`, `admin-desktop/index.html:133`: `posts, comments, post_likes, post_saves, ratings, video_progress, reports, chats, chat_members, entitlements, blocked_users, fountains, spot_photos`) | Il piano di disaster recovery "Scenario B" in `📲/README.md` **non è eseguibile**. TODO già aperto lì. |
| Console admin con secret key nel browser | `admin-desktop/index.html` — la secret key bypassa ogni RLS, salvata in `localStorage` | Una singola macchina compromessa = intero database esposto, inclusi i messaggi privati. |
| Zero monitoraggio | nessun Sentry, nessun analytics, nessun alerting | Si lancerebbe alla cieca. |
| Free mode solo lato client | `patch-gh-pages-test-free.py:234` forza `hasBase/hasChat/hasVideo/hasAny = !0`, ma le RLS rifiutano comunque le scritture | Con "tutto gratis" gli utenti vedono UI sbloccata e ricevono errori silenziosi dal server. Il gating va rimosso **anche nelle RLS**. |

---

## 2. Dominio

1. **Registrare `pkfamily.app`** (Cloudflare Registrar: prezzo di costo, WHOIS privacy inclusa
   e obbligatoria di default). `.app` è nella HSTS preload list → HTTPS forzato dal browser,
   coerente con una PWA.
2. **Prima di investire nel brand: verifica di anteriorità.** Ricerca "PkFAMILY" / "PK Family"
   su **EUIPO eSearch** e **UIBM**, più una ricerca di uso di fatto (Instagram, app store).
   Una palestra o un'associazione che già usa il nome può farlo cambiare dopo il lancio, con
   il dominio già stampato sui QR.
3. **DNS su Cloudflare**, record:
   - `pkfamily.app` → Pages (apex, CNAME flattening)
   - `www.pkfamily.app` → 301 → apex
   - `staging.pkfamily.app` → Pages preview, dietro Access
   - **CAA** → limita le CA autorizzate
   - **DMARC/SPF/DKIM** anche se non si invia posta: `v=DMARC1; p=reject;` +
     `v=spf1 -all` impedisce lo spoofing di `@pkfamily.app` in campagne di phishing verso i
     tuoi utenti.
4. **Email dedicate, mai quella personale**: `privacy@pkfamily.app` (diritti GDPR),
   `abuse@pkfamily.app` (segnalazioni DSA), `security@pkfamily.app` (aggiornare
   `SECURITY.md`, che oggi punta a `security@notot.family` con un SLA "48h ack / 14d fix" che
   una persona sola non può garantire — va reso realistico).
5. `docs/qr/webapp-qr.png` da rigenerare puntando a `https://pkfamily.app`; quello di test
   (`webapp-test-qr.png`) va archiviato.

---

## 3. Gestione degli accessi

### 3.1 Cosa si smonta

Tutto l'impianto di accesso attuale va rimosso, non adattato:

- il gate PkPASS in `gh-pages:index.html` (segreto client-side, verifica falsificabile in 10
  secondi dalla console del browser);
- la registrazione dispositivo via `mailto` che spedisce all'admin `Device ID` +
  `navigator.userAgent` — è **fingerprinting senza base giuridica né informativa**;
- la pagina `invito/` con l'IBAN personale (incompatibile con "gratis, no P.IVA");
- il path segreto `/t/<token>/`.

### 3.2 Cosa si costruisce

**Livelli di accesso** (nessuna registrazione forzata: chi arriva deve poter guardare):

| Livello | Può fare |
| --- | --- |
| **Anonimo** | Mappa e schede degli spot `verified`, sezione video, pagine legali. Sola lettura. |
| **Registrato** (`user`) | Tutto sopra + proporre spot, commentare, like, chat 1-a-1 e gruppi, profilo. |
| **`instructor`** | Come `user` + badge di riconoscimento. Concesso da un admin, **non è un tier a pagamento** — coerente con `docs/PROJECT_RULES_AND_ROADMAP.md` §3. |
| **`admin`** | Moderazione, verifica spot, gestione segnalazioni. Assegnato **solo a livello DB**, nessun endpoint lo concede. |

**Autenticazione**: Supabase Auth, email + password con conferma email obbligatoria (blocca
l'iscrizione con email altrui), oppure magic link. Password: minimo 12 caratteri, controllo
contro liste di password compromesse (opzione nativa Supabase). Rate limit su login e
registrazione.

**Età minima: 16 anni, autodichiarata a un age gate in fase di registrazione.**
Motivazione: l'art. 8 GDPR fissa a 16 anni la soglia per il consenso diretto dei minori,
con facoltà per gli Stati di abbassarla — l'Italia l'ha portata a 14. Sotto la soglia serve
il consenso verificabile di chi esercita la responsabilità genitoriale, e **non c'è modo
realistico di verificarlo** per un servizio gratuito gestito da una persona. Fissando 16 si
evita del tutto il problema. Va detto chiaramente nei Termini e nell'informativa, con una
procedura di rimozione se emerge un account sotto età.

**Accesso tramite genitore (account supervisionato).** Chi dichiara meno di 16 anni non viene
solo respinto: gli si offre di **chiedere a un genitore o tutore di aprire l'accesso**.

- Il minore inserisce l'email di un adulto → parte **una sola** email di richiesta. Se entro
  7 giorni non viene completata, la richiesta e l'email si cancellano (nessuna raccolta di
  contatti di terzi che resti a bagno).
- L'adulto crea **il proprio** account: è lui il titolare, dichiara di avere almeno 18 anni e
  di esercitare la responsabilità genitoriale sul minore che userà il servizio sotto la sua
  supervisione, e accetta Termini e gate di sicurezza (§3.4) **anche per suo conto**.
- Il profilo è marcato `supervised = true`. Il minore **non ha un account proprio**: non c'è
  un'email di minore da trattare, quindi non scatta l'art. 8 GDPR.
- **La chat nasce disattivata** su questi account. Il genitore può accenderla dalle
  impostazioni, dopo un avviso esplicito sul rischio di contatto con adulti sconosciuti.
  Mappa e video restano completi. La moderazione vede il flag `supervised`.
- Va detto chiaro nei Termini: il titolare dell'account risponde dell'uso che ne viene fatto.

*Nota onesta sul limite:* nulla impedisce a un quindicenne di dichiarare 16 anni, e nessun
servizio gratuito può verificarlo davvero. Il flusso genitoriale serve a dare una strada
corretta a chi la vuole percorrere e a dimostrare diligenza, non a costruire una barriera
tecnica che non esiste.

**Sicurezza dell'accesso amministrativo**: la secret key esce dal browser. Due opzioni,
in ordine di preferenza:
1. Il pannello di moderazione (`web-admin`) fa login con Supabase Auth come utente `admin`
   e lavora **sotto RLS**, usando la funzione `is_admin()` già presente in
   `supabase/migrations/0001_initial.sql:26`. Nessuna chiave privilegiata nel client.
2. Le operazioni che devono davvero bypassare le RLS (es. export completo) passano da una
   Supabase Edge Function server-side che verifica il ruolo.
   `admin-desktop/index.html` va deprecato.

### 3.3 Moderazione e segnalazioni (obbligo DSA)

Il flusso spot `pending → verified | rejected` esiste già lato schema e va esposto in UI:

- **Segnalazione** su spot, messaggi, profili e commenti (categorie: contenuto illecito,
  molestie, spot pericoloso, spam, proprietà privata) → tabella `reports` (già in produzione,
  0 righe).
- **Blocco utente** (tabella `blocked_users`, già in produzione): un utente bloccato non può
  scrivere in privato né vedere i tuoi messaggi.
- **Motivazione della decisione** (*statement of reasons*, art. 17 DSA) inviata all'autore
  quando un contenuto viene rimosso o uno spot rifiutato — il campo `rejection_reason` c'è
  già in `spots`.
- **Log di moderazione**: `spot_moderation_events` esiste; estenderlo agli altri contenuti.
- **Punto di contatto** pubblicato: `abuse@pkfamily.app`.

Nota di proporzionalità: come micro-impresa, l'art. 19 DSA esonera dalla Sezione 3 (gestione
reclami interna, ODR, trusted flagger, report di trasparenza). Restano dovuti gli obblighi
base: punto di contatto, T&C che spiegano la moderazione, meccanismo di notice-and-action,
statement of reasons.

### 3.4 Gate di sicurezza all'ingresso

Prima che la mappa mostri anche un solo spot, l'utente — **registrato o anonimo, alla prima
visita e a ogni cambio di versione del testo** — vede una schermata bloccante che spiega:

- la mappa è **informativa**: raccoglie e rende accessibile in un posto solo un'informazione
  che circola già nella community, e che altrimenti andrebbe cercata per vie traverse;
- PkFAMILY **non organizza, non supervisiona e non promuove** alcuna attività sportiva;
- gli spot **non sono ispezionati né certificati**: sono luoghi pubblici o segnalati da altri
  praticanti, le condizioni cambiano nel tempo e nessuno ne garantisce la sicurezza;
- alcuni spot possono trovarsi su **proprietà privata**: verificare prima di accedere è
  responsabilità di chi si muove;
- chi pratica **si assume consapevolmente il rischio** di infortunio, valuta da sé il proprio
  livello e le condizioni del luogo.

**Chi accetta** entra normalmente. **Chi rifiuta** non viene buttato fuori: resta nell'app in
**modalità informativa senza spot** — mappa vuota (nessun pin, nessuna coordinata, nessuna
scheda), sezione video e pagine legali accessibili, e un pulsante sempre presente per
accettare più tardi. Il rifiuto è revocabile in entrambe le direzioni dalle impostazioni.

**L'accettazione va registrata**, altrimenti non serve a niente in giudizio: tabella
`safety_acknowledgements` con `user_id` (o id anonimo di sessione), `versione` del testo,
**hash del testo esatto** mostrato, `accepted_at`. Ogni revisione del testo alza la versione e
il gate ricompare. Il testo di ogni versione resta versionato nel repo.

Il gate **non è un banner cookie** e non va confuso con esso: non è consenso al trattamento
dati, è una presa d'atto contrattuale. Il flag di accettazione in `localStorage` è quindi
storage tecnico.

Rinforzo puntuale: la stessa avvertenza, in forma breve, compare **nella scheda di ogni
spot** — è lì che la decisione di andarci viene presa davvero.

*Su cosa questo gate ottiene e cosa no, vedi §5.7: la valutazione onesta conta più della
schermata.*

---

## 4. Le tre sezioni funzionali

### 4.1 Mappa con gli spot

Base già presente in `mobile/lib/screens/spots_map_screen.dart` con `flutter_map` 7.0.2.

- **Tile**: OpenFreeMap (`tiles.openfreemap.org`, già usato dal bundle) o MapTiler con chiave.
  **Non** Esri World Imagery senza verificare la licenza (oggi usato in modalità test) e
  **non** tile Street View in hotlink.
- **Volume**: ~1.700 marker non si disegnano tutti. Serve clustering
  (`flutter_map_marker_cluster` o supercluster) + rendering solo del viewport, come già fa il
  bundle Expo.
- **Origine dei dati**: gli spot devono stare **nel database Supabase**, non incorporati nel
  bundle JS. Oggi produzione ha 24 spot; i 1.706 sono dentro `scripts/data/webapp_fixed_spots.json`.
  Vedi §5.5 per la ripulitura prima dell'import.
- **Scheda spot**: nome, descrizione, difficoltà (`difficulty_gauge.dart` esiste già), foto,
  presenza d'acqua, commenti, like, distanza e percorso a piedi.
- **Geolocalizzazione**: permesso richiesto **solo al tap** su "dove sono / percorso", mai
  all'avvio, con una schermata che spiega *perché* prima di chiedere. La posizione
  **non si salva** né si trasmette: resta nel device (`location_service.dart`).
- **Spot su proprietà privata**: campo `access_type` (pubblico / privato / con permesso) e
  rimozione su segnalazione del proprietario.

### 4.2 Chat: gruppi e private

Schema già presente (`conversations`, `conversation_members`, `messages` in
`supabase/migrations/0001_initial.sql:200+`, con RLS e `is_conversation_member()`), ma
**zero implementazione client** e 0 messaggi in produzione.

- **Private 1-a-1** (`kind = 'direct'`) e **gruppi** (`kind = 'group'`), con Supabase Realtime.
- Solo utenti registrati e con email confermata.
- Blocco utente, segnalazione messaggio, uscita dal gruppo.
- **Nessuna cifratura end-to-end** — e va detto esplicitamente nell'informativa: l'admin ha
  accesso tecnico al database. Promettere E2E senza averla sarebbe una dichiarazione falsa.
- **Retention**: i messaggi si conservano finché l'utente non li cancella o non chiude
  l'account; alla cancellazione dell'account i messaggi vengono **pseudonimizzati**
  (autore → "utente eliminato"), non cancellati dalle conversazioni altrui — è la soluzione
  standard per bilanciare art. 17 GDPR e il diritto degli altri partecipanti alla propria
  conversazione. Va scritta nell'informativa.
- Rate limit anti-spam sull'invio.

### 4.3 Video per chi inizia

Schema `videos` già presente (categorie `recovery / practice / conditioning`, livelli
`beginner / intermediate / advanced`), 0 righe in produzione. Client di lettura già abbozzato
in `mobile/lib/screens/tutorials_screen.dart`.

- **Il gating premium va rimosso**, non solo nascosto: `backend/app/services/video_service.py:21`
  (`is_premium`) e le RLS corrispondenti. Con "tutto gratis" ogni video è accessibile a tutti,
  anche agli anonimi.
- **Percorso "Inizia da qui"**: sequenza curata per chi non ha mai fatto parkour —
  riscaldamento e mobilità, atterraggio e rullata, quadrupedia, precision jump, vault base,
  progressione e gestione della paura, prevenzione infortuni e recupero. Un campo
  `order_index` + `is_starter` sulla tabella `videos`.
- **Embed, non hosting**: YouTube/Vimeo con `youtube-nocookie.com` e `privacy-enhanced mode`.
  Ospitare video propri costerebbe banda e aprirebbe obblighi ulteriori. **Attenzione privacy**:
  l'embed di terze parti carica risorse esterne → richiede consenso preventivo (§5.3), quindi
  il player va sostituito da un **placeholder cliccabile** finché l'utente non acconsente.
- **Sicurezza in ogni scheda**: disclaimer "progressione graduale, superficie adatta,
  spotter", coerente con §5.7.

---

## 5. Cautele legali e privacy — standard UE

> Questo piano organizza gli adempimenti e ne prepara i testi. **Non è consulenza legale**:
> prima del lancio pubblico, far rivedere informativa, Termini e valutazione d'impatto a un
> professionista. Il costo è basso rispetto al rischio, e la responsabilità come persona
> fisica è illimitata.

### 5.1 Identificazione del titolare (art. 13 GDPR + D.lgs 70/2003)

Anche senza P.IVA, un prestatore di servizi della società dell'informazione deve essere
identificabile: **nome e cognome + un indirizzo email di contatto**, in una pagina
`/legale/note-legali` linkata dal footer di ogni pagina.

**Non pubblicare l'indirizzo di casa.** Se in futuro servisse un recapito postale (o si
passasse a un'attività strutturata), usare una domiciliazione. Un DPO **non è obbligatorio**
a questa scala, ma va indicato un referente privacy: `privacy@pkfamily.app`.

### 5.2 Informativa privacy (artt. 13-14 GDPR)

Pagina `/legale/privacy`, in **italiano e inglese**, versionata con data e changelog.
Deve coprire, trattamento per trattamento:

| Trattamento | Dati | Base giuridica | Conservazione |
| --- | --- | --- | --- |
| Account | email, display name, password (hash) | art. 6.1.b (esecuzione del servizio) | fino a cancellazione + 30 gg di grazia |
| Spot proposti | testo, coordinate, foto, autore | art. 6.1.b + 6.1.f (interesse legittimo alla mappa comunitaria) | indefinita per spot `verified` (contenuto della community); l'attribuzione si può anonimizzare |
| Chat | messaggi, partecipanti, timestamp | art. 6.1.b | fino a cancellazione; pseudonimizzazione alla chiusura account |
| Geolocalizzazione | posizione precisa, **solo nel device** | art. 6.1.a (consenso, permesso browser) | **non conservata** |
| Moderazione e segnalazioni | contenuto segnalato, motivo, decisione | art. 6.1.c (obblighi DSA) + 6.1.f | 12 mesi |
| Log tecnici / antiabuso | IP, user agent, timestamp | art. 6.1.f | 30 giorni (rif. provvedimenti Garante sui log) |
| Backup | vedi §5.6 | art. 6.1.f | 30 giorni a rotazione |

Deve inoltre indicare: **destinatari e responsabili esterni** (Supabase, Cloudflare, GitHub,
YouTube/Vimeo per gli embed), **trasferimenti extra-UE** con la relativa garanzia, i **diritti**
(artt. 15-22) con le istruzioni concrete per esercitarli, il diritto di **reclamo al Garante**,
e il fatto che **non c'è cifratura end-to-end** in chat.

### 5.3 Cookie ed ePrivacy (art. 5.3 Dir. 2002/58, Linee guida Garante 2021)

**Strategia consigliata: nessun tracciamento → nessun banner.**

- Il token di sessione Supabase in `localStorage` è **tecnico/necessario**: non richiede
  consenso, ma va dichiarato nella cookie policy.
- **Niente Google Analytics.** Se serve una misura d'uso, usare **Plausible o Umami
  self-hosted in UE**, cookieless e con IP anonimizzato → nessun consenso richiesto.
- **Se e solo se** si aggiungono embed di terze parti (player YouTube) o tracciamento: serve
  un **CMP conforme** — banner con "Accetta" e "**Rifiuta**" **equivalenti** (niente dark
  pattern), granularità per finalità, nessun cookie non essenziale prima del consenso, revoca
  sempre accessibile. Con i player: placeholder cliccabile fino al consenso (§4.3).

### 5.4 Trasferimenti internazionali e responsabili del trattamento

- **Supabase**: verificare che il progetto (`gkdzdtxqkftebrxhgway`) sia in **regione UE**
  (Francoforte o Irlanda). Se è in US, **creare un nuovo progetto UE e migrare prima del
  lancio** — a 24 spot e 2 profili la migrazione costa poco; dopo il lancio costa molto.
  Firmare/accettare il **DPA** Supabase.
- **Cloudflare**: DPA + valutare la *Data Localisation Suite* se si vuole confinare
  l'elaborazione in UE.
- **GitHub**: resta per il codice e la CI; se `gh-pages` non serve più, il repo non tratta
  dati personali degli utenti (a patto di risolvere §5.6).
- Pubblicare la **lista dei sub-responsabili** in una pagina, con impegno a notificare le
  variazioni.

### 5.5 Provenienza dei dati e diritti di terzi

È il punto più sottovalutato, e riguarda contenuti già dentro il prodotto.

| Problema | Dove | Azione prima del lancio |
| --- | --- | --- |
| 1.706 spot estratti da una lista Google Maps condivisa | `scripts/data/gmaps_parkour_list.json`, `scripts/fetch_gmaps_list.py` | I ToS di Google vietano lo scraping, e sulla banca dati può gravare il **diritto sui generis** (artt. 102-bis/ter L. 633/41). Ricostruire il dataset da **OpenStreetMap** (ODbL, con attribuzione) e da segnalazioni della community. Coordinate e nomi di luogo *pubblici* non sono in sé proteggibili, ma la **lista come selezione** sì. |
| Immagini Street View in hotlink | `docs/demo/tools/fetch_streetview.py`, `streetviewpixels-pa.googleapis.com` | Fuori dalle API ufficiali con chiave è contrario ai ToS. **Rimuovere.** |
| Foto in hotlink da siti terzi | `webapp_fixed_spots.json` (`parkourbilbao.com`, `comune.roma.it`, `vistanet.it`, `abitarearoma.it`) | Rischio copyright. **Rimuovere**, tenere solo Wikimedia Commons **con attribuzione e licenza corrette** (63 immagini) e le foto caricate dagli utenti. |
| Foto caricate dagli utenti | nuovo | I Termini devono includere una **licenza non esclusiva** all'uso nell'app, con l'utente che dichiara di averne il diritto e che **non ci sono volti riconoscibili di terzi senza consenso**. |
| Nomi di persona nelle descrizioni | commit `031db8e` toglieva già un'attribuzione | Verificare che nessuna descrizione contenga dati personali di terzi. |

### 5.6 Il backup pubblico dei profili — da fermare subito

`.github/workflows/backup-quotidiano.yml` pubblica ogni notte su un branch **pubblico** di un
repo **pubblico** il contenuto leggibile via RLS, `profiles` inclusa. Con 2 profili è
trascurabile; con 500 utenti è una **diffusione di dati personali a destinatari indeterminati**,
senza base giuridica né informativa, e la storia git la rende difficile da revocare.
Il `README.md` in `📲/` la considera intenzionale ("il backup pubblico è pensato per essere
pubblico"): la premessa va rivista.

Azione: **prima del lancio** — escludere `profiles` (e ogni tabella con dati personali) dal
backup pubblico, oppure spostare l'intero backup su storage privato (R2/S3 privato o artifact
GitHub cifrato) con retention 30 giorni. Il backup pubblico può restare **solo** per spot,
video e fountains.

### 5.7 Sicurezza dei praticanti e responsabilità

Il parkour comporta rischio di infortunio, e la mappa indica luoghi fisici reali. Come persona
fisica, la responsabilità è illimitata sul patrimonio personale.

#### Cosa il gate di sicurezza (§3.4) può e non può fare

L'obiettivo dichiarato — «fare in modo che non esistano appigli legali per cause future» —
**non è raggiungibile da nessuna schermata**, e vale la pena essere espliciti sul perché,
perché la differenza cambia come va scritto il testo.

**Non può**, per legge:
- **escludere la responsabilità per dolo o colpa grave**: l'art. 1229 c.c. rende **nullo**
  qualunque patto in questo senso;
- **limitare la responsabilità per danni alla persona** verso un consumatore: è clausola
  vessatoria e inefficace (artt. 33 e 36 Cod. Consumo), anche se accettata con un click;
- **vincolare chi non ha accettato**: un passante travolto, il proprietario di un muro, i
  familiari di un infortunato in caso di danno iure proprio non sono parti di quel contratto;
- **impedire a qualcuno di citarti in giudizio.** Nessun testo lo impedisce. Il punto è come
  finisce la causa, non se viene aperta.

**Può**, ed è molto:
- **qualificare il servizio come informativo e non organizzativo.** È la distinzione che pesa
  di più: chi *organizza* un'attività sportiva ha un dovere di protezione dei partecipanti;
  chi *rende accessibile un'informazione* no. Il gate, i Termini e — soprattutto — **il modo in
  cui l'app parla** devono dire la stessa cosa. Un solo "prova questo salto!" da qualche parte
  nella UI vale più, contro di te, di dieci schermate di disclaimer;
- **documentare che l'utente era informato**: con versione, hash del testo e timestamp, si
  prova *cosa esattamente* è stato mostrato e quando. Senza registrazione, il gate in giudizio
  vale zero;
- **far pesare l'assunzione del rischio e il concorso del danneggiato** (art. 1227 c.c.):
  a fronte di un rischio noto, accettato per iscritto e volontariamente affrontato, il
  risarcimento si riduce o si azzera.

**Conseguenza pratica sulla stesura:** il testo va scritto come **presa d'atto e assunzione
consapevole del rischio**, mai come «l'utente esonera PkFAMILY da ogni responsabilità».
La seconda formula è nulla, e una clausola nulla non protegge — segnala solo che chi l'ha
scritta pensava di essere coperto. Chiedere di più al testo di quanto la legge gli concede
peggiora la posizione, non la migliora.

Le difese che spostano davvero l'ago, oltre al gate: **non comportarsi da organizzatore**,
rimuovere in fretta gli spot segnalati come pericolosi, non pubblicare spot su proprietà
privata, e — quando la community cresce — la **separazione patrimoniale** di un'ASD con
copertura assicurativa. Quest'ultima protegge più di qualsiasi popup.

- **Disclaimer chiaro** nei Termini e nelle schede spot: la pratica è a proprio rischio, gli
  spot non sono ispezionati né certificati, le condizioni cambiano nel tempo.
- **Nessuna clausola di esonero totale**: l'art. 1229 c.c. rende **nulla** la limitazione di
  responsabilità per dolo o colpa grave, e le clausole vessatorie verso i consumatori sono
  inefficaci. Un disclaimer serve a informare, non a immunizzare — non fingere il contrario.
- **Segnalazione spot pericoloso** con rimozione rapida, e attenzione agli spot su proprietà
  privata (il servizio non deve incoraggiare l'accesso abusivo).
- **Raccomandare un'assicurazione infortuni** agli utenti; valutarne una di responsabilità
  civile per sé.
- **Raccomandazione strutturale**: appena la community cresce o entra denaro, passare a
  **ASD/APS**. Separa il patrimonio, dà accesso a coperture assicurative pensate per lo sport
  e inquadra le quote come associative anziché come vendite.

### 5.8 Termini di servizio

Pagina `/legale/termini`: oggetto e gratuità del servizio, età minima 16, regole di condotta
(no molestie, no contenuti illeciti, no spam, no promozione di accesso a proprietà private),
licenza sui contenuti caricati, moderazione e sanzioni (warning → sospensione → ban) con
possibilità di contestare, disclaimer di sicurezza, limitazione di responsabilità nei limiti
di legge, legge applicabile italiana e **foro del consumatore** (quello di residenza
dell'utente: la clausola di foro esclusivo del fornitore è vessatoria e inefficace), procedura
di modifica dei Termini con preavviso.

### 5.9 Diritti degli interessati — implementati, non solo promessi

Devono essere **funzioni dell'app**, non una promessa in una pagina:

- **Accesso/portabilità (artt. 15, 20)**: pulsante "Scarica i miei dati" → JSON con profilo,
  spot, commenti, messaggi.
- **Cancellazione (art. 17)**: "Elimina account" in-app → cancellazione di profilo e
  contenuti personali, pseudonimizzazione dei messaggi (§4.2), 30 giorni di grazia, conferma
  via email.
- **Rettifica (art. 16)**: modifica del profilo.
- **Reclamo**: `privacy@pkfamily.app`, risposta entro **30 giorni** (art. 12.3).

### 5.10 Documentazione interna obbligatoria

Non pubblica, ma va prodotta e conservata:

- **Registro dei trattamenti (art. 30)**: l'esenzione per chi ha meno di 250 dipendenti **non
  si applica**, perché il trattamento non è occasionale e include geolocalizzazione.
- **Valutazione d'impatto (DPIA, art. 35)**: geolocalizzazione + community online la rendono
  fortemente consigliata (la geolocalizzazione sistematica è nella lista del Garante). Redigere
  almeno una DPIA leggera, documentando rischi e mitigazioni.
- **Procedura data breach (artt. 33-34)**: notifica al Garante entro **72 ore**, con
  contatti e un registro delle violazioni predisposti *prima* che serva.
- **Analisi del legittimo interesse (LIA)** per i log antiabuso e la mappa pubblica.

### 5.11 Sicurezza tecnica (art. 32 GDPR)

- **Audit completo delle RLS** prima del lancio: sono l'unica difesa, dato che la publishable
  key è pubblica (`📲/backup.mjs:20`). In particolare verificare che `messages` non sia mai
  leggibile da non membri e che nessuna policy permetta l'escalation a `admin`.
- **CSP restrittiva** via `_headers` Cloudflare, più `Strict-Transport-Security`,
  `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy` che nega tutto tranne `geolocation=(self)`.
- **Rotazione delle chiavi** al lancio; secret key **mai** in un client (§1.4).
- **Rate limiting** su auth, invio messaggi, creazione spot.
- **`/.well-known/security.txt`** con `security@pkfamily.app`.
- **Sentry** (self-hosted UE o region EU) con scrubbing dei PII.

### 5.12 Accessibilità

Lo **European Accessibility Act** (Dir. 2019/882, applicabile dal 28 giugno 2025) copre i
servizi di e-commerce; un servizio gratuito erogato da una microimpresa/persona fisica
ricade fuori o in esenzione. Ma il target include principianti su mobile in condizioni
difficili: puntare comunque a **WCAG 2.2 AA** su contrasto, dimensioni dei tocchi, focus
visibile e etichette dei form. Se un giorno si monetizza, l'obbligo diventa concreto.

---

## 6. Sequenza di esecuzione

**Fase 0 — Messa in sicurezza (subito, prima di ogni altra cosa)**
- Ricreare `gh-pages` come branch orfano senza `invito/` — l'IBAN sparisce anche dalla storia
  pubblica, l'anteprima sotto `/t/<token>/` resta accessibile.
- Escludere `profiles` dal backup pubblico (§5.6).
- Verificare la regione Supabase; se non è UE, pianificare la migrazione ora.
- Registrare `pkfamily.app`; verifica di anteriorità sul nome.

**Fase 1 — Fondamenta di codice**
- `flutter create --platforms web .` in `mobile/`; `supabase_flutter` al posto di `api_client.dart`.
- Esportare lo schema di produzione in `supabase/migrations/` (chiude il TODO di `📲/README.md`).
- Riparare `web-admin` (`src/lib/api.ts` mancante) o riscriverne la moderazione su Supabase Auth.
- CI: `ci.yml` con analyze/test/lint.

**Fase 2 — Funzionalità**
- Auth + age gate + profilo + eliminazione account ed export.
- Mappa: import degli spot ripuliti in Supabase, clustering, scheda, percorso.
- Chat: private e di gruppo su Realtime, blocco e segnalazione.
- Video: percorso "Inizia da qui", gating premium rimosso lato server.
- Moderazione: coda spot, segnalazioni, statement of reasons.

**Fase 3 — Legale e infrastruttura**
- Pagine `/legale/*` (privacy, termini, cookie, note legali, sub-responsabili) IT+EN.
- Registro trattamenti, DPIA, procedura breach, DPA firmati.
- Cloudflare Pages + DNS + `_headers` + Access sullo staging.
- Redirect 301 da `gh-pages` al nuovo dominio.

**Fase 4 — Pre-lancio**
- Audit RLS, revisione legale professionale, test su dispositivi reali.
- Beta chiusa su staging con la cerchia attuale.
- Sentry attivo, backup verificati con un restore di prova.

**Fase 5 — Lancio**
- Rimozione `noindex` + `robots.txt` permissivo, `sitemap.xml`.
- Tag `v1.0.0` → deploy in produzione. QR pubblico rigenerato.

### Verifica end-to-end

```sh
# Build e qualità
cd mobile && flutter analyze && flutter test && flutter build web --release
cd ../web-admin && npm run lint && npm run build     # oggi FALLISCE: @/lib/api mancante

# Sicurezza degli header (dopo il deploy)
curl -sI https://pkfamily.app | grep -iE 'content-security-policy|strict-transport|referrer|permissions'

# Isolamento RLS: con la publishable key, da NON autenticato
#  - GET /rest/v1/spots?status=eq.pending   → deve tornare []
#  - GET /rest/v1/messages                  → deve tornare [] o 401
#  - PATCH /rest/v1/profiles?id=eq.<altro>  → deve fallire

# Percorsi utente da provare a mano su staging
#  anonimo: gate sicurezza → accetta → mappa → scheda spot → video → pagine legali
#  gate rifiutato: mappa vuota, zero coordinate anche nelle risposte API; accetta dopo → spot
#  registrazione: age gate <16 → blocco + "chiedi a un genitore"; ≥16 → conferma email → login
#  genitore: richiesta via email → account supervised, chat spenta; attivala dalle impostazioni
#  spot: proponi → pending invisibile in pubblico → admin verifica → compare
#  chat: crea gruppo, invita, scrivi; blocca un utente; segnala un messaggio
#  diritti: esporta i miei dati → JSON completo; elimina account → dati via, messaggi pseudonimizzati
```

---
## 7. Il prompt operativo

Il prompt che mette in pratica tutti i punti di questo piano — mappa con gli spot, gate di
sicurezza, chat in gruppi e private, sezione video per chi inizia, accessi, dominio, deploy e
adempimenti legali/privacy — vive in un file a parte, pronto da incollare:

**→ [`docs/LAUNCH_PROMPT.md`](LAUNCH_PROMPT.md)**

È diviso in dieci blocchi eseguibili (BLOCCO 0 → 9). **Conviene lanciarli uno alla volta**,
non tutti insieme: ogni blocco chiude con del codice verificabile.

---

## 8. Cosa resta all'umano

Il prompt non può fare queste cose. Vanno fatte in parallelo:

1. Registrare `pkfamily.app` e verificare che il nome sia libero (EUIPO, UIBM, uso di fatto).
2. Verificare la regione del progetto Supabase; se non è UE, migrare **prima** del lancio.
3. Accettare i DPA di Supabase e Cloudflare; creare le tre caselle email.
4. **Far rivedere informativa, Termini e DPIA a un legale.** È l'unica voce che non ammette
   scorciatoie: il titolare è una persona fisica con responsabilità illimitata.
5. Valutare, appena la community cresce, il passaggio a **ASD/APS** con relativa copertura
   assicurativa.
