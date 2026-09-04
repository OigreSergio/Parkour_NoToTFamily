#!/usr/bin/env python3
"""Raccoglie da OpenStreetMap l'acqua potabile vicino agli spot.

L'app oggi interroga Overpass ogni volta che si apre uno spot: funziona, ma è
lenta, soggetta ai limiti dei mirror e inutile senza rete. Questo script fa
la stessa domanda una volta sola per tutti gli spot e salva il risultato, così
l'app risponde all'istante e anche offline (Overpass resta come aggiornamento).

L'ordine è quello chiesto: **prima Roma**, poi il resto d'Italia, poi l'Europa,
infine gli altri continenti. Il file cresce man mano, quindi interrompere lo
script lascia comunque i dati delle aree già fatte.

Non si chiede uno spot per volta. Gli spot si addensano nelle città, e chiedere
"tutta l'acqua dentro questo riquadro" costa a Overpass molto meno di trenta
cerchi separati: gli spot vengono raggruppati per riquadro (vedi [cells]) e per
ognuno parte una domanda sola, poi le distanze si calcolano qui. In Italia un
riquadro copre in media una decina di spot, e la corsa passa da ore a minuti.

Output: ``scripts/data/spot_water.json`` — { spot_id: [ {lat, lng, kind, name,
distance_m, osm_id}, ... ] }, ordinato per distanza.

Uso::

    python3 scripts/fetch_water_points.py [--radius 400] [--cell 0.25] [--area roma]
                                          [--out altrove.json]
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

# Solo mirror **globali**. Ce ne sono di regionali (overpass.osm.ch tiene la
# sola Svizzera) che rispondono 200 con zero risultati per il resto del mondo:
# entrerebbero nel file come "qui non c'è acqua" senza che nulla segnali
# l'errore. Prima di aggiungerne uno, chiedigli un nodo lontano da casa sua.
MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

USER_AGENT = "PkFAMILY/1.0 (mappa spot parkour; fontanelle da OpenStreetMap)"

# I mirror rispondono 429 o 504 spesso: si insiste a lungo, con attese che
# crescono, perché una corsa intera dura ore e ricominciarla costa di più.
MAX_ATTEMPTS = 8


def _backoff(attempt: int) -> float:
    return min(5 * 2**attempt, 120)

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
        if attempt >= MAX_ATTEMPTS:
            raise
        time.sleep(_backoff(attempt))
        return overpass(query, attempt + 1)
    except (urllib.error.URLError, TimeoutError, OSError):
        if attempt >= MAX_ATTEMPTS:
            raise
        # 429/504 sono la norma su Overpass: si aspetta e si cambia specchio.
        time.sleep(_backoff(attempt))
        return overpass(query, attempt + 1)


def cells(spots: list[dict], size: float) -> list[list[dict]]:
    """Raggruppa gli spot in riquadri di ``size`` gradi, nell'ordine dato.

    Il riquadro serve solo a mettere insieme spot vicini: la domanda vera usa
    l'ingombro degli spot che ci sono finiti dentro, che in città è molto più
    piccolo della cella.
    """
    groups: dict[tuple[int, int], list[dict]] = {}
    for spot in spots:
        key = (
            math.floor(float(spot["lat"]) / size),
            math.floor(float(spot["lng"]) / size),
        )
        groups.setdefault(key, []).append(spot)
    return list(groups.values())


def bbox_of(group: list[dict], radius: int) -> tuple[float, float, float, float]:
    """Ingombro degli spot, allargato di ``radius`` metri per non tagliare nulla."""
    lats = [float(s["lat"]) for s in group]
    lngs = [float(s["lng"]) for s in group]
    pad_lat = radius / 111_320
    # Ai poli un grado di longitudine vale pochi metri: il coseno lo tiene conto,
    # con un minimo per non far esplodere il riquadro (o dividere per zero).
    widest = max(abs(min(lats)), abs(max(lats)))
    pad_lng = radius / (111_320 * max(math.cos(math.radians(widest)), 0.05))
    return (
        min(lats) - pad_lat,
        min(lngs) - pad_lng,
        max(lats) + pad_lat,
        max(lngs) + pad_lng,
    )


def collect(group: list[dict], radius: int) -> list[tuple[list[dict], list[dict]]]:
    """Coppie (spot, nodi del loro riquadro), spezzando il gruppo quando serve.

    Un riquadro può non passare per due motivi: è troppo grande e il mirror non
    ce la fa in tempo (429/504, dopo tutti i tentativi), oppure l'URL è troppo
    lungo (414). In entrambi i casi la risposta è la stessa — chiedere di meno
    per volta — fino a un solo spot, che se proprio non passa viene lasciato
    indietro: la raccolta è lunga e non deve morire per un riquadro sfortunato.

    Le metà tornano separate, ognuna con i *suoi* nodi. È la parte che conta:
    mettendole in un mucchio solo, gli spot di una metà rimasta senza risposta
    verrebbero misurati sui nodi dell'altra e finirebbero nel file come "poca
    acqua qui" senza che nessuno se ne accorga. Chi non ha risposta non compare
    affatto, così non entra nel file e la corsa successiva lo ripesca.
    """
    try:
        data = overpass(build_query(bbox_of(group, radius)))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as error:
        if len(group) == 1:
            print(f"  lasciato indietro 1 spot ({error})", flush=True)
            return []
        half = len(group) // 2
        return collect(group[:half], radius) + collect(group[half:], radius)
    nodes = [e for e in data.get("elements", []) if "lat" in e and "lon" in e]
    return [(group, nodes)]


def build_query(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    box = f"({south:.6f},{west:.6f},{north:.6f},{east:.6f})"
    return (
        "[out:json][timeout:180];("
        f'node["amenity"="drinking_water"]{box};'
        f'node["man_made"="water_tap"]{box};'
        f'node["natural"="spring"]["drinking_water"="yes"]{box};'
        f'node["amenity"="fountain"]["drinking_water"="yes"]{box};'
        ");out body;"
    )


def water_near(spot: dict, nodes: list[dict], radius: int) -> list[dict]:
    """Le fontanelle entro ``radius`` metri dallo spot, dalla più vicina."""
    lat, lng = float(spot["lat"]), float(spot["lng"])
    near = []
    for node in nodes:
        tags = node.get("tags", {})
        if tags.get("drinking_water") == "no":
            continue
        distance = distance_m(lat, lng, node["lat"], node["lon"])
        if distance > radius:
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
    return near


def kind_of(tags: dict) -> str:
    return tags.get("man_made") or tags.get("natural") or tags.get("amenity") or "drinking_water"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--radius", type=int, default=400, help="metri attorno allo spot")
    parser.add_argument("--cell", type=float, default=0.25, help="lato del riquadro, in gradi")
    parser.add_argument("--area", choices=[a for a, _ in AREAS], help="ferma dopo quest'area")
    parser.add_argument("--pause", type=float, default=2.0, help="secondi fra le interrogazioni")
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help="dove scrivere (di suo il file nel repo; una corsa lunga può "
        "tenerlo fuori, così l'albero di git non cambia sotto i piedi)",
    )
    args = parser.parse_args()

    out: Path = args.out
    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    found: dict[str, list] = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}

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

    groups = cells(todo, args.cell)
    print(f"  {len(groups)} riquadri da interrogare")

    skipped_spots = 0
    asked = 0
    for group in groups:
        answered = collect(group, args.radius)
        answered_spots = [spot for sub, _ in answered for spot in sub]
        skipped_spots += len(group) - len(answered_spots)
        if not answered:
            time.sleep(args.pause)
            continue

        for sub, nodes in answered:
            for spot in sub:
                found[str(spot["id"])] = water_near(spot, nodes, args.radius)

        asked += len(answered_spots)
        with_water = sum(1 for v in found.values() if v)
        area = area_of(float(answered_spots[0]["lat"]), float(answered_spots[0]["lng"]))
        print(
            f"  [{area}] {asked}/{len(todo)} — spot con acqua vicina: {with_water}",
            flush=True,
        )
        out.write_text(json.dumps(found, ensure_ascii=False) + "\n", encoding="utf-8")
        time.sleep(args.pause)

    with_water = sum(1 for v in found.values() if v)
    points = sum(len(v) for v in found.values())
    print(f"fatto: {with_water}/{len(found)} spot hanno acqua entro {args.radius} m ({points} punti)")
    if skipped_spots:
        print(f"  {skipped_spots} spot lasciati indietro: rilancia lo script per riprenderli")


if __name__ == "__main__":
    main()
