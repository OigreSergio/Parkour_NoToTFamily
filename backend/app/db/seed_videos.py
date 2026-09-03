"""Seed the tutorial catalog from ``backend/seeds/videos.json``.

I video elencati nel file finiscono nella sezione **Tutorials** dell'app. Il
livello decide l'accesso: i `beginner` sono liberi per tutti (anche per gli
ospiti senza email), dagli `intermediate` in su servono l'abbonamento — la
regola vive in ``app.services.video_service``, il seed non la duplica.

Il seed è idempotente: un video già presente con lo stesso titolo viene
saltato, quindi si può rilanciare ogni volta che il catalogo cresce.

Uso (dentro il container api)::

    python -m app.db.seed_videos
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.video import TrickCategory, Video, VideoCategory, VideoLevel

SEED_FILE = Path(__file__).resolve().parents[2] / "seeds" / "videos.json"


async def seed() -> tuple[int, int]:
    entries = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    inserted = skipped = 0
    async with SessionLocal() as session:
        for entry in entries:
            exists = await session.scalar(select(Video.id).where(Video.title == entry["title"]))
            if exists is not None:
                skipped += 1
                continue
            trick_category = entry.get("trick_category")
            session.add(
                Video(
                    title=entry["title"],
                    description=entry.get("description", ""),
                    url=entry["url"],
                    thumbnail_url=entry.get("thumbnail_url"),
                    category=VideoCategory(entry["category"]),
                    level=VideoLevel(entry["level"]),
                    trick_category=(
                        TrickCategory(trick_category) if trick_category else None
                    ),
                    difficulty=entry.get("difficulty", 1),
                    duration_seconds=entry.get("duration_seconds", 0),
                )
            )
            inserted += 1
        await session.commit()
    return inserted, skipped


def main() -> None:
    inserted, skipped = asyncio.run(seed())
    print(f"Seed videos: {inserted} inseriti, {skipped} già presenti")


if __name__ == "__main__":
    main()
