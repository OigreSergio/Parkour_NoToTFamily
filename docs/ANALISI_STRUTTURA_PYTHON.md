# Analisi dei file e basi per un'applicazione Python che gira in remoto

> Prima analisi, 17 settembre 2026, branch `claude/analisi-struttura-python-o8yvue`.
> Scritta per chi deve decidere (l'admin) e per chi deve costruire (persone o agenti).
> Frasi complete, un fatto per riga, riferimenti a file e righe dove serve.

## Indice

1. [Cosa è stato analizzato](#1-cosa-è-stato-analizzato)
2. [Fotografia dei due repository](#2-fotografia-dei-due-repository)
3. [Il codice Python che esiste già](#3-il-codice-python-che-esiste-già)
4. [Come gira oggi l'applicazione, e dove](#4-come-gira-oggi-lapplicazione-e-dove)
5. [Problemi che contano per il remoto](#5-problemi-che-contano-per-il-remoto)
6. [La decisione: che cosa deve essere la base Python remota](#6-la-decisione-che-cosa-deve-essere-la-base-python-remota)
7. [La struttura creata: `remote-service/`](#7-la-struttura-creata-remote-service)
8. [Come si mette in remoto](#8-come-si-mette-in-remoto)
9. [Prossimi passi, in ordine](#9-prossimi-passi-in-ordine)
10. [Nota di consegna](#10-nota-di-consegna)

---

## 1. Cosa è stato analizzato

I tre file caricati sono scorciatoie macOS (`.webloc`) che puntano a file
conservati su claude.ai; dalla sessione remota quegli indirizzi rispondono
403, quindi il contenuto non è stato letto da lì. Il contenuto è però lo
stesso dei due repository collegati alla sessione, che sono stati letti per
intero al posto dei file:

| File caricato | Cosa è | Letto da |
| --- | --- | --- |
| `Parkour_NoToTFamily_CODICE.txt` (13 MB, due copie) | Un'esportazione testuale del codice del monorepo. Il repository sorgente pesa 3,4 MB e il branch pubblicato `gh-pages` 46,7 MB: la dimensione è compatibile con sorgenti più una parte della build. | Repository `OigreSergio/Parkour_NoToTFamily`, branch `main` (ultimo commit `b12b1de`) e branch `gh-pages` |
| `TernaryOperator_codice.zip` (17 kB) | Un progetto Java di un solo file. | Repository `OigreSergio/TernaryOperator` (commit `82743d6`) |

L'analisi ha due parti: una lettura diretta dei file che contano di più
(configurazione, punti d'ingresso, documenti di architettura, schema del
database, script di deploy) e una lettura parallela per aree, con verifica
indipendente di ogni rilievo, i cui esiti sono nel capitolo 5.

## 2. Fotografia dei due repository

### 2.1 TernaryOperator

Un file, `Main.java`, di 11 righe. Stampa i numeri da 1 a 100 e per ciascuno
il risultato di `checkValue`, che usa l'operatore ternario: `"FizzBuzz"` se il
valore è 5, `"Buzz"` in ogni altro caso. Non è il gioco FizzBuzz classico
(multipli di 3, di 5 e di entrambi): è un esercizio sull'operatore ternario, e
il messaggio dell'unico commit ("if-else easy to reed") lo conferma.

Cosa è stato fatto: il porting in Python con commenti riga per riga
(`main.py`), i test che fissano il comportamento (`test_main.py`) e un
`README.md`. Il porting conserva la logica dell'originale e affianca la regola
classica per confronto. È sul branch `claude/analisi-struttura-python-o8yvue`
di quel repository, già pubblicato.

### 2.2 Parkour_NoToTFamily

Un monorepo con più tecnologie. Lo stato per cartella, letto dal codice:

| Cartella | Tecnologia | Contenuto | Stato reale |
| --- | --- | --- | --- |
| `backend/` | Python 3.11, FastAPI, SQLAlchemy asincrono, PostGIS, Redis, Alembic | API completa: codice via email, ospiti, profili e quiz, informative, spot con moderazione, commenti, video con paywall, chat WebSocket. 5 migrazioni, 14 file di test. | Completo come **scaffold**. Non è in produzione: nessun host lo esegue, i client pubblicati non lo chiamano. |
| `mobile/` | Flutter (Riverpod, flutter_map, go_router) | 26 file Dart: mappa, lista, dettaglio spot, tutorial, onboarding, accesso ospite. Base URL dell'API a tempo di compilazione (`--dart-define=API_BASE_URL`, default `10.0.2.2:8000`). | Sorgenti fermi ad agosto. La build Flutter pubblicata a settembre ha funzioni in più i cui sorgenti **non sono nel repository** (masterplan 1.1 e 1.4, P0-3). |
| `web-admin/` | Next.js 14 | Login e coda degli spot in attesa: 4 file. | Prototipo. |
| `admin-desktop/` | HTML singolo | Console admin che chiede la chiave segreta Supabase in un campo di input e la usa dal browser. | Da ritirare (masterplan S0-2). Nel repository c'è solo il segnaposto `sb_secret_…` nel campo (`admin-desktop/index.html:70-71`), non una chiave. |
| `supabase/` | SQL, Node | 4 migrazioni (841 righe): profili, spot con RLS, like, audit, chat, video, informative, quiz, ospiti. Seed in Node con la chiave segreta letta dall'ambiente. | Buona base; lo schema reale di produzione ha tabelle in più non esportate (masterplan 1.3, P1-1). |
| `scripts/` | Python 3, JavaScript | Pipeline dati: lista Google Maps (1.710 spot), foto degli spot, QR, patch del bundle web pubblicato, deploy dell'anteprima. `scripts/web/` contiene i moduli JS del flusso d'accesso e dei percorsi. | Funzionanti; diversi sono legati al bundle Expo legacy. |
| `infra/` | Docker Compose | Server tile per la mappa in locale; OSRM self-hosted per i percorsi (fase 2 di `docs/ROUTING_PK.md`). | Pronti come compose, mai in produzione. |
| `📲/` | Node, GitHub Actions | Backup pubblico quotidiano su un branch rigenerato ogni notte. | Attivo. |
| `docs/` | Markdown | 12 documenti (circa 2.800 righe) più demo HTML, foto con manifest, QR. Il masterplan (`PKFAMILY_MASTERPLAN.md`, 976 righe) è il documento di direzione. | Ottimo; alcune parti descrivono il bundle Expo legacy. |
| `.github/workflows/` | GitHub Actions | `backup-quotidiano.yml`, `sync-map.yml`. | **Nessuna CI** di test, lint o build (P1-2). |

Numeri utili:

| Misura | Valore |
| --- | --- |
| File Python nel repository | 97 |
| Righe Python in `backend/` (app, migrazioni, test) | 7.803 |
| Endpoint HTTP del backend sotto `/api/v1` (più un WebSocket e `/healthz`) | 36 |
| File nel branch `gh-pages` | 83 (46,7 MB) |
| Workflow GitHub | 2 |
| Test del backend | 14 file (richiedono un Postgres con PostGIS raggiungibile: `backend/tests/conftest.py:13`) |

## 3. Il codice Python che esiste già

### 3.1 `backend/`: com'è fatto

A strati, con una regola di dipendenza in un verso solo
(`docs/ARCHITECTURE.md`): `api → schemas/services → repositories → models`.

| Strato | Cartella | Esempio letto |
| --- | --- | --- |
| Avvio, middleware, errori | `app/main.py` | CORS, limite di 120 richieste al minuto per IP, `/healthz`, gestore degli errori applicativi |
| Configurazione | `app/core/config.py` | Tutto da variabili d'ambiente con `pydantic-settings`; in produzione rifiuta il segreto JWT di default e una posta che non spedisce davvero |
| Rotte | `app/api/v1/*.py` | `spots.py`: invio (`pending`), ricerca per raggio con PostGIS, dettaglio, commenti |
| Regole | `app/services/*.py` | `spot_service.py`: commenti solo su spot verificati; gli spot non pubblici non vengono rivelati (404 invece di 403) |
| Accesso ai dati | `app/repositories/*.py` | `spots.py`: ogni query SQL vive qui |
| Modelli | `app/models/*.py` | `user.py`: ruoli `user`, `instructor`, `admin`; ospiti con chiave HMAC; `spot.py`: `geography(Point, 4326)` |

Le scelte buone da conservare in qualunque servizio Python del progetto: la
configurazione dall'ambiente con controlli di produzione, gli errori con un
codice stabile (`{"error": {"code", "message"}}`), i log strutturati, la
regola "nessuna dipendenza verso l'alto".

### 3.2 Dove presuppone il PC dell'autore

- `docs/PROVA_DA_TELEFONO.md` spiega come farlo raggiungere dal telefono
  sulla stessa Wi-Fi, con `--host 0.0.0.0`; non esiste una guida per un host.
- `docker-compose.yml` alla radice avvia Postgres, Redis, API e web-admin
  sulla stessa macchina, con credenziali di sviluppo.
- La posta di default è `console` (il codice di accesso finisce nel log e
  nella risposta come `debug_code`); la produzione richiede `smtp` o `api`.
- I test richiedono un database reale in ascolto su `localhost:5432`.

### 3.3 Cosa manca per farlo girare in remoto così com'è

Un Postgres con PostGIS gestito, un Redis, un provider di posta, un host per
il container, i segreti nell'ambiente, TLS davanti, una CI che esegua `ruff`
e `pytest` con un Postgres effimero, e un client che lo chiami. Nessuna di
queste cose è impossibile, ma il masterplan (capitolo 4.2) ha già deciso che
**non è questa la strada**: il backend di produzione è Supabase, e l'app
pubblicata gli parla già direttamente. Farlo girare in remoto duplicherebbe
le regole di prodotto in due posti (problema P1-3).

### 3.4 `scripts/*.py`

Sette script da riga di comando, ognuno con un docstring che ne spiega scopo e
uso: estrazione della lista Google Maps, importazione degli spot con nomi
dedotti dalla città più vicina, collegamento delle foto dai manifest,
ottimizzazione delle foto (Pillow), generazione dei QR, patch e aggiornamento
del bundle Expo pubblicato. Girano sul PC dell'autore o in
`sync-map.yml`. Sono i primi candidati a diventare **job** del servizio
remoto, perché lavorano su dati e non hanno interfaccia.

## 4. Come gira oggi l'applicazione, e dove

```
Telefono / browser
   │
   ├─► GitHub Pages (branch gh-pages)
   │     /                      vecchio bundle Expo (legacy) + pk-route.js, pk-scheda.js
   │     /t/30dc…/              build Flutter web di settembre (l'app vera)
   │     /t/prova-accesso/      pagina di prova dell'accesso via codice email
   │     /admin-inviti.html     console inviti con un segreto nel sorgente (P0-1)
   │
   ├─► Supabase (progetto PkFAMILY): Auth, Postgres + PostGIS + RLS, Storage
   │     ← l'app pubblicata parla direttamente con lui, con la chiave pubblicabile
   │
   └─► routing.openstreetmap.de (server pubblico OSRM, da pk-route.js)

GitHub Actions: backup pubblico ogni notte; rigenerazione mappa a richiesta.
PC dell'autore: backend FastAPI (solo per prove), script della pipeline, deploy con scripts/deploy_test_web.sh.
```

In una frase: la parte "remota" dell'applicazione oggi è **GitHub Pages più
Supabase**; il codice Python del repository non gira da nessuna parte se non
sul computer di chi lo sviluppa.

## 5. Problemi che contano per il remoto

Dal masterplan (capitolo 1.4), verificati leggendo il codice, più quelli
emersi in questa analisi. I valori dei segreti non sono riportati.

| # | Problema | Verifica fatta | Effetto sul lavoro |
| --- | --- | --- | --- |
| P0-1 | Segreto di firma degli inviti scritto nel sorgente di `admin-inviti.html` su `gh-pages` | Riga 85 del file: una costante con un valore reale (mascherato). | Va ruotato e la pagina rimossa (fase 0). Nessun servizio nuovo deve dipendere da quel segreto. |
| P0-1b | **Lo stesso segreto è anche su `main`**, in `docs/demo/tools/build_tutorial_preview.py:48` (stringa `PkFAMILY::<segreto>::` incorporata nelle pagine generate con `--gate`) | Confronto per hash con il valore di `admin-inviti.html`: identico. È nella storia git di `main`. | Cancellare il file non basta: il segreto va **ruotato** (S0-1, S0-4). Nessun codice nuovo lo riusa. |
| P0-2 | Console admin che usa la chiave segreta Supabase nel browser | `admin-desktop/index.html:70-71`: la chiave è un campo di input, non è nel repository. Il rischio è l'uso dal browser, non un segreto committato. | Le operazioni privilegiate devono passare da un server: è uno dei motivi per cui esiste il servizio remoto. |
| P0-3 | Sorgenti della build pubblicata non su `main` | `gh-pages` contiene `t/30dc…/main.dart.js`, `flutter_service_worker.js`, `manifest.json`; `mobile/lib` ha 26 file e una parte delle funzioni. | Il servizio Python non può contare su un client ricostruibile: espone rotte con un contratto chiaro, che il client adotterà quando i sorgenti saranno recuperati. |
| P1-1 | Schema di produzione diverso da quello delle migrazioni | `📲/backup-quotidiano.json` mostra la tabella `spots` reale con `lat`, `lng`, `skill_level`, `has_fountain`, `crowd_level`, `author_id`; le migrazioni definiscono `location` geography, `difficulty`, `water`, `submitted_by`. `profiles` reale ha `username` e `banned`, non `display_name`. | Le migrazioni 0001–0004 **non vanno eseguite** così come sono sul progetto vero. Il job `spots-export` accetta entrambe le forme e non fa supposizioni sulle colonne. |
| P1-2 | Nessuna CI | `.github/workflows/`: solo backup e sync. | Aggiunto il primo workflow di lint, test, scansione segreti e immagine (capitolo 7). |
| P1-3 | Due backend senza decisione | `backend/` completo e non usato; Supabase usato. | Il servizio remoto **non** riscrive le funzioni di prodotto. |
| N-1 | Un file del bundle Expo legacy su `gh-pages` contiene la stringa `sb_secret_` | `git grep` sul branch: un solo file, `_expo/static/js/web/entry-*.js`. Letto con il valore mascherato: è il codice della libreria `supabase-js` che controlla il prefisso (`e.startsWith("sb_secret_")`), lunghezza dopo il prefisso zero. **Non è una chiave.** | Nessuna rotazione necessaria; il file sparisce comunque con il bundle legacy (fase 0). |
| N-2 | Documenti non allineati al codice | `docs/ARCHITECTURE.md` descrive accesso con password e `POST /auth/login`; il codice usa codici via email e ospiti. `docs/PROJECT_RULES_AND_ROADMAP.md` §5 dà "Auth su mobile" come pianificata mentre `mobile/lib` ha già repository di auth e onboarding. | Chi legge solo i documenti costruisce la cosa sbagliata. Qui si è letto il codice. |

### 5.1 Esiti della lettura parallela per aree

Sei lettori indipendenti hanno letto per intero un'area ciascuno (backend,
Supabase e backup, mobile, web pubblicata, pipeline e workflow,
documentazione) e riportato ogni affermazione con file e riga. La doppia
verifica automatica di ogni rilievo è stata interrotta dopo i primi sette
verdetti perché su questa macchina girano due agenti alla volta e i rilievi
erano più di ottanta. Quindi:

- **verificato** = controllato di persona in questa sessione, con il comando
  o il file indicato;
- **riportato** = affermazione di un lettore, con citazione di file e riga,
  non ricontrollata.

Sono esclusi i rilievi di stile. Restano quelli che cambiano cosa un servizio
Python remoto deve fare o evitare.

#### Supabase, dati, backup

| Sev. | Stato | Rilievo | Conseguenza per il servizio remoto |
| --- | --- | --- | --- |
| P1 | verificato | Schema di produzione diverso dalle migrazioni (vedi P1-1 sopra). `supabase/seed/seed.mjs` scrive `display_name`, `location`, `difficulty`: contro produzione fallisce (riportato). | I job leggono le colonne che esistono davvero e scrivono solo campi dichiarati. |
| P1 | riportato | Le migrazioni si applicano a mano nel SQL Editor; nessun `supabase/config.toml`, nessuna CLI, nessun registro di cosa è applicato. Template OTP, SMTP e "anonymous sign-ins" sono impostazioni del pannello non versionate (`supabase/README.md:28-43`). | Il servizio non può dare per scontata nessuna funzione SQL delle migrazioni (`is_admin`, `my_content_ceiling`) finché non è confermata in produzione. |
| P2 | riportato | Grant per colonna: `select=*` fallisce su `member_profiles` e `experience_quiz_attempts` con un JWT utente (`0003_auth_profiles_and_legal.sql:81-89, 352-359`). | Su quelle tabelle vanno elencate le colonne. Su `spots` `select=*` è lecito. |
| P2 | riportato | Il tetto dei contenuti su `videos` scatta solo con un JWT utente; con la sola chiave pubblicabile il catalogo è intero (`0003:227-234`). | Un job che legge per conto di una persona deve inoltrare **il suo** JWT, mai una chiave di servizio. Oggi il servizio non lo sa fare (il client fissa l'intestazione alla chiave): è il passo 2 del cap. 9. |
| P2 | riportato | Il backup pubblico su GitHub include `profiles` (masterplan P2-4). `spot_moderation_events` non è popolata da alcun trigger e la console non la scrive. | Nessuna. Da risolvere nelle fasi 0 e 2 del masterplan. |

#### `backend/` (FastAPI)

| Sev. | Stato | Rilievo | Conseguenza per il servizio remoto |
| --- | --- | --- | --- |
| P1 | verificato | Il limitatore `slowapi` è inerte: `main.py:18` crea il `Limiter` ma nessun `SlowAPIMiddleware` viene aggiunto e nessuna rotta è decorata (`grep` su `backend/app`: zero occorrenze). `/auth/login` resta senza protezione dalla forza bruta. | Nel servizio remoto il limite di richieste è demandato al provider o a Cloudflare (masterplan 6.5); non è replicato il codice inerte. |
| P1 | verificato | La chat inoltra il messaggio via WebSocket solo al mittente (`chat.py:53-61`, `chat_service.py:30-40`) e il gestore delle connessioni vive in un solo processo; `docs/ARCHITECTURE.md:56` promette un fan-out via Redis che non esiste. | Conferma che la chat va su Supabase Realtime, non in Python. |
| P2 | riportato | `GET /spots/{id}` mostra anche spot `pending` e `rejected` a chi conosce l'id (`spots.py:77-82`). | Il job `spots-export` filtra `status=eq.verified` lato server. |
| P2 | verificato | In produzione `CORS_ORIGINS` omesso dà una lista vuota (`main.py:40`): i client browser vengono bloccati senza alcun errore di configurazione; app native e chiamate server-server non sono toccate. | `remote-service` rifiuta di partire con CORS vuoto in produzione. |
| P2 | riportato | Redis dichiarato in configurazione, compose e documenti ma mai usato; `INITIAL_ADMIN_*` e `S3_*` letti e mai usati: nessun modo di creare il primo admin. | Il servizio remoto non dichiara dipendenze che non usa. |
| P2 | riportato | `backend/Dockerfile`: manca `.dockerignore` (un `.env` locale finirebbe nell'immagine); `pip install -e .` gira prima di copiare i sorgenti. | Il `Dockerfile` di `remote-service` copia solo `pyproject.toml` e `pkremote/`. |
| P2 | riportato | Nessun test tocca il database (motore creato in modo pigro); nessuna CI li esegue. | La CI per `backend/` resta da fare (cap. 9, passo 5). |
| P2 | riportato | Ruotare `JWT_SECRET` invalida tutte le chiavi ospite e i codici in corso (HMAC con lo stesso segreto, `auth_service.py:42-50`). | Da sapere prima di qualsiasi rotazione. |
| P2 | riportato | SMTP: `starttls()` senza contesto TLS, quindi senza verifica del certificato (`mailer.py:99-101`). | Il servizio remoto non spedisce posta; se lo farà, userà l'API HTTPS del provider. |

#### `mobile/` (Flutter)

| Sev. | Stato | Rilievo | Conseguenza per il servizio remoto |
| --- | --- | --- | --- |
| P1 | verificato | L'app parla **solo** con FastAPI: zero riferimenti a Supabase in `mobile/lib`. L'URL è fissato in compilazione (`--dart-define`, default `http://10.0.2.2:8000`). | Finché il client non passa a Supabase (decisione P1-3), nessun client chiama il servizio remoto: le rotte esposte sono un contratto per il client futuro. |
| P1 | verificato | Il refresh token è salvato ma mai usato; nessuna gestione del 401. Dopo 15 minuti falliscono con 401 le rotte con bearer usate dall'app (`/api/v1/onboarding/*`); spot e informative sono pubblici e continuano a funzionare; i video degradano alla vista anonima. | Nessuna diretta. |
| P1 | verificato | La build Flutter pubblicata su `gh-pages` usa un backend finto (`https://preview.invalid`) e dati incorporati: zero occorrenze di `supabase` in `main.dart.js`. È un'anteprima, non un'app collegata. | Il "P0-3" del masterplan è confermato in una forma più netta: non esiste oggi un client Flutter collegato a un backend. |
| P2 | riportato | Manca `mobile/web/`: `flutter build web` non parte dai sorgenti. Release Android firmata con chiavi di debug. | Nessuna diretta. |

#### Web pubblicata

| Sev. | Stato | Rilievo | Conseguenza per il servizio remoto |
| --- | --- | --- | --- |
| P0 | verificato | Segreto degli inviti su `gh-pages` **e** su `main` (P0-1 e P0-1b sopra). | Rotazione. Il servizio non implementa inviti: sono una Edge Function (masterplan 4.5). |
| P1 | verificato | `web-admin` non compila: importa `@/lib/api` ma `web-admin/src/lib/` non è nel repository, escluso dalla regola `lib/` di `.gitignore:17`. | `web-admin` non è una base su cui contare. |
| P1 | riportato | Nessuna pagina online verifica più il frammento `#pass=`: la console inviti è orfana (il segreto resta pubblico). | Nessuna diretta. |
| P1 | riportato | `?api=http://…` da una pagina `https` è contenuto misto e il browser lo blocca; il default `https://api.notot.family` dei moduli web non esiste (`pk-legal.js:23`, `pk-onboarding.js:25`). | Il servizio remoto deve stare dietro HTTPS con un nome reale; `CORS_ORIGINS` deve includere `https://oigresergio.github.io`. |
| P2 | verificato | Il bundle Expo alla radice esegue scritture amministrative (stato degli spot, ruoli, ban, video) direttamente dal browser con la chiave pubblicabile; l'unico controllo lato client è un flag di interfaccia, l'unica barriera reale sono le RLS. Per `profiles` le migrazioni nel repository non prevedono alcuna policy admin (solo l'aggiornamento del proprio `display_name`) e la colonna `banned` non esiste in nessuna migrazione: quelle scritture funzionano solo se lo schema di produzione è diverso, cioè P1-1. `t/prova-accesso/` crea account reali sul progetto. | Rafforza S0-2: le azioni privilegiate passano da un server. Il confine tra Edge Functions e questo servizio è nel cap. 6. |
| P2 | riportato | `robots.txt` online è `Allow: /` con `Disallow` solo su `/admin-inviti.html` e `/t/`; i documenti dicono il contrario. | Nessuna. |

#### Pipeline, infrastruttura, workflow

| Sev. | Stato | Rilievo | Conseguenza per il servizio remoto |
| --- | --- | --- | --- |
| P1 | verificato | `sync-map.yml:41` patcha `ghp/t/*/_expo/…`, un percorso che su `gh-pages` non esiste (il bundle Expo è alla radice; `t/` contiene una build Flutter). | Il passo "patch del bundle" va tolto; i dati vanno prodotti da un job. |
| P1 | verificato | `scripts/deploy_test_web.sh` cancella tutto `gh-pages` e ripubblica sotto il token `2fe0…`, diverso da quello online (`30dc…`): eseguirlo oggi distruggerebbe l'app pubblicata. | Non va eseguito. Il deploy sarà un workflow. |
| P2 | riportato | La pipeline scrive JSON nel repository con due schemi diversi (`webapp_fixed_spots.json`: 1.706 spot; `backend/seeds/spots.json`: 26 spot) invece che su un backend. `fetch_gmaps_list.py` dipende da un endpoint interno di Google Maps non documentato. | Il job di importazione (cap. 9, passo 2) deve scegliere una destinazione sola: Supabase. |
| P2 | riportato | `infra/routing/`: compose pronto ma senza dati OSM né profilo `pk_foot.lua`. | `OSRM_BASE_URL` resta vuoto finché l'istanza non esiste; il proxy risponde 503 e i client usano il fallback. |
| P3 | riportato | `Pillow` e `qrcode` non sono dichiarati in alcun manifest; nessun test in `scripts/`. | Il job foto (cap. 9, passo 3) porterà le dipendenze nel `pyproject.toml` del servizio. |

#### Documentazione

| Sev. | Stato | Rilievo | Conseguenza per il servizio remoto |
| --- | --- | --- | --- |
| P2 | verificato | `ARCHITECTURE.md` (password, FastAPI unico), `DATA_MODEL.md` (ruoli e tabelle mancanti) e `PROJECT_RULES_AND_ROADMAP.md` §5 sono di una generazione precedente al codice e al masterplan. | Questo documento e `remote-service/README.md` rimandano al masterplan, non a quei file. |
| P2 | riportato | Il masterplan chiede `supabase/migrations/0003_stato_produzione.sql` ma il numero 0003 è già usato: serve un numero nuovo. `docs/ONBOARDING.md`, linkato da `LEGALE.md:96`, non esiste. | Nessuna. |

## 6. La decisione: che cosa deve essere la base Python remota

Le regole del masterplan che vincolano la scelta:

- **un solo backend di produzione, Supabase** (4.2): autenticazione, dati,
  RLS, storage, realtime, Edge Functions;
- **FastAPI resta servizio di supporto** (4.2): proxy con cache per i
  percorsi, job pesanti (foto, importazioni); nessuna nuova funzione di
  prodotto;
- **nessun segreto nel client** (2.4, 6.2): le operazioni privilegiate
  passano da funzioni server;
- **privacy by design** (6.4): la posizione dell'utente non lascia il
  dispositivo; verso il proxy dei percorsi viaggiano solo coordinate
  arrotondate a 100 m, senza identità;
- **tutto ciò che è online nasce da `main` via CI** (2.5, 4.6);
- **niente contenuti finti** (2.1): nessun job può creare post, commenti,
  voti o segnalazioni.

Da qui la forma della base Python:

1. **Un servizio senza stato e senza database proprio.** Legge Supabase via
   REST (PostgREST) con la chiave pubblicabile, che rispetta le RLS. La
   chiave segreta non è mai un ripiego: oggi nessun job la usa e da sola non
   attiva niente; quando un job privilegiato esisterà, la chiederà in modo
   esplicito. Niente Postgres né Redis da provisionare: si mette in remoto in
   minuti e si può riavviare o duplicare senza perdere dati di prodotto (la
   cache dei percorsi e i file dei job sono per istanza e si rigenerano).
2. **Tre responsabilità**, tutte previste dal masterplan: stato
   (`/healthz`, `/readyz`), proxy dei percorsi con cache e arrotondamento
   (`/api/v1/route`, fase 2 di `docs/ROUTING_PK.md`), job (esportazioni,
   importazioni, foto) eseguibili da riga di comando o via HTTP con token.
3. **Un contenitore costruito dalla CI** e pubblicato su GitHub Container
   Registry: da lì qualunque host lo avvia. La scelta dell'host è
   dell'admin (decisione aperta G del masterplan) e non è vincolata dal
   codice.
4. **Codice nuovo, commentato in italiano, separato da `backend/`.** Le
   funzioni di prodotto di `backend/` non vengono portate: vivono in
   Supabase. `backend/` resta com'è; la sua sorte (archivio in `legacy/`)
   resta la decisione G.
5. **Il confine con le Edge Functions.** Il masterplan (4.5) affida le
   scritture privilegiate brevi (ruoli, ban, moderazione, inviti) a Edge
   Functions in `supabase/functions/`, che oggi non esistono. Regola adottata
   qui: le scritture privilegiate iniziate da un browser non passano mai per
   una chiave segreta in questo servizio; questo servizio fa lavori lunghi o
   pesanti (foto, importazioni, esportazioni, proxy) e, quando saprà
   verificare il JWT di Supabase, letture per conto di una persona con il
   **suo** token. Se l'admin volesse usarlo come ponte per S0-2 prima delle
   Edge Functions, il modo è: token dell'utente inoltrato, azione autorizzata
   dalle RLS per `is_admin()`, riga di audit append-only. È una decisione
   da prendere, non presa qui.
6. **Il container è opzionale finché non esiste un consumatore.** Oggi OSRM
   non c'è (`infra/routing/` è senza dati) e il proxy non ha client; l'unico
   job con valore, `spots-export`, può girare in GitHub Actions senza server.
   La base è pronta per il container; accenderlo davvero ha senso quando
   parte l'OSRM proprio (decisione G).

Perché una cartella nuova e non un'estensione di `backend/`: `backend/`
porta con sé un database, Redis, la posta, le migrazioni e le rotte di
prodotto, cioè tutto ciò che il servizio remoto non deve avere. Partire da
un pacchetto piccolo, con un'unica dipendenza esterna (HTTP), rende il
deploy remoto la cosa facile invece di quella difficile.

## 7. La struttura creata: `remote-service/`

Il pacchetto si chiama `pkremote`. Ogni file inizia con un commento che
spiega cosa fa e perché è fatto così; qui l'elenco in una riga per file.

```
remote-service/
├── README.md               cos'è, come si avvia, come si mette in remoto, regole, come si estende
├── pyproject.toml          dipendenze (fastapi, uvicorn, httpx, pydantic, pydantic-settings, structlog), ruff, pytest
├── .env.example            tutte le variabili, commentate una a una
├── Dockerfile              immagine a due stadi, utente non root, HOST=0.0.0.0, healthcheck su /healthz
├── docker-compose.yml      avvio locale; profilo `routing` che affianca OSRM (dati in infra/routing)
├── pkremote/
│   ├── __init__.py         versione e mappa del pacchetto
│   ├── __main__.py         comando `pkremote`: serve | jobs | job <nome> | config (segreti mascherati)
│   ├── app.py              fabbrica dell'app: oggetti condivisi su app.state, middleware, gestori degli errori, rotte
│   ├── config.py           Settings da ambiente; in produzione rifiuta HOST≠0.0.0.0/::, CORS vuoto o "*", DEBUG, log non JSON, segreti segnaposto, JOB_TOKEN corto, SUPABASE_URL non https, chiave segreta senza pubblicabile; rifiuta sempre il router pubblico FOSSGIS come OSRM
│   ├── deps.py             come le rotte ottengono settings, client, cache, contesto e lock dei job; protezione con token (le rotte non toccano app.state)
│   ├── errors.py           AppError con codice stabile e i gestori che danno a tutti gli errori, anche 404/405/422 di FastAPI, la forma {"error": {"code", "message"}}
│   ├── logs.py             un solo formatter per structlog e uvicorn, JSON in remoto, console in locale, su stderr; maschera lat, lng, email, authorization, token; il log di accesso di uvicorn (query string e IP) è spento e sostituito da un evento per richiesta con X-Request-ID
│   ├── middleware.py       CORS; intestazioni nosniff, referrer, no-store, HSTS in produzione; un evento di log per richiesta con X-Request-ID
│   ├── security.py         confronto del token dei job a tempo costante
│   ├── api/health.py       GET /healthz (vivo) e GET /readyz (dipendenze configurate raggiungibili → 200, altrimenti 503; timeout breve, esito riusato per 10 s)
│   ├── api/route.py        GET /api/v1/route?from=lat,lng&to=lat,lng → RouteAnswer (distanza, durata, GeoJSON, cached, precision_m)
│   ├── api/jobs.py         GET /api/v1/jobs, POST /api/v1/jobs/{nome}; con Authorization: Bearer JOB_TOKEN; lo stesso job non gira due volte insieme (409)
│   ├── services/routing.py parse e validazione, arrotondamento a ~111 m, chiave di cache, chiamata a OSRM
│   ├── services/cache.py   cache in memoria con scadenza e limite LRU, protetta da lock
│   ├── integrations/http.py      una sola GET per tutte le chiamate in uscita: timeout opzionale, errori di rete → 502
│   ├── integrations/supabase.py  client PostgREST minimo (ping leggero, select, select_all a pagine con Range); `from_settings` lo costruisce solo dalla chiave pubblicabile; la chiave non compare mai in repr o log
│   ├── integrations/osrm.py      client OSRM (ping, route); converte lat,lng → lng,lat in un solo posto
│   ├── integrations/geo.py       decodifica EWKB (esadecimale PostGIS) e GeoJSON dei punti
│   ├── jobs/base.py        contratto Job, JobResult (anche risposta HTTP), JobContext.build (stesso contesto da CLI e da HTTP), registro, esecutore con tempi, log ed errori catturati
│   ├── jobs/ping.py        job di verifica del deploy
│   └── jobs/spots_export.py      legge gli spot verificati da Supabase (schema reale lat/lng o schema delle migrazioni) e scrive output/spots_verificati.json; zero righe = esito non riuscito, nessun file
├── .dockerignore           .env, ambienti virtuali, cache, risultati e test restano fuori dall'immagine
└── tests/                  103 test senza rete: Supabase e OSRM sono trasporti finti
```

E alla radice del repository:

```
.github/workflows/remote-service.yml   lint + test a ogni modifica; ai push su main costruisce l'immagine (amd64 e arm64), la prova su /healthz e la pubblica su ghcr.io
.github/workflows/gitleaks.yml         scansione segreti su ogni push e PR, e settimanale su tutta la storia (S0-4)
.github/dependabot.yml                 aggiornamenti settimanali di pip, immagini Docker e azioni (6.5)
.gitleaks.toml                         esclude solo la chiave pubblicabile di Supabase, pubblica per progetto
README.md, docs/PKFAMILY_MASTERPLAN.md (4.2, 4.6), docs/ROUTING_PK.md, docs/ARCHITECTURE.md   note che rimandano a remote-service/ e a questo documento
```

### 7.1 Cosa è stato verificato

| Verifica | Esito |
| --- | --- |
| `ruff check .` su `remote-service/` | pulito |
| `pytest` (103 test: configurazione, salute, routing, cache, job, client Supabase, geometrie, log, CLI) | 103 passati |
| `pkremote --version`, `pkremote jobs`, `pkremote config` con un finto `SUPABASE_SECRET_KEY` nell'ambiente | il valore non compare nell'output |
| `pkremote job ping` | JSON pulito su stdout, log su stderr |
| Server avviato con `pkremote serve` e interrogato con `curl` | `/healthz` 200 con intestazioni di sicurezza e `X-Request-ID`; `/readyz` 200 con dipendenze `not_configured`; `/api/v1/route` 503 `routing_unavailable` senza OSRM; `/api/v1/jobs` 401 senza token; `POST /api/v1/jobs/ping` 200 con token; preflight CORS corretto; nessuna riga di log contiene la query string delle richieste a `/api/v1/route` |
| Revisione avversaria del pacchetto (cinque revisori: correttezza, sicurezza e privacy, esecuzione remota, coerenza con il masterplan, test) e critico di completezza | 53 rilievi e 17 osservazioni letti uno per uno; i confermati sono stati corretti (vedi 7.3) |
| Test di `TernaryOperator` | 3 passati |

### 7.3 Cosa la revisione ha cambiato

La prima versione del pacchetto aveva difetti che i test non vedevano e che
in remoto avrebbero contato. I principali, con la correzione:

| Rilievo | Correzione |
| --- | --- |
| Il log di accesso di uvicorn scriveva la query string intera, cioè le coordinate precise prima dell'arrotondamento, e l'indirizzo IP: contro il masterplan 6.4 | Log di accesso spento; un evento per richiesta con metodo, percorso senza query, stato, durata e `X-Request-ID`; i log di uvicorn passano dallo stesso formatter JSON |
| Con la sola chiave segreta configurata, il servizio la usava per tutto, contro ciò che i commenti dichiaravano | Il client nasce solo dalla chiave pubblicabile; la segreta da sola non attiva niente e in produzione senza la pubblicabile è un errore di configurazione |
| Una configurazione di produzione non valida stampava il traceback di pydantic con i valori ricevuti, chiavi comprese | `pkremote` stampa solo le spiegazioni, senza valori |
| Il job `spots-export` leggeva colonne che in produzione non esistono e una sola pagina | Accetta lo schema reale e quello delle migrazioni; pagina con `Range` avanzando di quante righe arrivano; rifiuta un server che ignora `Range`; zero righe = esito non riuscito |
| Gli errori di FastAPI (parametro mancante, 404, 405) avevano una forma diversa da quella promessa ai client | Un solo involucro `{"error": {"code", "message"}}` per tutti |
| `/readyz` usava il timeout generale (10 s) in sequenza, scaricava lo schema OpenAPI di PostgREST e interrogava gli upstream a ogni sonda | Timeout dedicato, controlli in parallelo, lettura minima, esito riusato per 10 s |
| OSRM risponde 400 quando non trova un tragitto: il ramo che leggeva il codice non era raggiungibile | Il codice (`NoRoute`, `NoSegment`) viene letto anche sui 400 |
| `forwarded_allow_ips="*"`, `WEB_CONCURRENCY` che avvia più worker in silenzio, `/openapi.json` pubblico in produzione, messaggi d'errore che ripetevano le coordinate ricevute, lo stesso job eseguibile due volte insieme | Tutti corretti: `FORWARDED_ALLOW_IPS` configurabile, un solo worker, schema spento in produzione, messaggi senza eco, 409 sul job già in corso |
| gitleaks girava solo quando cambiava `remote-service/`; i test contenevano il prefisso reale della chiave segreta, che il criterio S0-2 vieta nel repository | Workflow `gitleaks.yml` separato su tutto il repository; valori finti senza quel prefisso |
| Nessun test per il mascheramento dei log, per il token sulla rotta che esegue i job, per la politica LRU, per i codici d'uscita della CLI | Aggiunti |

### 7.2 Cosa NON è stato verificato

- La **build dell'immagine Docker**: in questa sessione non c'è un demone
  Docker. Il `Dockerfile` è scritto secondo lo schema a due stadi standard,
  ma la prima build vera la farà il workflow o l'admin.
- Il **workflow GitHub**: parte al primo push su `main` (o a mano); qui
  è stato solo scritto. `gitleaks-action` è gratuita per account personali.
- Le chiamate a un **Supabase reale** e a un **OSRM reale**: i test usano
  trasporti finti. Il formato `application/geo+json` di PostgREST e la
  forma EWKB delle geometrie sono documentati e coperti da test, ma la
  prima esecuzione di `spots-export` contro il progetto vero va guardata.
- Nessun deploy è stato fatto: non ci sono segreti né un host in questa
  sessione.

## 8. Come si mette in remoto

I passi, nell'ordine, con chi li fa:

1. **Admin**: sceglie l'host (VPS con Docker, Fly.io, Render, Railway,
   Koyeb: tutti avviano un'immagine). Raccomandazione: un PaaS con immagini
   Docker e TLS incluso, per non gestire un reverse proxy.
2. **Admin**: imposta nel pannello dell'host (mai nel repository)
   `ENV=production`, `HOST=0.0.0.0`, `LOG_FORMAT=json`,
   `CORS_ORIGINS=https://oigresergio.github.io` (più il dominio futuro),
   `FORWARDED_ALLOW_IPS` secondo l'host, `SUPABASE_URL` e
   `SUPABASE_PUBLISHABLE_KEY` (che sono pubblici per costruzione: stanno già
   in `📲/backup.mjs` e nelle pagine online, quindi vanno trattati come
   variabili, non come segreti), e se vuole lanciare job da remoto un
   `JOB_TOKEN` generato con `secrets.token_urlsafe(32)`. La chiave segreta
   Supabase **non** serve per nulla di ciò che esiste oggi. Il masterplan
   (4.6, 6.5) vuole un progetto Supabase di anteprima con chiavi proprie:
   la prima esecuzione reale va fatta lì, non in produzione.
3. **Prima di tutto, questo lavoro deve arrivare su `main`**: è su un branch
   e va in pull request con CI verde (masterplan 7.1). Al primo push su
   `main` che tocca `remote-service/`, il workflow prova l'immagine e la
   pubblica come `ghcr.io/oigresergio/pkremote:latest` e `:sha-<commit>`. Il
   pacchetto nasce privato: l'admin lo rende pubblico o dà all'host un token
   di lettura. Il workflow `gitleaks.yml` sarà rosso finché il segreto degli
   inviti resta nella storia di `main` (P0-1b): è il comportamento voluto da
   S0-4, e la risposta è la rotazione.
4. **Admin**: punta l'host all'immagine per tag `sha-<commit>` (non `latest`,
   così ciò che è online è legato a un commit), health check su `/healthz`,
   porta quella che l'host mette in `PORT`. Un workflow di deploy con
   l'ambiente `production` ad approvazione è il passo successivo (cap. 9).
5. **Chiunque**: `curl https://<host>/healthz` e `curl https://<host>/readyz`
   devono rispondere 200; con un token, `POST /api/v1/jobs/ping` risponde
   `pong` con il nome dell'istanza.
6. **Poi**: quando esisterà l'OSRM self-hosted (`infra/routing/`), si
   imposta `OSRM_BASE_URL` (mai il server pubblico: la configurazione lo
   rifiuta) e il client dell'app chiama `https://<host>/api/v1/route`. Il
   client non è `scripts/web/pk-route.js`: quel file legge il JSON grezzo di
   OSRM, manda coordinate non arrotondate ed è caricato solo dal bundle Expo
   che la fase 0 elimina. Il client sarà l'app Flutter, i cui sorgenti vanno
   prima recuperati (P0-3); il contratto della risposta è documentato in
   `docs/ROUTING_PK.md` e in `remote-service/pkremote/api/route.py`.
7. **Per i soli job senza server**: un workflow con l'ambiente `production`
   (da creare: oggi nel repository non esiste alcun secret o variabile GitHub
   per Supabase) che fa `pip install ./remote-service && pkremote job
   spots-export` e salva il file come artefatto o lo passa alla build delle
   pagine statiche.

Il servizio si rifiuta di partire con una configurazione di produzione
pericolosa e dice cosa correggere: è voluto.

## 9. Prossimi passi, in ordine

| Ordine | Passo | Fase del masterplan | Dove |
| --- | --- | --- | --- |
| 1 | Pull request di questo lavoro verso `main`, CI verde, revisione; primo `spots-export` reale sul progetto di anteprima | 0 | admin + questo branch |
| 2 | Identità dell'utente nel servizio: verifica del JWT di Supabase Auth (chiavi pubbliche del progetto, `exp`, `aud`) e `as_user(token)` nel client PostgREST, così le letture per conto di una persona rispettano il suo tetto dei contenuti; il ruolo si legge da `profiles` con il suo token, mai da claim del client | 2 | `pkremote/auth.py`, `integrations/supabase.py`, `deps.py` |
| 3 | Job `spots-import`: porting di `scripts/import_gmaps_list_spots.py` e `wire_spot_photos.py` come job che producono **proposte** con `status=community` (regola 2), in prova a secco per default e con scrittura su Supabase solo con un flag esplicito e un client privilegiato dichiarato dal job (mai scritture in `posts`/`comments`) | 0–2 | `pkremote/jobs/` |
| 4 | Job `photo-ingest` lato server: rimozione EXIF e GPS, ridimensionamento, bucket privato con URL firmati (6.4) | 2 | `pkremote/jobs/` + Storage Supabase |
| 5 | OSRM self-hosted su un host con ~1 GB di RAM e `OSRM_BASE_URL` impostato; limite di distanza e limite di richieste per il proxy; contratto JSON pubblicato per l'app Flutter | 2 | `infra/routing/`, `pkremote/api/route.py`, `docs/ROUTING_PK.md` |
| 6 | Deploy da CI: workflow con ambiente `production` ad approvazione, deploy per tag `sha-<commit>`, smoke test dopo il deploy; ambiente `preview` con chiavi separate; lockfile delle dipendenze e immagini a digest (6.5) | 0 | `.github/workflows/` |
| 7 | Estendere la CI a `backend/` (ruff, pytest con Postgres effimero) e `mobile/` (analyze, test): è la parte di P1-2 che questo lavoro non copre | 0 | `.github/workflows/ci.yml` |
| 8 | Esportare lo schema di produzione in una nuova migrazione (il numero 0003 è già usato) e aggiornare `DATA_MODEL.md` a Supabase come backend di produzione | 0 | `supabase/`, `docs/` |
| 9 | Decidere il destino di `backend/` (decisione G): archivio in `legacy/` quando i job 3 e 4 sono qui | 2 | admin |

## 10. Nota di consegna

```
FATTO:
- Analisi dei due repository (questo documento), con lettura diretta di configurazione,
  punti d'ingresso, schema Supabase, workflow, script di deploy e branch gh-pages.
- remote-service/: pacchetto Python `pkremote` commentato in italiano (stato, proxy dei
  percorsi con cache e coordinate arrotondate, job con token, CLI), Dockerfile,
  .dockerignore, docker-compose, .env.example, README, 103 test; rivisto da cinque
  revisori indipendenti e corretto (cap. 7.3).
- .github/workflows/remote-service.yml (lint, test, immagine provata e pubblicata su GHCR),
  .github/workflows/gitleaks.yml (S0-4), .github/dependabot.yml, .gitleaks.toml.
- README.md alla radice, masterplan 4.2 e 4.6, ROUTING_PK.md, ARCHITECTURE.md: note brevi
  che rimandano a remote-service/ e a questo documento.
- Seconda passata di coerenza sul pacchetto: una sola funzione HTTP in uscita, client Supabase
  costruito in un posto solo, modelli di risposta definiti una volta (RouteAnswer, JobResult),
  middleware e gestori degli errori nei propri moduli, rotte che non toccano app.state.
- Per gli agenti: AGENTS.md (istruzioni condivise), CLAUDE.md, .junie/guidelines.md,
  configurazioni PyCharm in .run/, guida e incarichi di allenamento in docs/AGENTI_PYCHARM.md.
- TernaryOperator: porting Python commentato, test, README (branch già pubblicato).

VERIFICATO:
- ruff pulito e 103 test verdi in remote-service/; 3 test verdi in TernaryOperator.
- Server avviato in locale e interrogato con curl su tutte le rotte (esiti in 7.1); nessuna
  coordinata nei log.
- `pkremote config` non stampa i segreti; `pkremote job ping` produce JSON pulito.
- Quattro rilievi dei lettori ricontrollati da agenti indipendenti: tutti confermati.

NON FATTO:
- Build dell'immagine Docker (nessun demone Docker nella sessione), pull request e primo
  deploy: il lavoro è sul branch claude/analisi-struttura-python-o8yvue.
- Chiamate reali a Supabase e OSRM (test con trasporti finti).
- Verifica del JWT di Supabase e letture per conto di un utente (passo 2 del cap. 9).
- Job di importazione spot e pipeline foto: restano in scripts/ (passi 3 e 4 del cap. 9).
- Lockfile delle dipendenze, immagini a digest, workflow di deploy con approvazione.
- CI per backend/ e mobile/.

RISCHI / DECISIONI APERTE:
- Scelta dell'host e dominio (decisione G del masterplan): dell'admin.
- P0-1 (segreto degli inviti) è confermato su gh-pages E su main
  (docs/demo/tools/build_tutorial_preview.py:48): rotazione da parte di una persona (S0-1),
  poi rimozione della pagina e del file. Non è stato copiato né toccato in questa sessione.
- Il job spots-export è scritto sullo schema reale di produzione letto dal backup pubblico;
  la prima esecuzione contro il progetto vero va osservata (colonne e RLS possono essere
  cambiate dopo il 20 luglio 2026).
- `backend/` resta nel repository senza essere usato: la decisione di archiviarlo è
  dell'admin e non è presa qui.
- Il container remoto è pronto ma senza consumatori finché non esiste l'OSRM proprio:
  accenderlo prima è un costo e una superficie in più (cap. 6 punto 6).
- Il confine tra Edge Functions (che non esistono) e questo servizio per le azioni
  privilegiate (S0-2) è una scelta dell'admin (cap. 6 punto 5).

DIVERGENZE TROVATE:
- docs/ARCHITECTURE.md e docs/PROJECT_RULES_AND_ROADMAP.md descrivono un accesso con
  password e uno stato del mobile più arretrato di quello nel codice.
- Il masterplan (4.2) dice "FastAPI resta come servizio di supporto"; il servizio di
  supporto è stato costruito in una cartella nuova invece che dentro backend/, per le
  ragioni del cap. 6. È una scelta di struttura, non di direzione, e va confermata.
```
