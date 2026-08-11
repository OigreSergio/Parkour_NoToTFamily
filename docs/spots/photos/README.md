# Foto degli spot

Ogni cartella `<slug>/` (slug = nome dello spot) contiene un `manifest.json`
con le foto dello spot trovate sul web e verificate visivamente una a una:

```json
[{"file": "01.jpg", "source_page": "…", "image_url": "…",
  "author": "…", "license": "CC BY-SA 4.0"}]
```

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

## Foto proprie (upload manuale)

Per caricare scatti propri di uno spot resta valido il flusso classico:
foto nella cartella dello spot e

```sh
python scripts/add_spot_photos.py "Nome esatto dello spot" docs/spots/photos/<slug>/*.jpeg
```

che le normalizza (JPEG max 1600px) e aggiorna il seed con gli URL raw di
GitHub (attivi dopo il merge su `main`).
