# Foto degli spot

Ogni spot della mappa dovrebbe avere almeno una foto e una descrizione che dica
cosa ci si trova. Le foto vivono qui, una cartella per spot (nome = slug dello
spot), e vengono servite come URL raw di GitHub dal branch `main`:

```
https://raw.githubusercontent.com/OigreSergio/Parkour_NoToTFamily/main/docs/spots/photos/<slug>/01.jpg
```

Si è scelto `main` + raw URL (e non `gh-pages`) perché il branch `gh-pages`
viene sovrascritto dai deploy dell'export web: le foto lì non
sopravviverebbero.

## Due strade per una foto

| | Foto della crew | Foto da archivio libero |
| --- | --- | --- |
| Chi la scatta | chi va allo spot | terzi, già pubblicata |
| Cosa mostra | gli ostacoli veri (`kind: "spot"`) | il luogo intorno (`kind: "area"`) |
| Come entra | `scripts/add_spot_photos.py` | `scripts/import_commons_photos.py` |
| Attribuzione | nessuna | autore + licenza, obbligatori |

Le foto della crew sono sempre da preferire: una foto della zona dice dove
sei, una foto dello spot dice cosa ci puoi fare. Le foto da archivio servono a
non lasciare una scheda vuota nel frattempo, e in app portano il badge
**zona** proprio per non essere scambiate per una foto degli ostacoli.

## Aggiungere le foto della crew

1. Carica le foto originali nella cartella dello spot (va bene il drag & drop
   dall'interfaccia web di GitHub, in qualunque formato e risoluzione).
2. Da locale, normalizza e collega tutto con:

   ```sh
   python scripts/add_spot_photos.py "Nome esatto dello spot" docs/spots/photos/<slug>/*.jpeg
   ```

   Lo script converte in JPEG max 1600px (~150-400 KB l'una), le rinomina
   `01.jpg`, `02.jpg`, … e aggiorna `photo_urls` nel seed con gli URL raw.
3. Commit di foto + seed. Gli URL diventano attivi al merge su `main`; a quel
   punto rilancia `make seed-spots` per aggiornare il database.

## Aggiungere una foto da Wikimedia Commons

`sources.json` è la lista curata: per ogni spot, i file di Commons scelti a
mano dopo averli guardati uno per uno, con la didascalia e il tipo (`spot` o
`area`).

```json
"Colle Oppio Park": [
  {
    "file": "File:Parco del Colle Oppio - panoramio.jpg",
    "kind": "area",
    "caption": "I vialetti e i muretti del parco sopra il Colosseo"
  }
]
```

Poi:

```sh
python scripts/import_commons_photos.py --check      # licenze e metadati
python scripts/import_commons_photos.py              # scarica e riscrive i dati
```

Lo script scarica, normalizza (JPEG max 1600px) e riscrive `photo_urls` e
`photos` sia nel seed sia in `scripts/data/webapp_fixed_spots.json`. **Rifiuta
qualunque file con una licenza che non permetta il riuso commerciale con la
sola attribuzione** (niente NC, niente ND): se una foto non può stare in
un'app, non entra nel repo.

### Perché non prendiamo le foto dai forum e dai gruppi

Le foto che girano su Instagram, Facebook, Telegram e i forum di parkour sono
di chi le ha scattate: pubblicarle qui sarebbe una violazione di copyright, e
il repo è pubblico. Quei canali restano utilissimi per **incrociare le
informazioni** — capire quali spot esistono davvero, com'è cambiata una zona,
se un posto è ancora accessibile — ma le immagini no. Se una foto ti serve
davvero, chiedila a chi l'ha fatta e falla arrivare via
`scripts/add_spot_photos.py`, con il suo consenso.

## Attribuzione

Ogni voce di `photos` porta `author`, `license`, `license_url`, `source` e
`source_url`. Le licenze CC BY e CC BY-SA obbligano a mostrare autore e
licenza **ovunque** l'immagine compaia: per questo il credito viaggia nel
database (colonna `photos`, migrazione `0003_spot_photo_credits`) e non in un
file a parte, e viene mostrato sotto la foto sia nell'app mobile sia nella
galleria della web app di test.

## Copertura

Lo stato spot per spot è in [`COVERAGE.md`](COVERAGE.md), rigenerabile con:

```sh
python scripts/spot_coverage.py
```
