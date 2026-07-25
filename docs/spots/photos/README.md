# Foto degli spot

Le foto degli spot del seed (`backend/seeds/spots.json`) vivono qui, una
cartella per spot (nome = slug dello spot), e vengono servite come URL raw di
GitHub dal branch `main`:

```
https://raw.githubusercontent.com/OigreSergio/Parkour_NoToTFamily/main/docs/spots/photos/<slug>/01.jpg
```

Si è scelto `main` + raw URL (e non `gh-pages`) perché il branch `gh-pages`
viene sovrascritto dai deploy dell'export web: le foto lì non
sopravviverebbero.

## Come aggiungere le foto di uno spot

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

## Spot in attesa di foto

- `spot-verso-la-metro-cipro/` — creata, in attesa delle foto.
