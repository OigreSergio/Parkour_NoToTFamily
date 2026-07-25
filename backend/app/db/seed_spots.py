"""Seed verified spots from ``backend/seeds/spots.json``.

Gli spot elencati nel file entrano direttamente sulla mappa pubblica con
``status = verified`` (senza passare dalla coda di moderazione): il file è
pensato per gli spot raccolti dai maintainer quando l'invio dall'app non è
possibile. Il seed è idempotente — uno spot già presente con lo stesso nome
viene saltato, quindi si può rilanciare ogni volta che il file cresce.

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


async def seed() -> tuple[int, int]:
    entries = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    inserted = skipped = 0
    async with SessionLocal() as session:
        for entry in entries:
            exists = await session.scalar(select(Spot.id).where(Spot.name == entry["name"]))
            if exists is not None:
                skipped += 1
                continue
            session.add(
                Spot(
                    name=entry["name"],
                    description=entry.get("description", ""),
                    location=f"SRID=4326;POINT({entry['lng']} {entry['lat']})",
                    photo_urls=entry.get("photo_urls", []),
                    difficulty=entry.get("difficulty", 1),
                    status=SpotStatus.verified,
                    verified_at=datetime.now(timezone.utc),
                )
            )
            inserted += 1
        await session.commit()
    return inserted, skipped


def main() -> None:
    inserted, skipped = asyncio.run(seed())
    print(f"Seed spots: {inserted} inseriti, {skipped} già presenti")


if __name__ == "__main__":
    main()
