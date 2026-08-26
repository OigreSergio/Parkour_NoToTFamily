"""Seed verified spots from ``backend/seeds/spots.json``.

Gli spot elencati nel file entrano direttamente sulla mappa pubblica con
``status = verified`` (senza passare dalla coda di moderazione): il file è
pensato per gli spot raccolti dai maintainer quando l'invio dall'app non è
possibile. Il seed è idempotente e si può rilanciare ogni volta che il file
cambia: gli spot nuovi vengono inseriti, quelli già presenti (stesso ``name``)
vengono aggiornati con descrizione, difficoltà e foto del file — è così che
foto e descrizioni riviste arrivano al database senza ricreare la mappa.
Posizione e stato di moderazione non vengono toccati.

Uso (dentro il container api)::

    python -m app.db.seed_spots
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.spot import Spot, SpotStatus

SEED_FILE = Path(__file__).resolve().parents[2] / "seeds" / "spots.json"


#: Campi che il file può riscrivere su uno spot già in database.
EDITABLE = ("description", "photo_urls", "photos", "difficulty", "surveyed")


def _fields(entry: dict) -> dict:
    return {
        "description": entry.get("description", ""),
        "photo_urls": entry.get("photo_urls", []),
        "photos": entry.get("photos", []),
        "difficulty": entry.get("difficulty", 1),
        "surveyed": entry.get("surveyed", False),
    }


async def seed() -> tuple[int, int, int]:
    entries = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    inserted = updated = unchanged = 0
    async with SessionLocal() as session:
        for entry in entries:
            fields = _fields(entry)
            spot = await session.scalar(select(Spot).where(Spot.name == entry["name"]))
            if spot is None:
                session.add(
                    Spot(
                        name=entry["name"],
                        location=f"SRID=4326;POINT({entry['lng']} {entry['lat']})",
                        status=SpotStatus.verified,
                        verified_at=datetime.now(timezone.utc),
                        **fields,
                    )
                )
                inserted += 1
                continue
            changed = [f for f in EDITABLE if getattr(spot, f) != fields[f]]
            if not changed:
                unchanged += 1
                continue
            for field in changed:
                setattr(spot, field, fields[field])
            updated += 1
        await session.commit()
    return inserted, updated, unchanged


def main() -> None:
    inserted, updated, unchanged = asyncio.run(seed())
    print(
        f"Seed spots: {inserted} inseriti, {updated} aggiornati, "
        f"{unchanged} già allineati"
    )


if __name__ == "__main__":
    main()
