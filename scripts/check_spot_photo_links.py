#!/usr/bin/env python3
"""Controlla che i link alle foto degli spot siano ancora validi.

Le foto del web sono in hotlink: se la fonte cambia regole o sposta il file,
nell'app resta un riquadro vuoto senza che nessuno se ne accorga. Questo
script controlla i tre punti in cui vivono gli URL:

- i ``manifest.json`` in docs/spots/photos/<slug>/
- ``photos`` in scripts/data/webapp_fixed_spots.json e ``photo_urls`` in
  backend/seeds/spots.json
- ``photo.src`` in docs/demo/pk-scheda.js

Wikimedia Commons dal 2025 **rifiuta** l'hotlink dei thumb in misure non
standard (T360589): sono ammesse solo le larghezze in ``COMMONS_WIDTHS``.
Un thumb da 1600px oggi risponde 400, non l'immagine. Il controllo offline
(default) segnala queste misure; con ``--online`` fa anche una HEAD su ogni
URL, distanziata nel tempo perché Commons applica un rate limit severo.

Uso::

    python3 scripts/check_spot_photo_links.py
    python3 scripts/check_spot_photo_links.py --online --pausa 3
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PHOTOS_ROOT = REPO / "docs" / "spots" / "photos"
WEBAPP_JSON = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
SEED_JSON = REPO / "backend" / "seeds" / "spots.json"
PK_SCHEDA = REPO / "docs" / "demo" / "pk-scheda.js"

# https://www.mediawiki.org/wiki/Common_thumbnail_sizes
COMMONS_WIDTHS = {20, 40, 60, 120, 250, 330, 500, 960, 1280, 1920, 3840}
THUMB = re.compile(r"^https://upload\.wikimedia\.org/wikipedia/commons/thumb/.+?/(\d+)px-[^/]+$")
UA = "Mozilla/5.0 (compatible; PkFamilyMap/1.0; controllo link foto spot)"


def sources() -> list[tuple[str, str]]:
    """Tutti gli URL delle foto, con l'etichetta di dove stanno."""
    found: list[tuple[str, str]] = []
    for mf in sorted(PHOTOS_ROOT.glob("*/manifest.json")):
        for e in json.loads(mf.read_text(encoding="utf8")):
            found.append((f"manifest/{mf.parent.name}", e["image_url"]))
    if WEBAPP_JSON.exists():
        for s in json.loads(WEBAPP_JSON.read_text(encoding="utf8")):
            for u in s.get("photos") or []:
                found.append((f"webapp/{s['name']}", u))
    if SEED_JSON.exists():
        for s in json.loads(SEED_JSON.read_text(encoding="utf8")):
            for u in s.get("photo_urls") or []:
                found.append((f"seed/{s['name']}", u))
    if PK_SCHEDA.exists():
        text = PK_SCHEDA.read_text(encoding="utf8")
        for m in re.finditer(r'"photo":\s*\{"src":\s*"([^"]+)"', text):
            found.append(("pk-scheda", m.group(1).encode().decode("unicode_escape")))
    return found


def bad_width(url: str) -> int | None:
    """Larghezza del thumb Commons se non è tra quelle ammesse."""
    m = THUMB.match(url.split("?")[0])
    if not m:
        return None
    width = int(m.group(1))
    return None if width in COMMONS_WIDTHS else width


def reachable(url: str) -> str:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return "ok" if r.status == 200 else f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:  # rete, DNS, timeout
        return f"errore: {type(e).__name__}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--online", action="store_true", help="verifica anche con una HEAD")
    ap.add_argument("--pausa", type=float, default=3.0, help="secondi tra due richieste")
    args = ap.parse_args()

    urls = sources()
    print(f"{len(urls)} link da controllare in manifest, webapp, seed e pk-scheda\n")

    problemi = []
    for where, url in urls:
        width = bad_width(url)
        if width:
            problemi.append((where, url, f"thumb {width}px: misura non ammessa da Commons"))

    if args.online:
        visti: dict[str, str] = {}
        for where, url in urls:
            if url not in visti:
                visti[url] = reachable(url)
                time.sleep(args.pausa)
            if visti[url] != "ok":
                problemi.append((where, url, visti[url]))

    if not problemi:
        print("Tutti i link sono a posto.")
        return 0

    print(f"{len(problemi)} link da sistemare:\n")
    for where, url, why in problemi:
        print(f"- [{where}] {why}\n  {url}")
    print("\nPer i thumb Commons: usare una larghezza tra "
          + ", ".join(f"{w}px" for w in sorted(COMMONS_WIDTHS)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
