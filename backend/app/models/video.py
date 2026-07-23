import enum

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class VideoCategory(str, enum.Enum):
    recovery = "recovery"
    practice = "practice"
    conditioning = "conditioning"


class VideoLevel(str, enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class Video(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "videos"

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[VideoCategory] = mapped_column(
        Enum(VideoCategory, name="video_category"), nullable=False, index=True
    )
    level: Mapped[VideoLevel] = mapped_column(
        Enum(VideoLevel, name="video_level"), nullable=False, index=True
    )
    duration_seconds: Mapped[int] = mapped_column(default=0, nullable=False)
