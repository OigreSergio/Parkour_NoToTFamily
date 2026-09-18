"""Dipendenze FastAPI: come una rotta ottiene ciò che le serve.

FastAPI chiama queste funzioni per ogni richiesta e passa il risultato alla
rotta (`Depends`). Tutte leggono da `request.app.state`, dove `app.py` ha
messo la configurazione e gli oggetti creati all'avvio: le rotte non toccano
`app.state` direttamente e non importano oggetti globali, e nei test si può
montare un'app con client finti.
"""

import asyncio
from typing import Annotated

from fastapi import Depends, Header, Request

from pkremote.config import Settings
from pkremote.errors import JobsHttpDisabled, NotFound, Unauthorized
from pkremote.integrations.osrm import OSRMClient
from pkremote.integrations.supabase import SupabaseClient
from pkremote.jobs import REGISTRY, JobContext
from pkremote.security import bearer_token, token_matches
from pkremote.services.cache import TTLCache


def settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def route_cache_dep(request: Request) -> TTLCache:
    return request.app.state.route_cache


def ready_cache_dep(request: Request) -> TTLCache:
    return request.app.state.ready_cache


def osrm_dep(request: Request) -> OSRMClient | None:
    """None quando OSRM_BASE_URL non è impostato: la rotta risponde 503."""
    return request.app.state.osrm


def supabase_dep(request: Request) -> SupabaseClient | None:
    """None quando manca SUPABASE_URL o la chiave pubblicabile."""
    return request.app.state.supabase


def job_context_dep(request: Request) -> JobContext:
    """Lo stesso contesto che la CLI costruisce, con i client condivisi dell'app."""
    state = request.app.state
    return JobContext.build(state.settings, state.http, state.supabase)


async def job_lock_dep(name: str, request: Request) -> asyncio.Lock:
    """Un lock per nome di job (`name` è il parametro di percorso della rotta).

    Solo per i job registrati: altrimenti ogni nome inventato lascerebbe un
    lock in memoria per sempre. Il 404 qui è lo stesso che darebbe `run_job`.
    """
    if name not in REGISTRY:
        raise NotFound("job sconosciuto")
    state = request.app.state
    async with state.job_locks_guard:
        return state.job_locks.setdefault(name, asyncio.Lock())


def require_job_token(
    settings: Annotated[Settings, Depends(settings_dep)],
    authorization: Annotated[str, Header()] = "",
) -> None:
    """Protegge le rotte dei job.

    - senza JOB_TOKEN configurato: 503 `jobs_http_disabled` (i job restano
      disponibili da riga di comando);
    - token assente o diverso: 401. Il confronto è a tempo costante.
    """
    if not settings.jobs_http_enabled:
        raise JobsHttpDisabled("i job via HTTP sono disattivati: imposta JOB_TOKEN per abilitarli")
    if not token_matches(bearer_token(authorization), settings.job_token):
        raise Unauthorized("token dei job assente o non valido")
