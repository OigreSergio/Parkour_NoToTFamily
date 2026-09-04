#!/usr/bin/env python3
"""Raccoglie da OpenStreetMap l'acqua potabile vicino agli spot.

L'app oggi interroga Overpass ogni volta che si apre uno spot: funziona, ma è
lenta, soggetta ai limiti dei mirror e inutile senza rete. Questo script fa
la stessa domanda una volta sola per tutti gli spot e salva il risultato, così
l'app risponde all'istante e anche offline (Overpass resta come aggiornamento).

L'ordine è quello chiesto: **prima Roma**, poi il resto d'Italia, poi l'Europa,
infine gli altri continenti. Il file cresce man mano, quindi interrompere lo
script lascia comunque i dati delle aree già fatte.

Output: ``scripts/data/spot_water.json`` — { spot_id: [ {lat, lng, kind, name,
distance_m, osm_id}, ... ] }, ordinato per distanza.

Uso::

    python3 scripts/fetch_water_points.py [--radius 400] [--batch 20] [--area roma]
"""

from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPOTS = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
OUT = REPO / "scripts" / "data" / "spot_water.json"

MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

USER_AGENT = "PkFAMILY/1.0 (mappa spot parkour; fontanelle da OpenStreetMap)"

# Roma prima, poi l'Italia, poi l'Europa, poi tutto il resto: riquadri
# (sud, ovest, nord, est) usati solo per decidere l'ordine di lavoro.
AREAS: tuple[tuple[str, tuple[float, float, float, float] | None], ...] = (
    ("roma", (41.75, 12.30, 42.05, 12.70)),
    ("italia", (35.29, 6.60, 47.10, 18.80)),
    ("europa", (34.50, -25.00, 71.20, 45.00)),
    ("mondo", None),
)


def in_box(lat: float, lng: float, box: tuple[float, float, float, float]) -> bool:
    south, west, north, east = box
    return south <= lat <= north and west <= lng <= east


def area_of(lat: float, lng: float) -> str:
    for name, box in AREAS:
        if box is None or in_box(lat, lng, box):
            return name
    return "mondo"


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def overpass(query: str, attempt: int = 0) -> dict:
    """Interroga un mirror; ruota e aspetta quando è occupato.

    La domanda viaggia in GET (il POST non attraversa alcuni proxy): oltre una
    quindicina di spot per volta l'URL supera la lunghezza massima e i mirror
    rispondono 414, per cui chi chiama spezza il gruppo — vedi [ask_about].
    """
    mirror = MIRRORS[attempt % len(MIRRORS)]
    url = mirror + "?" + urllib.parse.urlencode({"data": query})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as error:
        if error.code == 414:  # URL troppo lungo: lo risolve chi chiama
            raise
        if attempt >= 5:
            raise
        time.sleep(5 * (attempt + 1))
        return overpass(query, attempt + 1)
    except (urllib.error.URLError, TimeoutError, OSError):
        if attempt >= 5:
            raise
        # 429/504 sono la norma su Overpass: si aspetta e si cambia specchio.
        time.sleep(5 * (attempt + 1))
        return overpass(query, attempt + 1)


def ask_about(batch: list[dict], radius: int) -> list[dict]:
    """Nodi d'acqua attorno a un gruppo di spot, spezzandolo se l'URL è lungo."""
    try:
        data = overpass(build_query(batch, radius))
    except urllib.error.HTTPError as error:
        if error.code != 414 or len(batch) == 1:
            raise
        half = len(batch) // 2
        return ask_about(batch[:half], radius) + ask_about(batch[half:], radius)
    return [e for e in data.get("elements", []) if "lat" in e and "lon" in e]


def build_query(batch: list[dict], radius: int) -> str:
    parts = []
    for spot in batch:
        lat, lng = float(spot["lat"]), float(spot["lng"])
        parts.append(f'node(around:{radius},{lat},{lng})["amenity"="drinking_water"];')
        parts.append(f'node(around:{radius},{lat},{lng})["man_made"="water_tap"];')
        parts.append(
            f'node(around:{radius},{lat},{lng})["natural"="spring"]["drinking_water"="yes"];'
        )
        parts.append(
            f'node(around:{radius},{lat},{lng})["amenity"="fountain"]["drinking_water"="yes"];'
        )
    return "[out:json][timeout:180];(" + "".join(parts) + ");out body;"


def kind_of(tags: dict) -> str:
    return tags.get("man_made") or tags.get("natural") or tags.get("amenity") or "drinking_water"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=int, default=400, help="metri attorno allo spot")
    parser.add_argument("--batch", type=int, default=12, help="spot per interrogazione")
    parser.add_argument("--area", choices=[a for a, _ in AREAS], help="ferma dopo quest'area")
    parser.add_argument("--pause", type=float, default=2.0, help="secondi fra le interrogazioni")
    args = parser.parse_args()

    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    found: dict[str, list] = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}

    order = {name: i for i, (name, _) in enumerate(AREAS)}
    todo = [s for s in spots if str(s["id"]) not in found]
    todo.sort(key=lambda s: order[area_of(float(s["lat"]), float(s["lng"]))])
    if args.area:
        limit = order[args.area]
        todo = [s for s in todo if order[area_of(float(s["lat"]), float(s["lng"]))] <= limit]

    print(f"{len(spots)} spot, {len(found)} già fatti, {len(todo)} da interrogare")
    by_area: dict[str, int] = {}
    for spot in todo:
        by_area[area_of(float(spot["lat"]), float(spot["lng"]))] = (
            by_area.get(area_of(float(spot["lat"]), float(spot["lng"])), 0) + 1
        )
    print("  per area:", ", ".join(f"{k}={v}" for k, v in by_area.items()))

    for start in range(0, len(todo), args.batch):
        batch = todo[start : start + args.batch]
        nodes = ask_about(batch, args.radius)

        for spot in batch:
            lat, lng = float(spot["lat"]), float(spot["lng"])
            near = []
            for node in nodes:
                tags = node.get("tags", {})
                if tags.get("drinking_water") == "no":
                    continue
                distance = distance_m(lat, lng, node["lat"], node["lon"])
                if distance > args.radius:
                    continue
                near.append(
                    {
                        "osm_id": node["id"],
                        "lat": round(node["lat"], 6),
                        "lng": round(node["lon"], 6),
                        "kind": kind_of(tags),
                        "name": tags.get("name"),
                        "distance_m": round(distance),
                    }
                )
            near.sort(key=lambda w: w["distance_m"])
            found[str(spot["id"])] = near

        with_water = sum(1 for v in found.values() if v)
        area = area_of(float(batch[0]["lat"]), float(batch[0]["lng"]))
        print(
            f"  [{area}] {min(start + args.batch, len(todo))}/{len(todo)} — "
            f"spot con acqua vicina: {with_water}",
            flush=True,
        )
        OUT.write_text(json.dumps(found, ensure_ascii=False) + "\n", encoding="utf-8")
        time.sleep(args.pause)

    with_water = sum(1 for v in found.values() if v)
    points = sum(len(v) for v in found.values())
    print(f"fatto: {with_water}/{len(found)} spot hanno acqua entro {args.radius} m ({points} punti)")


if __name__ == "__main__":
    main()
