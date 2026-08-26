#!/usr/bin/env python3
"""Rigenera ``docs/spots/photos/COVERAGE.md``: cosa manca, spot per spot.

Uno spot è *completo* quando ha una descrizione utile, almeno una foto che
mostri gli ostacoli (``kind: "spot"``, non una foto della zona) e un rilievo
fatto sul posto (``surveyed``). Il report serve a vedere in un colpo d'occhio
quali schede sono ancora da chiudere, senza aprire il seed.

Uso::

    python scripts/spot_coverage.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_FILE = REPO_ROOT / "backend" / "seeds" / "spots.json"
OUT_FILE = REPO_ROOT / "docs" / "spots" / "photos" / "COVERAGE.md"
#: Sotto questa soglia la descrizione è un indirizzo, non una scheda.
MIN_DESCRIPTION = 120


def row(spot: dict) -> tuple[str, bool]:
    photos = spot.get("photos") or []
    crew = sum(1 for p in photos if p.get("kind") == "spot")
    area = len(photos) - crew
    if crew:
        photo_cell = f"✅ {crew} spot" + (f" + {area} zona" if area else "")
    elif area:
        photo_cell = f"🟡 {area} zona"
    else:
        photo_cell = "❌ nessuna"

    desc_ok = len(spot.get("description", "")) >= MIN_DESCRIPTION
    surveyed = bool(spot.get("surveyed"))
    complete = bool(crew) and desc_ok and surveyed

    cells = [
        spot["name"],
        photo_cell,
        "✅" if desc_ok else "❌",
        "✅" if surveyed else "❌ da rilevare",
    ]
    return "| " + " | ".join(cells) + " |", complete


def main() -> None:
    spots = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    rows, complete = [], 0
    for spot in sorted(spots, key=lambda s: s["name"]):
        line, ok = row(spot)
        rows.append(line)
        complete += ok

    with_photos = sum(1 for s in spots if s.get("photos"))
    surveyed = sum(1 for s in spots if s.get("surveyed"))

    text = f"""# Copertura degli spot

Rigenerato con `python scripts/spot_coverage.py` — non modificare a mano.

**{len(spots)} spot** · {with_photos} con almeno una foto · {surveyed} con gli
ostacoli rilevati sul posto · **{complete} completi** (foto degli ostacoli +
descrizione + rilievo).

Legenda foto: `✅ spot` = si vedono gli ostacoli · `🟡 zona` = si vede solo il
luogo intorno, non gli ostacoli · `❌` = nessuna foto.

| Spot | Foto | Descrizione | Rilievo |
| --- | --- | --- | --- |
{chr(10).join(rows)}

## Cosa serve per chiudere una scheda

1. **Una foto degli ostacoli** — scattata sul posto, non della zona:
   `python scripts/add_spot_photos.py "<nome spot>" foto.jpg`
2. **Il rilievo** — cosa c'è davvero (altezze, distanze, fondo, orari buoni),
   scritto nella descrizione; poi `"surveyed": true` nel seed.

Vedi [`README.md`](README.md) per il flusso completo.
"""
    OUT_FILE.write_text(text, encoding="utf-8")
    print(f"{OUT_FILE.relative_to(REPO_ROOT)}: {complete}/{len(spots)} spot completi")


if __name__ == "__main__":
    main()
