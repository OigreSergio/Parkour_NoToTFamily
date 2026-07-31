from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound
from app.models.spot import Spot, SpotComment, SpotStatus
from app.repositories import spots as spots_repo
from app.schemas.spot import SpotCreate


def can_discuss(spot: Spot) -> bool:
    """Comments are readable/writable only on verified spots.

    Pending and rejected spots are not public, so opening them to comments
    would leak their existence.
    """
    return spot.status == SpotStatus.verified


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


async def list_comments(session: AsyncSession, *, spot_id: UUID) -> list[SpotComment]:
    spot = await spots_repo.get(session, spot_id)
    if spot is None:
        raise NotFound("spot not found")
    if not can_discuss(spot):
        raise NotFound("spot not found")  # do not reveal non-public spots
    return await spots_repo.list_comments(session, spot_id)


async def add_comment(
    session: AsyncSession, *, spot_id: UUID, author_id: UUID, body: str
) -> SpotComment:
    spot = await spots_repo.get(session, spot_id)
    if spot is None:
        raise NotFound("spot not found")
    if not can_discuss(spot):
        raise Forbidden("comments are allowed on verified spots only")
    comment = await spots_repo.add_comment(
        session, spot_id=spot_id, author_id=author_id, body=body
    )
    await session.commit()
    return comment
