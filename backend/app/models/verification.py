import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class VerificationPurpose(str, enum.Enum):
    """What a code unlocks. Codes are never valid across purposes."""

    #: Prove control of an address, then sign in or create the account.
    email_login = "email_login"
    #: Re-verify an address already attached to an account.
    email_change = "email_change"


class EmailVerificationCode(UUIDPKMixin, TimestampMixin, Base):
    """A one-time numeric code mailed to an address.

    Only the HMAC of the code is stored: a database dump does not let anyone
    replay a live code, and the HMAC key is the server secret. The row is
    kept after use (``consumed_at``) so that rate limiting can count recent
    requests and so that a support question has an audit trail — the code
    itself is never recoverable from it.
    """

    __tablename__ = "email_verification_codes"
    __table_args__ = (Index("email_verification_codes_email_created_idx", "email", "created_at"),)

    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[VerificationPurpose] = mapped_column(
        Enum(VerificationPurpose, name="verification_purpose"),
        default=VerificationPurpose.email_login,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
