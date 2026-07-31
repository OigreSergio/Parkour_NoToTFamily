from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, require_admin
from app.api.v1.spots import _to_out
from app.core.exceptions import NotFound
from app.models.spot import SpotStatus
from app.models.user import User
from app.repositories import spots as spots_repo
from app.repositories import users as users_repo
from app.schemas.spot import SpotOut, SpotRejectRequest
from app.schemas.user import RoleChangeRequest, UserOut
from app.services import spot_service, user_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/spots", response_model=list[SpotOut])
async def queue(
    status: SpotStatus = SpotStatus.pending,
    admin: User = Depends(require_admin),  # noqa: ARG001
    session: AsyncSession = Depends(db_session),
) -> list[SpotOut]:
    spots = await spots_repo.list_by_status(session, status)
    return [_to_out(s) for s in spots]


@router.post("/spots/{spot_id}/verify", response_model=SpotOut)
async def verify(
    spot_id: UUID,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
) -> SpotOut:
    spot = await spot_service.verify(session, spot_id=spot_id, verifier_id=admin.id)
    return _to_out(spot)


@router.post("/spots/{spot_id}/reject", response_model=SpotOut)
async def reject(
    spot_id: UUID,
    data: SpotRejectRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
) -> SpotOut:
    spot = await spot_service.reject(
        session, spot_id=spot_id, verifier_id=admin.id, reason=data.reason
    )
    return _to_out(spot)


@router.post("/users/{user_id}/role", response_model=UserOut)
async def change_user_role(
    user_id: UUID,
    data: RoleChangeRequest,
    admin: User = Depends(require_admin),  # noqa: ARG001
    session: AsyncSession = Depends(db_session),
) -> UserOut:
    """Qualify a member as instructor, or revoke the qualification.

    All accounts start as `user` (peers). This endpoint moves a member
    between `user` and `instructor` only; the `admin` role is reserved and
    cannot be granted or removed here.
    """
    target = await users_repo.get_by_id(session, user_id)
    if target is None:
        raise NotFound("user not found")
    user_service.change_role(target, data.role)
    await session.commit()
    return UserOut.model_validate(target)
