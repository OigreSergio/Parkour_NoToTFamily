#!/usr/bin/env python3
"""Arricchisce gli spot con fatti verificabili, da fonti citabili.

`clean_spots.py` toglie quello che non è vero. Questo aggiunge quello che si
può sapere davvero, e **solo quello**:

  * **toponimo reale** al posto di «Spot Athens 3», dal nome della feature
    OpenStreetMap più vicina (parco, piazza, campo). Per uno spot di parkour un
    parco vale più di un indirizzo civico, ed evita del tutto Nominatim, che è
    rate-limitato a 1 richiesta/secondo e su 1.700 spot diventa mezz'ora di
    attesa nella migliore delle ipotesi;
  * **contesto**: superficie, tipo di area, e soprattutto `amenity=drinking_water`
    nel raggio → `hasFountain` **reale**, al posto del `false` piatto su tutti;
  * **foto con licenza**: Wikimedia Commons per geolocalizzazione, Mapillary se
    c'è un token. Autore e licenza si salvano insieme all'URL: senza, la foto
    non è pubblicabile.

Quello che questo script **non fa, e non deve fare**: livello di difficoltà,
affollamento, cosa ci si allena. Non esistono in nessuna API. Generarli
significherebbe inventare fatti su luoghi fisici dove la gente si fa male —
l'opposto di ciò che rende difendibile una mappa informativa. Quei campi
restano `null` finché non arriva qualcuno che c'è stato.

    export MAPILLARY_TOKEN=MLY|...        # opzionale
    python3 scripts/enrich_spots.py --limit 50      # prova su pochi
    python3 scripts/enrich_spots.py                 # tutti, riprendibile

La cache in `scripts/data/enrichment_cache.json` rende lo script riprendibile:
interromperlo non perde lavoro, e rilanciarlo non ripete le chiamate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "scripts" / "data" / "webapp_fixed_spots.json"
CACHE = ROOT / "scripts" / "data" / "enrichment_cache.json"

# Identificarsi è richiesto dalle usage policy di OSM e Wikimedia, e comunque è
# il minimo: chi gestisce quei server deve poter capire chi li sta usando.
UA = "PkFAMILY-spot-enrichment/1.0 (+https://pkfamily.app; contatto: abuse@pkfamily.app)"

OVERPASS = "https://overpass-api.de/api/interpreter"
COMMONS = "https://commons.wikimedia.org/w/api.php"
MAPILLARY = "https://graph.mapillary.com/images"

# Raggio di ricerca del contesto. Oltre, si descriverebbe un altro posto.
RADIUS_M = 150

# Overpass è un servizio pubblico condiviso: una pausa fra le chiamate non è
# cortesia, è la condizione per continuare a poterlo usare.
PAUSE_S = 1.2


def get_json(url: str, params: dict | None = None, data: bytes | None = None) -> dict | None:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as err:  # noqa: BLE001 — una fonte giù non ferma le altre
        print(f"    ! {type(err).__name__}: {err}", file=sys.stderr)
        return None


def osm_context(lat: float, lng: float) -> dict:
    """Feature OSM intorno allo spot: nome del luogo, superficie, acqua."""
    query = f"""
    [out:json][timeout:30];
    (
      nwr(around:{RADIUS_M},{lat},{lng})[leisure~"^(park|pitch|fitness_station|playground|sports_centre)$"];
      nwr(around:{RADIUS_M},{lat},{lng})[place~"^(square)$"];
      nwr(around:{RADIUS_M},{lat},{lng})[amenity="drinking_water"];
      nwr(around:{RADIUS_M},{lat},{lng})[sport="parkour"];
    );
    out tags center 30;
    """
    body = get_json(OVERPASS, {"data": query})
    if not body:
        return {}

    elements = body.get("elements", [])
    context: dict = {"osm_checked": True}

    # Acqua: un fatto, con una fonte. Diverso dal `false` messo su tutti.
    if any(e.get("tags", {}).get("amenity") == "drinking_water" for e in elements):
        context["hasFountain"] = True

    if any(e.get("tags", {}).get("sport") == "parkour" for e in elements):
        context["osm_parkour_facility"] = True

    # Il nome del luogo: si preferisce una feature nominata e ampia.
    named = [
        e for e in elements
        if e.get("tags", {}).get("name")
        and e.get("tags", {}).get("amenity") != "drinking_water"
    ]
    if named:
        priority = {"park": 0, "square": 1, "sports_centre": 2, "pitch": 3, "playground": 4}
        named.sort(
            key=lambda e: priority.get(
                e["tags"].get("leisure") or e["tags"].get("place", ""), 9
            )
        )
        context["osm_place"] = named[0]["tags"]["name"]

    surfaces = {e.get("tags", {}).get("surface") for e in elements} - {None}
    if surfaces:
        context["osm_surface"] = sorted(surfaces)[0]

    return context


def commons_photo(lat: float, lng: float, place: str | None) -> dict | None:
    """Una foto da Wikimedia Commons, **solo se è di questo posto**.

    La sola vicinanza non basta, e non è un dettaglio: provando il campo su
    otto spot, la geosearch ha restituito una foto di cavi in fibra ottica e
    una chiesa bizantina, entrambe a meno di 150 m e nessuna delle due
    attinente. Attaccarle allo spot sarebbe stato inventare un dato — la stessa
    cosa che `clean_spots.py` ha appena finito di rimuovere.

    Perciò serve che il titolo dell'immagine contenga il nome del luogo
    identificato da OpenStreetMap. Meno foto, ma vere.
    """
    if not place or len(place) < 4:
        return None

    found = get_json(
        COMMONS,
        {
            "action": "query", "format": "json", "list": "geosearch",
            "gsradius": RADIUS_M, "gscoord": f"{lat}|{lng}",
            "gsnamespace": 6, "gslimit": 5,
        },
    )
    pages = (found or {}).get("query", {}).get("geosearch", [])
    needle = place.casefold()
    matching = [p for p in pages if needle in p["title"].casefold()]
    if not matching:
        return None

    title = matching[0]["title"]
    info = get_json(
        COMMONS,
        {
            "action": "query", "format": "json", "titles": title,
            "prop": "imageinfo", "iiprop": "url|extmetadata",
        },
    )
    for page in (info or {}).get("query", {}).get("pages", {}).values():
        for image in page.get("imageinfo", []):
            meta = image.get("extmetadata", {})
            licence = meta.get("LicenseShortName", {}).get("value")
            # Senza licenza nota non si pubblica: meglio nessuna foto che una
            # foto che non si può mostrare.
            if not licence:
                continue
            return {
                "url": image["url"],
                "author": _strip_html(meta.get("Artist", {}).get("value", "")),
                "license": licence,
                "source_url": image.get("descriptionurl"),
                "source": "wikimedia",
            }
    return None


def mapillary_photo(lat: float, lng: float, token: str) -> dict | None:
    """Una foto stradale da Mapillary — CC-BY-SA 4.0.

    È la sostituzione **lecita** degli hotlink a Street View che il BLOCCO 3
    rimuove: Mapillary ha un'API ufficiale e le immagini sono sotto licenza
    libera, purché si attribuisca.
    """
    d = RADIUS_M / 111_320
    bbox = f"{lng - d},{lat - d},{lng + d},{lat + d}"
    body = get_json(
        MAPILLARY,
        {"access_token": token, "bbox": bbox, "limit": 1, "fields": "id,thumb_1024_url,creator"},
    )
    for image in (body or {}).get("data", []):
        if not image.get("thumb_1024_url"):
            continue
        return {
            "url": image["thumb_1024_url"],
            "author": (image.get("creator") or {}).get("username"),
            "license": "CC-BY-SA 4.0",
            "source_url": f"https://www.mapillary.com/app/?pKey={image['id']}",
            "source": "mapillary",
        }
    return None


def _strip_html(value: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", value).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="quanti spot processare")
    parser.add_argument("--force", action="store_true", help="ignora la cache")
    args = parser.parse_args()

    token = os.environ.get("MAPILLARY_TOKEN")
    if not token:
        print(
            "MAPILLARY_TOKEN assente.\n"
            "  Mapillary è la sola fonte che dia foto **dello spot**: immagini\n"
            "  stradali alle coordinate, sotto CC-BY-SA. Senza token resta solo\n"
            "  Wikimedia, che scatta unicamente quando il nome del luogo\n"
            "  combacia — cioè quasi mai. Token gratuito su mapillary.com.\n"
        )

    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    todo = [
        s for s in spots
        if s.get("completeness") == "da_completare"
        and (args.force or s["id"] not in cache)
    ]
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(todo)} spot da arricchire (su {len(spots)} totali).\n")

    for i, spot in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {spot['name']}")
        found = osm_context(spot["lat"], spot["lng"])
        time.sleep(PAUSE_S)

        # Mapillary per primo: è immagine stradale **alle coordinate**, quindi
        # mostra davvero il posto. Commons è un ripiego che scatta di rado.
        photo = mapillary_photo(spot["lat"], spot["lng"], token) if token else None
        if not photo:
            photo = commons_photo(spot["lat"], spot["lng"], found.get("osm_place"))
        if photo:
            found["photo"] = photo

        cache[spot["id"]] = found
        CACHE.write_text(
            json.dumps(cache, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )

        bits = []
        if found.get("osm_place"):
            bits.append(f"luogo: {found['osm_place']}")
        if found.get("hasFountain"):
            bits.append("acqua")
        if found.get("photo"):
            bits.append(f"foto {found['photo']['source']}")
        print(f"    {', '.join(bits) if bits else 'niente di verificabile'}")

    # La cache si riversa sugli spot solo alla fine: così un'interruzione a
    # metà non lascia il dataset in uno stato ibrido.
    applied = 0
    for spot in spots:
        found = cache.get(spot["id"])
        if not found:
            continue

        place = found.get("osm_place")
        if place and spot["name"].startswith("Spot "):
            spot["name"] = place
            applied += 1

        if found.get("hasFountain") and spot.get("hasFountain") is None:
            spot["hasFountain"] = True

        if found.get("photo"):
            spot.setdefault("photos", [])
            urls = {p["url"] if isinstance(p, dict) else p for p in spot["photos"]}
            if found["photo"]["url"] not in urls:
                spot["photos"].append(found["photo"])

        if spot.get("photos") and spot.get("completeness") == "da_completare":
            spot["completeness"] = "arricchito"

    SPOTS.write_text(
        json.dumps(spots, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"\n{applied} toponimi reali applicati. Copertura: scripts/spot_coverage.mjs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
