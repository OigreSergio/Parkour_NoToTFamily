#!/usr/bin/env python3
"""Porta nell'app le fontanelle raccolte da OpenStreetMap.

``fetch_water_points.py`` interroga Overpass per tutti gli spot e scrive
``scripts/data/spot_water.json``. Questo script lo compatta e lo copia in
``mobile/assets/water/spot_water.json``, che l'app legge per rispondere subito
e anche senza rete (Overpass resta come ripiego per gli spot che il dataset non
conosce, per esempio quelli appena segnalati).

Uso: python3 scripts/wire_spot_water.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "scripts" / "data" / "spot_water.json"
TARGET = REPO / "mobile" / "assets" / "water" / "spot_water.json"

# Nel bundle bastano i campi che la scheda mostra.
FIELDS = ("osm_id", "lat", "lng", "kind", "name", "distance_m")


def main() -> None:
    harvest = json.loads(SOURCE.read_text(encoding="utf-8"))

    compact = {
        spot_id: [
            {k: point[k] for k in FIELDS if point.get(k) is not None}
            for point in points
        ]
        for spot_id, points in harvest.items()
    }

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(compact, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with_water = sum(1 for v in compact.values() if v)
    points = sum(len(v) for v in compact.values())
    size_kb = TARGET.stat().st_size // 1024
    print(
        f"{len(compact)} spot ({with_water} con acqua entro 400 m, {points} punti) "
        f"-> {TARGET.relative_to(REPO)} ({size_kb} KB)"
    )


if __name__ == "__main__":
    main()
