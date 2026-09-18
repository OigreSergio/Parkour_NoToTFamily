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
    i18n/                 it.json, en.json — nessuna stringa nel codice
    fonts/ icons/         Fraunces e Karla (OFL), icone generate dal codice
  tools/                  build_data, build_precache, make_icons, fetch_fonts,
                          serve, desktop, screenshot, build_beta, build_demo
  dist/                   le beta e le demo costruite (non versionate)
  tests/                  prove Playwright: avvio, offline, installabilità
```

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

### Le prove

```sh
cd app && npm install && npm test
```

Coprono: l'avvio e la navigazione, la ricerca, l'avviso sui rischi che compare
una volta sola, i filtri, **la ricarica a rete staccata**, la mappa (colori del
masterplan, gomitoli che contano, trascinamento lento, doppio tocco, pizzico,
filtro chiaro e scuro), il manifest e le icone, il fatto che nelle cache non
finisca niente che riguardi una persona, la fascia della beta e la modalità
sviluppatore (compreso il rifiuto di una chiave segreta).

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

## La modalità sviluppatore

«Tu → Avanzate → Accendi la modalità sviluppatore». Compare una fascia ambra in
testa; toccandola si apre il pannello (`#/admin`). Da lì, senza aprire un
editor:

- **spot**: cercarli, correggerne nome, descrizione, stato, livello,
  affollamento, fontanella e coordinate; prenderne il punto dal centro della
  mappa; crearne di nuovi; toglierne; ripristinare quello che dice il file;
- **mappa e tessere**: provare dal vivo un altro filtro di colore (chiaro e
  scuro), un'altra sorgente di tessere, il lato della cella dei gomitoli, lo
  zoom da cui compaiono le fontanelle;
- **collegamenti**: l'indirizzo del servizio dei percorsi, le cifre con cui la
  posizione parte dal telefono, Supabase;
- **esporta / importa**: un JSON con tutte le modifiche, e un secondo file con
  i soli spot da rivedere già nei nomi di campo di
  `scripts/data/webapp_fixed_spots.json`.

Tre cose che il pannello non fa, e lo dice in testa a sé stesso:

1. **non pubblica niente**: le modifiche restano sul dispositivo finché non le
   esporti, e a portarle nel repository è una persona (principio 5);
2. **non finge**: ogni spot toccato o creato porta il segno «locale», e quelli
   nuovi nascono `pending`. Verificato lo diventa uno spot quando una persona
   lo verifica (principio 2);
3. **non accetta chiavi segrete**: il campo della publishable key rifiuta
   quello che sembra una secret key, e lo dice (principio 4).

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
