"""Costruisce l'applicazione FastAPI. È il punto in cui tutto si incastra.

`create_app` è una *fabbrica*: riceve (o legge) la configurazione, crea i
client condivisi e monta le rotte. Avere una funzione, e non un oggetto
globale, permette a ogni test di costruirsi un'app con la configurazione e i
client finti che vuole, e a uvicorn di avviarla con `--factory`.

Ciclo di vita (`lifespan`):
- all'avvio: un solo `httpx.AsyncClient` per processo (un pool di connessioni
  riusato da tutte le richieste), la cache dei percorsi, l'ultimo esito di
  /readyz, i lock dei job, i client Supabase e OSRM se configurati;
- alla chiusura: il client HTTP viene chiuso in modo pulito.
"""

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from pkremote import __version__
from pkremote.api import health, jobs, route
from pkremote.config import Settings, get_settings
from pkremote.errors import AppError
from pkremote.integrations.osrm import OSRMClient
from pkremote.integrations.supabase import SupabaseClient
from pkremote.logs import bind_request, clear_request, configure_logging, log
from pkremote.security import install_security_headers
from pkremote.services.cache import TTLCache

# Stato HTTP -> codice stabile, per gli errori che non nascono da AppError.
ERROR_CODES_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    422: "bad_request",
}


def build_supabase_client(settings: Settings, http: httpx.AsyncClient) -> SupabaseClient | None:
    """Il client di lettura nasce solo dalla chiave pubblicabile.

    Con le RLS attive quel client vede solo dati pubblici, che per le letture
    è esattamente ciò che vogliamo. La chiave segreta non è mai un ripiego:
    se è l'unica presente, il servizio lo dice nel log e resta senza Supabase.
    """
    if not settings.supabase_configured:
        if settings.supabase_url is not None and settings.supabase_secret_key is not None:
            log.warning(
                "supabase_lettura_disattivata",
                motivo="manca SUPABASE_PUBLISHABLE_KEY: la chiave segreta non si usa per leggere",
            )
        return None
    assert settings.supabase_url is not None  # garantiti da supabase_configured
    assert settings.supabase_publishable_key is not None
    return SupabaseClient(
        url=settings.supabase_url,
        key=settings.supabase_publishable_key,
        role="publishable",
        http=http,
    )


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
        app.state.supabase = build_supabase_client(settings, http)
        app.state.osrm = (
            OSRMClient(base_url=settings.osrm_base_url, profile=settings.osrm_profile, http=http)
            if settings.osrm_base_url
            else None
        )
        log.info(
            "avvio",
            env=settings.env,
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

    # CORS: chi, dal browser, può chiamare questa API. In produzione la lista
    # è obbligatoria e non ammette "*" (controllo in config.py).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # niente cookie: l'API non ha sessioni
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    install_security_headers(app, production=settings.is_production)

    # Tutti gli errori hanno la stessa forma, {"error": {"code", "message"}}:
    # quelli nostri (AppError), quelli di validazione di FastAPI (parametro
    # mancante o malformato) e quelli di Starlette (404, 405).
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Solo dove e perché, mai il valore ricevuto (potrebbe essere una coordinata).
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error.get('loc', ()))}: {error.get('msg', '')}"
            for error in exc.errors()
        )
        payload = {
            "error": {"code": "bad_request", "message": f"richiesta non valida ({problems})"}
        }
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ERROR_CODES_BY_STATUS.get(exc.status_code, "http_error")
        payload = {"error": {"code": code, "message": str(exc.detail)}}
        return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)

    @app.middleware("http")
    async def _request_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Un evento per richiesta al posto del log di accesso di uvicorn:
        metodo, percorso senza query string, stato, durata. Niente indirizzo
        del chiamante, niente parametri (le coordinate stanno lì).

        L'identificativo della richiesta compare in ogni riga di log emessa
        mentre la richiesta è in corso e torna al client in `X-Request-ID`:
        un errore visto dal telefono si ritrova nei log del provider.
        """
        request_id = uuid.uuid4().hex[:12]
        bind_request(request_id=request_id, method=request.method, path=request.url.path)
        started = time.monotonic()
        try:
            response = await call_next(request)
            log.info(
                "richiesta",
                status=response.status_code,
                elapsed_ms=round((time.monotonic() - started) * 1000),
            )
        finally:
            clear_request()
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(health.router)
    app.include_router(route.router)
    app.include_router(jobs.router)
    return app
