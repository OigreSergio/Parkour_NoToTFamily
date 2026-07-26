"""Seed verified spots into the database from ``backend/seeds/spots.json``.

Usage (inside the api container or a configured backend env):

    python -m app.db.seed_spots

Idempotent: a spot whose name already exists in the table is skipped, so the
script can run on every deploy without creating duplicates.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.spot import Spot, SpotStatus

SEED_FILE = Path(__file__).resolve().parents[2] / "seeds" / "spots.json"


async def seed() -> None:
    entries = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    async with SessionLocal() as session:
        for entry in entries:
            exists = await session.scalar(
                select(Spot.id).where(Spot.name == entry["name"])
            )
            if exists:
                print(f"skip (already present): {entry['name']}")
                continue
            spot = Spot(
                name=entry["name"],
                description=entry.get("description", ""),
                location=f"SRID=4326;POINT({entry['lng']} {entry['lat']})",
                photo_urls=entry.get("photo_urls", []),
                difficulty=entry.get("difficulty", 1),
                status=SpotStatus.verified,
                verified_at=datetime.now(timezone.utc),
            )
            session.add(spot)
            print(f"added: {entry['name']} ({entry['lat']}, {entry['lng']})")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
