# `app/` — PkFAMILY come applicazione, anche senza rete

Quello che il QR apriva era una pagina: un indirizzo nel browser, la barra in
alto, e la mano davanti agli occhi appena finisce il campo. Questa cartella è
la stessa cosa fatta diventare **un'applicazione**: si installa, ha la sua
icona, si apre a tutto schermo e **funziona in modalità aereo**.

- **Nata per il telefono.** Schermo verticale, barra in basso, aree da toccare
  di 44 px, niente che dipenda dal mouse. Su uno schermo largo non si allarga:
  resta nella sua cornice verticale, perché provarla dal PC deve mostrare
  quello che si vede in mano.
- **Il computer è il banco di prova.** `tools/desktop.py` la apre in una
  finestra a sé, formato telefono; `npm test` la mette alla prova, offline
  compreso.
- **Senza rete è la regola, non l'eccezione.** Gli spot, le fontanelle, il
  catalogo dei tutorial, i caratteri e tutta l'interfaccia sono già dentro:
  1,05 MB in tutto. La rete serve per le tessere di mappa che non hai ancora
  scaricato, per le foto e per i video.

## Provarla, subito

Serve **Python 3.14 o successivo** (`python3 --version`): è il pavimento del
repository, e gli strumenti di `tools/` lo danno per scontato. L'app in sé non
ha bisogno di niente.

```sh
python3 app/tools/desktop.py         # finestra formato telefono, server incluso
```

Oppure, se preferisci il tuo browser:

```sh
python3 app/tools/serve.py           # http://127.0.0.1:8080
```

> **`localhost` o `https`, non c'è una terza via.** I browser accendono il
> service worker — cioè l'offline — solo su indirizzi sicuri. Dal computer
> `127.0.0.1` lo è; da telefono, in Wi-Fi, `http://192.168.…` **no**.

### Dal telefono

| Come | Cosa serve | Offline |
| --- | --- | --- |
| Cavo USB + `chrome://inspect` → *Port forwarding* `8080 → localhost:8080` | il cavo | **sì** (sul telefono l'indirizzo è `http://localhost:8080`) |
| `python3 app/tools/serve.py --https` e accetti il certificato | stessa Wi-Fi | **sì**, dopo aver accettato l'avviso del browser |
| `python3 app/tools/serve.py` e apri l'indirizzo di rete | stessa Wi-Fi | no: si vede tutto, ma non si installa e non va offline |
| Pubblicata su GitHub Pages da `main` via CI | una persona che la pubblica | **sì** |

Per il QR con il tuo indirizzo:
`python3 scripts/make_qr.py "https://192.168.x.y:8080/" /tmp/pk.png`.

Una volta aperta: schermata **Tu → Installa l'app** (su iPhone: *Condividi →
Aggiungi alla schermata Home*). Da lì in poi è un'icona come le altre.

## Cosa c'è dentro

```
app/
  public/                 l'applicazione: si pubblica com'è, senza build
    index.html            il guscio e la schermata di avvio
    manifest.webmanifest  nome, icone, colori: è ciò che la rende installabile
    sw.js                 il service worker: guscio, dati e tessere offline
    precache.json         l'elenco dei file da tenere (generato)
    styles/pk.css         i token del masterplan, cap. 3.2–3.4
    build.json            da dove viene questa copia: sviluppo o beta
    js/                   moduli ES, nessuna dipendenza
      app.js              avvio, rotte, service worker, fascia di canale
      admin.js            modalità sviluppatore: sovrascritture locali ed export
      map.js              la mappa: tela, tessere, spilli, lino di riserva
      data.js store.js    dati che l'app porta con sé / dati che restano qui
      offline.js          stato delle cache e scarico delle tessere in anticipo
      route.js legal.js   distanze e percorsi / avviso sui rischi
      screens/            mappa, spot, scheda, tutorial, Tu, pannello sviluppatore
    data/                 spots.json, fountains.json, tutorials.json (generati)
    media/                i video degli spot: viaggiano dentro il pacchetto
    i18n/                 it.json, en.json — nessuna stringa nel codice
    fonts/ icons/         Fraunces e Karla (OFL), icone generate dal codice
  android/                il guscio Android: manifesto, risorse, la tela web
  mac/                    il guscio macOS: l'eseguibile del bundle e l'avviatore
  tools/                  build_data, build_precache, make_icons, fetch_fonts,
                          serve, desktop, screenshot, build_beta, build_demo,
                          build_demo_python, build_apk, build_mac_app, qr,
                          build_pubblica
  dist/                   le beta e le demo costruite (non versionate)
  demo/                   motore.py: la logica dell'app scritta in Python
  tests/                  prove Playwright: avvio, offline, installabilità
```

### Un video su uno spot

Le foto degli spot stanno su Wikimedia e senza rete non ci sono. Un video no:
il file viaggia dentro il pacchetto, quindi si vede anche in aereo. Per
aggiungerne uno:

1. porta il filmato in un formato che i browser sanno leggere — H.264 in un
   `.mp4`, non HEVC in un `.mov` — e tienilo corto e leggero:

   ```sh
   ffmpeg -i girato.mov -vf "scale=960:-2,fps=30" -c:v libx264 -profile:v main \
     -pix_fmt yuv420p -crf 26 -preset slow -c:a aac -b:a 64k -ac 1 \
     -movflags +faststart app/public/media/<nome>.mp4
   ffmpeg -ss 1.5 -i girato.mov -frames:v 1 -vf scale=960:-2 -q:v 4 \
     app/public/media/<nome>.jpg          # la locandina
   ```

2. aggiungi i due campi allo spot **nella fonte**,
   `scripts/data/webapp_fixed_spots.json` (non in `app/public/data/`, che è
   generato):

   ```json
   "video": "media/<nome>.mp4", "videoPoster": "media/<nome>.jpg"
   ```

3. `python3 app/tools/build_data.py` e poi `python3 app/tools/build_precache.py`.

Il video entra nell'elenco offline, quindi pesa su ogni copia: l'APK passa da
0,8 a 1,2 MB per cinque secondi. Nella demo in un file solo il filmato non c'è
— lì dentro non c'è posto per i file accanto — e la scheda lo nasconde invece
di lasciare un riquadro vuoto.

### Rigenerare ciò che è generato

```sh
python3 app/tools/build_data.py        # spot, fontanelle, tutorial dalle fonti del repo
python3 app/tools/make_icons.py        # le icone, dai colori del design system
python3 app/tools/fetch_fonts.py       # i caratteri (serve rete, una volta sola)
python3 app/tools/build_precache.py    # l'elenco offline + la versione
```

Ognuno accetta `--check`: non scrive e fallisce se il file non è aggiornato.
`build_precache.py` va **sempre per ultimo**: la versione è l'impronta di
tutti gli altri file, ed è quella che dice al service worker di riscaricare.

### La mappa sotto le dita

Un dito trascina, due pizzicano, due tocchi nello stesso punto avvicinano.
Dove gli spilli si accavallerebbero c'è un gomitolo con il numero: toccandolo
la mappa si avvicina finché non si sfila, e nessuno spot sparisce in silenzio.

Toccato uno spillo, dal basso sale la scheda dello spot. Ha due altezze e una
maniglia vera: si trascina su per leggere la descrizione intera e l'acqua
vicina, giù per tornare all'essenziale, ancora giù per chiuderla. La maniglia
è un bottone, quindi con il tasto Tab ci si arriva e con Invio si alza e si
abbassa; `aria-expanded` dice com'è messa.

La tela è un disegno, non ha nodi da leggere: quello che succede lì dentro —
lo spot scelto con il suo stato e la distanza, la scheda chiusa, il gomitolo
aperto — viene detto in `#pk-annuncio`, una regione `aria-live` gentile
(`annuncia` in `js/ui.js`). Con il tasto Tab si entra anche nella tela: le
frecce spostano, `+` e `−` cambiano lo zoom.

### Le prove

```sh
cd app && npm install && npm test
```

Coprono: l'avvio e la navigazione, la ricerca, l'avviso sui rischi che compare
una volta sola, i filtri, **la ricarica a rete staccata**, la mappa (colori del
masterplan, gomitoli che contano, trascinamento lento, doppio tocco, pizzico,
filtro chiaro e scuro, le due altezze della scheda, l'annuncio della scelta),
il manifest e le icone, il fatto che nelle cache non finisca niente che
riguardi una persona, la fascia della beta e la modalità sviluppatore
(compreso il rifiuto di una chiave segreta).

Dove Playwright non può scaricare il proprio Chromium:
`PK_CHROMIUM=/percorso/di/chrome npm test`.

## La beta da provare sul computer

```sh
python3 app/tools/build_beta.py --zip
```

Ne esce una cartella che sta in piedi da sola in `app/dist/` (1,1 MB; 0,4 MB
zippata): dentro c'è l'app, un `avvia.py` che non chiede niente al repository e
un LEGGIMI con cosa provare per prima cosa. Si copia su un'altra macchina, si
lancia `python3 avvia.py`, e l'app si apre in una finestra formato telefono.

La copia porta `build.json` con canale `beta`: l'app se ne accorge e mette in
testa la fascia **BETA** con la versione, così nessuno confonde una prova con
il prodotto. Da «Tu → Avanzate» c'è **Segnala un problema**, che mette in coda
sul dispositivo cosa stavi facendo, dove eri e che schermo hai.

L'elenco dei file da tenere offline viene ricalcolato sulla copia: la versione
del service worker è l'impronta di *quei* file, e cambia a ogni beta.

## La demo in un file solo

```sh
python3 app/tools/build_demo.py
```

`app/dist/pkfamily-demo.html`: 1,16 MB, **un file**. Niente da scompattare,
niente da installare, nessun server — si apre con un doppio clic e dentro c'è
tutto: interfaccia, codice, caratteri e i dati veri (1.706 spot, le fontanelle,
i 124 tutorial). La rete serve solo per le tessere della mappa che non hai già
visto, per le foto e per i video.

È il modo più corto per far provare l'app a qualcuno: si manda il file.

Come ci sta tutto dentro: l'app è fatta di moduli ES che si chiamano fra loro e
leggono i dati con `fetch`, e da `file://` nessuna delle due cose funziona.
`build_demo.py` mette i moduli in un registro (uno dentro l'altro, ognuno nel
suo ambito) e i dati in `globalThis.__PK_INLINE__`, che `data.js`, `i18n.js` e
`app.js` sanno già leggere. I caratteri diventano indirizzi `data:`.

Quello che la demo non ha, rispetto alla beta: il service worker — da `file://`
non esiste — quindi niente «prepara quest'area» e niente aggiornamenti. La
schermata «Tu» lo dice invece di fingere una cache che non c'è.

## La demo con il motore in Python

```sh
python3 app/tools/build_demo_python.py --cartella ~/Desktop
```

Ne esce **un solo file `.py`** (0,5 MB) da mettere sul desktop. Si apre con un
doppio clic: parte un server locale, si apre una finestra formato telefono, e
a cercare fra 1.706 spot è **Python, non il browser**.

```sh
python3 pkfamily-demo.py              # apre la demo in una finestra
python3 pkfamily-demo.py --installa   # mette l'icona sul desktop
python3 pkfamily-demo.py --api        # solo il motore, senza finestra
```

Il motore è `app/demo/motore.py`: riquadro visibile, ricerca, spot vicini con
distanza e tempi a piedi, fontanelle di uno spot, catalogo dei tutorial. L'app
glielo chiede via `/api/…` perché `build.json`, dentro il pacchetto, dice
`"motore": "/api"`; senza quella riga l'app fa tutto da sé come sempre.

| Domanda | `/api/…` |
| --- | --- |
| chi c'è nel riquadro (e le fontanelle intorno) | `/riquadro?nord&sud&ovest&est` |
| chi corrisponde a una ricerca, ordinato per vicinanza | `/cerca?q&lat&lng&verificati&fontanella&livello` |
| gli spot più vicini a un punto, con i tempi a piedi | `/vicini?lat&lng&quanti` |
| uno spot e le sue fontanelle | `/spot/<id>` |
| il catalogo filtrato | `/tutorial?livello&categoria` |

**Non è un backend di prodotto.** Le regole del prodotto stanno in Supabase
(AGENTS.md, regola 3): qui non c'è nessuna regola nuova, nessuna scrittura,
nessun account — c'è la stessa lettura che l'app fa da sola, spostata dove la
si può guardare e misurare. Se il motore tace, l'app torna a rispondere da
sola: c'è una prova che stacca `/api` e verifica che la ricerca funzioni
lo stesso.

## L'APK, e il QR che lo porta sul telefono

```sh
python3 app/tools/build_apk.py     # app/dist/pkfamily-<versione>.apk
python3 app/tools/qr.py            # lo serve, e mostra il QR da inquadrare
```

`build_apk.py` produce un **APK vero** (0,8 MB), firmato e installabile. Dentro
non c'è un'app riscritta in Java: c'è **questa** app, quella di `app/public/`,
con il suo service worker e i suoi 1.706 spot. Il guscio Android
(`app/android/`) è una tela web a tutto schermo che se li prende da dentro il
pacchetto.

Un dettaglio che decide se funziona o no. I file dell'app non arrivano da
`file://` — da lì i moduli, `fetch`, IndexedDB e il service worker non
funzionano — e nemmeno da un server locale su una porta a caso, perché la
porta fa parte dell'origine e cambierebbe a ogni avvio, portandosi via
preferenze, spot messi da parte e tessere scaricate. Arrivano intercettando
le richieste a `https://appassets.androidplatform.net/`, il nome che Android
riserva proprio a questo: non esiste in rete, e per il browser è un'origine
sicura, quindi il service worker può registrarsi. Le richieste che il service
worker fa per conto suo passano da un cliente a parte (`ServiceWorkerClient`):
senza quello, l'offline non si preparerebbe.

Si compila **senza Gradle e senza rete**, con gli strumenti che stanno già
nell'SDK: `aapt2`, `javac`, `d8`, `zipalign`, `apksigner`. Servono un SDK di
Android (`ANDROID_HOME`) e un JDK 17 o più recente.

**La firma è di prova.** Senza `--keystore`, il pacchetto viene firmato con una
chiave generata in `app/dist/`, che non entra nel repository e non vale niente:
serve solo perché Android non installa un APK non firmato. La chiave vera di
pubblicazione è di una persona, non di uno script (AGENTS.md, regola 6). Per
questo l'app porta in testa la fascia «APK DI PROVA».

`qr.py` fa il resto: trova l'indirizzo di questo computer sulla rete di casa,
serve l'APK, e disegna il QR — a schermo con i colori giusti, e in
`app/dist/pkfamily-qr.png` e `.svg`. Il telefono lo inquadra, si apre una
pagina che avvia il download e spiega i due tocchi per installare. Non passa
da internet: il file va dal computer al telefono sulla stessa rete Wi-Fi.

Il QR è disegnato lì dentro, senza librerie da installare (modo byte,
correzione M, versioni 1–9). `python3 app/tools/qr.py --prova` ne controlla
l'impronta e la struttura; i disegni da cui vengono le impronte sono stati
riletti da un decodificatore indipendente, non solo confrontati con sé stessi.

### Solo guardare, senza installare

```sh
python3 app/tools/qr.py --app                  # QR → l'app nel browser del telefono
python3 app/tools/qr.py --app '#/spot/<id>'    # aperta dritta su uno spot
python3 app/tools/qr.py --app --https          # e con l'offline acceso
```

Serve i file di `app/public/` sulla rete di casa e disegna il QR: il telefono
lo inquadra e apre l'app, senza installare niente. È il giro più corto per
guardare una modifica sul telefono vero.

### Passo passo

1. Telefono e computer **sulla stessa Wi-Fi**.
2. `python3 app/tools/build_apk.py` (la prima volta) e poi `python3 app/tools/qr.py`.
3. Il QR compare nel Terminale, con sotto l'indirizzo. Se la finestra è stretta,
   apri `app/dist/pkfamily-qr.png`.
4. Inquadralo con la fotocamera: nessuna app da installare.
5. Il download parte da solo; apri il file, concedi il permesso, **Installa**.
6. **Ctrl+C** quando hai finito.

Se qualcosa non torna — rete ospite, firewall del Mac, indirizzo che comincia
per `127.` — la tabella dei casi sta in
[`docs/APP_OFFLINE.md`](../docs/APP_OFFLINE.md).

## PkFAMILY.app: provarla sul Mac

```sh
python3 app/tools/build_mac_app.py --cartella ~/Desktop
python3 app/tools/build_mac_app.py --apk ~/Downloads/pkfamily-0.1.0-apk.20260921.apk
python3 app/tools/build_mac_app.py --zip     # il pacchetto da passare
```

Un APK non gira su un Mac. Quello che si può fare è **aprirlo e mettere nel
bundle i file che ci stanno dentro** — è quello che fa questo strumento,
verificandoli per impronta uno per uno. Sul Mac si prova la stessa app che si
installa sul telefono, byte per byte; resta fuori solo il guscio Android, che
solo un telefono può far girare. La fascia in testa dice **APK DI PROVA** con
la versione dell'APK da cui viene, o **APP DI PROVA** se il bundle è stato
costruito dai sorgenti perché un APK non c'era.

Il bundle sta in piedi da solo: `Contents/Resources/app` è l'applicazione,
`Contents/Resources/avvia.py` la accende su `127.0.0.1` (l'offline si attiva
solo su `localhost` o `https`: da `file://` non funzionerebbe niente), e
`Contents/MacOS/PkFAMILY` trova il Python 3 del Mac — va bene qualunque
versione dalla 3.9 in su, perché l'avviatore del bundle resta compatibile
all'indietro apposta: su quel Mac la versione non la scegliamo noi. macOS non
porta più un Python di serie: se manca, compare una finestra che lo dice.

Uno `.zip` scaricato da internet arriva in quarantena: la prima volta si apre
con **tasto destro sull'app → Apri**. Costruirlo sul proprio Mac evita la
faccenda.

## La demo a un indirizzo pubblico, con accessi veri

```sh
python3 app/tools/build_pubblica.py --supabase-url https://<progetto>.supabase.co \
    --supabase-key sb_publishable_...
```

Prepara in `app/dist/pubblica/` la cartella da servire: file statici, niente
da installare. È la stessa app, con due differenze — porta l'indirizzo del
progetto Supabase e la sola chiave pubblicabile, e mette in testa la fascia
**DEMO PUBBLICA**.

Servita da un indirizzo `https`, quell'app cambia natura: si installa sulla
schermata Home, funziona offline (il service worker si accende solo su
contesto sicuro), e **ci si entra davvero** — codice via email o ingresso
come ospite, con account veri in `auth.users`. Essendo file statici, cento
telefoni insieme non si accorgono l'uno dell'altro.

Due strade per metterla online, e mettere l'app online è comunque una scelta
di una persona:

- **un host statico esterno** (Cloudflare Pages, Netlify): comando di
  costruzione `python3 app/tools/build_pubblica.py --cartella sito`, cartella
  `sito`, le due variabili di Supabase. Non tocca niente di quello che è già
  pubblicato, ed è il motivo per cui `build_pubblica.py` gira anche sulla 3.11
  di quelle immagini;
- **`.github/workflows/pubblica-demo.yml`**, a mano e solo da `main`. Funziona,
  ma sostituisce il sito servito oggi da `gh-pages` e zittisce `sync-map.yml`,
  che su quel branch scrive.

I passi, in ordine, con le impostazioni da mettere nel progetto Supabase:
[`docs/DEMO_PUBBLICA.md`](../docs/DEMO_PUBBLICA.md).

Il QR, una volta che l'indirizzo esiste:

```sh
python3 app/tools/qr.py --indirizzo https://<utente>.github.io/<repo>/
```

Una chiave che sembra segreta (`sb_secret`, `service_role`, un JWT) ferma la
costruzione: pubblicarla vorrebbe dire consegnare a chiunque il potere di
scrivere nel database, e una volta online non la si riprende più.

## La modalità sviluppatore

«Tu → Avanzate → Accendi la modalità sviluppatore». Compare una fascia ambra in
testa; toccandola si apre il pannello (`#/admin`).

**Il pannello non ha uno schema scritto a mano.** I campi di una collezione li
deduce dai dati che ci sono; le impostazioni sono le foglie di
`js/config.js`. Aggiungere un campo a `build_data.py` lo fa comparire qui
senza toccare una riga del pannello — ed è il motivo per cui le impostazioni
correggibili sono ventiquattro invece delle undici che qualcuno aveva elencato
a mano.

Cinque sezioni, che si aprono e si chiudono:

- **Stato dell'app**: chi sta rispondendo alle domande (l'app o il motore in
  Python, e perché), quante voci ha ogni collezione e quante ne sono toccate,
  cosa c'è in cache, quanto spazio si occupa, se il browser ha promesso di non
  buttarlo via — e il pulsante per chiederglielo;
- **Dati**, una collezione alla volta: **spot**, **tutorial** e **fontanelle**
  (in sola lettura: non hanno una chiave propria, si correggono su
  OpenStreetMap). Si cerca, si corregge, si crea, si toglie, si ripristina —
  anche un campo solo, con «Riporta al file». Sotto i campi noti c'è
  l'**ispettore**: le chiavi che lo schema non conosce si vedono, si
  modificano e se ne aggiungono. Si può segnare una voce **da rivedere** con
  il motivo, senza cambiarle niente;
- **Configurazione**: tutte le foglie di `CONFIG`, raggruppate dal percorso
  vero (`tiles`, `routing`, `supabase`, `filtroTessere`, `partenza`,
  `andature`, e `altre` per le chiavi di primo livello). Le due che fanno
  **uscire dati dal dispositivo** — `motore` e `routing.servizio` — lo dicono
  con un avviso fisso;
- **Magazzino di questo dispositivo**: i quattro depositi (`kv`, `preferiti`,
  `note`, `coda`) con chiavi e valori. Si guarda e si cancella; in `note`,
  `preferiti` e `coda` **non** si crea, perché sarebbe fabbricare il contributo
  di una persona. Niente di tutto questo entra in un file esportato: lì dentro
  c'è anche `mappa.vista`, cioè dove è stata una persona;
- **Esporta e importa**: un JSON con tutte le modifiche, e un secondo file con
  i soli spot da rivedere già nei nomi di campo di
  `scripts/data/webapp_fixed_spots.json`.

Prima di salvare, quando c'è qualcosa da dire, compare un riquadro che dice
**cosa ne farà l'app** di quei valori — uno stato che nessuna schermata
conosce, un livello senza traduzione, coordinate fuori intervallo — e offre
«Salva lo stesso». Avvisa solo su quello che è **cambiato**: un avviso che
compare sempre è un avviso che non si legge più.

Tre cose che il pannello non fa, e lo dice in testa a sé stesso:

1. **non pubblica niente**: le modifiche restano sul dispositivo finché non le
   esporti, e a portarle nel repository è una persona (principio 5);
2. **non finge**: ogni voce toccata o creata porta il segno «locale» — spot e
   tutorial — e gli spot nuovi nascono `pending`. Verificato lo diventa uno
   spot quando una persona lo verifica (principio 2);
3. **non accetta chiavi segrete**: il rifiuto vale su **ogni** scrittura, non
   solo sulla casella della publishable key — un campo di uno spot, una voce
   del magazzino, un file importato (principio 4).

L'indirizzo `#/admin` da solo non basta: senza aver acceso la modalità porta a
«Tu». Non è una difesa — è un'app che gira sul telefono di chi la usa — ma
evita di darsi i poteri per sbaglio.

## Le regole rispettate qui dentro

- **Niente contenuti finti** (principio 1). L'app mostra dati che esistono già
  nel repository e non ne inventa. I 1.680 spot importati restano marcati
  `community` e la scheda lo dice: verificato lo diventa quando una persona lo
  verifica, non quando lo decide un file.
- **Nessun segreto** (principio 4): `js/config.js` nasce senza chiavi. Finché
  `supabase.url` è vuoto l'app è completamente locale.
- **La posizione non esce dal telefono** (principio 3): distanze e ordinamenti
  si calcolano qui. L'unica uscita possibile è il calcolo di un percorso, che
  si chiede a mano e parte arrotondato a ~110 m — la stessa regola del
  servizio in `remote-service/`.
- **Un solo linguaggio visivo** (principio 6): i colori, i caratteri e le
  misure sono quelli del masterplan, capitolo 3.

## Da dove vengono i dati

| File | Fonte |
| --- | --- |
| `data/spots.json` | `scripts/data/webapp_fixed_spots.json` (26 verificati + 1.680 importati dalla lista Google Maps condivisa) |
| `data/fountains.json` | `scripts/data/spot_fountains.json`, da OpenStreetMap (ODbL) |
| `data/tutorials.json` | `backend/seeds/videos.json` |
| tessere di mappa | OpenStreetMap e Esri World Imagery, scaricate dal dispositivo |
| caratteri | Fraunces e Karla, SIL OFL 1.1 — vedi `public/fonts/LICENSE.md` |

## Cosa non fa ancora

Sta scritto qui perché non sembri un'omissione:

- **non c'è l'accesso** con email e codice: l'app funziona senza account, e i
  contributi scritti offline restano in coda sul dispositivo finché non sarà
  collegata a Supabase;
- **non c'è la chat, non c'è la community**: quelle vivono online;
- **i video dei tutorial** si guardano su YouTube, quindi con la rete: offline
  restano titolo, livello, durata e canale;
- **non sostituisce la build Flutter** pubblicata su `gh-pages`: le sta
  accanto. I sorgenti di quella build non sono su `main` (masterplan 1.4), ed
  è la ragione per cui questa applicazione nasce come cartella a sé invece che
  come una modifica a quella.
