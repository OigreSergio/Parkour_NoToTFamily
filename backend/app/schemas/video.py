from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.video import VideoCategory, VideoLevel


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    url: str
    thumbnail_url: str | None
    category: VideoCategory
    level: VideoLevel
    duration_seconds: int
    created_at: datetime


class VideoCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=2000)
    url: str = Field(max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    category: VideoCategory
    level: VideoLevel
    duration_seconds: int = Field(default=0, ge=0)
