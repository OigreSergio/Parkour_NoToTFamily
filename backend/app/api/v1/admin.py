from uuid import UUID

from fastapi import APIRouter, Depends, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, require_admin
from app.api.v1.spots import _to_out
from app.models.spot import SpotStatus
from app.models.user import User
from app.repositories import spots as spots_repo
from app.schemas.spot import SpotCreate, SpotOut, SpotRejectRequest, SpotVerifyRequest
from app.services import spot_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/spots", response_model=list[SpotOut])
async def queue(
    status: SpotStatus = SpotStatus.pending,
    admin: User = Depends(require_admin),  # noqa: ARG001
    session: AsyncSession = Depends(db_session),
) -> list[SpotOut]:
    spots = await spots_repo.list_by_status(session, status)
    return [_to_out(s) for s in spots]


@router.post("/spots", response_model=SpotOut, status_code=http_status.HTTP_201_CREATED)
async def create_spot(
    data: SpotCreate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
) -> SpotOut:
    """Create a spot that is immediately verified (admin-only)."""
    spot = await spot_service.create_verified(session, data=data, admin_id=admin.id)
    return _to_out(spot)


@router.post("/spots/{spot_id}/verify", response_model=SpotOut)
async def verify(
    spot_id: UUID,
    data: SpotVerifyRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
) -> SpotOut:
    spot = await spot_service.verify(
        session,
        spot_id=spot_id,
        verifier_id=admin.id,
        photos_real=data.photos_real,
        note=data.note,
    )
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
