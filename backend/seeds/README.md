# Seed spots

`spots.json` contiene gli spot raccolti dai maintainer da caricare direttamente
come **verificati** sulla mappa pubblica (utile quando l'invio dall'app o via
mail non funziona).

## Formato

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

## Caricamento

```sh
make seed-spots
# oppure, dentro il container api:
python -m app.db.seed_spots
```

# Seed video / tutorial

`videos.json` contiene la selezione curata di tutorial di parkour presi dai canali
YouTube di riferimento. La selezione, i criteri di inclusione/esclusione e la
valutazione della qualità didattica sono documentati in
[`docs/TUTORIAL_CATALOG.md`](../../docs/TUTORIAL_CATALOG.md).

## Formato

```json
{
  "title": "Titolo esatto del video su YouTube",
  "description": "Canale — argomento. Cosa si impara.",
  "url": "https://www.youtube.com/watch?v=...",
  "thumbnail_url": "https://i.ytimg.com/vi/.../hqdefault.jpg",
  "category": "practice | conditioning | recovery",
  "level": "beginner | intermediate | advanced",
  "trick_category": "basics | vaults | wall_tricks | bar_tricks | ground_tricks | flips | other",
  "difficulty": 3,
  "duration_seconds": 310,
  "source_channel": "Nome del canale",
  "quality": "Alta | Media"
}
```

I campi da `title` a `duration_seconds` corrispondono a `VideoCreate`
(`backend/app/schemas/video.py`). `source_channel` e `quality` sono metadati
editoriali del catalogo e vengono ignorati dal loader.

- `url` fa da chiave: il seed salta i video già presenti con lo stesso URL,
  quindi si può rilanciare ogni volta che il catalogo cresce.
- `difficulty` va da 1 a 10 e pilota l'indicatore nella lista dei tutorial.
- `level` decide anche l'accesso: `beginner` è libero, gli altri livelli
  richiedono l'abbonamento (vedi `app/services/video_service.py`).

Ogni voce viene validata con `VideoCreate` prima di toccare il database: se una
riga è malformata il seed si ferma subito indicando indice e titolo.

## Caricamento

```sh
make seed-videos
# oppure, dentro il container api:
python -m app.db.seed_videos
```
