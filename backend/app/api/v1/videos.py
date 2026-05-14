from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, require_admin
from app.models.user import User
from app.models.video import VideoCategory, VideoLevel
from app.repositories import videos as videos_repo
from app.schemas.video import VideoCreate, VideoOut

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=list[VideoOut])
async def list_videos(
    category: VideoCategory | None = Query(default=None),
    level: VideoLevel | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(db_session),
) -> list[VideoOut]:
    items = await videos_repo.list_videos(session, category=category, level=level, limit=limit)
    return [VideoOut.model_validate(v) for v in items]


@router.post("", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def create_video(
    data: VideoCreate,
    admin: User = Depends(require_admin),  # noqa: ARG001
    session: AsyncSession = Depends(db_session),
) -> VideoOut:
    v = await videos_repo.create(session, data)
    await session.commit()
    return VideoOut.model_validate(v)
