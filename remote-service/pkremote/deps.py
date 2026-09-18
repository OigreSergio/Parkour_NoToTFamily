"""Dipendenze FastAPI: come una rotta ottiene ciò che le serve.

FastAPI chiama queste funzioni per ogni richiesta e passa il risultato alla
rotta (`Depends`). Tutte leggono da `request.app.state`, dove `app.py` ha
messo la configurazione e i client creati all'avvio: così le rotte non
importano oggetti globali e nei test si può montare un'app con client finti.
"""

from typing import Annotated

import httpx
from fastapi import Depends, Header, Request

from pkremote.config import Settings
from pkremote.errors import JobsHttpDisabled, Unauthorized
from pkremote.integrations.osrm import OSRMClient
from pkremote.integrations.supabase import SupabaseClient
from pkremote.security import bearer_token, token_matches
from pkremote.services.cache import TTLCache


def settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def http_dep(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def route_cache_dep(request: Request) -> TTLCache:
    return request.app.state.route_cache


def osrm_dep(request: Request) -> OSRMClient | None:
    """None quando OSRM_BASE_URL non è impostato: la rotta risponde 503."""
    return request.app.state.osrm


def supabase_dep(request: Request) -> SupabaseClient | None:
    return request.app.state.supabase


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
