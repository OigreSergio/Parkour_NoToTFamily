# Revisione delle foto degli spot — 4 settembre 2026

Le foto degli spot non erano rappresentative: molte ritraggono il monumento o
il quartiere invece dei muretti, dei gradoni e degli spazi in cui si allena.
Il caso segnalato di **Spot Metro Colosseo** (tre foto dell'ingresso della
metropolitana) e di **Spot Rooftop Casal Lumbroso** (nessuna foto, Street View
a 83 m che inquadra una siepe) non erano eccezioni: erano la regola.

Questo documento è il risultato della revisione, foto per foto.

## Come è stata fatta

Ho scaricato e guardato **una per una tutte le 68 foto** collegate agli spot
(quelle dei `manifest.json`, cioè quelle che l'app mostra), **le 52
inquadrature Street View** usate come ripiego per gli spot senza foto e le
**14 foto di contesto** della scheda demo. Per ognuna la domanda era una sola: *guardando questa immagine, uno che non c'è
mai stato riconosce lo spot e capisce su cosa si allena?*

Tre esiti, scritti dentro ogni `manifest.json` nel campo `review`:

| verdetto | significato |
| --- | --- |
| `ok` | si vedono gli ostacoli, lo spot è riconoscibile |
| `debole` | posto giusto ma ostacoli poco leggibili (foto scura, di archivio, troppo lontana, affollata): resta finché non arriva di meglio |
| `da-sostituire` | non è lo spot (monumento, strada, prato, cartolina): **non viene più collegata all'app** |

`scripts/wire_spot_photos.py` ora salta le `da-sostituire`: meglio nessuna
foto che una foto che non è lo spot. Restano nel manifest, con il motivo,
così non vengono ripescate per sbaglio (`--tutte` le ricollega comunque).

## Il risultato in numeri

- 68 foto controllate: **9 ok**, **19 deboli**, **40 da sostituire** (59%).
- Le foto collegate all'app passano da 68 a **28**, più il primo scatto
  proprio (MA Spot Ruspoli, vedi in fondo): **29**.
- 5 spot restano **senza nessuna foto**: EUR Laghetto, Spot EUR, Spot Metro
  Colosseo, Spot Colonne Colosseo, Spot Tufello.
- Altri 8 spot **non avevano mai avuto foto** (MA Spot Ruspoli — ora sistemato
  —, Rooftop Casal Lumbroso, Pizzeria Massimina, Scuola Massimina, Massimina
  Parco Nord, Massimina Parco Sud, Via Giovanni Prati, NoToT Game).
- Restano **12 spot su 26 senza foto**, e aspettano scatti tuoi.

La causa è nel modo in cui erano state raccolte: cercando su Wikimedia Commons
il *nome del posto*. Su Commons le foto di "Colosseo", "EUR" o "Tufello" sono
foto del monumento e del quartiere — non esistono foto dei muretti su cui ci
si allena. Quelle bisogna farle.

## Spot per spot

Ordine: prima quelli da rifare, poi quelli a posto. Tutti a Roma tranne gli
ultimi cinque.

### Da rifotografare — nessuna foto utilizzabile (priorità 1)

| Spot | Situazione | Street View di ripiego |
| --- | --- | --- |
| **Spot Metro Colosseo** | 3 foto scartate: ingresso della metro, facciata, folla | l'inquadratura principale (5 m) mostra i muretti in travertino con il Colosseo dietro: **è l'unica cosa buona che ha** |
| **EUR Laghetto** | 3 scartate: laghetto, cascata, Palazzo dello Sport | inutile: strada con auto in sosta e un cantiere |
| **Spot EUR** | 3 scartate: Palasport, obelisco, laghetto | parziale: si intravede il sottopasso con gradini e bordi |
| **Spot Colonne Colosseo** | 3 scartate: traffico, monumento, cartolina del Colosseo | debole: prato e cordolo, il muro di mattoni antico |
| **Spot Tufello** | 3 scartate: due foto d'archivio in bianco e nero e auto su uno sterrato | **buona**: pilotis, muretti e scale del complesso |

### Da fotografare — non hanno mai avuto foto (priorità 2)

| Spot | Street View di ripiego |
| --- | --- |
| **Spot Rooftop Casal Lumbroso** | inutile: panorama a 83 m su una siepe, il tetto non si vede — è il secondo caso che avevi segnalato |
| **Spot Scuola Massimina** | inutile: siepe e cancellata, lo spot è oltre |
| **Spot Massimina Parco Nord** | debole: parcheggio davanti alla recinzione del parco |
| **Spot Massimina Parco Sud** | debole: recinzione e campetto sullo sfondo |
| **Spot Pizzeria Massimina** | debole: strada residenziale con ringhiere |
| **Spot Via Giovanni Prati** | parziale: la rampa del garage con i muretti |
| **Spot NoToT Game** | parziale: la piazzetta coi muretti in mattoni, ma auto in primo piano |

### Sistemati con foto proprie

| Spot | Foto |
| --- | --- |
| **MA Spot — Largo Emanuele Ruspoli** | 1 `ok` — il piazzale dall'alto: muretti, fioriere, gradoni e campo ribassato. Scatto tuo del 4 settembre 2026, ripulito dall'emoji e dalle barre dello screenshot. Manca ancora un dettaglio ravvicinato dei muretti. |

### Restano con una foto debole (priorità 3)

| Spot | Cosa resta | Cosa manca |
| --- | --- | --- |
| **Garbatella — Scalinate** | la scalinata con i muretti laterali (`ok`) | una seconda angolazione dal basso |
| **Parkour Park Municipio Roma III** | le strutture in uso (`ok`) + un doppione | una foto dell'area vuota, per vedere il layout |
| **Foro Italico — Stadio dei Marmi** | i gradoni in marmo ravvicinati (`ok`) | niente di urgente |
| **Colle Oppio Park** | la Fontana delle Anfore | i muretti veri del parco |
| **Spot Colosseo — Monte Oppio** | il ninfeo con balaustre | il punto in cui ci si allena |
| **Spot Corviale 1 / 2 / 3** | tre foto d'archivio in bianco e nero | tutto: i tre spot si distinguono solo dal vivo |
| **Spot Primavalle** | il cortile col pergolato | la scalinata coi muretti che si vede in Street View |
| **Spot Villa Carpegna** | la vasca circolare | il resto del parco (Street View è a 122 m, inutile) |
| **Villa Borghese — Piazza di Siena** | l'ovale coi cipressi, un muretto in controluce | i tronchi e i muretti bassi della descrizione |
| **Spot verso la metro Cipro** | il piazzale e il passaggio coperto | le fioriere e la scalinata da vicino (la Street View rigenerata ora le inquadra) |
| **Spot con fontanella - Trastevere/Gianicolo** | il muretto del belvedere (con gente) | **prima va chiarita la posizione**, vedi sotto |

### A posto (fuori Roma, non serve intervenire)

| Spot | Foto |
| --- | --- |
| **El laberinto de Uribarri** (Bilbao) | 2 `ok` — sono foto della community di Parkour Bilbao, si vede esattamente lo spot |
| **Freeway Park** (Seattle) | 2 `ok` + 1 debole — blocchi, terrazzamenti e gradoni |
| **Frank Kitts Park** (Wellington) | 1 `ok` + 1 debole; scartata l'area giochi per bambini |
| **Bunkers del Carmel** (Barcellona) | 1 `ok` + 2 deboli (molta gente e volti riconoscibili) |
| **Yoro Park** (Giappone) | 1 debole; scartate due panoramiche dall'alto |

## Due problemi nei dati, non nelle foto (uno già risolto)

1. **Spot con fontanella - Trastevere/Gianicolo** — le coordinate
   (41.894056, 12.433333) cadono su **via Gregorio VII, Municipio XIII**
   (verificato con Nominatim/OpenStreetMap): sono a circa 2,4 km dal
   Gianicolo e non sono a Trastevere. La Street View di quel punto mostra
   palazzine e una scalinata di quartiere, non il belvedere. O sono sbagliate
   le coordinate, o lo sono il nome e le foto: va deciso dal vivo. Finché non
   è chiaro, le foto del Gianicolo restano `debole` e non vale la pena
   cercarne altre.

2. **Spot verso la metro Cipro** — nella scheda demo
   (`docs/demo/pk-scheda.js`) le due inquadrature Street View puntavano a un
   panorama che non esiste più: l'immagine che tornava era **completamente
   nera**. Rigenerando `pk-scheda.js` il panorama è stato ripreso a 17 m e
   ora mostra la piazzetta con le fioriere in mattoni e i bordi in
   travertino — cioè proprio quello che dice la descrizione dello spot.

## La scheda demo (`pk-scheda.js`)

La sezione "Contesto visivo" della scheda spot mostra Street View più una
"foto della zona" presa dal web. Anche quelle 14 foto sono state guardate una
per una: **12 mostravano il monumento o il quartiere** — il Colosseo per lo
spot della metro, il laghetto per l'EUR, Villa Carpegna sotto la neve, largo
Borromeo per Primavalle — e per giunta **prendevano il posto della seconda
angolazione Street View**, che è più utile. Sono state tolte da `CURATED` in
`docs/demo/tools/build_pk_scheda.py`; restano Foro Italico (i gradoni in
marmo) e Garbatella (la scalinata). La didascalia ora dice "Foto della zona",
per non farla passare per una foto dello spot.

`pk-scheda.js` è rigenerato: `python3 docs/demo/tools/build_pk_scheda.py`.

## Come mandare le foto nuove

Dai video della sessione le istantanee migliori le tira fuori uno script:

```sh
python3 scripts/extract_spot_frames.py "Spot Rooftop Casal Lumbroso" video1.mp4 video2.mp4
python3 scripts/wire_spot_photos.py     # collega le foto a webapp e seed
```

Campiona il video, scarta i fotogrammi mossi, scuri o troppo simili tra loro e
tiene le tre migliori. Scrive anche `_provini.jpg` nella cartella dello spot:
un contatto numerato dei candidati, per rilanciare con `--scegli 2,5,9` se la
scelta automatica non convince. Per foto già scattate col telefono resta
`scripts/add_spot_photos.py`.

**Cosa inquadrare** (vale sia per gli scatti sia per il video):

- una **veduta larga** dello spot con un riferimento riconoscibile intorno
  (il palazzo, l'insegna, la scalinata): serve a ritrovare il posto;
- un **primo piano dell'ostacolo principale** — muretto, rail, gap — con
  qualcuno accanto in piedi, così si capisce l'altezza;
- se lo spot ha punti diversi (Corviale 1/2/3, i due parchi della Massimina),
  una foto per punto, altrimenti restano indistinguibili;
- luce alle spalle, niente controluce; telefono in orizzontale e fermo — per
  il video, panoramiche lente;
- niente volti riconoscibili di terzi, niente targhe, niente minori.

Tre foto per spot bastano: larga, dettaglio, seconda angolazione.

## Controllo dei link

Le foto del web sono in hotlink e si rompono da sole. Wikimedia Commons dal
2025 rifiuta i thumb in misure non standard: i 22 link a `1600px` presenti nei
manifest **rispondevano 400**, cioè erano già morti. Sono stati portati a
`1280px` (misura ammessa). Per ricontrollare:

```sh
python3 scripts/check_spot_photo_links.py            # misure e formato
python3 scripts/check_spot_photo_links.py --online   # anche raggiungibilità
```

Da tenere presente: Commons applica un rate limit severo all'hotlink. Per
questo `wire_spot_photos.py` ora distingue "il thumb non esiste" (allora usa
l'originale) da "Commons mi ha risposto 429" (allora tiene il thumb): prima,
sotto rate limit, un thumb da 1280px veniva sostituito con l'originale a piena
risoluzione, che può pesare decine di MB sul telefono di chi apre la scheda.
Quando le foto proprie avranno sostituito quelle del web, il problema
sparisce.
