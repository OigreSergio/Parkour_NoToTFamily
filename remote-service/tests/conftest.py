"""Attrezzi comuni ai test.

Idea di fondo: ogni test costruisce la propria app con `create_app`, passando
una configurazione esplicita e, quando serve, un client HTTP con trasporto
finto (`httpx.MockTransport`). Così nessun test tocca la rete, nessun test
dipende dalle variabili d'ambiente della macchina, e si può provare anche il
caso "OSRM risponde 500" senza avere OSRM.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from pkremote.app import create_app
from pkremote.config import Settings

# Tutte le variabili d'ambiente che la configurazione leggerebbe: vengono
# tolte prima di ogni test, così un `PORT` o un `ENV` impostati nel sistema
# non cambiano l'esito dei test.
ENVIRONMENT_KEYS = [name.upper() for name in Settings.model_fields]


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def make_settings() -> Callable[..., Settings]:
    """Configurazione di test: `env=test`, log leggibili, un'origine CORS finta."""

    def _make(**overrides: Any) -> Settings:
        values: dict[str, Any] = {
            "app_env": "test",
            "log_format": "console",
            "cors_origins": ["http://localhost:3000"],
        }
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return _make


@pytest.fixture
def make_client(make_settings: Callable[..., Settings]) -> Callable[..., Any]:
    """Un client HTTP verso un'app costruita apposta per il test.

    Uso::

        async with make_client(handler, osrm_base_url="http://osrm:5000") as (client, app):
            response = await client.get("/readyz")

    `handler` è una funzione `(httpx.Request) -> httpx.Response` che fa le
    veci di Supabase e OSRM. Se manca, l'app crea un client HTTP vero ma
    nessun test qui lo usa verso la rete.
    """

    @asynccontextmanager
    async def _make(
        handler: Callable[[httpx.Request], httpx.Response] | None = None, **overrides: Any
    ) -> AsyncIterator[tuple[httpx.AsyncClient, FastAPI]]:
        settings = make_settings(**overrides)
        upstream = None
        if handler is not None:
            upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app = create_app(settings, http_client=upstream)
        try:
            # `lifespan_context` esegue avvio e arresto dell'app come farebbe uvicorn.
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    yield client, app
        finally:
            if upstream is not None:  # anche se il test fallisce a metà
                await upstream.aclose()

    return _make
