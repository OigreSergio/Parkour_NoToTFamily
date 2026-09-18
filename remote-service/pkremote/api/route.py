"""`GET /api/v1/route?from=lat,lng&to=lat,lng`: il proxy dei percorsi.

È la rotta che `docs/ROUTING_PK.md` (fase 2) prevede al posto della chiamata
diretta al server pubblico fatta oggi da `scripts/web/pk-route.js`. Il
profilo lo decide l'istanza con `OSRM_PROFILE`, non il client. La risposta
contiene una geometria GeoJSON già nel formato che MapLibre disegna:

    {
      "distance_m": 1234.5, "duration_s": 987.6,
      "geometry": {"type": "LineString", "coordinates": [[12.49, 41.90], ...]},
      "cached": false, "precision_m": 111, "source": "osrm"
    }
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from pkremote.config import Settings
from pkremote.deps import osrm_dep, route_cache_dep, settings_dep
from pkremote.integrations.osrm import OSRMClient
from pkremote.services.cache import TTLCache
from pkremote.services.routing import RouteAnswer, compute_route, parse_point

router = APIRouter(prefix="/api/v1", tags=["percorsi"])


@router.get("/route")
async def get_route(
    settings: Annotated[Settings, Depends(settings_dep)],
    osrm: Annotated[OSRMClient | None, Depends(osrm_dep)],
    cache: Annotated[TTLCache, Depends(route_cache_dep)],
    from_: Annotated[str, Query(alias="from", description='Partenza come "lat,lng"')],
    to: Annotated[str, Query(description='Arrivo come "lat,lng"')],
) -> RouteAnswer:
    """Percorso pedonale tra due punti. 503 se il motore non è configurato,
    502 se OSRM non risponde, 404 `no_route` se non esiste un tragitto,
    422 se le coordinate non sono valide."""
    return await compute_route(
        parse_point(from_),
        parse_point(to),
        osrm=osrm,
        cache=cache,
        decimals=settings.coordinate_decimals,
    )
