"""Decodifica delle geometrie: EWKB esadecimale e GeoJSON."""

import struct

import pytest

from pkremote.integrations.geo import parse_ewkb_point, point_from_location

LNG, LAT = 12.4964, 41.9028


def _ewkb(order: str, *, srid: bool) -> str:
    """Costruisce un EWKB di punto: 1 byte ordine, 4 byte tipo, [4 byte SRID], x, y."""
    geometry_type = 1 | (0x20000000 if srid else 0)
    raw = (b"\x01" if order == "<" else b"\x00") + struct.pack(f"{order}I", geometry_type)
    if srid:
        raw += struct.pack(f"{order}I", 4326)
    raw += struct.pack(f"{order}dd", LNG, LAT)
    return raw.hex()


@pytest.mark.parametrize("order", ["<", ">"])
@pytest.mark.parametrize("srid", [True, False])
def test_parse_ewkb_point(order: str, srid: bool) -> None:
    assert parse_ewkb_point(_ewkb(order, srid=srid)) == (LAT, LNG)


@pytest.mark.parametrize("bad", ["zz", "0101", "0102000020E6100000" + "00" * 16])
def test_parse_ewkb_point_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_ewkb_point(bad)


def test_point_from_location_accepts_geojson_and_ewkb() -> None:
    assert point_from_location({"type": "Point", "coordinates": [LNG, LAT]}) == (LAT, LNG)
    assert point_from_location(_ewkb("<", srid=True)) == (LAT, LNG)
    assert point_from_location({"type": "Point", "coordinates": []}) is None
    assert point_from_location("non-esadecimale") is None
    assert point_from_location(None) is None


def test_point_from_location_rejects_bad_geojson_coordinates() -> None:
    assert point_from_location({"type": "Point", "coordinates": ["a", "b"]}) is None
    assert point_from_location({"type": "Point", "coordinates": [None, 41.9]}) is None
    assert point_from_location({"type": "Point", "coordinates": [float("nan"), 41.9]}) is None
    assert point_from_location({"type": "Point", "coordinates": [12.4]}) is None
