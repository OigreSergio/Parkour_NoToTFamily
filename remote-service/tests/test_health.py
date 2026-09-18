"""/healthz, /readyz, intestazioni di sicurezza, forma uniforme degli errori."""

import httpx

from tests.production import PRODUCTION


def osrm_alive(_: httpx.Request) -> httpx.Response:
    """Un OSRM vivo che risponde "nessun segmento": conta come ok."""
    return httpx.Response(400, json={"code": "InvalidQuery"})


async def test_healthz_reports_instance_without_secrets(make_client) -> None:
    async with make_client(
        instance_name="prova",
        supabase_url="https://x.supabase.co",
        supabase_publishable_key="sb_publishable_finta",
    ) as (client, _):
        response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["instance"] == "prova"
    assert "finta" not in response.text


async def test_readyz_without_dependencies_is_ready(make_client) -> None:
    async with make_client() as (client, _):
        response = await client.get("/readyz")
    assert response.status_code == 200
    statuses = {check["name"]: check["status"] for check in response.json()["checks"]}
    assert statuses == {"supabase": "not_configured", "osrm": "not_configured"}


async def test_readyz_fails_when_a_configured_dependency_is_down(make_client) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with make_client(handler, osrm_base_url="http://osrm:5000") as (client, _):
        response = await client.get("/readyz")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


async def test_readyz_ok_when_dependencies_answer(make_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/rest/v1/"):
            assert request.headers["apikey"] == "sb_publishable_finta"
            assert request.url.params["limit"] == "1"  # lettura minima, non lo schema
            return httpx.Response(200, json=[])
        return osrm_alive(request)

    async with make_client(
        handler,
        osrm_base_url="http://osrm:5000",
        supabase_url="https://x.supabase.co",
        supabase_publishable_key="sb_publishable_finta",
    ) as (client, _):
        response = await client.get("/readyz")
    assert response.status_code == 200
    assert all(check["status"] == "ok" for check in response.json()["checks"])


async def test_readyz_reports_which_dependency_is_down(make_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/rest/v1/"):
            return httpx.Response(500)
        return osrm_alive(request)

    async with make_client(
        handler,
        osrm_base_url="http://osrm:5000",
        supabase_url="https://x.supabase.co",
        supabase_publishable_key="sb_publishable_finta",
    ) as (client, _):
        response = await client.get("/readyz")
    assert response.status_code == 503
    checks = {check["name"]: check for check in response.json()["checks"]}
    assert checks["supabase"]["status"] == "error"
    assert "500" in checks["supabase"]["detail"]
    assert checks["osrm"]["status"] == "ok"


async def test_readyz_treats_a_timeout_as_error(make_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("troppo lento", request=request)

    async with make_client(handler, osrm_base_url="http://osrm:5000") as (client, _):
        response = await client.get("/readyz")
    assert response.status_code == 503
    assert "ReadTimeout" in response.json()["checks"][1]["detail"]


async def test_readyz_reuses_its_last_result(make_client) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return osrm_alive(request)

    async with make_client(handler, osrm_base_url="http://osrm:5000", ready_cache_seconds=60) as (
        client,
        _,
    ):
        first = await client.get("/readyz")
        second = await client.get("/readyz")
    assert first.status_code == second.status_code == 200
    assert calls == 1  # la seconda sonda non ha toccato OSRM


async def test_readyz_without_cache_probes_every_time(make_client) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return osrm_alive(request)

    async with make_client(handler, osrm_base_url="http://osrm:5000", ready_cache_seconds=0) as (
        client,
        _,
    ):
        await client.get("/readyz")
        await client.get("/readyz")
    assert calls == 2


async def test_only_secret_key_leaves_supabase_unconfigured(make_client) -> None:
    """La chiave segreta non è mai il ripiego per le letture."""
    async with make_client(
        supabase_url="https://x.supabase.co", supabase_secret_key="segreto-lungo-abbastanza"
    ) as (client, app):
        response = await client.get("/readyz")
    assert app.state.supabase is None
    statuses = {check["name"]: check["status"] for check in response.json()["checks"]}
    assert statuses["supabase"] == "not_configured"


async def test_every_response_carries_a_request_id(make_client) -> None:
    async with make_client() as (client, _):
        response = await client.get("/healthz")
    assert len(response.headers["x-request-id"]) == 12


async def test_security_headers_are_present(make_client) -> None:
    async with make_client() as (client, _):
        response = await client.get("/healthz")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"
    # HSTS solo in produzione: in locale, su http, sarebbe sbagliato.
    assert "strict-transport-security" not in response.headers


async def test_production_hides_docs_and_schema_and_adds_hsts(make_client) -> None:
    async with make_client(**PRODUCTION) as (client, _):
        health = await client.get("/healthz")
        docs = await client.get("/docs")
        schema = await client.get("/openapi.json")
    assert health.status_code == 200
    assert "max-age=" in health.headers["strict-transport-security"]
    assert docs.status_code == 404
    assert schema.status_code == 404
    assert schema.json()["error"]["code"] == "not_found"


async def test_development_serves_docs(make_client) -> None:
    async with make_client(env="development") as (client, _):
        schema = await client.get("/openapi.json")
    assert schema.status_code == 200


async def test_unknown_path_and_method_use_the_error_envelope(make_client) -> None:
    async with make_client() as (client, _):
        missing = await client.get("/non-esiste")
        wrong_method = await client.delete("/healthz")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    assert wrong_method.status_code == 405
    assert wrong_method.json()["error"]["code"] == "method_not_allowed"
