"""The seed files must stay loadable: they are what fills a fresh database.

These are pure schema checks — no database — so they run in CI like the rest of
the unit tests and catch a malformed entry before `make seed-*` does.
"""

import json
from pathlib import Path

import pytest

from app.models.video import TrickCategory, VideoCategory, VideoLevel
from app.schemas.video import VideoCreate

SEEDS = Path(__file__).resolve().parents[1] / "seeds"


def _load(name: str) -> list[dict]:
    return json.loads((SEEDS / name).read_text(encoding="utf-8"))


def test_spots_seed_entries_are_well_formed() -> None:
    spots = _load("spots.json")
    assert spots, "spots.json is empty"

    names = [spot["name"] for spot in spots]
    assert len(names) == len(set(names)), "the seed is keyed by name, so names must be unique"

    for spot in spots:
        assert -90 <= spot["lat"] <= 90
        assert -180 <= spot["lng"] <= 180
        assert 1 <= spot.get("difficulty", 1) <= 5
        assert all(url.startswith("http") for url in spot.get("photo_urls", []))


def test_videos_seed_entries_match_the_api_schema() -> None:
    videos = _load("videos.json")
    assert videos, "videos.json is empty"

    titles = [video["title"] for video in videos]
    assert len(titles) == len(set(titles)), "the seed is keyed by title, so titles must be unique"

    for video in videos:
        # Same validation the API applies to a video submitted over HTTP.
        parsed = VideoCreate.model_validate(video)
        assert parsed.category in set(VideoCategory)
        assert parsed.level in set(VideoLevel)
        assert parsed.trick_category is None or parsed.trick_category in set(TrickCategory)
        assert parsed.url.startswith("http")
        assert parsed.duration_seconds > 0, f"{parsed.title} has no duration"


@pytest.mark.parametrize("name", ["spots.json", "videos.json"])
def test_seed_files_are_utf8_json_lists(name: str) -> None:
    assert isinstance(_load(name), list)
