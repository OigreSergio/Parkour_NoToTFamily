# Seed

Due file di seed alimentano il database con i contenuti curati dai maintainer:
`spots.json` (spot verificati sulla mappa) e `videos.json` (catalogo tutorial).

## Spots

`spots.json` contiene gli spot raccolti dai maintainer da caricare direttamente
come **verificati** sulla mappa pubblica (utile quando l'invio dall'app o via
mail non funziona).

### Formato

```json
{
  "name": "Nome univoco dello spot",
  "lat": 41.907192,
  "lng": 12.449997,
  "difficulty": 2,
  "description": "Cosa si trova sul posto e che movimenti permette.",
  "photo_urls": []
}
```

- `name` fa da chiave: il seed salta gli spot già presenti con lo stesso nome,
  quindi si può rilanciare ogni volta che il file cresce.
- `difficulty` va da 1 (facile) a 5.
- `photo_urls` è opzionale: URL pubblici delle foto, quando disponibili.

### Caricamento

```sh
make seed-spots
# oppure, dentro il container api:
python -m app.db.seed_spots
```

## Videos

`videos.json` è il catalogo tutorial del progetto: i video selezionati per la
sezione **Tutorials** dell'app, con livello, categoria di trick, difficoltà e
durata. È generato dalla pagina `tutorial-catalog.html` pubblicata su
`gh-pages`:

```sh
python3 scripts/import_tutorial_catalog.py
```

### Formato

```json
{
  "title": "Titolo univoco del video",
  "description": "Cosa insegna il video (canale: Nome del canale).",
  "url": "https://www.youtube.com/watch?v=ID",
  "thumbnail_url": "https://i.ytimg.com/vi/ID/hqdefault.jpg",
  "category": "practice",
  "level": "beginner",
  "trick_category": "basics",
  "difficulty": 1,
  "duration_seconds": 310
}
```

- `title` fa da chiave: il seed salta i video già presenti con lo stesso titolo.
- `category` è `recovery` | `practice` | `conditioning`; `level` è `beginner` |
  `intermediate` | `advanced` (da `intermediate` in su il video è premium e
  richiede l'abbonamento per essere guardato — vedi `video_service.py`).
- `trick_category` raggruppa la griglia dei tutorial: `flips`, `basics`,
  `vaults`, `wall_tricks`, `bar_tricks`, `ground_tricks`, `other`.
- `difficulty` va da 1 a 10.

### Caricamento

```sh
make seed-videos
# oppure, dentro il container api:
python -m app.db.seed_videos
```
