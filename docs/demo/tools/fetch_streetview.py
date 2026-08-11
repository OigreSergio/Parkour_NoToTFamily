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

# Correzioni manuali all'inquadratura alternativa (feedback della community):
# nome spot → pano_id da usare come seconda angolazione. Serve quando la
# scelta automatica becca un'inquadratura sfortunata (es. furgone davanti).
ALT_OVERRIDES = {
    "Spot NoToT Game": "CbFPxk2sJSbkDUQ4Zr24gw",  # piazzetta coi muretti, senza furgone
}


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


def find_pano(lat: float, lng: float, with_alt: bool = False, preferred_alt: str | None = None):
    """Trova il panorama più vicino allo spot.

    Ritorna (pano_id, pano_lat, pano_lng, data 'YYYY-MM' | None) o None.
    Con with_alt=True ritorna (primario, alternativo | None): l'alternativo è
    un secondo panorama ad almeno 8 m dal primario — una vera seconda
    inquadratura dello stesso posto, usata come "foto" per gli spot senza
    immagini trovate online.
    """
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
        primary = (pano.group(1), float(coords.group(1)), float(coords.group(2)), date)
        if not with_alt:
            return primary
        alts = re.findall(
            r'\[\[2,"([A-Za-z0-9_-]{20,24})"\],null,\[\[null,null,(4\d\.\d+),(1\d\.\d+)\]', blob
        )
        best = None
        for aid, alat, alng in alts:
            alat, alng = float(alat), float(alng)
            if preferred_alt and aid == preferred_alt:
                best = (0, (aid, alat, alng, None))
                break
            if aid == primary[0] or distance_m(primary[1], primary[2], alat, alng) < 8:
                continue  # stesso pano o troppo vicino: stessa inquadratura
            d = distance_m(alat, alng, lat, lng)
            if best is None or d < best[0]:
                best = (d, (aid, alat, alng, None))
        return primary, (best[1] if best else None)
    return (None, None) if with_alt else None


def comments_by_spot(tables: dict) -> dict[str, list[dict]]:
    """Group the real community comments by spot id.

    The page is (at most) a place to *read* real comments — nothing is ever
    written from here. Tolerant to schema drift: a comment may reference the
    spot directly (`spot_id`) or through its post (`post_id` → posts.spot_id),
    and the text may live in `body`, `content` or `text`.
    """
    profiles = {p.get("id"): p.get("username") or "membro" for p in tables.get("profiles", [])}
    posts = {p.get("id"): p for p in tables.get("posts", [])}
    grouped: dict[str, list[dict]] = {}
    for c in tables.get("comments", []):
        spot_id = c.get("spot_id")
        if not spot_id and c.get("post_id") in posts:
            spot_id = posts[c["post_id"]].get("spot_id")
        if not spot_id:
            continue
        body = c.get("body") or c.get("content") or c.get("text") or ""
        if not body:
            continue
        grouped.setdefault(spot_id, []).append(
            {
                "author": profiles.get(c.get("author_id") or c.get("user_id"), "membro"),
                "body": body,
                "created_at": c.get("created_at"),
            }
        )
    return grouped


def main() -> int:
    backup = json.loads(BACKUP.read_text())
    spots = backup["tabelle"]["spots"]
    spot_comments = comments_by_spot(backup["tabelle"])
    out = []
    def to_sv(pano, lat, lng):
        pano_id, plat, plng, date = pano
        return {
            "pano_id": pano_id,
            "pano_lat": plat,
            "pano_lng": plng,
            "yaw": round(bearing(plat, plng, lat, lng), 1),
            "date": date,
            "distance_m": round(distance_m(plat, plng, lat, lng)),
        }

    for s in spots:
        lat, lng = s["lat"], s["lng"]
        found, alt = find_pano(lat, lng, with_alt=True, preferred_alt=ALT_OVERRIDES.get(s["name"]))
        entry = {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "lat": lat,
            "lng": lng,
            "skill_level": s["skill_level"],
            "crowd_level": s["crowd_level"],
            "has_fountain": s["has_fountain"],
            "comments": spot_comments.get(s["id"], []),
            "streetview": None,
            "streetview_alt": None,
        }
        if found:
            entry["streetview"] = to_sv(found, lat, lng)
            if alt:
                entry["streetview_alt"] = to_sv(alt, lat, lng)
            sv = entry["streetview"]
            alt_txt = (
                f" + alt a {entry['streetview_alt']['distance_m']} m"
                if entry["streetview_alt"]
                else ""
            )
            print(f"✓ {s['name']}: pano {sv['pano_id']} a {sv['distance_m']} m, yaw {sv['yaw']}°{alt_txt}")
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
