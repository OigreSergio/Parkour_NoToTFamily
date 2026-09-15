from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, optional_current_user, require_admin
from app.core.exceptions import NotFound
from app.models.user import User
from app.models.video import TrickCategory, VideoCategory, VideoLevel
from app.repositories import profiles as profiles_repo
from app.repositories import videos as videos_repo
from app.schemas.video import VideoCreate, VideoOut
from app.services import access_policy, video_service


async def _access_for(session: AsyncSession, user: User | None) -> access_policy.ContentAccess:
    """The ceiling that applies to ``user``.

    Visitors and accounts that have not answered the onboarding questions keep
    the catalogue they have always had: the ceiling is a consequence of having
    told the app who you are, not a penalty for not having.
    """
    if user is None:
        return access_policy.FULL_ACCESS
    profile = await profiles_repo.get(session, user.id)
    if profile is None or profile.birth_date is None:
        return access_policy.FULL_ACCESS
    return access_policy.access_for(
        profile,
        today=datetime.now(timezone.utc).date(),
        instructor_approved=await profiles_repo.has_approved_certification(session, user.id),
    )

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

    Tutorials above the caller's ceiling are **left out entirely** rather than
    returned locked. That is deliberate: a `locked` entry is a visible signal,
    and for an under-18 account the whole point of the safe experience is that
    there is nothing to see — no greyed-out row, no counter that does not add
    up, nothing a client could render as "this app is treating me
    differently". See `app.services.access_policy`.
    """
    items = await videos_repo.list_videos(
        session, category=category, level=level, trick_category=trick_category, limit=limit
    )
    access = await _access_for(session, user)
    return [
        video_service.to_out(v, user) for v in items if access_policy.is_within(v, access)
    ]


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(
    video_id: UUID,
    user: User | None = Depends(optional_current_user),
    session: AsyncSession = Depends(db_session),
) -> VideoOut:
    video = await videos_repo.get_by_id(session, video_id)
    if video is None:
        raise NotFound("video not found")
    access = await _access_for(session, user)
    if not access_policy.is_within(video, access):
        # Same answer as a video that does not exist: a distinguishable 403
        # would tell the caller exactly what is being kept from them.
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
