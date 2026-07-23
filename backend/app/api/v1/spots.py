from fastapi import APIRouter, Depends, Query, status
from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.core.exceptions import NotFound
from app.models.spot import Spot
from app.models.user import User
from app.repositories import spots as spots_repo
from app.schemas.spot import Point, SpotCreate, SpotOut, SpotSearchQuery
from app.services import spot_service

router = APIRouter(prefix="/spots", tags=["spots"])


def _to_out(spot: Spot) -> SpotOut:
    pt = to_shape(spot.location)
    return SpotOut(
        id=spot.id,
        name=spot.name,
        description=spot.description,
        location=Point(lat=pt.y, lng=pt.x),
        photo_urls=spot.photo_urls,
        difficulty=spot.difficulty,
        status=spot.status,
        submitted_by=spot.submitted_by,
        verified_at=spot.verified_at,
        created_at=spot.created_at,
    )


@router.post("", response_model=SpotOut, status_code=status.HTTP_201_CREATED)
async def submit_spot(
    data: SpotCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> SpotOut:
    spot = await spot_service.submit(session, data=data, submitted_by=user.id)
    return _to_out(spot)


@router.get("", response_model=list[SpotOut])
async def list_nearby(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_m: int = Query(5000, ge=10, le=50_000),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(db_session),
) -> list[SpotOut]:
    q = SpotSearchQuery(lat=lat, lng=lng, radius_m=radius_m, limit=limit)
    spots = await spots_repo.list_verified_near(
        session, lat=q.lat, lng=q.lng, radius_m=q.radius_m, limit=q.limit
    )
    return [_to_out(s) for s in spots]


@router.get("/{spot_id}", response_model=SpotOut)
async def get_spot(spot_id, session: AsyncSession = Depends(db_session)) -> SpotOut:
    spot = await spots_repo.get(session, spot_id)
    if spot is None:
        raise NotFound("spot not found")
    return _to_out(spot)
