from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.spot import SpotStatus


class Point(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class SpotCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    location: Point
    photo_urls: list[str] = Field(default_factory=list, max_length=10)
    difficulty: int = Field(default=1, ge=1, le=5)


class SpotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    location: Point
    photo_urls: list[str]
    difficulty: int
    status: SpotStatus
    submitted_by: UUID | None
    verified_at: datetime | None
    created_at: datetime


class SpotRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class SpotSearchQuery(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_m: int = Field(default=5000, ge=10, le=50_000)
    limit: int = Field(default=100, ge=1, le=500)
