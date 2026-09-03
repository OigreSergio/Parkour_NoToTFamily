#!/usr/bin/env python3
"""Trova un'inquadratura Street View per ogni spot della mappa.

Dal satellite molti spot non si vedono: alberi, tettoie e palazzi coprono
quello che c'è a terra. Street View invece guarda lo spot da dove ci si
arriva a piedi. Per ogni spot di ``scripts/data/webapp_fixed_spots.json``
questo script interroga l'endpoint pubblico ``GeoPhotoService.SingleImageSearch``
(lo stesso usato dal sito di Google Maps, nessuna API key) e salva il panorama
più vicino con l'angolo di ripresa (yaw) calcolato *verso* lo spot, così la
miniatura inquadra il posto giusto e non la strada a caso.

Output: ``scripts/data/spot_streetview.json`` — { spot_id: {pano_id, pano_lat,
pano_lng, yaw, date, distance_m} }. Lo script è ripartibile: rilanciato, salta
gli spot già risolti.

Uso::

    python3 scripts/fetch_spot_streetview.py [--limit N] [--workers N]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPOTS = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
OUT = REPO / "scripts" / "data" / "spot_streetview.json"

SEARCH_URL = (
    "https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch"
    "?pb=!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{lat}!4d{lng}!2d{radius}"
    "!3m10!2m2!1sen!2sUS!9m1!1e2!11m4!1m3!1e2!2b1!3e2"
    "!4m10!1e1!1e2!1e3!1e4!1e8!1e6!5m1!1e2!6m1!1e2&callback=cb"
)

# Raggi di ricerca in metri: si allarga solo se il primo giro non trova nulla.
RADII = (40, 120, 300)

# Oltre questa distanza il panorama non inquadra più lo spot: meglio il satellite.
MAX_PANO_DISTANCE_M = 180

PANO_RE = re.compile(r'\[2,"([A-Za-z0-9_-]{20,24})"\]')
COORD_RE = re.compile(r"\[null,null,(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)\]")
DATE_RE = re.compile(r"\[(20\d\d),(\d{1,2})\]")

_lock = threading.Lock()


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", errors="replace")


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Direzione in gradi da (lat1,lng1) verso (lat2,lng2)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lng2 - lng1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def find_pano(lat: float, lng: float) -> dict | None:
    """Panorama più vicino a (lat, lng), già puntato verso lo spot."""
    for radius in RADII:
        try:
            blob = http_get(SEARCH_URL.format(lat=lat, lng=lng, radius=radius))
        except Exception:
            continue
        pano = PANO_RE.search(blob)
        coords = COORD_RE.search(blob)
        if not pano or not coords:
            continue
        pano_lat, pano_lng = float(coords.group(1)), float(coords.group(2))
        distance = distance_m(pano_lat, pano_lng, lat, lng)
        if distance > MAX_PANO_DISTANCE_M:
            continue
        dates = DATE_RE.findall(blob)
        return {
            "pano_id": pano.group(1),
            "pano_lat": round(pano_lat, 7),
            "pano_lng": round(pano_lng, 7),
            # Guarda verso lo spot, non lungo la strada.
            "yaw": round(bearing(pano_lat, pano_lng, lat, lng), 1),
            "date": f"{dates[-1][0]}-{int(dates[-1][1]):02d}" if dates else None,
            "distance_m": round(distance),
        }
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="solo i primi N spot da risolvere")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    found: dict = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}

    todo = [s for s in spots if str(s["id"]) not in found]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(spots)} spot totali, {len(found)} già risolti, {len(todo)} da cercare")

    done = 0

    def work(spot: dict) -> None:
        nonlocal done
        pano = find_pano(float(spot["lat"]), float(spot["lng"]))
        with _lock:
            found[str(spot["id"])] = pano  # None = nessun panorama utile
            done += 1
            if done % 50 == 0 or done == len(todo):
                hits = sum(1 for v in found.values() if v)
                print(f"  {done}/{len(todo)} — con Street View: {hits}", flush=True)
                OUT.write_text(
                    json.dumps(found, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
                )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(work, todo))

    OUT.write_text(json.dumps(found, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    hits = sum(1 for v in found.values() if v)
    print(f"fatto: {hits}/{len(found)} spot con un'inquadratura Street View")


if __name__ == "__main__":
    main()
