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

from fetch_water_points import AREAS, area_of

REPO = Path(__file__).resolve().parents[1]
SPOTS = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
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
    _report_by_area(compact)


def _report_by_area(compact: dict[str, list]) -> None:
    """Quanto è coperta ogni area: Roma prima, poi l'Italia, l'Europa, il resto.

    È l'ordine in cui è stato chiesto di allargarsi, e serve a vedere a colpo
    d'occhio dove il dataset è già completo e dove l'app ripiega su Overpass.
    """
    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    total: dict[str, int] = {}
    done: dict[str, int] = {}
    wet: dict[str, int] = {}
    for spot in spots:
        area = area_of(float(spot["lat"]), float(spot["lng"]))
        total[area] = total.get(area, 0) + 1
        points = compact.get(str(spot["id"]))
        if points is None:
            continue
        done[area] = done.get(area, 0) + 1
        if points:
            wet[area] = wet.get(area, 0) + 1

    for area, _ in AREAS:
        if not total.get(area):
            continue
        print(
            f"  {area}: {done.get(area, 0)}/{total[area]} spot interrogati, "
            f"{wet.get(area, 0)} con acqua vicina"
        )


if __name__ == "__main__":
    main()
