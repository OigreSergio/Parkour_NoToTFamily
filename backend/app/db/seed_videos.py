"""Seed tutorial videos from ``backend/seeds/videos.json``.

Il file contiene la selezione curata di tutorial di parkour descritta in
``docs/TUTORIAL_CATALOG.md``. Ogni voce viene validata con ``VideoCreate`` prima
di finire a database, così un errore nel JSON si vede subito e non a metà
caricamento. Il seed è idempotente — un video già presente con lo stesso ``url``
viene saltato, quindi si può rilanciare ogni volta che il catalogo cresce.

Le chiavi editoriali del catalogo (``source_channel``, ``quality``, ``safety``)
non fanno parte del modello e vengono ignorate.

Uso (dentro il container api)::

    python -m app.db.seed_videos
"""

import asyncio
import json
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.video import Video
from app.schemas.video import VideoCreate

SEED_FILE = Path(__file__).resolve().parents[2] / "seeds" / "videos.json"

# Metadati editoriali del catalogo, non colonne di ``videos``.
CATALOG_ONLY_FIELDS = ("source_channel", "quality", "safety")


def load_entries(path: Path = SEED_FILE) -> list[VideoCreate]:
    """Legge il file di seed e valida ogni voce, riportando l'indice in errore."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for index, item in enumerate(raw):
        payload = {k: v for k, v in item.items() if k not in CATALOG_ONLY_FIELDS}
        try:
            entries.append(VideoCreate(**payload))
        except ValidationError as exc:
            title = item.get("title", "?")
            raise ValueError(f"{path.name} voce {index} ({title}) non valida:\n{exc}") from exc
    return entries


async def seed() -> tuple[int, int]:
    entries = load_entries()
    inserted = skipped = 0
    async with SessionLocal() as session:
        for entry in entries:
            exists = await session.scalar(select(Video.id).where(Video.url == entry.url))
            if exists is not None:
                skipped += 1
                continue
            session.add(Video(**entry.model_dump()))
            inserted += 1
        await session.commit()
    return inserted, skipped


def main() -> None:
    inserted, skipped = asyncio.run(seed())
    print(f"Seed videos: {inserted} inseriti, {skipped} già presenti")


if __name__ == "__main__":
    main()
