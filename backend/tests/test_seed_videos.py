import json

import pytest

from app.db.seed_videos import SEED_FILE, load_entries
from app.models.video import Video


def test_seed_file_is_valid() -> None:
    """Ogni voce di seeds/videos.json deve essere caricabile come Video."""
    entries = load_entries()
    assert entries, "il file di seed è vuoto"
    for entry in entries:
        Video(**entry.model_dump())


def test_seed_urls_are_unique() -> None:
    """L'url fa da chiave di idempotenza: due voci non possono condividerlo."""
    entries = load_entries()
    urls = [entry.url for entry in entries]
    assert len(urls) == len(set(urls))


def test_catalog_only_fields_are_not_persisted() -> None:
    """I metadati editoriali del catalogo non devono finire nel modello."""
    raw = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    assert any("source_channel" in item for item in raw)
    assert not any(hasattr(entry, "source_channel") for entry in load_entries())


def test_invalid_entry_reports_its_position(tmp_path) -> None:
    bad = tmp_path / "videos.json"
    bad.write_text(
        json.dumps(
            [
                {
                    "title": "ok",
                    "url": "https://example.test/a",
                    "category": "practice",
                    "level": "beginner",
                },
                {
                    "title": "rotto",
                    "url": "https://example.test/b",
                    "category": "categoria-inesistente",
                    "level": "beginner",
                },
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"voce 1 \(rotto\)"):
        load_entries(bad)
