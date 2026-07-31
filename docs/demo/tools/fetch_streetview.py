#!/usr/bin/env python3
"""Recupera il contesto Street View per gli spot del backup.

Per ogni spot in 📲/backup-quotidiano.json interroga l'endpoint pubblico
GeoPhotoService.SingleImageSearch (lo stesso usato dal sito di Google Maps,
nessuna API key richiesta) e trova il panorama Street View più vicino.
Calcola poi l'angolo di ripresa (yaw) dal panorama verso lo spot, così la
miniatura inquadra davvero lo spot e non la strada a caso.

Output: docs/demo/spots-streetview.json e, per far funzionare la pagina anche
aperta come file locale (senza server), gli stessi dati vengono iniettati in
docs/demo/spots-street-view.html tra i marker SPOTS_DATA_START/END.

Uso:
    python3 docs/demo/tools/fetch_streetview.py
"""

import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BACKUP = REPO / "📲" / "backup-quotidiano.json"
OUT = REPO / "docs" / "demo" / "spots-streetview.json"
HTML = REPO / "docs" / "demo" / "spots-street-view.html"

SEARCH_URL = (
    "https://maps.googleapis.com/maps/api/js/GeoPhotoService.SingleImageSearch"
    "?pb=!1m5!1sapiv3!5sUS!11m2!1m1!1b0!2m4!1m2!3d{lat}!4d{lng}!2d{radius}"
    "!3m10!2m2!1sen!2sUS!9m1!1e2!11m4!1m3!1e2!2b1!3e2"
    "!4m10!1e1!1e2!1e3!1e4!1e8!1e6!5m1!1e2!6m1!1e2&callback=cb"
)

RADII = [50, 120, 300, 600]  # metri: allarga la ricerca se lo spot è dentro un parco


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", errors="replace")


def bearing(lat1, lng1, lat2, lng2) -> float:
    """Bearing iniziale in gradi da (lat1,lng1) a (lat2,lng2)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lng2 - lng1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def distance_m(lat1, lng1, lat2, lng2) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_pano(lat: float, lng: float):
    """Ritorna (pano_id, pano_lat, pano_lng, data 'YYYY-MM' | None) o None."""
    for radius in RADII:
        raw = http_get(SEARCH_URL.format(lat=lat, lng=lng, radius=radius))
        m = re.search(r"cb\(\s*(.*)\s*\)\s*$", raw, re.S)
        if not m:
            continue
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list) or len(data) < 2 or not data[1]:
            continue  # nessun panorama in questo raggio
        blob = m.group(1)
        pano = re.search(r'\[2,"([A-Za-z0-9_-]{20,24})"\]', blob)
        coords = re.search(r"\[null,null,(4\d\.\d+),(1\d\.\d+)\]", blob)
        if not pano or not coords:
            continue
        dates = re.findall(r"\[(20\d\d),(\d{1,2})\]", blob)
        date = f"{dates[-1][0]}-{int(dates[-1][1]):02d}" if dates else None
        return pano.group(1), float(coords.group(1)), float(coords.group(2)), date
    return None


def main() -> int:
    backup = json.loads(BACKUP.read_text())
    spots = backup["tabelle"]["spots"]
    out = []
    for s in spots:
        lat, lng = s["lat"], s["lng"]
        found = find_pano(lat, lng)
        entry = {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "lat": lat,
            "lng": lng,
            "skill_level": s["skill_level"],
            "crowd_level": s["crowd_level"],
            "has_fountain": s["has_fountain"],
            "streetview": None,
        }
        if found:
            pano_id, plat, plng, date = found
            yaw = round(bearing(plat, plng, lat, lng), 1)
            entry["streetview"] = {
                "pano_id": pano_id,
                "pano_lat": plat,
                "pano_lng": plng,
                "yaw": yaw,
                "date": date,
                "distance_m": round(distance_m(plat, plng, lat, lng)),
            }
            print(f"✓ {s['name']}: pano {pano_id} a {entry['streetview']['distance_m']} m, yaw {yaw}°, {date}")
        else:
            print(f"✗ {s['name']}: nessun panorama trovato entro {RADII[-1]} m")
        out.append(entry)

    payload = {"generated_from": str(BACKUP.name), "spots": out}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"\nScritto {OUT.relative_to(REPO)} ({len(out)} spot)")

    if HTML.exists():
        html = HTML.read_text()
        block = (
            "/* SPOTS_DATA_START */\n"
            f"const DATA = {json.dumps(payload, ensure_ascii=False)};\n"
            "/* SPOTS_DATA_END */"
        )
        new_html, n = re.subn(
            r"/\* SPOTS_DATA_START \*/.*?/\* SPOTS_DATA_END \*/", block, html, flags=re.S
        )
        if n:
            HTML.write_text(new_html)
            print(f"Dati iniettati in {HTML.relative_to(REPO)}")
        else:
            print("ATTENZIONE: marker SPOTS_DATA non trovati nell'HTML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
