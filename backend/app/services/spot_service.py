from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, ValidationFailed
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


async def create_verified(session: AsyncSession, *, data: SpotCreate, admin_id: UUID) -> Spot:
    """Admin-only: create a spot that is immediately public (``verified``).

    Regular users can only ``submit`` (status starts as ``pending``); this is
    the single code path that skips the moderation queue, and it still leaves
    an audit trail.
    """
    spot = await spots_repo.create(session, data=data, submitted_by=admin_id)
    spot = await spots_repo.set_verified(session, spot=spot, verifier_id=admin_id)
    await spots_repo.record_event(
        session, spot_id=spot.id, actor_id=admin_id, action="created_by_admin"
    )
    await session.commit()
    return spot


async def verify(
    session: AsyncSession,
    *,
    spot_id: UUID,
    verifier_id: UUID,
    photos_real: bool,
    note: str | None = None,
) -> Spot:
    if not photos_real:
        raise ValidationFailed("cannot verify a spot without confirming its photos are real")
    spot = await spots_repo.get(session, spot_id)
    if spot is None:
        raise NotFound("spot not found")
    if spot.status == SpotStatus.verified:
        raise Conflict("spot already verified")
    if not spot.photo_urls:
        raise ValidationFailed("a spot needs at least one photo before it can be verified")
    spot = await spots_repo.set_verified(session, spot=spot, verifier_id=verifier_id)
    await spots_repo.record_event(
        session,
        spot_id=spot.id,
        actor_id=verifier_id,
        action="verified",
        note=note or "photos confirmed real",
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
