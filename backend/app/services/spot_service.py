from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound
from app.models.spot import Spot, SpotStatus
from app.repositories import spots as spots_repo
from app.schemas.spot import SpotCreate


async def submit(session: AsyncSession, *, data: SpotCreate, submitted_by: UUID) -> Spot:
    spot = await spots_repo.create(session, data=data, submitted_by=submitted_by)
    await spots_repo.record_event(
        session, spot_id=spot.id, actor_id=submitted_by, action="submitted"
    )
    await session.commit()
    return spot


async def verify(session: AsyncSession, *, spot_id: UUID, verifier_id: UUID) -> Spot:
    spot = await spots_repo.get(session, spot_id)
    if spot is None:
        raise NotFound("spot not found")
    if spot.status == SpotStatus.verified:
        raise Conflict("spot already verified")
    spot = await spots_repo.set_verified(session, spot=spot, verifier_id=verifier_id)
    await spots_repo.record_event(
        session, spot_id=spot.id, actor_id=verifier_id, action="verified"
    )
    await session.commit()
    return spot


async def reject(
    session: AsyncSession, *, spot_id: UUID, verifier_id: UUID, reason: str
) -> Spot:
    spot = await spots_repo.get(session, spot_id)
    if spot is None:
        raise NotFound("spot not found")
    spot = await spots_repo.set_rejected(
        session, spot=spot, verifier_id=verifier_id, reason=reason
    )
    await spots_repo.record_event(
        session, spot_id=spot.id, actor_id=verifier_id, action="rejected", note=reason
    )
    await session.commit()
    return spot
