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
