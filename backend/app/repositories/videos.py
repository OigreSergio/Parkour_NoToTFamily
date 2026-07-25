from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video import TrickCategory, Video, VideoCategory, VideoLevel
from app.schemas.video import VideoCreate


async def list_videos(
    session: AsyncSession,
    *,
    category: VideoCategory | None = None,
    level: VideoLevel | None = None,
    trick_category: TrickCategory | None = None,
    limit: int = 50,
) -> list[Video]:
    stmt = select(Video).order_by(Video.created_at.desc()).limit(limit)
    if category is not None:
        stmt = stmt.where(Video.category == category)
    if level is not None:
        stmt = stmt.where(Video.level == level)
    if trick_category is not None:
        stmt = stmt.where(Video.trick_category == trick_category)
    return list((await session.execute(stmt)).scalars())


async def get_by_id(session: AsyncSession, video_id: UUID) -> Video | None:
    return await session.get(Video, video_id)


async def create(session: AsyncSession, data: VideoCreate) -> Video:
    video = Video(**data.model_dump())
    session.add(video)
    await session.flush()
    return video
