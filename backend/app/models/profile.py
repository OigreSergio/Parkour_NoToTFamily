import enum
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class PractitionerType(str, enum.Enum):
    athlete = "athlete"
    instructor = "instructor"


class ExperienceBand(str, enum.Enum):
    """How long the member says they have been training.

    The bands are exactly the options offered in the app, in order. Their
    ordering is meaningful: see ``app.services.access_policy``.
    """

    less_than_month = "less_than_month"
    few_months = "few_months"
    six_months = "six_months"
    one_year = "one_year"
    couple_years = "couple_years"
    over_5_years = "over_5_years"
    over_10_years = "over_10_years"


#: Shared type object: the same Postgres enum backs three columns across two
#: tables, so it must be one instance (SQLAlchemy then emits CREATE TYPE once).
_EXPERIENCE_BAND = Enum(ExperienceBand, name="experience_band")


class CertificationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class UserProfile(TimestampMixin, Base):
    """Everything the app needs to decide what to show a member.

    One row per user, created the moment the account is created. The row is
    server-side only in one important respect: ``birth_date`` and everything
    derived from it (whether the member is a minor, the resulting content
    ceiling) is never echoed back to clients in a form the UI could render as
    a badge — see ``docs/ONBOARDING.md``. The safe experience for minors is
    the *same* experience, with a different set of exercises behind it.
    """

    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    practitioner_type: Mapped[PractitionerType | None] = mapped_column(
        Enum(PractitionerType, name="practitioner_type"), nullable=True
    )
    #: What the member declared. Grants access immediately (provisionally).
    experience_band: Mapped[ExperienceBand | None] = mapped_column(_EXPERIENCE_BAND, nullable=True)
    #: What the mini-game actually supports. Overrides the declared band.
    verified_band: Mapped[ExperienceBand | None] = mapped_column(_EXPERIENCE_BAND, nullable=True)
    quiz_passed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quiz_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class InstructorCertification(UUIDPKMixin, TimestampMixin, Base):
    """A dossier submitted by someone claiming to teach parkour.

    The files themselves are **not** stored: the certificate and the identity
    document are mailed to the review mailbox and then dropped. Keeping an ID
    document on the application servers would be a liability out of all
    proportion to the feature; what stays here is the metadata plus a SHA-256
    digest of each file, enough to prove later that the reviewed document is
    the submitted one.
    """

    __tablename__ = "instructor_certifications"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: Nationally recognised body that issued the certificate, as declared.
    issuing_body: Mapped[str] = mapped_column(String(160), nullable=False)
    certificate_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    certificate_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    identity_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[CertificationStatus] = mapped_column(
        Enum(CertificationStatus, name="certification_status"),
        default=CertificationStatus.pending,
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class LegalAcceptance(UUIDPKMixin, TimestampMixin, Base):
    """Proof that a specific version of a notice was put in front of someone.

    Stored per (user, document, version): bumping a document's version makes
    every previous acceptance stop counting, and the pop-up comes back.
    """

    __tablename__ = "legal_acceptances"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    document_version: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: Kept for evidentiary value; truncated to /24 (IPv4) by the service.
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ExperienceQuizAttempt(UUIDPKMixin, TimestampMixin, Base):
    """One run of the vault-naming game.

    ``questions`` holds the answer key server-side: a list of
    ``{"slug": ..., "options": [...]}``. It never leaves the server, so the
    client cannot read the answers out of its own traffic.
    """

    __tablename__ = "experience_quiz_attempts"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    claimed_band: Mapped[ExperienceBand | None] = mapped_column(_EXPERIENCE_BAND, nullable=True)
    questions: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    granted_band: Mapped[ExperienceBand | None] = mapped_column(_EXPERIENCE_BAND, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
