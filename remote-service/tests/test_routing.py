"""Il proxy dei percorsi: parsing, arrotondamento, cache, errori a monte."""

import time

import httpx
import pytest

from pkremote.errors import BadRequest
from pkremote.services.cache import TTLCache
from pkremote.services.routing import (
    Point,
    cache_key,
    parse_point,
    precision_in_meters,
    round_point,
)

OSRM_OK = {
    "code": "Ok",
    "routes": [
        {
            "distance": 1234.5,
            "duration": 900.0,
            "geometry": {"type": "LineString", "coordinates": [[12.496, 41.903], [12.501, 41.912]]},
        }
    ],
}


def test_parse_point_accepts_lat_lng() -> None:
    assert parse_point("41.9028,12.4964") == Point(lat=41.9028, lng=12.4964)


@pytest.mark.parametrize("text", ["41.9", "a,b", "91,0", "0,181", "1,2,3"])
def test_parse_point_rejects_invalid_input(text: str) -> None:
    with pytest.raises(BadRequest):
        parse_point(text)


def test_round_point_and_precision() -> None:
    assert round_point(Point(41.902777, 12.496365), 3) == Point(41.903, 12.496)
    assert precision_in_meters(3) == 111
    assert precision_in_meters(2) == 1110
    assert precision_in_meters(6) == 1  # mai "0 metri"


def test_bad_request_messages_do_not_echo_the_input() -> None:
    # Una coordinata sbagliata è pur sempre una posizione: non torna indietro.
    for text in ["41.912345", "41.912345,abc", "91.5,12.5"]:
        with pytest.raises(BadRequest) as info:
            parse_point(text)
        assert "41.9" not in info.value.message
        assert "91.5" not in info.value.message


def test_cache_key_depends_on_points_and_profile() -> None:
    a, b = Point(41.903, 12.496), Point(41.912, 12.501)
    assert cache_key(a, b, "foot") == cache_key(a, b, "foot")
    assert cache_key(a, b, "foot") != cache_key(b, a, "foot")
    assert cache_key(a, b, "foot") != cache_key(a, b, "pk_foot")


async def test_ttl_cache_expires_and_evicts(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    cache = TTLCache(ttl_seconds=10, max_entries=2)
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.set("c", 3)  # oltre il limite: "a" (la meno recente) viene scartata
    assert await cache.get("a") is None
    assert await cache.get("b") == 2
    now[0] += 11  # tutto scaduto
    assert await cache.get("b") is None
    assert cache.stats()["entries"] == 1  # resta solo "c", non ancora letta


async def test_ttl_cache_evicts_the_least_recently_used() -> None:
    cache = TTLCache(ttl_seconds=60, max_entries=2)
    await cache.set("a", 1)
    await cache.set("b", 2)
    assert await cache.get("a") == 1  # "a" torna a essere la più recente
    await cache.set("c", 3)  # deve uscire "b", non "a"
    assert await cache.get("b") is None
    assert await cache.get("a") == 1
    assert await cache.get("c") == 3


async def test_route_without_osrm_is_503(make_client) -> None:
    async with make_client() as (client, _):
        response = await client.get(
            "/api/v1/route", params={"from": "41.9028,12.4964", "to": "41.91,12.5"}
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "routing_unavailable"


async def test_route_proxies_rounded_coordinates_and_caches(make_client) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=OSRM_OK)

    params = {"from": "41.902777,12.496365", "to": "41.912345,12.501234"}
    async with make_client(handler, osrm_base_url="http://osrm:5000") as (client, _):
        first = await client.get("/api/v1/route", params=params)
        second = await client.get("/api/v1/route", params=params)

    assert first.status_code == 200
    body = first.json()
    assert body["cached"] is False
    assert body["distance_m"] == 1234.5
    assert body["precision_m"] == 111
    assert body["geometry"]["type"] == "LineString"
    # Una sola chiamata a OSRM, con coordinate arrotondate e nell'ordine lng,lat.
    assert len(seen) == 1
    assert "/route/v1/foot/12.496,41.903;12.501,41.912" in seen[0]
    assert "12.496365" not in seen[0]
    # La seconda risposta viene dalla cache.
    assert second.json()["cached"] is True


async def test_route_cache_is_keyed_on_rounded_coordinates(make_client) -> None:
    """Due richieste diverse nella stessa cella da ~100 m: una sola chiamata a OSRM."""
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=OSRM_OK)

    async with make_client(handler, osrm_base_url="http://osrm:5000") as (client, _):
        first = await client.get(
            "/api/v1/route", params={"from": "41.902777,12.496365", "to": "41.912345,12.501234"}
        )
        second = await client.get(
            "/api/v1/route", params={"from": "41.902801,12.496399", "to": "41.912311,12.501199"}
        )
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert calls == 1


async def test_route_upstream_failure_is_502(make_client) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with make_client(handler, osrm_base_url="http://osrm:5000") as (client, _):
        response = await client.get(
            "/api/v1/route", params={"from": "41.9,12.5", "to": "41.91,12.5"}
        )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_error"


async def test_route_no_route_is_502(make_client) -> None:
    # OSRM risponde 400 con il codice nel corpo quando non trova un tragitto.
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": "NoRoute", "message": "Impossible route."})

    async with make_client(handler, osrm_base_url="http://osrm:5000") as (client, _):
        response = await client.get(
            "/api/v1/route", params={"from": "41.9,12.5", "to": "41.91,12.5"}
        )
    assert response.status_code == 502
    assert "NoRoute" in response.json()["error"]["message"]


async def test_route_bad_coordinates_is_422(make_client) -> None:
    async with make_client(osrm_base_url="http://osrm:5000") as (client, _):
        response = await client.get("/api/v1/route", params={"from": "x", "to": "41.91,12.5"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "bad_request"


async def test_route_missing_parameter_uses_the_error_envelope(make_client) -> None:
    """Gli errori di validazione di FastAPI hanno la stessa forma dei nostri."""
    async with make_client(osrm_base_url="http://osrm:5000") as (client, _):
        response = await client.get("/api/v1/route", params={"from": "41.9028,12.4964"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "bad_request"
    assert "to" in body["error"]["message"]
    assert "41.9028" not in response.text  # il valore ricevuto non viene ripetuto
