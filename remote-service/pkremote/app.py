"""Costruisce l'applicazione FastAPI. È il punto in cui tutto si incastra.

`create_app` è una *fabbrica*: riceve (o legge) la configurazione, crea gli
oggetti condivisi e monta le rotte. Avere una funzione, e non un oggetto
globale, permette a ogni test di costruirsi un'app con la configurazione e i
client finti che vuole, e a uvicorn di avviarla con `--factory`.

Ciclo di vita (`lifespan`), tutto su `app.state`, letto dalle rotte tramite
`deps.py`:
- all'avvio: un solo `httpx.AsyncClient` per processo (un pool di connessioni
  riusato da tutte le richieste), la cache dei percorsi, l'ultimo esito di
  /readyz, i lock dei job, i client Supabase e OSRM se configurati;
- alla chiusura: il client HTTP viene chiuso in modo pulito.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from pkremote import __version__
from pkremote.api import health, jobs, route
from pkremote.config import Settings, get_settings
from pkremote.errors import install_error_handlers
from pkremote.integrations.osrm import OSRMClient
from pkremote.integrations.supabase import SupabaseClient
from pkremote.logs import configure_logging, log
from pkremote.middleware import install_middleware
from pkremote.services.cache import TTLCache


def create_app(
    settings: Settings | None = None, http_client: httpx.AsyncClient | None = None
) -> FastAPI:
    """Crea l'app. `http_client` esiste per i test (trasporto finto); in
    produzione resta None e il client viene creato e chiuso dal lifespan."""
    settings = settings or get_settings()
    configure_logging(log_format=settings.log_format, debug=settings.debug)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owns_client = http_client is None
        http = http_client or httpx.AsyncClient(
            timeout=settings.http_timeout_seconds,
            headers={"User-Agent": f"pkremote/{__version__}"},
        )
        app.state.http = http
        app.state.route_cache = TTLCache(
            ttl_seconds=settings.route_cache_ttl_seconds,
            max_entries=settings.route_cache_max_entries,
        )
        # L'ultimo esito di /readyz, per non interrogare gli upstream a ogni sonda.
        app.state.ready_cache = TTLCache(
            ttl_seconds=max(1, settings.ready_cache_seconds), max_entries=1
        )
        # Un lock per nome di job: la stessa esportazione non gira due volte
        # insieme, scrivendo lo stesso file (vedi api/jobs.py).
        app.state.job_locks = {}
        app.state.job_locks_guard = asyncio.Lock()
        app.state.supabase = SupabaseClient.from_settings(settings, http)
        app.state.osrm = (
            OSRMClient(base_url=settings.osrm_base_url, profile=settings.osrm_profile, http=http)
            if settings.osrm_base_url
            else None
        )
        log.info(
            "avvio",
            env=settings.app_env,
            instance=settings.instance_name,
            version=__version__,
            supabase=app.state.supabase is not None,
            osrm=app.state.osrm is not None,
            jobs_http=settings.jobs_http_enabled,
        )
        try:
            yield
        finally:
            if owns_client:
                await http.aclose()
            log.info("arresto", instance=settings.instance_name)

    app = FastAPI(
        title="PkFAMILY - servizio remoto",
        version=__version__,
        lifespan=lifespan,
        # Documentazione interattiva e schema OpenAPI solo fuori dalla produzione:
        # in remoto l'elenco delle rotte non è un'informazione da regalare.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    install_middleware(app, settings)
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(route.router)
    app.include_router(jobs.router)
    return app
