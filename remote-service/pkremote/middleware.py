"""Ciò che succede a ogni richiesta, prima e dopo la rotta.

Tre cose, in un posto solo:

1. CORS: chi, dal browser, può chiamare questa API. In produzione la lista è
   obbligatoria e non ammette "*" (controllo in `config.py`).
2. Intestazioni di sicurezza su ogni risposta: `X-Content-Type-Options`
   (il browser non "indovina" il tipo di un file), `Referrer-Policy` (chi
   segue un link da qui non porta con sé l'URL completo), `Cache-Control:
   no-store` (le risposte dell'API non vanno salvate da proxy intermedi: le
   coordinate di un percorso, anche arrotondate, non devono restare in una
   cache condivisa), `Strict-Transport-Security` solo in produzione, dove il
   TLS è garantito dal provider (in locale, su http, sarebbe un errore).
3. Un evento di log per richiesta al posto del log di accesso di uvicorn:
   metodo, percorso senza query string, stato, durata. Niente indirizzo del
   chiamante, niente parametri (le coordinate stanno lì). L'identificativo
   della richiesta compare in ogni riga di log emessa nel frattempo e torna
   al client in `X-Request-ID`: un errore visto dal telefono si ritrova nei
   log del provider.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pkremote.config import Settings
from pkremote.errors import error_payload
from pkremote.logs import bind_request, clear_request, log

CallNext = Callable[[Request], Awaitable[Response]]


def install_middleware(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,  # niente cookie: l'API non ha sessioni
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def _security_headers(request: Request, call_next: CallNext) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cache-Control", "no-store")
        if settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    @app.middleware("http")
    async def _request_log(request: Request, call_next: CallNext) -> Response:
        request_id = uuid.uuid4().hex[:12]
        bind_request(request_id=request_id, method=request.method, path=request.url.path)
        started = time.monotonic()
        try:
            response: Response = await call_next(request)
        except Exception:
            # Un errore non previsto: la traccia va nel log con l'id della
            # richiesta, e il client riceve l'involucro di sempre con lo stesso
            # id, così l'errore visto dal telefono si ritrova nei log.
            log.exception(
                "richiesta_fallita", elapsed_ms=round((time.monotonic() - started) * 1000)
            )
            clear_request()
            response = JSONResponse(
                status_code=500,
                content=error_payload("internal_error", "errore interno: cita X-Request-ID"),
            )
        else:
            log.info(
                "richiesta",
                status=response.status_code,
                elapsed_ms=round((time.monotonic() - started) * 1000),
            )
            clear_request()
        response.headers["X-Request-ID"] = request_id
        return response
