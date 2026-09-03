#!/usr/bin/env python3
"""Scrive lo stile "ricamo" come style JSON per l'app Flutter.

L'app rende la mappa con ``vector_map_tiles``, che legge uno style JSON in
formato MapLibre. Questo script prende gli stessi layer usati sul bundle web
(``scripts/pk_embroidery_style.py``) e li scrive in
``mobile/assets/map/embroidery_style.json``, così le due mappe restano lo
stesso ricamo.

Uso::

    python3 scripts/build_embroidery_style.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pk_embroidery_style import EMB_LAYERS, LINO  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = REPO_ROOT / "mobile" / "assets" / "map" / "embroidery_style.json"

# Tile vettoriali pubblici OpenFreeMap (schema OpenMapTiles), gli stessi del
# bundle web. L'URL versionato viene risolto a runtime dal TileJSON; questo
# resta come fallback.
TILE_JSON_URL = "https://tiles.openfreemap.org/planet"

STYLE = {
    "version": 8,
    "name": "PkFAMILY ricamo",
    "metadata": {
        "pk:generated-by": "scripts/build_embroidery_style.py",
        "pk:source": "scripts/pk_embroidery_style.py (stesso stile del bundle web)",
    },
    "sources": {
        "openmaptiles": {"type": "vector", "url": TILE_JSON_URL},
    },
    "layers": EMB_LAYERS,
}


def main() -> None:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(
        json.dumps(STYLE, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{len(EMB_LAYERS)} layer (fondo {LINO}) scritti in "
        f"{OUT_FILE.relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
