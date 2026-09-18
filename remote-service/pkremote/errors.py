"""Errori applicativi: un codice stabile, un messaggio, uno stato HTTP.

Ogni errore che il servizio vuole comunicare a chi lo chiama è una sottoclasse
di `AppError`. Il gestore in `app.py` li trasforma tutti nella stessa forma:

    {"error": {"code": "routing_unavailable", "message": "..."}}

Il `code` è la parte che i client devono usare per decidere cosa fare (per
esempio: su `routing_unavailable` la web app disegna la linea d'aria); il
`message` è diagnostico, può cambiare e non va mostrato tale e quale a un
utente (le traduzioni stanno nei client). È la stessa forma che il backend
esistente produce con il suo gestore (`backend/app/main.py`,
`app_error_handler`), così un client tratta i due servizi allo stesso modo.
"""

from fastapi import status


class AppError(Exception):
    """Base degli errori applicativi. Le sottoclassi fissano `code` e `status_code`."""

    code: str = "app_error"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.code
        super().__init__(self.message)

    def to_payload(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


class BadRequest(AppError):
    """Parametri mancanti o fuori dai limiti (es. coordinate non valide)."""

    code = "bad_request"
    status_code = 422  # la costante di Starlette ha cambiato nome tra le versioni


class Unauthorized(AppError):
    """Token dei job assente o sbagliato."""

    code = "unauthorized"
    status_code = status.HTTP_401_UNAUTHORIZED


class NotFound(AppError):
    """Risorsa inesistente (es. un job con quel nome non è registrato)."""

    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND


class Conflict(AppError):
    """L'azione contrasta con lo stato attuale (es. lo stesso job è già in corso)."""

    code = "conflict"
    status_code = status.HTTP_409_CONFLICT


class NotConfigured(AppError):
    """La funzione esiste ma l'ambiente non l'ha attivata (es. OSRM_BASE_URL vuoto).

    503 e non 500: non è un guasto, è una scelta di configurazione, e i client
    hanno un fallback previsto.
    """

    code = "not_configured"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class RoutingUnavailable(NotConfigured):
    code = "routing_unavailable"


class JobsHttpDisabled(NotConfigured):
    code = "jobs_http_disabled"


class UpstreamError(AppError):
    """Un servizio esterno (Supabase, OSRM) ha risposto male o non ha risposto."""

    code = "upstream_error"
    status_code = status.HTTP_502_BAD_GATEWAY
