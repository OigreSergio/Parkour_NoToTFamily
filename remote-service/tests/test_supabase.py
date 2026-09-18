"""Il client PostgREST: richieste costruite bene, chiave mai in chiaro, errori tradotti."""

import httpx
import pytest
from pydantic import SecretStr

from pkremote.errors import UpstreamError
from pkremote.integrations.supabase import SupabaseClient


def make(http: httpx.AsyncClient, key: str = "k") -> SupabaseClient:
    return SupabaseClient(url="https://x.supabase.co", key=SecretStr(key), role="p", http=http)


async def test_select_builds_a_postgrest_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json=[{"id": 1}])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = SupabaseClient(
            url="https://x.supabase.co/",
            key=SecretStr("sb_publishable_finta"),
            role="publishable",
            http=http,
        )
        rows = await client.select("spots", params={"select": "id", "status": "eq.verified"})

    assert rows == [{"id": 1}]
    url = str(captured["url"])
    assert url.startswith("https://x.supabase.co/rest/v1/spots?")
    assert "status=eq.verified" in url
    headers = captured["headers"]
    assert headers["apikey"] == "sb_publishable_finta"  # type: ignore[index]
    assert headers["authorization"] == "Bearer sb_publishable_finta"  # type: ignore[index]
    assert "finta" not in repr(client)


async def test_http_error_status_becomes_upstream_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "no"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = make(http)
        with pytest.raises(UpstreamError):
            await client.select("spots")
        with pytest.raises(UpstreamError):
            await client.ping()


async def test_non_json_body_becomes_upstream_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>manutenzione</html>")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(UpstreamError, match="non JSON"):
            await make(http).select("spots")


async def test_network_error_becomes_upstream_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("giù", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(UpstreamError, match="non raggiungibile"):
            await make(http).select("spots")


async def test_ping_is_a_minimal_read_with_the_given_timeout() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        await make(http).ping(timeout_seconds=2.5)
    assert seen[0].url.path == "/rest/v1/spots"
    assert seen[0].url.params["limit"] == "1"
    assert seen[0].extensions["timeout"]["read"] == 2.5


async def test_select_all_paginates_with_range_header() -> None:
    """Cinque righe a pagine di due: l'intestazione Range avanza di quante righe arrivano."""
    all_rows = [{"id": i} for i in range(5)]
    ranges: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        ranges.append(request.headers["range"])
        start, end = (int(x) for x in request.headers["range"].split("-"))
        return httpx.Response(200, json=all_rows[start : end + 1])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        rows = await make(http).select_all("spots", params={"select": "*"}, page_size=2)
    assert rows == all_rows
    assert ranges == ["0-1", "2-3", "4-5", "5-6"]  # l'ultima pagina è vuota: fine


async def test_select_all_copes_with_a_server_limit_smaller_than_the_page() -> None:
    """Il progetto restituisce al massimo 2 righe anche se ne chiediamo 5: nessuna saltata."""
    all_rows = [{"id": i} for i in range(5)]

    def handler(request: httpx.Request) -> httpx.Response:
        start, _ = (int(x) for x in request.headers["range"].split("-"))
        return httpx.Response(200, json=all_rows[start : start + 2])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        rows = await make(http).select_all("spots", page_size=5)
    assert rows == all_rows


async def test_select_all_refuses_a_server_that_ignores_range() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}])  # sempre la stessa pagina

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(UpstreamError, match="Range"):
            await make(http).select_all("spots", page_size=1)


async def test_select_all_stops_on_416() -> None:
    """Quando l'ultima pagina è esattamente piena, la successiva risponde 416: finito."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["range"] == "0-1":
            return httpx.Response(200, json=[{"id": 0}, {"id": 1}])
        return httpx.Response(416)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        rows = await make(http).select_all("spots", page_size=2)
    assert rows == [{"id": 0}, {"id": 1}]
