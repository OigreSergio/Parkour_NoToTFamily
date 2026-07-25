from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, optional_current_user, require_admin
from app.core.exceptions import NotFound
from app.models.user import User
from app.models.video import TrickCategory, VideoCategory, VideoLevel
from app.repositories import videos as videos_repo
from app.schemas.video import VideoCreate, VideoOut
from app.services import video_service

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("", response_model=list[VideoOut])
async def list_videos(
    category: VideoCategory | None = Query(default=None),
    level: VideoLevel | None = Query(default=None),
    trick_category: TrickCategory | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User | None = Depends(optional_current_user),
    session: AsyncSession = Depends(db_session),
) -> list[VideoOut]:
    """Public tutorial catalog.

    Anyone can browse; premium videos (above beginner) are returned with
    `locked=true` and no `url` unless the caller is subscribed.
    """
    items = await videos_repo.list_videos(
        session, category=category, level=level, trick_category=trick_category, limit=limit
    )
    return [video_service.to_out(v, user) for v in items]


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(
    video_id: UUID,
    user: User | None = Depends(optional_current_user),
    session: AsyncSession = Depends(db_session),
) -> VideoOut:
    video = await videos_repo.get_by_id(session, video_id)
    if video is None:
        raise NotFound("video not found")
    return video_service.to_out(video, user)


@router.post("", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
async def create_video(
    data: VideoCreate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
) -> VideoOut:
    v = await videos_repo.create(session, data)
    await session.commit()
    return video_service.to_out(v, admin)
