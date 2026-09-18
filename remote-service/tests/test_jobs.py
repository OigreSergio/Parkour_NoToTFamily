"""I job: protezione via token, esecuzione via HTTP e da riga di comando, esportazione spot."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from pkremote.__main__ import main
from pkremote.config import get_settings
from pkremote.integrations.supabase import SupabaseClient
from pkremote.jobs import REGISTRY, JobContext, JobResult, run_job
from pkremote.jobs.spots_export import unique_slug

TOKEN = "token-di-prova-abbastanza-lungo-123"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
# POINT(12.4964 41.9028), SRID 4326, little endian.
EWKB_POINT = "0101000020E610000003780B2428FE2840166A4DF38EF34440"


def paged(rows: list[dict], *, seen: list[httpx.Request] | None = None):
    """Un Supabase finto che rispetta l'intestazione Range come PostgREST."""

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        start = int(request.headers["range"].split("-")[0])
        return httpx.Response(200, json=rows[start : start + 1000])

    return handler


async def run_export(make_settings, tmp_path: Path, handler) -> JobResult:
    """Esegue spots-export contro un Supabase finto, senza passare da HTTP."""
    settings = make_settings(jobs_output_dir=tmp_path)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        supabase = SupabaseClient(
            url="https://x.supabase.co", key=SecretStr("k"), role="publishable", http=http
        )
        ctx = JobContext(settings=settings, http=http, supabase=supabase, output_dir=tmp_path)
        return await run_job("spots-export", ctx)


async def test_jobs_http_disabled_without_token(make_client) -> None:
    async with make_client() as (client, _):
        response = await client.get("/api/v1/jobs")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "jobs_http_disabled"


async def test_jobs_require_a_valid_token(make_client) -> None:
    async with make_client(job_token=TOKEN) as (client, _):
        missing = await client.get("/api/v1/jobs")
        wrong = await client.get("/api/v1/jobs", headers={"Authorization": "Bearer sbagliato"})
        right = await client.get("/api/v1/jobs", headers=AUTH)
        # Anche la rotta che esegue davvero un job è protetta.
        run_missing = await client.post("/api/v1/jobs/ping")
        run_empty = await client.post("/api/v1/jobs/ping", headers={"Authorization": "Bearer "})
        run_basic = await client.post("/api/v1/jobs/ping", headers={"Authorization": "Basic abc"})
        run_unknown = await client.post("/api/v1/jobs/non-esiste")
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert right.status_code == 200
    assert {job["name"] for job in right.json()} >= {"ping", "spots-export"}
    assert run_missing.status_code == 401
    assert run_empty.status_code == 401
    assert run_basic.status_code == 401
    assert run_unknown.status_code == 401  # il token si controlla prima del nome


async def test_run_ping_job_over_http(make_client, tmp_path: Path) -> None:
    async with make_client(job_token=TOKEN, jobs_output_dir=tmp_path, instance_name="x") as (
        client,
        _,
    ):
        response = await client.post("/api/v1/jobs/ping", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["message"] == "pong"
    assert body["data"]["instance"] == "x"
    assert "elapsed_ms" in body["data"]


async def test_unknown_job_is_404_and_leaves_no_lock_behind(make_client, tmp_path: Path) -> None:
    async with make_client(job_token=TOKEN, jobs_output_dir=tmp_path) as (client, app):
        response = await client.post("/api/v1/jobs/non-esiste", headers=AUTH)
        locks = dict(app.state.job_locks)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "non-esiste" not in locks  # nessun lock per nomi inventati


async def test_same_job_does_not_run_twice_at_once(make_client, tmp_path: Path) -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    class SlowJob:
        name = "lento-di-prova"
        description = "aspetta un segnale"

        async def run(self, ctx: JobContext) -> JobResult:
            started.set()
            await release.wait()
            return JobResult(ok=True, message="finito")

    REGISTRY["lento-di-prova"] = SlowJob()
    try:
        async with make_client(job_token=TOKEN, jobs_output_dir=tmp_path) as (client, _):
            first = asyncio.create_task(client.post("/api/v1/jobs/lento-di-prova", headers=AUTH))
            await started.wait()
            second = await client.post("/api/v1/jobs/lento-di-prova", headers=AUTH)
            release.set()
            first_response = await first
    finally:
        del REGISTRY["lento-di-prova"]
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"
    assert first_response.status_code == 200
    assert first_response.json()["ok"] is True


async def test_spots_export_reads_production_rows_and_writes_file(
    make_client, tmp_path: Path
) -> None:
    """Righe nella forma REALE di produzione (lat/lng, skill_level, has_fountain)."""
    requests: list[httpx.Request] = []
    rows = [
        {
            "id": "1",
            "name": "Spot verso la metro Cipro",
            "description": "muretti",
            "lat": 41.9028,
            "lng": 12.4964,
            "skill_level": "intermedio",  # in produzione è un testo, non un numero
            "has_fountain": True,
            "crowd_level": "basso",  # esiste in produzione ma NON va esportato
            "author_id": "u1",
            "status": "verified",
            "verified_at": "2026-07-01T10:00:00+00:00",
        },
        {"id": "2", "name": "Senza posizione", "lat": None, "lng": None},
        {"id": "3", "name": "Fuori dal mondo", "lat": 500, "lng": 900},
    ]

    async with make_client(
        paged(rows, seen=requests),
        job_token=TOKEN,
        jobs_output_dir=tmp_path,
        supabase_url="https://x.supabase.co",
        supabase_publishable_key="sb_publishable_finta",
    ) as (client, _):
        response = await client.post("/api/v1/jobs/spots-export", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"] == {
        "count": 1,
        "skipped": 2,
        "slug_collisions": 0,
        "file": str(tmp_path / "spots_verificati.json"),
        "elapsed_ms": body["data"]["elapsed_ms"],
    }
    # Solo spot verificati, a pagine, in ordine stabile, con la chiave pubblicabile.
    request = requests[0]
    assert request.url.path == "/rest/v1/spots"
    assert request.url.params["status"] == "eq.verified"
    assert request.url.params["order"] == "name.asc,id.asc"
    assert request.headers["range"] == "0-999"
    assert request.headers["apikey"] == "sb_publishable_finta"
    written = json.loads((tmp_path / "spots_verificati.json").read_text(encoding="utf-8"))
    assert written["count"] == 1
    spot = written["spots"][0]
    assert spot["slug"] == "spot-verso-la-metro-cipro"
    assert (spot["lat"], spot["lng"]) == (41.9028, 12.4964)
    assert spot["difficulty"] == "intermedio"
    assert spot["fountain"] is True
    assert "crowd_level" not in spot
    assert "author_id" not in spot


async def test_spots_export_accepts_migration_rows_with_ewkb(make_settings, tmp_path: Path) -> None:
    """Righe nella forma delle migrazioni (location EWKB, difficulty, water)."""
    rows = [
        {"id": "1", "name": "Uno", "location": EWKB_POINT, "difficulty": 3, "water": False},
        {"id": "2", "name": "Rotto", "location": "zz"},
    ]
    result = await run_export(make_settings, tmp_path, paged(rows))
    assert result.ok is True
    assert result.data["count"] == 1
    assert result.data["skipped"] == 1
    written = json.loads((tmp_path / "spots_verificati.json").read_text(encoding="utf-8"))
    spot = written["spots"][0]
    assert (spot["lat"], spot["lng"]) == (41.9028, 12.4964)
    assert spot["difficulty"] == 3
    assert spot["fountain"] is False


async def test_spots_export_reports_slug_collisions(make_settings, tmp_path: Path) -> None:
    rows = [
        {"id": "aaaa-1", "name": "Muretti", "lat": 41.9, "lng": 12.5},
        {"id": "bbbb-2", "name": "Muretti", "lat": 41.8, "lng": 12.4},
    ]
    result = await run_export(make_settings, tmp_path, paged(rows))
    assert result.data["slug_collisions"] == 1
    written = json.loads((tmp_path / "spots_verificati.json").read_text(encoding="utf-8"))
    assert [spot["slug"] for spot in written["spots"]] == ["muretti", "muretti-bbbb2"]


def test_unique_slug_never_repeats() -> None:
    taken = {"spot", "spot-abc"}
    assert unique_slug("nuovo", "x", taken) == ("nuovo", False)
    assert unique_slug("spot", "abc", taken) == ("spot-abc-2", True)


async def test_spots_export_with_zero_rows_fails_and_writes_nothing(
    make_settings, tmp_path: Path
) -> None:
    result = await run_export(make_settings, tmp_path, paged([]))
    assert result.ok is False
    assert "nessuno spot" in result.message
    assert not (tmp_path / "spots_verificati.json").exists()


async def test_run_job_turns_upstream_errors_into_a_failed_result(
    make_settings, tmp_path: Path
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    result = await run_export(make_settings, tmp_path, handler)
    assert result.ok is False
    assert result.message.startswith("upstream_error")


async def test_run_job_survives_an_unexpected_exception(make_settings, tmp_path: Path) -> None:
    class BrokenJob:
        name = "rotto-di-prova"
        description = "solleva un'eccezione inattesa"

        async def run(self, ctx: JobContext) -> JobResult:
            raise RuntimeError("boom")

    REGISTRY["rotto-di-prova"] = BrokenJob()
    try:
        settings = make_settings(jobs_output_dir=tmp_path)
        async with httpx.AsyncClient() as http:
            ctx = JobContext(settings=settings, http=http, supabase=None, output_dir=tmp_path)
            result = await run_job("rotto-di-prova", ctx)
    finally:
        del REGISTRY["rotto-di-prova"]
    assert result.ok is False
    assert "RuntimeError" in result.message
    assert "elapsed_ms" in result.data


async def test_run_job_reports_an_unwritable_output_dir(make_settings, tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("non sono una cartella")
    target = blocker / "dentro"
    settings = make_settings(jobs_output_dir=target)
    async with httpx.AsyncClient() as http:
        ctx = JobContext(settings=settings, http=http, supabase=None, output_dir=target)
        result = await run_job("ping", ctx)
    assert result.ok is False
    assert "Error" in result.message  # NotADirectoryError / FileExistsError secondo il sistema


async def test_spots_export_without_supabase_fails_cleanly(make_settings, tmp_path: Path) -> None:
    settings = make_settings(jobs_output_dir=tmp_path)
    async with httpx.AsyncClient() as http:
        ctx = JobContext(settings=settings, http=http, supabase=None, output_dir=tmp_path)
        result = await run_job("spots-export", ctx)
    assert result.ok is False
    assert "Supabase non configurato" in result.message


# --- CLI ---------------------------------------------------------------------------------


def test_cli_lists_jobs(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["jobs"]) == 0
    printed = capsys.readouterr().out
    assert "ping" in printed
    assert "spots-export" in printed


def test_cli_runs_ping(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)  # nessun .env di sviluppo deve influire
    monkeypatch.setenv("JOBS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_FORMAT", "console")
    get_settings.cache_clear()
    try:
        assert main(["job", "ping"]) == 0
    finally:
        get_settings.cache_clear()
    printed = capsys.readouterr().out
    assert json.loads(printed)["message"] == "pong"


def test_cli_config_masks_secrets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "segreto-finta-xyz")
    monkeypatch.setenv("LOG_FORMAT", "console")
    get_settings.cache_clear()
    try:
        assert main(["config"]) == 0
    finally:
        get_settings.cache_clear()
    printed = capsys.readouterr().out
    assert "finta-xyz" not in printed
    assert "**********" in printed


def test_cli_unknown_job_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_FORMAT", "console")
    get_settings.cache_clear()
    try:
        assert main(["job", "non-esiste"]) == 2
    finally:
        get_settings.cache_clear()
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "not_found"


def test_cli_failed_job_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JOBS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_FORMAT", "console")
    get_settings.cache_clear()
    try:
        assert main(["job", "spots-export"]) == 1  # Supabase non configurato
    finally:
        get_settings.cache_clear()
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_cli_invalid_production_config_exits_2_without_revealing_secrets(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("HOST", "127.0.0.1")  # sbagliato in produzione
    monkeypatch.setenv("CORS_ORIGINS", "https://oigresergio.github.io")
    monkeypatch.setenv("JOB_TOKEN", "token-segretissimo-di-prova-1234567890")
    get_settings.cache_clear()
    try:
        assert main(["config"]) == 2
    finally:
        get_settings.cache_clear()
    captured = capsys.readouterr()
    assert "HOST" in captured.err
    assert "segretissimo" not in captured.err
    assert captured.out == ""
