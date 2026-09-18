"""Percorsi: dal punto A al punto B passando da OSRM, con cache e privacy.

È la "fase 2" di docs/ROUTING_PK.md: oggi la web app chiama direttamente il
server pubblico FOSSGIS da `scripts/web/pk-route.js`; con questo modulo può
chiamare invece `GET /api/v1/route` del servizio remoto, che:

1. arrotonda le coordinate ricevute (privacy: masterplan cap. 6.4 chiede che
   verso il proxy viaggino solo coordinate arrotondate a circa 100 m, e qui lo
   facciamo comunque anche se il client se ne dimenticasse);
2. cerca il tragitto in cache;
3. se manca, chiede a OSRM e salva la risposta.

Il modulo non sa nulla di HTTP: la rotta in `api/route.py` fa solo da
traduttore tra query string e queste funzioni.
"""

from dataclasses import asdict, dataclass, replace
from typing import Any

from pkremote.errors import BadRequest, RoutingUnavailable
from pkremote.integrations.osrm import OSRMClient
from pkremote.services.cache import TTLCache


@dataclass(frozen=True)
class Point:
    """Una coordinata geografica. `lat` prima di `lng`, come si legge su una mappa."""

    lat: float
    lng: float


@dataclass(frozen=True)
class RouteAnswer:
    """Ciò che il servizio restituisce a chi chiede un percorso."""

    distance_m: float
    duration_s: float
    #: Geometria GeoJSON `LineString` con coordinate `[lng, lat]`, pronta per MapLibre.
    geometry: dict[str, Any]
    #: Vero se la risposta viene dalla cache e non da una chiamata a OSRM.
    cached: bool
    #: Con quanta approssimazione (in metri) sono state usate le coordinate.
    precision_m: int
    #: Chi ha calcolato il percorso (oggi solo "osrm").
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_point(text: str) -> Point:
    """Da "41.9028,12.4964" a `Point(lat=41.9028, lng=12.4964)`.

    Controlla forma e intervalli: una latitudine fuori da [-90, 90] o una
    longitudine fuori da [-180, 180] non è un errore di OSRM da inoltrare, è
    una richiesta sbagliata da rifiutare subito con 422.
    """
    # I messaggi non ripetono il valore ricevuto: una coordinata, anche
    # sbagliata, è pur sempre una posizione, e la risposta potrebbe finire in
    # un log del client o di un proxy.
    parts = text.split(",")
    if len(parts) != 2:
        raise BadRequest('coordinate attese come "lat,lng"')
    try:
        lat, lng = float(parts[0]), float(parts[1])
    except ValueError as exc:
        raise BadRequest("coordinate non numeriche") from exc
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
        raise BadRequest("coordinate fuori intervallo (lat in [-90, 90], lng in [-180, 180])")
    return Point(lat=lat, lng=lng)


def round_point(point: Point, decimals: int) -> Point:
    """Arrotonda a `decimals` cifre: 3 cifre = circa 111 m di passo in latitudine."""
    return Point(lat=round(point.lat, decimals), lng=round(point.lng, decimals))


def precision_in_meters(decimals: int) -> int:
    """Un grado di latitudine vale ~111 km; ogni decimale divide per 10.

    Mai zero: con 6 decimali il passo è 11 centimetri, che si dichiara come
    1 metro invece di far credere a una precisione infinita.
    """
    return max(1, round(111_000 / (10**decimals)))


def cache_key(a: Point, b: Point, profile: str) -> str:
    """Chiave stabile: stesso tragitto, stesso profilo = stessa voce di cache."""
    return f"{profile}|{a.lat},{a.lng}|{b.lat},{b.lng}"


async def compute_route(
    start: Point,
    end: Point,
    *,
    osrm: OSRMClient | None,
    cache: TTLCache,
    decimals: int,
) -> RouteAnswer:
    """Il percorso da `start` a `end`, dalla cache o da OSRM.

    Se OSRM non è configurato alza `RoutingUnavailable` (503): i client
    conoscono il caso e ripiegano sulla distanza in linea d'aria.
    """
    if osrm is None:
        raise RoutingUnavailable(
            "il motore dei percorsi non è configurato su questa istanza (OSRM_BASE_URL vuoto)"
        )

    # Arrotondamento PRIMA di qualsiasi altra cosa: da qui in poi il servizio
    # lavora, mette in cache e inoltra solo coordinate approssimate.
    start, end = round_point(start, decimals), round_point(end, decimals)
    key = cache_key(start, end, osrm.profile)

    cached = await cache.get(key)
    if cached is not None:
        return replace(cached, cached=True)

    result = await osrm.route(start, end)  # può alzare UpstreamError (502)
    answer = RouteAnswer(
        distance_m=result.distance_m,
        duration_s=result.duration_s,
        geometry=result.geometry,
        cached=False,
        precision_m=precision_in_meters(decimals),
        source="osrm",
    )
    await cache.set(key, answer)
    return answer
