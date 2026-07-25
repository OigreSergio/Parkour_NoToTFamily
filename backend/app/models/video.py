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


class TrickCategory(str, enum.Enum):
    """Tutorial grouping shown in the mobile Tutorials grid."""

    flips = "flips"
    basics = "basics"
    vaults = "vaults"
    wall_tricks = "wall_tricks"
    bar_tricks = "bar_tricks"
    ground_tricks = "ground_tricks"
    other = "other"


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
    # NULL for non-tutorial videos (e.g. recovery routines without a trick).
    trick_category: Mapped[TrickCategory | None] = mapped_column(
        Enum(TrickCategory, name="trick_category"), nullable=True, index=True
    )
    # 1-10, drives the difficulty gauge in the tutorial list.
    difficulty: Mapped[int] = mapped_column(default=1, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(default=0, nullable=False)
