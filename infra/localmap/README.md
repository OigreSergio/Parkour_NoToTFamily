# Mappa ricamo in locale — server indipendente (PC o telefono)

La mappa "ricamo" della web app usa tile vettoriali: online arrivano da
OpenFreeMap, ma il bundle patchato legge le sorgenti da due variabili
(`__PK_TILES__`, `__PK_GLYPHS__`), quindi l'intera mappa può girare da un
server locale, senza internet: PC che fa da server e telefoni collegati al
suo hotspot/Wi-Fi.

## 1. Genera i tile della zona (una tantum, serve internet)

[Planetiler](https://github.com/onthegomap/planetiler) produce un unico file
`.pmtiles` in schema OpenMapTiles — lo stesso che lo stile ricamo si aspetta:

```sh
cd infra/localmap
# Italia intera (~2 GB, ~15 min). Per il pianeta intero: --area=planet
# (~80 GB di output e ore di calcolo, serve un disco grande).
docker run --rm -v "$PWD/data:/data" ghcr.io/onthegomap/planetiler:latest \
  --download --area=italy --output=/data/map.pmtiles
```

## 2. Scarica i font per le etichette (una tantum)

```sh
sh fetch-fonts.sh   # scarica i range Noto Sans usati dallo stile in data/fonts/
```

## 3. Copia l'app e attiva la config locale

```sh
git fetch origin gh-pages
git --git-dir=../../.git archive origin/gh-pages | tar -x -C app/   # copia il sito
cp config.local.js app/t/*/config.local.js
# in app/t/*/index.html aggiungi PRIMA dello script del bundle:
#   <script src="./config.local.js"></script>
# e in config.local.js sostituisci SERVER_IP con l'IP del PC (es. 192.168.1.10)
```

## 4. Avvia

```sh
docker compose -f docker-compose.localmap.yml up -d
# tile server → http://SERVER_IP:8080/map.json
# web app     → http://SERVER_IP:8081/t/<token>/
```

Dal telefono (collegato allo stesso Wi-Fi/hotspot, anche senza SIM): apri
`http://SERVER_IP:8081/t/<token>/`. Mappa, spilli e i 26 spot fissi
funzionano tutti in locale; Supabase e il router dei percorsi restano
funzioni online (l'app li salta con fallback quando non raggiungibili).
