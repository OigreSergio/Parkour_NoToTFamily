import json

import pytest

from app.db.seed_videos import SEED_FILE, load_entries
from app.models.video import Video, VideoLevel


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


# I video di sicurezza sono marcati beginner per scelta di prodotto: nel backend
# il livello pilota anche il paywall, e questi contenuti devono restare gratuiti
# anche quando sono tecnicamente più impegnativi (vedi docs/TUTORIAL_CATALOG.md).
SAFETY_VIDEO_URLS = {
    "https://www.youtube.com/watch?v=CDxhYN6KKz4",  # rolling sul cemento
    "https://www.youtube.com/watch?v=Ehlx0KrVJa0",  # 10 tipi di rolling
    "https://www.youtube.com/watch?v=ohjbbVwg6OU",  # cadere senza farsi male
    "https://www.youtube.com/watch?v=r9XPcXQ-7VY",  # 10 modi di cadere
    "https://www.youtube.com/watch?v=ZTlEwMtDH9s",  # atterraggio da altezza
    "https://www.youtube.com/watch?v=xNGPuvDcGLw",  # superhero landing
    "https://www.youtube.com/watch?v=UUzpvxuRYg4",  # allenarsi da infortunato
}


def test_safety_videos_stay_free() -> None:
    by_url = {entry.url: entry for entry in load_entries()}
    missing = SAFETY_VIDEO_URLS - by_url.keys()
    assert not missing, f"video di sicurezza spariti dal seed: {missing}"
    for url in SAFETY_VIDEO_URLS:
        assert by_url[url].level == VideoLevel.beginner, url
