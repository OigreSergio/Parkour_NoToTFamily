# Foto degli spot

Ogni cartella `<slug>/` (slug = nome dello spot) contiene un `manifest.json`
con le foto dello spot verificate visivamente una a una:

```json
[{"file": "01.jpg", "source_page": "…", "image_url": "…",
  "author": "…", "license": "CC BY-SA 4.0",
  "review": {"verdict": "ok|debole|da-sostituire",
             "note": "perché", "checked": "2026-09-04"}}]
```

`review` è l'esito della revisione del 4 settembre 2026
(vedi [PHOTO_AUDIT.md](../PHOTO_AUDIT.md)): `ok` = si vedono gli ostacoli,
`debole` = posto giusto ma poco leggibile, `da-sostituire` = ritrae il
monumento o il quartiere, non lo spot. Le `da-sostituire` restano qui con il
motivo ma **non vengono collegate all'app**.

Le immagini **non** vengono copiate nel repo: l'app le carica in hotlink
dalle fonti (per Wikimedia Commons si usa il thumb da 1280px). Il
collegamento avviene con:

```sh
python3 scripts/wire_spot_photos.py
```

che riempie `photos`/`photosCount` in `scripts/data/webapp_fixed_spots.json`
e `photo_urls` in `backend/seeds/spots.json`. I manifest restano la
documentazione di fonte, autore e licenza di ogni scatto (quasi tutte le
foto vengono da Wikimedia Commons con licenza aperta; le poche eccezioni —
stampa locale, siti di community — sono segnate nel manifest e da citare o
sostituire prima di un uso pubblico).

## Foto proprie dai video della sessione

```sh
python3 scripts/extract_spot_frames.py "Nome dello spot" sessione.mp4
python3 scripts/wire_spot_photos.py
```

Campiona il video, scarta i fotogrammi mossi, scuri o quasi identici e tiene
le migliori come `vid-NN.jpg`, aggiornando il manifest. Scrive anche
`_provini.jpg`, un contatto numerato dei candidati: se la scelta automatica
non convince, si rilancia con `--scegli 2,5,9`.

## Foto proprie (upload manuale)

Per caricare scatti propri di uno spot resta valido il flusso classico:
foto nella cartella dello spot e

```sh
python scripts/add_spot_photos.py "Nome esatto dello spot" docs/spots/photos/<slug>/*.jpeg
```

che le normalizza (JPEG max 1600px) e aggiorna il seed con gli URL raw di
GitHub (attivi dopo il merge su `main`).

## Controllo dei link

```sh
python3 scripts/check_spot_photo_links.py [--online]
```

Verifica manifest, webapp, seed e `pk-scheda.js`. Commons accetta in hotlink
solo alcune larghezze di thumb (250, 330, 500, 960, 1280, 1920, 3840…): una
misura diversa risponde 400 e nell'app resta un riquadro vuoto.
