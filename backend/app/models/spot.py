import enum
from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import ARRAY, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class SpotStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class Spot(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "spots"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    location: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=False, index=True
    )
    photo_urls: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    # Una voce per foto: stessi URL di photo_urls più autore, licenza e link
    # alla pagina originale. CC BY / CC BY-SA vogliono l'attribuzione ovunque
    # la foto venga mostrata, quindi viaggia insieme alla foto.
    photos: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # False quando lo spot è in mappa ma nessuno ne ha ancora censito gli
    # ostacoli sul posto: l'app lo segnala e invita a completarlo.
    surveyed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    status: Mapped[SpotStatus] = mapped_column(
        Enum(SpotStatus, name="spot_status"),
        default=SpotStatus.pending,
        nullable=False,
        index=True,
    )
    submitted_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verified_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list["SpotModerationEvent"]] = relationship(
        back_populates="spot", cascade="all, delete-orphan"
    )


class SpotModerationEvent(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "spot_moderation_events"

    spot_id: Mapped[UUID] = mapped_column(
        ForeignKey("spots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    spot: Mapped[Spot] = relationship(back_populates="events")
