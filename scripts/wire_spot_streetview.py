#!/usr/bin/env python3
"""Collega agli spot l'inquadratura Street View trovata da fetch_spot_streetview.

Scrive nello spot corrispondente di ``scripts/data/webapp_fixed_spots.json``:

- ``streetview``: {pano_id, yaw, date, distance_m} — la provenienza;
- ``street_view_url``: la miniatura già pronta, che i client usano come
  copertina quando lo spot non ha foto proprie.

Uso: python3 scripts/wire_spot_streetview.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPOTS = REPO / "scripts" / "data" / "webapp_fixed_spots.json"
PANOS = REPO / "scripts" / "data" / "spot_streetview.json"

# Stessa miniatura usata dalla scheda web (docs/demo/pk-scheda.js).
THUMB = (
    "https://streetviewpixels-pa.googleapis.com/v1/thumbnail"
    "?panoid={pano_id}&cb_client=maps_sv.tactile.gps"
    "&w=640&h=360&yaw={yaw}&pitch=0&thumbfov=100"
)


def main() -> None:
    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    panos = json.loads(PANOS.read_text(encoding="utf-8"))

    wired = 0
    for spot in spots:
        pano = panos.get(str(spot["id"]))
        if not pano:
            spot.pop("streetview", None)
            spot.pop("street_view_url", None)
            continue
        spot["streetview"] = {
            "pano_id": pano["pano_id"],
            "yaw": pano["yaw"],
            "date": pano.get("date"),
            "distance_m": pano.get("distance_m"),
        }
        spot["street_view_url"] = THUMB.format(pano_id=pano["pano_id"], yaw=pano["yaw"])
        wired += 1

    SPOTS.write_text(json.dumps(spots, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{wired}/{len(spots)} spot con inquadratura Street View collegata")


if __name__ == "__main__":
    main()
