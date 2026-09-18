"""Stato del servizio: le due domande che un host remoto fa in continuazione.

- `GET /healthz` ("sei vivo?"): risponde subito, senza toccare la rete. Il
  provider la usa per decidere se riavviare il container.
- `GET /readyz` ("sei pronto a servire?"): prova ogni dipendenza configurata,
  in parallelo, con il timeout breve di `READY_TIMEOUT_SECONDS`, e riusa
  l'esito per `READY_CACHE_SECONDS`. Un bilanciatore la usa per decidere se
  mandare traffico a questa istanza.

Una dipendenza **non configurata** non rende il servizio "non pronto": il
servizio è progettato per girare anche solo con /healthz e i job locali. Solo
una dipendenza configurata che non risponde produce 503.

Gli stati sono parole fisse in inglese (`ok`, `error`, `not_configured`,
`ready`, `not_ready`): sono per le macchine, come i `code` degli errori.
"""

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from pkremote import __version__
from pkremote.config import Settings
from pkremote.deps import osrm_dep, ready_cache_dep, route_cache_dep, settings_dep, supabase_dep
from pkremote.errors import UpstreamError
from pkremote.integrations.osrm import OSRMClient
from pkremote.integrations.supabase import SupabaseClient
from pkremote.logs import log
from pkremote.services.cache import TTLCache

router = APIRouter(tags=["stato"])


@router.get("/healthz")
async def healthz(settings: Annotated[Settings, Depends(settings_dep)]) -> dict[str, str]:
    """Vivo. Nessun segreto, nessun dato: solo ciò che serve a riconoscere l'istanza."""
    return {
        "status": "ok",
        "instance": settings.instance_name,
        "env": settings.app_env,
        "version": __version__,
    }


async def _check(name: str, client: Any, timeout_seconds: float) -> dict[str, str]:
    """Esegue `client.ping()` entro `timeout_seconds` secondi e traduce l'esito."""
    if client is None:
        return {"name": name, "status": "not_configured"}
    try:
        await client.ping(timeout_seconds=timeout_seconds)
    except UpstreamError as exc:
        return {"name": name, "status": "error", "detail": exc.message}
    except Exception as exc:  # un controllo di prontezza non deve mai rispondere 500
        log.exception("readyz_controllo_fallito", dipendenza=name)
        return {
            "name": name,
            "status": "error",
            "detail": f"errore inatteso: {exc.__class__.__name__}",
        }
    return {"name": name, "status": "ok"}


@router.get("/readyz")
async def readyz(
    settings: Annotated[Settings, Depends(settings_dep)],
    supabase: Annotated[SupabaseClient | None, Depends(supabase_dep)],
    osrm: Annotated[OSRMClient | None, Depends(osrm_dep)],
    ready_cache: Annotated[TTLCache, Depends(ready_cache_dep)],
    route_cache: Annotated[TTLCache, Depends(route_cache_dep)],
) -> JSONResponse:
    """Pronto. 200 se tutte le dipendenze configurate rispondono, altrimenti 503.

    L'esito resta valido per `READY_CACHE_SECONDS`: sonde ravvicinate non
    costano chiamate a Supabase e OSRM, e nessuno può usare questa rotta per
    far martellare gli upstream.
    """
    cached = await ready_cache.get("readyz")
    if cached is not None:
        return JSONResponse(status_code=cached["status_code"], content=cached["body"])
    checks = await asyncio.gather(
        _check("supabase", supabase, settings.ready_timeout_seconds),
        _check("osrm", osrm, settings.ready_timeout_seconds),
    )
    ready = all(check["status"] != "error" for check in checks)
    body = {
        "status": "ready" if ready else "not_ready",
        "checks": list(checks),
        "route_cache": route_cache.stats(),
    }
    status_code = 200 if ready else 503
    if settings.ready_cache_seconds > 0:
        await ready_cache.set("readyz", {"status_code": status_code, "body": body})
    return JSONResponse(status_code=status_code, content=body)
