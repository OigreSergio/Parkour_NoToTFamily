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
    # First photo, ready to use as list/map thumbnail without unpacking the
    # whole array client-side. None when the spot has no photos yet.
    preview_url: str | None = None
    difficulty: int
    status: SpotStatus
    submitted_by: UUID | None
    verified_at: datetime | None
    created_at: datetime


class SpotRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class SpotCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class SpotCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    spot_id: UUID
    author_id: UUID | None
    author_name: str | None = None
    body: str
    created_at: datetime


class SpotSearchQuery(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    # 20 000 km copre il pianeta: serve alla mappa "tutti gli spot" dei client,
    # che non hanno ancora una query per riquadro di schermo.
    radius_m: int = Field(default=5000, ge=10, le=20_000_000)
    limit: int = Field(default=100, ge=1, le=2000)
