"""Client per OSRM (Open Source Routing Machine).

OSRM espone `GET /route/v1/<profilo>/<lng>,<lat>;<lng>,<lat>` e risponde con
un JSON che ha `code: "Ok"` e una lista `routes`. Attenzione all'ordine:
OSRM vuole **longitudine prima della latitudine**, al contrario di come si
parla di coordinate; `Point` nel resto del servizio usa `lat, lng` e la
conversione avviene solo qui, in un posto solo.

Quando non trova un tragitto OSRM risponde 400 con `{"code": "NoRoute"}` (o
`NoSegment`, `InvalidQuery`): il motore è vivo, il codice dice cosa manca.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from pkremote.errors import UpstreamError
from pkremote.logs import log

if TYPE_CHECKING:  # evita l'import circolare a runtime: serve solo ai tipi
    from pkremote.services.routing import Point


@dataclass(frozen=True)
class OSRMRoute:
    distance_m: float
    duration_s: float
    geometry: dict[str, Any]


class OSRMClient:
    def __init__(self, *, base_url: str, profile: str, http: httpx.AsyncClient) -> None:
        self._base = base_url.rstrip("/")
        self.profile = profile
        self._http = http

    def __repr__(self) -> str:
        return f"OSRMClient(base_url={self._base!r}, profile={self.profile!r})"

    async def ping(self, *, timeout_seconds: float | None = None) -> None:
        """Verifica che il motore risponda: usata da /readyz.

        Si chiede il punto stradale più vicino a una coordinata qualunque:
        anche un 400 ("nessun segmento") dimostra che il processo è vivo. Solo
        un errore di rete o un 5xx contano come guasto. `timeout_seconds`, se
        dato, vince sul timeout del client condiviso.
        """
        url = f"{self._base}/nearest/v1/{self.profile}/12.4964,41.9028"
        options: dict[str, Any] = (
            {"timeout": timeout_seconds} if timeout_seconds is not None else {}
        )
        try:
            response = await self._http.get(url, params={"number": 1}, **options)
        except httpx.HTTPError as exc:
            raise UpstreamError(f"OSRM non raggiungibile: {exc.__class__.__name__}") from exc
        if response.status_code >= 500:
            raise UpstreamError(f"OSRM risponde {response.status_code}")

    async def route(self, start: "Point", end: "Point") -> OSRMRoute:
        """Il percorso tra due punti già arrotondati (vedi services/routing.py)."""
        coords = f"{start.lng},{start.lat};{end.lng},{end.lat}"
        url = f"{self._base}/route/v1/{self.profile}/{coords}"
        params = {"overview": "full", "geometries": "geojson", "steps": "false"}
        try:
            response = await self._http.get(url, params=params)
        except httpx.HTTPError as exc:
            log.warning("osrm_non_raggiungibile", error=exc.__class__.__name__)
            raise UpstreamError(f"OSRM non raggiungibile: {exc.__class__.__name__}") from exc
        # OSRM risponde 400 con un JSON `{"code": "NoRoute" | "NoSegment" | ...}`
        # quando è vivo ma non ha un tragitto: il codice vale più dello stato.
        if response.status_code not in (200, 400):
            raise UpstreamError(f"OSRM risponde {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise UpstreamError("OSRM: risposta non JSON") from exc
        if body.get("code") != "Ok" or not body.get("routes"):
            raise UpstreamError(f"OSRM: {body.get('code', 'risposta senza codice')}")
        first = body["routes"][0]
        return OSRMRoute(
            distance_m=float(first["distance"]),
            duration_s=float(first["duration"]),
            geometry=first["geometry"],
        )
