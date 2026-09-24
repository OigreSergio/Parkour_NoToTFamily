# La demo a un indirizzo pubblico

Come si arriva a un link — e a un QR — che apre PkFAMILY su un telefono
qualunque, con accessi veri e più persone dentro insieme.

Tre pezzi, e due sono già fatti:

| Pezzo | Stato | Chi lo fa |
| --- | --- | --- |
| L'app sa entrare davvero (codice via email, ospite, sessione) | **fatto**, `app/public/js/auth.js` | — |
| La copia da servire si prepara da sola | **fatto**, `app/tools/build_pubblica.py` | — |
| L'indirizzo pubblico esiste | **da fare** | una persona: vedi il capitolo 3 |

Il terzo pezzo non è dimenticanza né pigrizia. AGENTS.md regola 6:

> Tutto ciò che va online nasce da `main` tramite CI: niente build a mano,
> niente push su `gh-pages`, niente modifiche al progetto Supabase di
> produzione, niente rotazione di chiavi reali. Quelle le fa una persona.

Qui sotto c'è tutto quello che serve perché quella persona ci metta dieci
minuti.

---

## 1. Subito, senza niente online: il telefono sulla rete di casa

Funziona adesso, senza decidere niente:

```sh
python3 app/tools/qr.py --app
```

Serve `app/public/` sulla rete locale e disegna il QR nel terminale. Il
telefono lo inquadra e apre l'app. Più telefoni insieme vanno bene: il server
è a thread (`ThreadingHTTPServer`), non fa i turni.

Due limiti, e sono il motivo per cui questo non basta:

- **solo chi è sulla stessa rete.** Un amico a casa sua non entra;
- **è `http://`, non `https://`.** Il service worker non parte — niente
  offline, niente installazione sulla schermata Home — e gli accessi
  viaggerebbero in chiaro. `--https` mette un certificato fatto in casa: il
  telefono mostra un avviso rosso e bisogna forzare. Si può fare per una
  prova, non per far provare l'app a qualcuno.

Per il resto — offline vero, installazione, accessi — serve un indirizzo
`https` pubblico.

## 2. Che cosa succede quando l'indirizzo c'è

La stessa app, servita da `https://…`, cambia natura:

- **si installa.** Chrome offre «Installa app», iPhone «Aggiungi alla schermata
  Home». Da lì è un'icona come le altre.
- **funziona offline.** Il service worker si accende solo su contesto sicuro:
  aperta una volta con la rete, l'app riparte anche in aereo.
- **si entra davvero.** Con l'email si riceve un codice e si entra; in
  alternativa si entra come ospite. Gli account sono righe vere in
  `auth.users`, con la loro riga in `public.profiles` creata dal trigger
  (migrazione `0001`, poi `0004` per gli ospiti). Nessun account finto:
  AGENTS.md regola 1.
- **regge il traffico simultaneo.** I file sono statici, li serve una CDN:
  cento telefoni insieme non si accorgono l'uno dell'altro. Gli accessi li
  regge Supabase. Non c'è niente in mezzo che faccia i turni.

Una cosa da sapere sul «simultaneo»: **una sessione per dispositivo**. Il
gettone di rinnovo ruota a ogni uso, quindi due telefoni sullo stesso account
se lo strappano di mano a vicenda e uno dei due si ritrova fuori. Per far
provare l'app a dieci persone servono dieci accessi — dieci email, o dieci
ingressi come ospite — non un account passato in giro.

## 3. Metterla online — i passi, in ordine

### 3.1 La scelta che va fatta prima: dove

Il flusso `.github/workflows/pubblica-demo.yml` pubblica su **GitHub Pages**
usando l'origine «GitHub Actions».

⚠️ **Questo sostituisce il sito servito oggi dal branch `gh-pages`**, che
contiene la web app Flutter (`/t/<id>/`), la pagina di prova dell'accesso
(`/t/prova-accesso/`), il catalogo dei tutorial e le schede degli spot. Il
branch non viene toccato — nessuno ci scrive, resta leggibile con
`git show origin/gh-pages:<file>` — ma smette di essere quello pubblicato.
Per tornare indietro si rimette «Deploy from a branch» a mano.

Se quella roba deve restare online, **non usare questo flusso**: la stessa
cartella prodotta da `build_pubblica.py` si serve da qualunque host statico
(Cloudflare Pages, Netlify, un secondo repository con le sue Pages). Il
flusso cambia solo negli ultimi due passi; il resto di questo documento vale
identico.

### 3.2 Il progetto Supabase

Serve un progetto con le migrazioni applicate. Ce n'è già uno in piedi —
quello che regge la pagina di prova dell'accesso su `gh-pages` — ma **puntarci
la demo pubblica è una decisione, non un dettaglio**: da quel momento chi apre
il link si iscrive lì, e sono righe vere nel database vero. L'alternativa è un
secondo progetto Supabase per l'anteprima, che è anche quello che AGENTS.md
regola 1 presuppone («i dati sintetici stanno solo in un ambiente di
anteprima»).

Deciso quale, nel suo pannello:

| Dove | Cosa |
| --- | --- |
| SQL Editor | le migrazioni `supabase/migrations/0001` → `0004`, in ordine |
| Authentication → Providers → Email | acceso |
| Authentication → Providers → Anonymous sign-ins | acceso, se si vuole l'ingresso come ospite |
| Authentication → Emails → Magic Link | il corpo deve contenere `{{ .Token }}`: l'app chiede **un codice**, non un collegamento |
| Authentication → URL Configuration → Site URL | l'indirizzo pubblicato |
| Settings → API Keys | copiare la chiave **pubblicabile** (`sb_publishable_…`) |

Sulla chiave: quella pubblicabile è fatta per stare in un client e le RLS
restano in piedi (AGENTS.md regola 2). La vecchia chiave `anon` in forma di
JWT è pubblicabile anche lei, ma da fuori è **indistinguibile** dalla
`service_role`, che invece scavalca ogni regola: per questo sia
`build_pubblica.py` sia `app/public/js/ispettore.js` la rifiutano. Se il
progetto ha solo quella vecchia, se ne genera una nuova dal pannello.

### 3.3 Le variabili del repository

Settings → Secrets and variables → Actions → **Variables** (non Secrets: la
chiave pubblicabile finisce comunque dentro la pagina, e un valore che deve
essere pubblico messo fra i segreti fa solo credere che sia protetto):

```
PUBBLICA_DEMO            = si
SUPABASE_URL             = https://<progetto>.supabase.co
SUPABASE_PUBLISHABLE_KEY = sb_publishable_...
```

Senza i due valori di Supabase la demo si pubblica lo stesso, ma resta quella
locale: si guarda, non si entra.

`PUBBLICA_DEMO` è il secondo interruttore. Il primo è premere il pulsante, e i
pulsanti si premono per sbaglio; questo flusso sostituisce un sito.

### 3.4 Pages

Settings → Pages → Source: **GitHub Actions**.

### 3.5 Il pulsante

Actions → «Pubblica la demo» → Run workflow, da `main`.

Il flusso, in ordine: controlla i due interruttori, controlla che i file
generati siano aggiornati (pubblicare dati vecchi è peggio che non pubblicare:
nessuno se ne accorge), prepara la cartella, **rilegge i file veri cercando
chiavi segrete**, e solo allora carica.

Alla fine, nel riepilogo della corsa, c'è l'indirizzo.

### 3.6 Il QR

```sh
python3 app/tools/qr.py --indirizzo https://<utente>.github.io/<repo>/
```

Disegna il QR nel terminale e lo salva come PNG. Da inquadrare con la
fotocamera: niente app da scaricare, niente APK, niente avvisi di sicurezza.

---

## 4. Provare la stessa cosa prima di pubblicarla

```sh
python3 app/tools/build_pubblica.py \
    --cartella /tmp/sito \
    --supabase-url https://<progetto>.supabase.co \
    --supabase-key sb_publishable_...
python3 -m http.server --directory /tmp/sito 8080
```

Su `http://localhost:8080` il service worker parte lo stesso (localhost è
contesto sicuro per il browser), quindi si prova tutto: installazione,
offline, accesso vero. È la copia identica a quella che andrebbe online.

Per provarlo dal telefono senza pubblicare, `qr.py --app` serve `app/public/`,
non questa cartella: lì dentro non c'è `build.json` con Supabase. Il modo
onesto di provare l'accesso dal telefono è pubblicare.

## 5. Che cosa **non** fa tutto questo

- **Non mette in produzione niente.** La demo è marcata: fascia «DEMO
  PUBBLICA» in testa a ogni schermata, e gli spot non verificati restano
  marcati `community`. AGENTS.md regola 3: solo gli spot verificati sono
  pubblici.
- **Non crea account.** Li creano le persone che entrano. Nessuno script,
  nessun seed, nessun job scrive in `auth.users` (regola 1).
- **Non cambia il progetto Supabase.** Le impostazioni del capitolo 3.2 le
  mette una persona, a mano, dal pannello (regola 6).
- **Non porta la posizione da nessuna parte.** Resta sul dispositivo, e quella
  che parte verso il servizio dei percorsi è arrotondata a tre decimali
  (~110 m) prima di uscire (regola 4).

## 6. Dove sta ogni cosa

| File | Cosa |
| --- | --- |
| `app/public/js/auth.js` | il client di Supabase Auth: codice via email, ospite, rinnovo, uscita |
| `app/public/js/screens/you.js` | la sezione «Account» |
| `app/public/js/config.js` | `supabase: {url, publishableKey}`, vuoti nel repository |
| `app/tools/build_pubblica.py` | prepara la cartella da servire |
| `.github/workflows/pubblica-demo.yml` | la mette online, a mano, solo da `main` |
| `app/tests/accesso.spec.mjs` | le prove: codice sbagliato, rete che cade, gettone revocato, chiave segreta |
| `supabase/migrations/0001…0004` | profili, ruoli, informative, ospiti anonimi |
| `docs/AUTENTICAZIONE.md` | il flusso dell'accesso nel dettaglio |
| `docs/APP_OFFLINE.md` | l'app installabile, l'APK, il Mac, il QR sulla rete di casa |
