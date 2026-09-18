"""Log strutturati, pensati per essere letti da un servizio remoto.

Due formati:

- `json`: una riga JSON per evento. È ciò che i provider (Fly, Render, un
  qualsiasi raccoglitore di log) sanno indicizzare e filtrare;
- `console`: colorato e leggibile, per lo sviluppo sul proprio computer.

Tutto passa da un unico punto: i log del servizio (structlog) e quelli di
uvicorn (il modulo `logging` standard) finiscono nello stesso formatter, così
in remoto ogni riga è JSON, comprese quelle di avvio e arresto del server.
L'output va su stderr: stdout resta ai dati (per esempio il JSON di
`pkremote job <nome>`).

Una regola vale ovunque: **nessun dato personale nei log** (masterplan
cap. 4.7 e 6.4). Il processore `_omit_personal_data` sostituisce il valore
di chiavi come `email`, `lat`, `lng`, `authorization` con un segnaposto; e il
log di accesso di uvicorn, che scriverebbe la query string intera (quindi le
coordinate esatte prima dell'arrotondamento) e l'indirizzo del chiamante, è
spento: al suo posto `app.py` registra un evento per richiesta con metodo,
percorso senza query, stato e durata.
"""

import logging
import sys
from typing import Any

import structlog

# Chiavi il cui valore non deve mai comparire in un log, qualunque sia l'evento.
PERSONAL_OR_SECRET_KEYS = frozenset(
    {
        "email",
        "lat",
        "lng",
        "latitude",
        "longitude",
        "coords",
        "authorization",
        "apikey",
        "api_key",
        "token",
        "password",
        "secret",
        "key",
        "query",
        "client_addr",
    }
)


def _omit_personal_data(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Processore structlog: maschera i valori delle chiavi sensibili."""
    for key in list(event_dict):
        if key.lower() in PERSONAL_OR_SECRET_KEYS:
            event_dict[key] = "[omesso]"
    return event_dict


def configure_logging(*, log_format: str, debug: bool) -> None:
    """Configura structlog e il modulo `logging` standard (usato da uvicorn).

    Va chiamata una volta all'avvio; chiamarla di nuovo (per esempio nei test)
    è innocuo perché riconfigura da capo.
    """
    level = logging.DEBUG if debug else logging.INFO

    # Processori comuni: valgono sia per gli eventi structlog sia per le righe
    # che arrivano dal modulo logging (uvicorn, librerie).
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,  # id della richiesta, metodo, percorso
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # sempre UTC (masterplan 0.4)
        _omit_personal_data,
    ]
    renderer: Any = (
        structlog.dev.ConsoleRenderer()
        if log_format == "console"
        else structlog.processors.JSONRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
    )
    # Su stderr, non stdout: così `pkremote job <nome>` può stampare il suo JSON
    # su stdout e chi lo lancia lo legge pulito. I provider raccolgono entrambi.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # I logger di uvicorn passano dalla radice, senza handler propri: in remoto
    # anche "Started server process" è una riga JSON. Il log di accesso resta
    # spento (vedi in testa): `__main__.py` lo disattiva anche in uvicorn.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


def bind_request(**values: Any) -> None:
    """Lega dei valori (id della richiesta, metodo, percorso) a tutti i log
    emessi da qui alla fine della richiesta: `merge_contextvars` li aggiunge
    a ogni evento senza doverli passare a mano."""
    structlog.contextvars.bind_contextvars(**values)


def clear_request() -> None:
    structlog.contextvars.clear_contextvars()


#: Il logger da importare negli altri moduli: `from pkremote.logs import log`.
log = structlog.get_logger("pkremote")
