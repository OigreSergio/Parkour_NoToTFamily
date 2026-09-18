"""Una sola funzione per tutte le chiamate HTTP in uscita.

Supabase e OSRM hanno in comune tre cose: un timeout opzionale che vince su
quello del client condiviso, la traduzione degli errori di rete di httpx in
`UpstreamError` (502, con il nome del servizio nel messaggio) e la regola di
non loggare mai l'URL completo, che potrebbe contenere coordinate. Stanno
qui, una volta sola: i client dei singoli servizi si occupano solo di
costruire la richiesta e leggere la risposta.
"""

from typing import Any

import httpx

from pkremote.errors import UpstreamError


async def fetch(
    http: httpx.AsyncClient,
    url: str,
    *,
    service: str,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout_seconds: float | None = None,
) -> httpx.Response:
    """`GET url` con i parametri e le intestazioni dati.

    Restituisce la risposta qualunque sia lo stato HTTP: decidere se un 400 è
    un errore spetta a chi conosce il servizio. Solo un errore di rete (DNS,
    connessione, timeout) diventa `UpstreamError`.
    """
    options: dict[str, Any] = {}
    if timeout_seconds is not None:
        options["timeout"] = timeout_seconds
    try:
        return await http.get(url, params=params or {}, headers=headers or {}, **options)
    except httpx.HTTPError as exc:
        raise UpstreamError(f"{service} non raggiungibile: {exc.__class__.__name__}") from exc
