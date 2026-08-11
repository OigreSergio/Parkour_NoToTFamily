#!/usr/bin/env python3
"""Collega agli spot le foto trovate sul web (hotlink dalle fonti).

Legge i ``manifest.json`` in docs/spots/photos/<slug>/ — ognuno è un array
di voci {"file","source_page","image_url","author","license"} raccolte e
verificate visivamente una a una (Wikimedia Commons in primis) — e scrive:

- ``photos`` + ``photosCount`` nello spot corrispondente di
  scripts/data/webapp_fixed_spots.json (slug = slugify(name));
- ``photo_urls`` nello spot omonimo di backend/seeds/spots.json, se esiste.

Le immagini NON vengono copiate nel repo: si usano gli URL sorgente
(gli originali di Commons sono ridotti al thumb da 1280px). Attribuzioni
e licenze restano documentate nei manifest.

Uso: python3 scripts/wire_spot_photos.py
"""

import json
import re
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PHOTOS_ROOT = REPO / "docs" / "spots" / "photos"
WEBAPP_JSON = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
SEED_JSON = REPO / "backend" / "seeds" / "spots.json"

COMMONS = re.compile(
    r"^https://upload\.wikimedia\.org/wikipedia/commons/"
    r"(?:thumb/)?([0-9a-f])/([0-9a-f]{2})/([^/?]+?)(?:/\d+px-[^/?]+)?$")
UA = "PkFamilyMap/1.0 (collegamento foto spot; repo Parkour_NoToTFamily)"


def slugify(name):
    a = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", a.lower()).strip("-")


def reachable(url):
    """HEAD con retry: Commons applica rate limit alle richieste ravvicinate."""
    import time
    import urllib.error
    import urllib.request
    for attempt in range(4):
        time.sleep(0.4 if attempt == 0 else 3 * attempt)
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status == 200
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                continue  # rate limit: riprova
            return False
        except Exception:
            continue
    return False


def display_url(image_url):
    """URL Commons (originale o thumb di qualunque taglia) -> thumb 1280px,
    con fallback sull'originale se il thumb non è disponibile (immagini più
    piccole di 1280px). Ogni altro URL resta com'è."""
    image_url = image_url.split("?")[0]
    m = COMMONS.match(image_url)
    if not m:
        return image_url
    d1, d2, name = m.groups()
    original = f"https://upload.wikimedia.org/wikipedia/commons/{d1}/{d2}/{name}"
    thumb = (f"https://upload.wikimedia.org/wikipedia/commons/thumb/"
             f"{d1}/{d2}/{name}/1280px-{name}")
    if reachable(thumb):
        return thumb
    print(f"   thumb non disponibile, uso l'originale: {name}")
    return original


def main():
    webapp = json.loads(WEBAPP_JSON.read_text(encoding="utf8"))
    seeds = json.loads(SEED_JSON.read_text(encoding="utf8"))
    by_slug = {slugify(s["name"]): s for s in webapp}
    seed_by_slug = {slugify(s["name"]): s for s in seeds}

    wired = 0
    for mf in sorted(PHOTOS_ROOT.glob("*/manifest.json")):
        slug = mf.parent.name
        entries = json.loads(mf.read_text(encoding="utf8"))
        if not entries:
            continue
        spot = by_slug.get(slug)
        if spot is None:
            print(f"!! manifest {slug} senza spot corrispondente, salto")
            continue
        urls = [display_url(e["image_url"]) for e in entries]
        spot["photos"] = urls
        spot["photosCount"] = len(urls)
        if slug in seed_by_slug:
            seed_by_slug[slug]["photo_urls"] = urls
        wired += 1
        print(f"{slug}: {len(urls)} foto")

    WEBAPP_JSON.write_text(json.dumps(webapp, ensure_ascii=False) + "\n", encoding="utf8")
    SEED_JSON.write_text(json.dumps(seeds, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"{wired} spot con foto collegate")


if __name__ == "__main__":
    main()
