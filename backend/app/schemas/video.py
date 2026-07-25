from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.video import TrickCategory, VideoCategory, VideoLevel


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    # None when the viewer is not allowed to watch (see `locked`).
    url: str | None
    thumbnail_url: str | None
    category: VideoCategory
    level: VideoLevel
    trick_category: TrickCategory | None = None
    difficulty: int = 1
    duration_seconds: int
    # True for videos above beginner level, which require a subscription.
    is_premium: bool = False
    # True when the current viewer cannot watch this video (url is hidden).
    locked: bool = False
    created_at: datetime


class VideoCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    url: str = Field(max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    category: VideoCategory
    level: VideoLevel
    trick_category: TrickCategory | None = None
    difficulty: int = Field(default=1, ge=1, le=10)
    duration_seconds: int = Field(default=0, ge=0)
