from datetime import datetime, timezone
from uuid import UUID

from geoalchemy2.functions import ST_DWithin, ST_GeogFromText
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spot import Spot, SpotModerationEvent, SpotStatus
from app.schemas.spot import Point, SpotCreate


def _point_wkt(p: Point) -> str:
    return f"SRID=4326;POINT({p.lng} {p.lat})"


async def create(session: AsyncSession, *, data: SpotCreate, submitted_by: UUID) -> Spot:
    spot = Spot(
        name=data.name,
        description=data.description,
        location=_point_wkt(data.location),
        photo_urls=data.photo_urls,
        difficulty=data.difficulty,
        status=SpotStatus.pending,
        submitted_by=submitted_by,
    )
    session.add(spot)
    await session.flush()
    return spot


async def get(session: AsyncSession, spot_id: UUID) -> Spot | None:
    return await session.get(Spot, spot_id)


async def list_verified_near(
    session: AsyncSession, *, lat: float, lng: float, radius_m: int, limit: int
) -> list[Spot]:
    origin = ST_GeogFromText(f"SRID=4326;POINT({lng} {lat})")
    stmt = (
        select(Spot)
        .where(Spot.status == SpotStatus.verified)
        .where(ST_DWithin(Spot.location, origin, radius_m))
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


async def list_by_status(session: AsyncSession, status: SpotStatus, *, limit: int = 100) -> list[Spot]:
    stmt = select(Spot).where(Spot.status == status).order_by(Spot.created_at).limit(limit)
    return list((await session.execute(stmt)).scalars())


async def set_verified(session: AsyncSession, *, spot: Spot, verifier_id: UUID) -> Spot:
    spot.status = SpotStatus.verified
    spot.verified_by = verifier_id
    spot.verified_at = datetime.now(timezone.utc)
    spot.rejection_reason = None
    await session.flush()
    return spot


async def set_rejected(
    session: AsyncSession, *, spot: Spot, verifier_id: UUID, reason: str
) -> Spot:
    spot.status = SpotStatus.rejected
    spot.verified_by = verifier_id
    spot.verified_at = datetime.now(timezone.utc)
    spot.rejection_reason = reason
    await session.flush()
    return spot


async def record_event(
    session: AsyncSession, *, spot_id: UUID, actor_id: UUID, action: str, note: str | None = None
) -> SpotModerationEvent:
    event = SpotModerationEvent(spot_id=spot_id, actor_id=actor_id, action=action, note=note)
    session.add(event)
    await session.flush()
    return event
