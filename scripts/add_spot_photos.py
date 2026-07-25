#!/usr/bin/env python3
"""Ottimizza le foto di uno spot e aggiorna ``photo_urls`` nel seed.

Prende una o più immagini (in qualunque formato/risoluzione, anche appena
caricate via GitHub web), le normalizza in JPEG max 1600px sotto
``docs/spots/photos/<slug>/`` e riscrive ``photo_urls`` dello spot
corrispondente in ``backend/seeds/spots.json`` con gli URL raw di GitHub.

Uso::

    python scripts/add_spot_photos.py "Spot verso la metro Cipro" foto1.jpg foto2.heic ...

Richiede Pillow (``pip install pillow``). Le immagini sorgente possono stare
ovunque; quelle già presenti nella cartella dello spot vengono sostituite.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

REPO_ROOT = Path(__file__).resolve().parents[1]
PHOTOS_ROOT = REPO_ROOT / "docs" / "spots" / "photos"
SEED_FILE = REPO_ROOT / "backend" / "seeds" / "spots.json"
RAW_BASE = "https://raw.githubusercontent.com/OigreSergio/Parkour_NoToTFamily/main/docs/spots/photos"
MAX_SIDE = 1600
JPEG_QUALITY = 82


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    spot_name, sources = sys.argv[1], [Path(p) for p in sys.argv[2:]]
    missing = [p for p in sources if not p.is_file()]
    if missing:
        print(f"File non trovati: {', '.join(map(str, missing))}")
        return 1

    seeds = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    entry = next((s for s in seeds if s["name"] == spot_name), None)
    if entry is None:
        names = ", ".join(s["name"] for s in seeds)
        print(f'Spot "{spot_name}" non trovato nel seed. Spot presenti: {names}')
        return 1

    slug = slugify(spot_name)
    out_dir = PHOTOS_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    (out_dir / ".gitkeep").unlink(missing_ok=True)

    urls = []
    for i, src in enumerate(sources, start=1):
        with Image.open(src) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((MAX_SIDE, MAX_SIDE))
            out = out_dir / f"{i:02d}.jpg"
            img.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        urls.append(f"{RAW_BASE}/{slug}/{out.name}")
        print(f"{src} -> {out.relative_to(REPO_ROOT)} ({out.stat().st_size // 1024} KB)")

    entry["photo_urls"] = urls
    SEED_FILE.write_text(
        json.dumps(seeds, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f'Aggiornato {SEED_FILE.relative_to(REPO_ROOT)}: {len(urls)} foto per "{spot_name}"')
    print("Nota: gli URL raw puntano a main — diventano attivi dopo il merge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
