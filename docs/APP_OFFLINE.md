# L'app installabile che funziona senza rete

> Stato: prima versione completa, in `app/`. Si prova dal computer, si
> installa dal telefono. Non è ancora pubblicata: pubblicare è un'azione di
> una persona (principio 5 del masterplan).

## Il problema

Il QR porta a `https://oigresergio.github.io/Parkour_NoToTFamily/t/<token>/`:
una **pagina**. Ne discendono tre cose, tutte vere insieme:

1. **senza rete non c'è niente.** La build Flutter pubblicata ha un
   `flutter_service_worker.js`, ma `manifest.json` e `index.html` sono ancora
   quelli del generatore («A new Flutter project», colore `#0175C2`): non si
   installa bene, e quello che tiene in cache è il guscio, non i dati;
2. **non sembra un'applicazione.** Barra degli indirizzi, nessuna icona,
   nessuna schermata di avvio di marca;
3. **i sorgenti di quella build non stanno su `main`** (masterplan 1.4).
   Qualunque intervento su di essa sarebbe una patch sul bundle pubblicato —
   cioè esattamente ciò che il principio 5 vieta.

## La scelta

`app/` è un'applicazione web installabile (PWA) **scritta nel repository**,
senza passaggio di build, che porta con sé i dati e funziona in modalità
aereo. Non sostituisce la build Flutter: le sta accanto e risolve il problema
che quella non può risolvere finché i suoi sorgenti non tornano su `main`.

| | Build Flutter su `gh-pages` | `app/` |
| --- | --- | --- |
| Sorgenti su `main` | no | sì |
| Si installa con icona e nome propri | male (manifest del generatore) | sì |
| Si apre senza rete | solo il guscio | sì, dati compresi |
| Spot disponibili offline | no | 1.706, con fontanelle |
| Mappa senza rete | bianca | lino con la trama, spilli al loro posto |
| Tessere scaricabili in anticipo | no | sì, l'area visibile |
| Account, chat, community | sì (online) | no |
| Video dei tutorial | sì (online) | scheda offline, video online |

Quando i sorgenti della build Flutter torneranno su `main`, due strade — e
vanno decise da una persona, non da un agente:

- **A.** L'app Flutter prende da qui il manifest, le icone, la schermata di
  avvio e la strategia di cache, e `app/` resta come banco di prova.
- **B.** `app/` diventa il guscio offline pubblicato accanto alla build
  Flutter, che resta la versione completa quando c'è rete.

## Come funziona l'offline

Tre cache, tre vite diverse (dettaglio in `app/public/sw.js`):

| Cache | Cosa tiene | Quando cambia |
| --- | --- | --- |
| `pkfamily-app-<versione>` | i 35 file elencati in `precache.json`: guscio, codice, caratteri, icone, **spot, fontanelle, tutorial** | a ogni nuova versione; la vecchia viene cancellata |
| `pkfamily-tiles` | le tessere già viste o scaricate a mano | tetto di 4.000, escono le più vecchie |
| `pkfamily-media` | le foto degli spot già aperti | tetto di 300 |

Quello che riguarda le persone — Supabase, il proxy dei percorsi — **non entra
in nessuna cache**: passa dalla rete o non passa. C'è una prova automatica che
lo verifica (`app/tests/offline.spec.mjs`).

La versione è l'impronta del contenuto di tutti i file: cambiarne uno cambia
la versione, il service worker se ne accorge e la schermata «Tu» offre
l'aggiornamento.

## Il vincolo da conoscere prima di provare

**Il service worker si accende solo su `localhost` o su `https`.** È una
regola dei browser. Quindi:

- dal computer, `http://127.0.0.1:8080` va benissimo (`app/tools/serve.py`);
- dal telefono in Wi-Fi, `http://192.168.x.y:8080` mostra l'app ma **non la
  rende offline né installabile**;
- dal telefono con l'offline vero: cavo USB e `chrome://inspect` → *Port
  forwarding*, oppure `serve.py --https` accettando il certificato locale,
  oppure la pubblicazione da `main` via CI.

**E serve Python 3.14 o successivo** (`python3 --version`): è il pavimento del
repository, e gli strumenti di `app/tools/` lo danno per scontato. L'app in sé
non ha bisogno di niente; i pacchetti che si passano ad altri — la beta, la
demo e `PkFAMILY.app` — portano invece un avviatore che funziona dalla 3.9 in
su, perché su quel computer la versione non la scegliamo noi.

## Provarla come beta

`python3 app/tools/build_beta.py --zip` produce in `app/dist/` una cartella che
sta in piedi da sola (1,1 MB, 0,4 MB zippata): app, avviatore e LEGGIMI. Si
copia su qualunque computer con Python 3.9 o successivo e si lancia con
`python3 avvia.py`.

La copia porta `build.json` con canale `beta`: l'app mette in testa la fascia
**BETA** con la versione, e «Tu → Avanzate» offre *Segnala un problema*, che
mette in coda sul dispositivo cosa stavi facendo, dove eri e che schermo hai.

Non è una pubblicazione: è un pacchetto da passare a mano a chi prova.

## La demo con il motore in Python

`python3 app/tools/build_demo_python.py --cartella ~/Desktop` produce un solo
file `.py` da mettere sul desktop: doppio clic, e l'app si apre in una finestra
formato telefono con la logica gestita da `app/demo/motore.py` — riquadro,
ricerca, vicini, fontanelle, tutorial. `--installa` mette l'icona sul desktop.

Serve a due cose: provare l'app sul computer con dati veri, e vedere come si
comporta con un servizio davanti invece che con tutto dentro il browser.

Non è un backend di prodotto (AGENTS.md, regola 3): nessuna regola nuova,
nessuna scrittura, nessun account. E se tace, l'app continua da sola.

## Installarla davvero: l'APK, e il QR che lo porta sul telefono

```sh
python3 app/tools/build_apk.py     # app/dist/pkfamily-<versione>.apk (0,8 MB)
python3 app/tools/qr.py            # lo serve sulla rete di casa e mostra il QR
```

Installare dal browser («Aggiungi alla schermata Home») resta la strada
principale e non chiede niente a nessuno. L'APK serve a chi quella strada non
la trova, o a chi vuole passare l'app a mano: si inquadra il QR con la
fotocamera, il telefono scarica, due tocchi e c'è.

Dentro l'APK non c'è un'app riscritta: c'è **questa** app, con il suo service
worker e i suoi dati. Il guscio Android (`app/android/`, due classi Java) è
una tela web che intercetta le richieste a `https://appassets.androidplatform.net/`
— un indirizzo che Android riserva a questo scopo e che in rete non esiste — e
risponde con i file presi da dentro il pacchetto. È l'unico modo per avere
insieme le tre cose che servono: un'origine sicura (senza la quale il service
worker non si registra), un'origine **stabile** (una porta a caso cambierebbe
a ogni avvio, e con lei preferenze, spot messi da parte e tessere scaricate) e
nessuna richiesta che esca davvero dal telefono.

Si compila senza Gradle e senza rete, con `aapt2`, `javac`, `d8`, `zipalign` e
`apksigner`. La firma è una chiave di prova generata in `app/dist/`, che non
entra nel repository: la chiave di pubblicazione è di una persona (AGENTS.md,
regola 6), e per questo l'app porta in testa la fascia **APK DI PROVA**.

### Vedere l'app sul telefono senza installare niente

```sh
python3 app/tools/qr.py --app                       # si apre sulla mappa
python3 app/tools/qr.py --app '#/spot/<id>'         # o dritta su uno spot
python3 app/tools/qr.py --app --https               # per provare anche l'offline
```

Il telefono inquadra il QR e apre l'app nel browser, sulla rete di casa: non
si installa niente e non si aspetta nessun pacchetto. È il modo più corto per
guardare una modifica sul telefono vero, e serve i file di `app/public/` così
come sono in questo momento.

In HTTP l'offline resta spento — i browser lo accendono solo su `localhost` o
`https` — quindi per provare anche quello serve `--https`, e sul telefono si
accetta il certificato una volta.

### Il QR, passo passo

1. **Metti telefono e computer sulla stessa Wi-Fi.** È tutto quello che serve:
   nessun cavo, nessun account, nessun sito di mezzo.
2. Dal Terminale, nella cartella del repository:

   ```sh
   python3 app/tools/build_apk.py     # solo la prima volta, o dopo una modifica
   python3 app/tools/qr.py
   ```

   Se l'APK ce l'hai già altrove (per esempio in `~/Downloads`):
   `python3 app/tools/qr.py --file ~/Downloads/pkfamily-0.1.0-apk.20260921.apk`.
3. Nel Terminale compare **il QR disegnato**, e sotto l'indirizzo che contiene
   — qualcosa come `http://192.168.1.42:8080/`. Se la finestra è stretta il
   disegno si spezza: allargala, o apri `app/dist/pkfamily-qr.png`, che è lo
   stesso QR come immagine.
4. **Inquadralo con la fotocamera del telefono.** Non serve nessuna app: sia
   iPhone sia Android leggono i QR dalla fotocamera e mostrano una notifica da
   toccare.
5. Si apre una pagina con scritto **PkFAMILY** e il download parte da solo. Se
   non parte, sulla stessa pagina c'è il bottone.
6. Apri il file scaricato. Android chiede il permesso di installare da questa
   sorgente: concedilo, poi **Installa**.
7. Quando hai finito, **Ctrl+C** nel Terminale: il server si spegne. Finché
   gira, chiunque sia su quella Wi-Fi può scaricare il file.

Quello che può andare storto, e cosa vuol dire:

| Cosa vedi | Cosa succede |
| --- | --- |
| La fotocamera legge il QR ma la pagina non si apre | Telefono e computer non sono sulla stessa rete. Occhio alle reti «ospiti» e alle Wi-Fi che isolano i dispositivi fra loro |
| Si apre e resta a girare | Il firewall del Mac sta bloccando. Impostazioni di Sistema → Rete → Firewall: o lo spegni per un minuto, o consenti le connessioni in entrata a Python |
| L'indirizzo nel QR comincia per `127.` | Il computer non ha trovato il proprio indirizzo di rete. Prendilo a mano (Impostazioni → Wi-Fi → Dettagli) e passalo: `python3 app/tools/qr.py --ip 192.168.1.42` |
| «Porta già in uso» | Un'altra cosa sta usando la 8080: `python3 app/tools/qr.py --porta 8090` |
| Su iPhone il file si scarica ma non si installa | Un APK è Android. Su iPhone l'app si installa dal browser: apri l'app e «Condividi → Aggiungi alla schermata Home» |

## Provarla sul Mac, senza un telefono

```sh
python3 app/tools/build_mac_app.py --cartella ~/Desktop
```

Ne esce **PkFAMILY.app** sulla Scrivania: doppio clic e si apre in una finestra
formato telefono, senza barra degli indirizzi. Dentro ci sono l'app,
l'avviatore e l'icona; serve solo Python 3 (dalla 3.9 in su), che macOS non
porta più di serie — se manca, il bundle lo dice con una finestra invece di
non fare niente.

**Un APK non gira su un Mac**, e nessun trucco lo cambia. Quello che lo
strumento fa è aprire l'APK e mettere nel bundle *esattamente i file che ci
stanno dentro*, verificandoli per impronta uno per uno: sul Mac si prova la
stessa app che si installa sul telefono, byte per byte. Resta fuori solo il
guscio Android — due classi Java — che solo un telefono può far girare. Per
questo la fascia in testa dice **APK DI PROVA** con la versione dell'APK da cui
viene.

Senza un APK a portata di mano il bundle si costruisce lo stesso, dai sorgenti
di `app/public/`, e allora la fascia dice **APP DI PROVA**: così si sa sempre
cosa si sta guardando. Con `--apk ~/Downloads/pkfamily-....apk` si indica
l'APK da aprire.

`--zip` produce il pacchetto da passare a qualcuno. Uno `.zip` che arriva da
internet, però, viene messo in quarantena da macOS: la prima volta si apre con
**tasto destro sull'app → Apri**, non con il doppio clic. Costruirlo sul
proprio Mac evita del tutto la faccenda.

## La modalità sviluppatore

Si accende da «Tu → Avanzate» e apre un pannello (`#/admin`) per correggere
spot, provare dal vivo il filtro delle tessere, cambiare sorgenti e
collegamenti, esportare tutto in JSON. Dettagli in
[`app/README.md`](../app/README.md).

Le tre regole che la tengono dentro i principi del masterplan:

| Principio | Come è rispettato |
| --- | --- |
| 5 — solo `main` via CI va online | il pannello non pubblica: esporta file da rivedere |
| 2 — solo verificato è pubblico | ogni spot toccato porta il segno «locale»; i nuovi nascono `pending` |
| 4 — nessun segreto nel client | il campo della publishable key rifiuta quello che sembra una secret key |

È la sostituzione, per la parte di dati, di quello che oggi fa
`admin-desktop/` con la secret key dentro il browser (problema P0 del
masterplan, cap. 6.2): qui non c'è nessuna chiave privilegiata, e infatti non
si può scrivere su Supabase — si esporta e si passa da una persona.

## Cosa manca per andare online

Sono cose da persona, elencate perché siano decidibili:

1. **pubblicare**: un workflow che da `main` copia `app/public/` sotto un
   percorso di `gh-pages`. Oggi non esiste e non va creato a mano;
2. **collegare Supabase**: `app/public/js/config.js` nasce con `supabase.url`
   vuoto. Riempirlo (URL e publishable key, mai la secret key) accende
   l'accesso e l'invio della coda dei contributi;
3. **decidere A o B** qui sopra;
4. **i caratteri**: Fraunces e Karla sono incorporati (OFL 1.1). Se in futuro
   servono giapponese o cinese, si dichiara il fallback di sistema — l'app è
   già pronta a farlo (`--testo` in `pk.css`).

## Dove guardare

- l'applicazione: [`app/README.md`](../app/README.md);
- il design system che segue: masterplan capitolo 3;
- la regola sull'arrotondamento delle coordinate: `docs/ROUTING_PK.md` e
  `remote-service/pkremote/services/routing.py`;
- come si prova dal telefono l'altra parte del prodotto:
  [`PROVA_DA_TELEFONO.md`](PROVA_DA_TELEFONO.md).
