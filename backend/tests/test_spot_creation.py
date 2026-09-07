"""Creating a spot answers with the spot, not with a 500.

Two things had to be true for `POST /api/v1/spots` to work at all, and neither
was: `shapely` has to be installed (geoalchemy2 imports it lazily inside
`to_shape`), and the freshly created object has to be reloaded, because until
then its `location` is still the WKT string that was assigned rather than the
WKBElement everything downstream expects.

Both failures wrote the row and then blew up on the way out — the worst shape
a bug can have, since the data looks fine afterwards.
"""

from uuid import uuid4

import pytest

from app.repositories import spots as spots_repo
from app.schemas.spot import Point, SpotCreate


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False
        self.refreshed: list[object] = []

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed = True

    async def refresh(self, obj) -> None:
        self.refreshed.append(obj)


def test_shapely_is_installed() -> None:
    # geoalchemy2 imports it inside to_shape(), so a missing shapely does not
    # fail at startup — it fails on the first spot anyone reads or writes.
    from geoalchemy2.shape import to_shape  # noqa: F401


async def test_a_created_spot_is_reloaded_before_it_is_returned() -> None:
    session = _FakeSession()
    spot = await spots_repo.create(
        session,
        data=SpotCreate(
            name="Colle Oppio",
            description="gradoni",
            location=Point(lat=41.8925, lng=12.4966),
            difficulty=2,
            photo_urls=[],
        ),
        submitted_by=uuid4(),
    )
    assert session.flushed
    # Without this the caller serialises the WKT string it just wrote, and
    # to_shape() refuses it: "Only WKBElement and WKTElement objects are
    # supported", after the row is already in the database.
    assert session.refreshed == [spot]


def test_the_point_is_written_as_wgs84() -> None:
    wkt = spots_repo._point_wkt(Point(lat=41.8925, lng=12.4966))
    # Longitude first, as PostGIS expects — swapping them puts Rome in Somalia.
    assert wkt == "SRID=4326;POINT(12.4966 41.8925)"


@pytest.mark.parametrize(
    ("lat", "lng"),
    [(41.8925, 12.4966), (-33.8688, 151.2093), (0.0, 0.0)],
)
def test_coordinates_survive_the_round_trip(lat: float, lng: float) -> None:
    from geoalchemy2.shape import to_shape
    from geoalchemy2.elements import WKTElement

    wkt = spots_repo._point_wkt(Point(lat=lat, lng=lng))
    point = to_shape(WKTElement(wkt.split(";", 1)[1], srid=4326))
    assert (point.y, point.x) == (lat, lng)
