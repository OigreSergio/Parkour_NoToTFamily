from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.video import Video, VideoCategory, VideoLevel
from app.schemas.video import VideoCreate


async def list_videos(
    session: AsyncSession,
    *,
    category: VideoCategory | None = None,
    level: VideoLevel | None = None,
    limit: int = 50,
) -> list[Video]:
    stmt = select(Video).order_by(Video.created_at.desc()).limit(limit)
    if category is not None:
        stmt = stmt.where(Video.category == category)
    if level is not None:
        stmt = stmt.where(Video.level == level)
    return list((await session.execute(stmt)).scalars())


async def create(session: AsyncSession, data: VideoCreate) -> Video:
    video = Video(**data.model_dump())
    session.add(video)
    await session.flush()
    return video
