"""Le foto di una segnalazione: quante devono essere e cosa si accetta."""

import pytest

from app.core.exceptions import ValidationFailed
from app.services import photo_storage


def test_a_report_needs_at_least_three_photos() -> None:
    with pytest.raises(ValidationFailed):
        photo_storage.validate_count(2)
    photo_storage.validate_count(3)  # non solleva


def test_a_report_cannot_carry_an_album() -> None:
    with pytest.raises(ValidationFailed):
        photo_storage.validate_count(photo_storage.MAX_PHOTOS + 1)


@pytest.mark.parametrize(
    ("content_type", "extension"),
    [("image/jpeg", ".jpg"), ("image/png", ".png"), ("image/webp", ".webp")],
)
def test_known_image_types_are_accepted(content_type: str, extension: str) -> None:
    assert photo_storage.validate_upload(content_type, 1024) == extension


def test_the_charset_suffix_does_not_confuse_the_check() -> None:
    assert photo_storage.validate_upload("image/jpeg; charset=binary", 1024) == ".jpg"


@pytest.mark.parametrize("content_type", ["application/pdf", "text/html", None, ""])
def test_anything_that_is_not_an_image_is_refused(content_type: str | None) -> None:
    with pytest.raises(ValidationFailed):
        photo_storage.validate_upload(content_type, 1024)


def test_empty_and_oversized_photos_are_refused() -> None:
    with pytest.raises(ValidationFailed):
        photo_storage.validate_upload("image/jpeg", 0)
    with pytest.raises(ValidationFailed):
        photo_storage.validate_upload("image/jpeg", photo_storage.MAX_BYTES + 1)


def test_a_stored_photo_lands_under_media_and_is_served_back(tmp_path) -> None:
    url = photo_storage.store(b"\xff\xd8\xff fake jpeg", "image/jpeg", media_root=tmp_path)

    assert url.startswith(f"{photo_storage.MEDIA_URL}/spots/")
    assert url.endswith(".jpg")
    saved = tmp_path / "spots" / url.rsplit("/", 1)[-1]
    assert saved.read_bytes() == b"\xff\xd8\xff fake jpeg"


def test_two_photos_never_overwrite_each_other(tmp_path) -> None:
    first = photo_storage.store(b"a" * 10, "image/png", media_root=tmp_path)
    second = photo_storage.store(b"b" * 10, "image/png", media_root=tmp_path)

    assert first != second
    assert len(list((tmp_path / "spots").iterdir())) == 2
