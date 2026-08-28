# Cose che restano all'umano

Azioni del lancio ([`LAUNCH_PLAN.md`](LAUNCH_PLAN.md)) che nessuno script può fare al posto
tuo. Ordinate per urgenza.

---

## 🔴 Prima di scrivere altro codice

### 0. Le sessioni anonime sono spente, e senza di loro il gate non esiste
Trovato nel BLOCCO 9 interrogando la produzione. È il buco più serio emerso finora, perché
non si vede leggendo il codice.

```sh
GET /auth/v1/settings                          →  "anonymous_users": false
GET /rest/v1/spots?select=id,name,lat,lng      →  200, 24 spot con le coordinate
```

Il secondo comando è senza login, con la sola chiave pubblica. **Chiunque, senza account e
senza aver visto il gate, legge tutti gli spot con le coordinate.**

Perché succede, ed è la parte che conta: la policy della migration `0005` è dichiarata
`to authenticated`. Si applica cioè al ruolo `authenticated`. Chi non apre nessuna sessione è
`anon`, e quella policy **non lo tocca**. Il disegno teneva per una ragione che non sta
nell'SQL — il client apre una sessione anonima all'avvio, trasformando ogni visitatore in
`authenticated` — ma quella è una riga di Dart, e la difesa non può stare in un client che
l'utente controlla. Con le sessioni anonime spente, non succede nemmeno quello.

Due cose, in **quest'ordine**:

1. **Attiva le sessioni anonime**: Dashboard → Authentication → Sign In / Providers →
   *Anonymous sign-ins*. Servono comunque: senza, nessun visitatore può registrare la presa
   d'atto, e la mappa resterebbe vuota per chi non ha un account.
2. **Applica `0010_gate_anche_senza_login.sql`**, che nega gli spot al ruolo `anon` in modo
   esplicito. Un `anon` non ha un `auth.uid()` a cui legare una presa d'atto: per lui la
   risposta è no, non «dipende».

L'ordine inverso non rompe niente di irreparabile, ma svuota la mappa a tutti quelli che non
sono registrati, e nessuno capisce perché.

Se decidi invece di **non** attivare le sessioni anonime, la conseguenza è che per vedere la
mappa bisogna registrarsi. È una decisione di prodotto legittima, ma va presa: la terza
strada — il gate che c'è nell'interfaccia e non nel database — non è una strada.

`scripts/audit_rls.mjs` controlla adesso entrambe le cose insieme e dice quale manca.

### 1. Regione del progetto Supabase → Francoforte
Il progetto è `gkdzdtxqkftebrxhgway`. Verifica in **Dashboard → Settings → General** che la
region sia **Frankfurt `eu-central-1`**.

Nota: **Supabase non offre una region in Italia.** `eu-south-1` (Milano) non è tra quelle
disponibili, e Zurigo e Londra sono fuori SEE. Francoforte è la region europea più collaudata
della piattaforma, e la differenza di latenza rispetto a Parigi è impercettibile per una web app.

Se il progetto non è già lì: creane uno nuovo in UE e migra **adesso**. Oggi ci sono 24 spot e
2 profili — la migrazione costa un pomeriggio. Dopo il lancio costa il lancio.

### 1-bis. La chat è rotta in produzione, e serve la secret key per ripararla
`GET /rest/v1/chats` risponde **HTTP 500**:

```
42P17: infinite recursion detected in policy for relation "chat_members"
```

Le policy di `chats` e `chat_members` si interrogano a vicenda. Non è «manca il client»: a
livello di database la chat **non può funzionare**.

La correzione è pronta in `supabase/migrations/0004_fix_chat_rls_recursion.sql` (funzione
`SECURITY DEFINER` che spezza il ciclo). **Prima di applicarla**: esegui il punto 1-ter, così
sai quali policy esistono davvero, e prova su un progetto di staging — la migration ricrea le
policy delle tabelle di chat.

Verifica dopo: le tre tabelle devono rispondere 200 con lista vuota, mai più 500.

### 1-ter. Il dump vero dello schema
`supabase/migrations/0003_production_baseline.sql` è una **ricostruzione**, non un dump: le
colonne sono state dedotte dall'esterno con la sola publishable key. Tipi, default, vincoli,
indici, foreign key e **tutte le policy RLS** non sono visibili così.

```sh
npm i -g supabase && supabase login
scripts/dump_schema.sh gkdzdtxqkftebrxhgway
```

L'output sostituisce quel file. Finché non lo fai, lo **Scenario B** di
[`../📲/README.md`](../📲/README.md) resta **non eseguibile**, e i tipi TypeScript generati
(`supabase gen types`) non sono producibili.

### 1-quater. Impostazioni Supabase da attivare a mano
Il codice del BLOCCO 2 le dà per presenti; senza, alcune parti restano inerti.

- **Authentication → Sign In / Providers → Email**: conferma email **obbligatoria**.
- **Authentication → Anonymous sign-ins: ON.** Senza, un visitatore non registrato non ha
  `auth.uid()`, la sua presa d'atto non è registrabile e la policy RESTRICTIVE su `spots` gli
  nega tutti gli spot. L'app resta usabile, ma la mappa è vuota finché non fa login.
- **Authentication → Password**: lunghezza minima 12 e *leaked password protection* attiva.
- **Authentication → URL Configuration**: Site URL e redirect su `pkfamily.app` e
  `staging.pkfamily.app`, altrimenti i link di conferma email puntano altrove.
- **Rate limits**: stringere quelli di signup e reset password.
- **Edge Function `parent-access-request`**: da scrivere e deployare. Finché non c'è, la
  schermata "chiedi a un genitore" mostra un errore leggibile invece di fallire in silenzio.
- **pg_cron**: schedulare `purge_expired_parent_requests()` ogni giorno. Se non gira, le email
  dei genitori restano oltre i 7 giorni dichiarati nell'informativa.
- **Cancellazione account**: serve un processo server-side che, scaduti i 30 giorni, rimuova
  profilo e contenuti e **pseudonimizzi** i messaggi. Il client segna solo la richiesta: non
  può cancellare da `auth.users` senza la secret key.

### 1-quinquies. Perché la chat funzioni
Oltre ad applicare `0004` (ricorsione) e `0007` (limiti, blocco, cancellazione):

- **Database → Replication**: abilita Realtime sulla tabella `messages`. Senza, i messaggi
  arrivano solo ricaricando.
- **pg_cron**: schedula `pseudonymise_deleted_accounts()` ogni giorno. Se non gira, il
  pulsante «elimina account» segna solo una data e non cancella niente — il diritto
  dell'art. 17 resta sulla carta.
- **La riga in `auth.users`** va rimossa a parte con l'Admin API: da SQL non è raggiungibile.
  La funzione pseudonimizza i messaggi e cancella il profilo, ma l'utente auth resta.
- Il trigger di rate limit sta a **20 messaggi al minuto**. Se in beta risultasse stretto, si
  cambia in un punto solo (`enforce_message_rate_limit`).

### 2. Dominio `pkfamily.app`
Registralo su **Cloudflare Registrar** (prezzo di costo, WHOIS privacy inclusa).

**Prima di registrarlo**, verifica che il nome sia libero: [EUIPO eSearch](https://euipo.europa.eu/eSearch/),
[UIBM](https://www.uibm.gov.it/), più una ricerca di uso di fatto su Instagram e negli app
store. Una palestra che già usa "PK Family" può farti cambiare nome a QR stampati.

### 3. Branch `backup` sul remoto
Il fix di `📲/backup.mjs` esclude `profiles` dai backup **futuri**. Il branch `backup` oggi
online contiene ancora la versione vecchia con 2 profili (username, ruolo, flag `banned`).

Si rigenera da solo alla prossima corsa notturna (03:17 UTC). Per chiuderla subito: lancia a
mano il workflow **"📲 Backup quotidiano"** da Actions dopo aver mergiato, oppure cancella il
branch `backup` e lascia che lo ricrei.

### 4. Vecchi commit di `gh-pages` ancora raggiungibili per SHA
La storia è stata riscritta e l'IBAN non è più raggiungibile navigando il branch. Ma GitHub
conserva gli oggetti orfani ancora per un po': chi conosce lo SHA del vecchio commit
(`56dfa3d`) può aprirlo per URL diretto finché non passa la garbage collection, e lo stesso
vale per eventuali fork o cache.

Se vuoi chiudere anche quella finestra, apri una richiesta a **GitHub Support** chiedendo la
garbage collection degli oggetti irraggiungibili sul repository. Considerato che si tratta di
un IBAN già stampato su bonifici e non di una credenziale, la valutazione è tua — ma se il
conto ti preoccupa, cambiare IBAN è più definitivo di qualsiasi pulizia della storia.

### 4-bis. Lacune di schema che bloccano blocchi successivi
Emerse sondando le tabelle vuote. Nessuna è urgente oggi, tutte servono prima del lancio, e
tutte richiedono una migration da applicare con le tue credenziali:

| Tabella | Manca | Blocca |
| --- | --- | --- |
| `spot_photos` | `source`, `author`, `license`, `source_url` | BLOCCO 3-bis: Mapillary è CC-BY-SA e Wikimedia richiede attribuzione. Senza questi campi le foto **non sono pubblicabili**. |
| `videos` | `is_starter`, `order_index` | BLOCCO 5: il percorso "Inizia da qui" non è esprimibile. |
| `reports` | `spot_id`, `status`, `resolved_at`, `resolved_by` | BLOCCO 6: uno **spot pericoloso non è segnalabile**, e non c'è modo di documentare che una segnalazione è stata trattata (obblighi DSA). |
| `spots` | `completeness` | BLOCCO 3-bis: distinguere gli spot descritti dai segnaposto. |

### 5. Rollback del sito temporaneamente scoperto
`gh-pages` è stato ricreato come branch orfano per togliere l'IBAN dalla storia pubblica.
Conseguenza: lo **"Scenario C"** di [`../📲/README.md`](../📲/README.md) — «git revert su
gh-pages e il sito torna com'era» — non ha più una storia su cui tornare, finché non ci sono
almeno due deploy nuovi. Se l'anteprima si rompe adesso, va ricostruita, non revertita.

---

## 🟠 Prima del lancio pubblico

### 6. Revisione legale
**Questa è l'unica voce che non ammette scorciatoie.** Informativa privacy, Termini di
servizio, testo del gate di sicurezza e DPIA vanno rivisti da un professionista prima di
essere pubblici. I testi che genererà il BLOCCO 7 sono **bozze tecnicamente informate, non
consulenza legale**, e il titolare è una persona fisica con responsabilità illimitata sul
patrimonio personale.

Chiedi in particolare una lettura di:
- il testo del gate di sicurezza — deve essere **presa d'atto e assunzione del rischio**, mai
  esonero di responsabilità (una clausola nulla non protegge: vedi §5.7 del piano);
- la qualificazione del servizio come **informativo e non organizzativo**;
- il flusso di accesso tramite genitore.

I testi da far leggere, ora che esistono — cinque pubblici e quattro interni:

| File | Cosa è |
|---|---|
| `mobile/assets/legal/privacy.md` | Informativa artt. 13-14 |
| `mobile/assets/legal/termini.md` | Termini di servizio |
| `mobile/assets/legal/cookie.md` | Cookie e archiviazione locale |
| `mobile/assets/legal/note-legali.md` | Imprint, art. 7 d.lgs. 70/2003 |
| `mobile/assets/legal/sub-responsabili.md` | Elenco dei responsabili esterni |
| `docs/privacy/registro-trattamenti.md` | Registro art. 30 |
| `docs/privacy/dpia.md` | Valutazione d'impatto art. 35 |
| `docs/privacy/procedura-data-breach.md` | Procedura artt. 33-34 |
| `docs/privacy/lia-legittimo-interesse.md` | Test di bilanciamento per l'art. 6.1.f |

I quattro in `docs/privacy/` **non vanno pubblicati**: sono documentazione da tenere e
mostrare al Garante se la chiede, non pagine per gli utenti.

#### 6-bis. Il nome del titolare manca ancora
`note-legali.md` contiene il segnaposto `[nome e cognome — da completare prima della
pubblicazione]`. L'art. 7 del d.lgs. 70/2003 chiede che il prestatore sia identificabile:
**con quella parentesi quadra il sito non è a norma.** Non l'ho scritto io di proposito —
mettere un nome per conto tuo in una pagina di identificazione legale non è una cosa che
posso decidere.

`mobile/test/legal_texts_test.dart` lo segnala a ogni esecuzione dei test, senza fallire.
Quando lo completi, valuta se far diventare quel controllo un `expect`: da lì in poi un
ritorno al segnaposto sarebbe un errore, non un promemoria.

#### 6-ter. I testi sono solo in italiano — deviazione dal piano
Il piano (§5.2 e BLOCCO 7) chiedeva le pagine legali **in italiano e inglese**. Ne ho scritte
solo la versione italiana, e la scelta va confermata o ribaltata da te.

Il motivo: tutta l'interfaccia è in italiano, quindi oggi una versione inglese non
raggiungerebbe nessuno che non legga già l'italiano. Ma raddoppierebbe il costo della
revisione legale, e soprattutto **due versioni divergono**: una traduzione non revisionata
dell'informativa è un testo che afferma cose leggermente diverse dall'originale, in un
documento su cui l'utente ha diritto di fare affidamento. Peggio di non averlo.

Quando tradurre diventa dovuto: l'art. 12.1 chiede che l'informativa sia comprensibile
all'interessato, e la mappa ha 1.151 spot fuori dall'Italia. **Nel momento in cui l'app
prende una lingua in più, le pagine legali la prendono insieme a lei** — e la revisione
legale copre entrambe le versioni, non solo l'originale.

### 7. DPA e caselle email
- Accetta il **DPA di Supabase** (Dashboard → Settings → Legal) e quello di **Cloudflare**.
- Crea `privacy@pkfamily.app`, `abuse@pkfamily.app`, `security@pkfamily.app` e
  `info@pkfamily.app` (quest'ultima è il recapito dell'imprint in `note-legali.md`). Non usare
  la tua email personale: finiscono in pagine pubbliche.
- **Verifica adesso di poter accedere al portale del Garante con SPID o CIE.** Serve per
  notificare una violazione entro 72 ore, e scoprire che l'identità digitale è scaduta mentre
  il cronometro corre è il modo più stupido di arrivare tardi. La procedura è in
  `docs/privacy/procedura-data-breach.md`.

### 7-bis. Token Mapillary — è il passo che sblocca le foto
Registrati su [mapillary.com](https://www.mapillary.com/) e crea un token (gratuito), poi:

```sh
export MAPILLARY_TOKEN='MLY|...'
python3 scripts/enrich_spots.py --limit 50   # prova
python3 scripts/enrich_spots.py              # tutti, riprendibile
node scripts/spot_coverage.mjs               # quanto è cambiato
```

Mapillary è **immagine stradale alle coordinate**: mostra davvero il posto, ed è sotto
CC-BY-SA 4.0 con attribuzione — la sostituzione lecita degli hotlink a Street View.

Perché serve a te e non posso farlo io: **Overpass è irraggiungibile da questo ambiente**
(connessione resettata) e Nominatim risponde 429. Lo script gestisce rate limit e cache ed è
riprendibile, ma va lanciato da una rete normale. Su 1.700 spot conta un paio d'ore, in
background.

Una cosa provata sul campo e poi scartata: cercare foto su Wikimedia **per sola vicinanza**
restituiva una foto di cavi in fibra ottica e una chiesa bizantina, entrambe entro 150 m e
nessuna delle due attinente. Ora Wikimedia scatta solo se il nome del luogo combacia — quindi
di rado. Senza token Mapillary, le foto restano quelle che carica la community.

### 7-ter. Portare gli spot dentro Supabase
Oggi vivono in un file JSON nel repo. Il loro posto è il database: finché sono lì, nessun
utente può contribuire e ogni correzione richiede un deploy.

```sh
node scripts/import_spots_supabase.mjs --dry-run   # vedi cosa scriverebbe
SUPABASE_URL=https://<ref>.supabase.co \
SUPABASE_SECRET_KEY=sb_secret_... \
node scripts/import_spots_supabase.mjs
```

Serve la **secret key**: l'import scrive spot `community` che nessun client potrebbe
inserire, ed è giusto così. Da lanciare dal tuo PC, mai da una CI. È idempotente su
`external_id`: rilanciarlo aggiorna, non duplica. Applica prima le migration `0005` e `0006`,
che aggiungono le colonne che l'import scrive (`completeness`, `locality`, `country`,
provenienza delle foto).

### 8. Provenienza dei 1.706 spot
Il dataset in `scripts/data/webapp_fixed_spots.json` deriva da una lista Google Maps condivisa
(`scripts/fetch_gmaps_list.py`). I ToS di Google vietano lo scraping, e sulla lista come
*selezione* può gravare il diritto sui generis sulle banche dati (artt. 102-bis/ter L. 633/41).

Coordinate e nomi di luoghi pubblici non sono in sé proteggibili: il problema è la lista.
Va ricostruita da **OpenStreetMap** (ODbL, con attribuzione) e da segnalazioni della community.
Il BLOCCO 3 ripulisce le foto, ma **questa decisione è tua**.

### 8-bis. Cloudflare: progetti, DNS e i quattro secret
I workflow di deploy esistono e sono pronti; senza queste cose non partono.

**Due progetti Cloudflare Pages**, creati dal pannello (non serve collegare il repo: il deploy
lo fa il workflow con Wrangler):

| Progetto | Dominio | Chi ci entra |
| --- | --- | --- |
| `pkfamily` | `pkfamily.app` + `www.pkfamily.app` | tutti |
| `pkfamily-staging` | `staging.pkfamily.app` | solo tu, dietro Cloudflare Access |

Su `pkfamily-staging` metti una **policy Access** con la tua email (e quelle di chi provalo
con te). Senza, lo staging è un secondo sito pubblico con dati di prova dentro.

**DNS su Cloudflare**, oltre ai record dei due progetti:
- **CAA** — limita quali autorità possono emettere certificati per il dominio;
- **SPF `v=spf1 -all` e DMARC `v=DMARC1; p=reject;`** anche se non mandi posta. Senza,
  chiunque può spedire email che sembrano venire da `@pkfamily.app`, e le prime a riceverle
  sarebbero le persone iscritte all'app.

**Quattro secret** in GitHub → Settings → Secrets → Actions:

| Secret | Dove si prende |
| --- | --- |
| `SUPABASE_URL` | Dashboard Supabase → Project Settings → API |
| `SUPABASE_PUBLISHABLE_KEY` | stessa pagina — la **publishable**, non la secret |
| `CLOUDFLARE_API_TOKEN` | Cloudflare → My Profile → API Tokens, permesso *Cloudflare Pages: Edit* |
| `CLOUDFLARE_ACCOUNT_ID` | barra laterale della dashboard Cloudflare |

Il token Cloudflare va creato **con il solo permesso Pages**, non con quello globale: se
GitHub venisse compromesso, un token che sa solo pubblicare pagine è molto meno grave di uno
che può cambiare il DNS.

Nota su `SUPABASE_PUBLISHABLE_KEY` come secret: non è un segreto — finisce nel bundle e ce
l'hanno tutti. Sta lì solo perché è un valore di configurazione che cambia fra progetti.
`prepare_deploy.mjs` si rifiuta di pubblicare se il valore comincia per `sb_secret_`.

### 8-ter. Dependabot e CodeQL
`SECURITY.md` li dava per attivi da mesi. Non lo erano: nessun `.github/dependabot.yml`,
nessuna scansione nelle impostazioni del repository. Ora il file dice la verità («da
attivare»), e attivarli è un minuto:

- **Dependabot** — Settings → Code security → Dependabot alerts + security updates;
- **CodeQL** — stessa pagina, *Code scanning* → Set up → Default. Analizza JavaScript e
  Python; Dart non è fra i linguaggi supportati, quindi copre `web-admin/` e `scripts/`, non
  l'app.

### 9. Assicurazione
Valuta una polizza di responsabilità civile a tuo nome. E appena la community cresce o entra
del denaro, valuta il passaggio a **ASD/APS**: separa il patrimonio personale e dà accesso a
coperture pensate per lo sport. Protegge più di qualsiasi disclaimer.

### 10. ~~`SECURITY.md`~~ — fatto nel BLOCCO 8
Riscritto: l'indirizzo è `security@pkfamily.app` e i tempi sono quelli che una persona sola
può davvero tenere (una settimana per la presa in carico, non 48 ore). Sono sparite anche le
voci spuntate che descrivevano il backend FastAPI mai deployato — Argon2id, rotazione dei
refresh token, allowlist CORS — e che davano un'impressione di solidità che il sistema vero
non aveva.

Resta a te: **attivare davvero Dependabot e CodeQL** (§8-ter), che il vecchio file dava per
già attivi.

### 10-ter. Il redirect di gh-pages, al momento giusto
La pagina è pronta in `deploy/gh-pages/` e si pubblica con
`./scripts/publish_gh_pages_redirect.sh --fallo`.

**Non l'ho lanciato, e non va lanciato adesso.** Finché `pkfamily.app` non risponde,
`gh-pages` è l'unica versione raggiungibile dell'app: sostituirla vorrebbe dire mandare su una
pagina morta chiunque abbia il QR stampato. Lo script lo verifica da solo e si ferma con un
errore se il sito nuovo non risponde 200.

Da sapere prima: **GitHub Pages non può fare un 301 vero.** Il redirect HTTP lo decide il
server, e quel server non è nostro. La pagina usa `rel=canonical` (la parte che conta perché
i motori di ricerca non tengano in giro un doppione), un meta refresh e un link visibile.
Funziona, ma è meno di un 301 e va saputo.

Dopo averlo lanciato: lo «Scenario C» di `📲/README.md` — tornare indietro sul sito con un
`git revert` su `gh-pages` — non ha più una storia su cui tornare. Il rollback diventa
«ripubblica il tag precedente», che è comunque meglio.

---

## 🟡 Da decidere

### 10-bis. `sync-map.yml` è stato rimosso
Il workflow rigenerava i dati rifacendo lo **scraping della lista Google Maps** e poi patchava
il bundle su `gh-pages`. Il secondo passo puntava a uno script che non esiste più; il primo è
esattamente ciò che il BLOCCO 3-bis smette di fare. Se ti serviva per altro, dimmelo: va
riscritto, non ripristinato.

### 11. Video del percorso "Inizia da qui"
Le sette tappe sono scritte: titolo, descrizione e nota di sicurezza sono pronte e valgono
già da sole. **Mancano i video**, e li scegli tu:

```sh
# 1. apri scripts/data/starter_path.json
# 2. per ogni tappa incolla in `youtube_id` gli 11 caratteri dopo v= nell'URL
node scripts/seed_starter_path.mjs --check            # verifica
SUPABASE_URL=… SUPABASE_SECRET_KEY=… node scripts/seed_starter_path.mjs
```

Non li ho scelti io di proposito: non conosco id YouTube reali per queste tappe, e
inventarli avrebbe prodotto link morti o video che parlano d'altro — lo stesso dato finto
che abbiamo tolto dagli spot. Lo script verifica ogni id via oEmbed (esiste? come si chiama
davvero? chi l'ha fatto?) e **si rifiuta di caricare** ciò che non riesce a verificare.

Una nota che semplifica la scelta: oEmbed risponde solo per i video con l'incorporamento
abilitato, e quella impostazione è dell'autore. Se passa la verifica, l'autore ha già detto
di sì. In più noi non incorporiamo affatto: apriamo un link, che non richiede permesso.

Le tappe senza video restano visibili con «video in arrivo»: un percorso dichiaratamente
incompleto è più utile di uno che finge di esserlo.

### 12. Error tracking — si lancia senza, e questo è il perché
**Decisione presa nel BLOCCO 8, da confermare o ribaltare.** Nessun Sentry, nessuna
telemetria, nessun servizio terzo.

Il motivo non è il costo (Sentry ha un piano gratuito con region UE). È che aggiungere un
error tracker significa aggiungere **un responsabile del trattamento**: una riga nel registro
art. 30, una voce in `sub-responsabili.md`, un paragrafo nell'informativa, un DPA da firmare
e un altro posto dove finiscono dati che possono contenere frammenti di contenuto utente. Su
un progetto con tre fornitori in tutto, il quarto va giustificato.

Cosa costa la scelta, detto chiaramente: **quando l'app si rompe per qualcuno, non lo
sappiamo.** Non c'è un cruscotto, non c'è un alert, non c'è un conteggio. Lo sapremo se
qualcuno scrive.

Cosa c'è al posto suo:
- una schermata d'errore leggibile invece del rettangolo grigio, che dice a chi la vede di
  scrivere a `info@pkfamily.app` e cosa raccontare (`_SchermataErrore` in `main.dart`);
- gli errori 5xx e il traffico anomalo restano visibili nell'analitica di Cloudflare, che è
  già un nostro fornitore e non aggiunge niente;
- i log di Postgres in Supabase, per gli errori lato database.

**Quando ribaltarla:** se la community cresca abbastanza che «me lo dirà qualcuno» smette di
funzionare — indicativamente dalle poche centinaia di utenti attivi. A quel punto il candidato
giusto è **GlitchTip self-hosted** o Sentry in region UE con `sendDefaultPii: false`, e
l'informativa va aggiornata prima di accenderlo, non dopo.

### 12-bis. L'app pesa 31 MB, e il service worker se li porta giù tutti
Misurato al primo build di produzione. Il grosso è CanvasKit: 26 MB fra i tre motori di
rendering che Flutter include (`canvaskit.wasm`, `skwasm.wasm`, `skwasm_heavy.wasm`, più la
variante Chromium e i file `.symbols`).

Alla **prima apertura** il browser ne scarica una frazione: un motore solo, circa 10 MB fra
wasm e `main.dart.js`. Ma il service worker generato da Flutter, appena attivato, precarica
**l'intero pacchetto** per l'uso offline. Su un telefono in strada, con la rete che fa quello
che può, sono 31 MB non richiesti.

Le opzioni, in ordine di quanto costano:

1. **Lasciare così.** L'uso offline è un vantaggio reale per un'app che si apre davanti a un
   muro dove il campo non prende. Il download avviene in background, dopo il primo caricamento.
2. **`--pwa-strategy=none`** al build: niente service worker, niente precaricamento, niente
   offline. L'app resta installabile.
3. Un service worker scritto a mano che precarichi solo lo stretto necessario. È la soluzione
   giusta e la più costosa: va mantenuta a ogni aggiornamento di Flutter.

Il mio consiglio è la 1 finché non ci sono lamentele: l'offline vale quei megabyte, per
questa app più che per altre. Ma è una decisione, e va presa sapendo il numero.

**Da non fare mai:** cancellare i file `.symbols` dall'output per risparmiare 4 MB. Il service
worker li elenca fra le risorse, e uno che manca fa fallire l'attivazione — l'app smette di
funzionare offline senza dire perché.

### 12-ter. 🟠 Le foto Mapillary potrebbero scadere — da verificare col token
Emerso scrivendo la CSP, che deve elencare gli host da cui arrivano le immagini.

`scripts/enrich_spots.py` salva in `spot_photos.url` il campo `thumb_1024_url` restituito
dall'API Mapillary. Quegli URL stanno su una CDN di Meta e — per quanto ne so — sono
**firmati e a scadenza**: parametri `oh` e `oe` nella query, validi per un tempo limitato. Se
è così, le foto importate smetterebbero di caricarsi dopo qualche tempo, tutte insieme, senza
che nessuno tocchi niente.

Non ho potuto verificarlo: Mapillary non è raggiungibile da qui e serve un token. **Quando
lanci `enrich_spots.py` (§7-bis), guarda un URL restituito**: se contiene `oe=` e `oh=`, la
scadenza c'è.

Il rimedio, se confermato: l'id dell'immagine è già salvato dentro `source_url`
(`mapillary.com/app/?pKey=<id>`), quindi il thumb si può richiedere di nuovo al momento di
mostrarlo, oppure — meglio — scaricare l'immagine una volta e metterla in Supabase Storage,
il che risolve anche la CSP e la dipendenza da una CDN di Meta.

La CSP intanto elenca sia `images.mapillary.com` sia `*.fbcdn.net`, perché non so quale dei
due l'API restituisca. **Quando lo sai, togli quello che non serve** da
`deploy/_headers.template`: una riga in meno in `img-src` è una superficie in meno.

### 13. Backup completo settimanale
`📲/README.md` lo raccomanda 1×/settimana sul tuo PC, e non è automatizzabile (richiede la
secret key, che non deve stare in nessun CI). Mettilo in calendario.

### 13-bis. Il ripristino, provato almeno una volta
Lo «Scenario B» di `📲/README.md` non è un piano di ripristino finché nessuno l'ha eseguito:
è un file. La procedura è il §9 di [`COLLAUDO.md`](COLLAUDO.md) — progetto vuoto, migration,
ripristino, e **l'app fatta partire contro quel progetto**, perché «i dati ci sono» e «i dati
si usano» non sono la stessa cosa.

Segna quanto ci metti. È il numero che dice quanto dura un disastro, e serve saperlo prima
che serva.

### 14. Il collaudo a mano
[`COLLAUDO.md`](COLLAUDO.md) è la sequenza da provare su staging prima di mettere il tag: il
gate rifiutato, l'age gate, l'accesso del genitore, la chat con due account, l'export dei
dati, la cancellazione con i messaggi pseudonimizzati, e l'app aperta **da telefono in 4G**.

Due passaggi lì dentro non sono formalità e vale la pena anticiparli qui:

- **con il gate rifiutato, chiedi gli spot all'API a mano.** Deve tornare `[]`. È il controllo
  che ha trovato il buco del §0;
- **su un account supervisionato con la chat spenta, prova a scrivere via API.** Se passa, il
  vincolo è solo nell'interfaccia e non vale niente.

---

## 🔴 Da chiudere per prima: le segnalazioni sono leggibili da chiunque

Emerso sondando la produzione durante il BLOCCO 6, con la sola chiave pubblica:

```
GET  /rest/v1/reports?select=*   → HTTP 200
POST /rest/v1/reports            → 42501, la RLS rifiuta
```

La RLS è attiva, ma la policy di **lettura** è permissiva verso tutti. Oggi la tabella è
vuota e non è successo niente. Alla prima segnalazione di molestie, però, chi l'ha scritta e
cosa ha scritto sarebbero leggibili da chiunque abbia la chiave — **compresa la persona
segnalata**. Se segnalare espone chi segnala, nessuno segnala più, e il meccanismo di
notice-and-action dell'art. 16 DSA diventa una casella vuota.

Stessa lettura aperta su `post_saves` (cosa una persona ha salvato) ed `entitlements`.

La migration `0009` le chiude con policy RESTRICTIVE, che si combinano in AND con quelle
esistenti senza doverle conoscere. **Applicala prima di aprire le iscrizioni**, e poi verifica:

```sh
SUPABASE_URL=… SUPABASE_PUBLISHABLE_KEY=… node scripts/audit_rls.mjs
```

Una nota sull'audit: su una tabella vuota dichiara «non concludente», non «passato». È
esattamente per questo che il buco era passato inosservato — vuota, quindi apparentemente a
posto. Rilancialo quando ci saranno dati veri.

## Moderazione: due cose da schedulare

- `purge_old_moderation_events()` — il registro si conserva 12 mesi, poi va ripulito.
- Il ruolo `admin` resta assegnabile **solo a livello di database**: nessun percorso
  dell'applicazione lo concede, e la console lo esclude esplicitamente.
