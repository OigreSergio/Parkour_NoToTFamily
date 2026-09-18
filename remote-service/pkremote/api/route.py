"""`GET /api/v1/route?from=lat,lng&to=lat,lng`: il proxy dei percorsi.

È la rotta che `docs/ROUTING_PK.md` (fase 2) prevede al posto della chiamata
diretta al server pubblico fatta oggi da `scripts/web/pk-route.js`. La
risposta contiene una geometria GeoJSON già nel formato che MapLibre disegna.

Esempio di risposta:

    {
      "distance_m": 1234.5, "duration_s": 987.6,
      "geometry": {"type": "LineString", "coordinates": [[12.49, 41.90], ...]},
      "cached": false, "precision_m": 111, "source": "osrm"
    }
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from pkremote.config import Settings
from pkremote.deps import osrm_dep, route_cache_dep, settings_dep
from pkremote.integrations.osrm import OSRMClient
from pkremote.services.cache import TTLCache
from pkremote.services.routing import compute_route, parse_point

router = APIRouter(prefix="/api/v1", tags=["percorsi"])


class RouteOut(BaseModel):
    distance_m: float
    duration_s: float
    geometry: dict[str, Any]
    cached: bool
    precision_m: int
    source: str


@router.get("/route", response_model=RouteOut)
async def get_route(
    settings: Annotated[Settings, Depends(settings_dep)],
    osrm: Annotated[OSRMClient | None, Depends(osrm_dep)],
    cache: Annotated[TTLCache, Depends(route_cache_dep)],
    from_: Annotated[str, Query(alias="from", description='Partenza come "lat,lng"')],
    to: Annotated[str, Query(description='Arrivo come "lat,lng"')],
) -> RouteOut:
    """Percorso pedonale tra due punti. 503 se il motore non è configurato,
    502 se OSRM non risponde, 422 se le coordinate non sono valide."""
    answer = await compute_route(
        parse_point(from_),
        parse_point(to),
        osrm=osrm,
        cache=cache,
        decimals=settings.coordinate_decimals,
    )
    return RouteOut(**answer.to_dict())
