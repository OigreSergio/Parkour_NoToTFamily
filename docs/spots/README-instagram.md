# Instagram nella scheda degli spot

Quando la family apre la scheda di uno spot, in fondo compare il **Contesto
visivo** (`docs/demo/pk-scheda.js`): copertina Street View puntata sullo
spot, seconda angolazione o foto della zona, vista aerea, 360° inline, link a
Google Street View e — da qui — i contenuti Instagram collegati allo spot,
così chi vuole dare un'occhiata si fa un'idea più completa di come si
presenta il posto.

I contenuti stanno in **`docs/spots/instagram.json`**, una voce per spot
(chiave = `id` dello spot in `scripts/data/webapp_fixed_spots.json`):

```json
"af810dbb-3109-4974-82c7-6cbdd5054efa": {
  "name": "Parkour Park Municipio Roma III",
  "location": {"id": "272111109", "slug": "vigne-nuove-montesacro-porte-di-roma", "name": "Vigne Nuove - Montesacro"},
  "posts": [
    {"url": "https://www.instagram.com/p/DU_VC2giPeT/", "kind": "post", "topic": "parkour",
     "title": "Roma ha il suo Parkour Park. E non è …"}
  ],
  "accounts": [{"handle": "playground.colosseo", "name": "…", "why": "…"}],
  "hashtags": ["nototfamily"]
}
```

| Campo       | Cosa fa nella scheda                                                                 |
| ----------- | ------------------------------------------------------------------------------------ |
| `location`  | Pagina Instagram del luogo (`instagram.com/explore/locations/<id>/<slug>/`): il pulsante **Su Instagram** la apre, cioè tutte le foto geotaggate lì. Senza `location` il pulsante apre la ricerca già compilata (nome spot + città + parkour). |
| `hashtags`  | Se presente, il pulsante apre l'hashtag invece del luogo (es. `#nototfamily` per lo spot del NoToT Game). |
| `posts`     | Post/reel pubblici pertinenti, elencati nel blocco **Dalla community su Instagram** con titolo (l'inizio della didascalia) e link; **Mostra il post qui** carica l'embed ufficiale di Instagram inline (`…/embed/captioned/`), solo su richiesta perché pesante. `topic`: `parkour` se si vede parkour allo spot, `luogo` se mostra solo il posto. |
| `accounts`  | Profili che pubblicano da quel posto (palestre, pagine del parco/quartiere), mostrati come chip `@handle`. |

## Come si aggiornano

Instagram non permette di cercare per luogo senza login e non ha API
pubbliche, quindi la raccolta è manuale, aiutata da un motore di ricerca web:

- pagina del luogo: `site:instagram.com/explore/locations <nome del posto> Roma`;
- post e reel: `instagram parkour <nome spot / quartiere>`, `reel parkour Roma <spot>`;
- profili: `instagram <palestra / parco / quartiere>`.

Poi:

```sh
python3 scripts/instagram_spots.py missing            # spot di Roma ancora senza voce
python3 scripts/instagram_spots.py location "Spot Tufello" 390378695 tufello-roma "Tufello - Roma"
python3 scripts/instagram_spots.py add "Spot Tufello" https://www.instagram.com/reel/XXXX/ --kind reel --title "…"
python3 scripts/instagram_spots.py check              # validazione
python3 docs/demo/tools/build_pk_scheda.py            # rigenera pk-scheda.js + pk-scheda-spots.json
scripts/deploy_pk_scheda.sh                           # pubblica su gh-pages
```

## Coprire il maggior numero di spot

Gli spot sono 1706 e i nomi della lista community sono di due tipi: nomi
propri ("Parco Ermanno Olmi", "Bunkers del Carmel", "Parkour Getafe Park")
e nomi generici ("Spot Brescia 3"). Per i primi si può trovare la pagina
del luogo; per i secondi il pulsante **Su Instagram** apre la ricerca già
compilata con nome e città (`Brescia parkour`), che per il parkour dice più
del geotag di un'intera città.

Tre sorgenti, dalla più precisa alla più ampia:

1. **Wikidata** (`scripts/wikidata_instagram_places.py`, nessuna chiave):
   i luoghi noti con ID Instagram registrato (proprietà P4173) vicini alle
   coordinate dello spot. Precisi ma pochi, e vanno scelti a mano perché a
   100 m può esserci sia il parco giusto sia un bar o la città intera.
2. **Ricerca web a mano** (motore di ricerca, `site:instagram.com/explore/locations <nome> <città>`):
   è come sono stati trovati i luoghi di Roma, dei parchi e quartieri
   italiani e dei parkour park esteri.
3. **Ricerca automatica quotidiana** (`scripts/find_instagram_places.py` +
   workflow `instagram-luoghi`): con una chiave gratuita di Google
   Programmable Search (100 query al giorno, nessuna carta) ogni notte
   cerca la pagina del luogo per gli spot con nome proprio ancora scoperti
   e apre una PR con quelle accettate (titolo o slug che contengono il nome
   dello spot); le altre finiscono in `instagram-candidates.json` da
   rivedere. Setup una volta sola:
   - https://programmablesearchengine.google.com → "Aggiungi", attivare
     "Cerca in tutto il web", copiare l'ID motore di ricerca (cx);
   - https://console.cloud.google.com/apis/library/customsearch.googleapis.com
     → "Abilita" (crea un progetto se chiesto), poi API e servizi →
     Credenziali → "Crea credenziali" → "Chiave API";
   - nel repository: Settings → Secrets and variables → Actions → due
     secret `GOOGLE_CSE_KEY` e `GOOGLE_CSE_CX`;
   - Settings → Actions → General → "Allow GitHub Actions to create and
     approve pull requests", altrimenti il workflow non può aprire la PR.
   Da quel momento basta fare merge delle PR e lanciare
   `scripts/deploy_pk_scheda.sh`.

Stato al 2026-09-07: 184 spot con voce (tutti i 26 della family, i 31 di
Roma e dintorni, un centinaio di parchi, piazze, quartieri e paesi
italiani, i parkour park e gli spot famosi all'estero), 164 pagine del
luogo, 38 post/reel, 34 profili.

## Cose da sapere

- Si incorporano solo post **pubblici**, con l'embed ufficiale di Instagram
  (nessun download, nessuna copia delle immagini: gli URL delle foto di
  Instagram sono firmati e scadono). Un post cancellato o reso privato mostra
  l'avviso di Instagram dentro l'embed: basta toglierlo dal file.
- I titoli sono l'inizio della didascalia come indicizzato dai motori di
  ricerca; a volte sono troncati (`…`). Vanno bene così: servono a capire cosa
  si apre.
- La pagina del luogo è la cosa più vicina a "cercare su Instagram con la
  posizione dello spot": raccoglie tutto ciò che la gente ha geotaggato lì,
  parkour e non.
