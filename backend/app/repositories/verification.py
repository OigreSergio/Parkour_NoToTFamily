from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verification import EmailVerificationCode, VerificationPurpose


async def create(
    session: AsyncSession,
    *,
    email: str,
    code_hash: str,
    purpose: VerificationPurpose,
    expires_at: datetime,
) -> EmailVerificationCode:
    row = EmailVerificationCode(
        email=email.lower(),
        code_hash=code_hash,
        purpose=purpose,
        expires_at=expires_at,
    )
    session.add(row)
    await session.flush()
    return row


async def latest_open(
    session: AsyncSession, *, email: str, purpose: VerificationPurpose
) -> EmailVerificationCode | None:
    """The most recent code for this address that has not been used yet."""
    stmt = (
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == email.lower(),
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def latest_any(session: AsyncSession, *, email: str) -> EmailVerificationCode | None:
    stmt = (
        select(EmailVerificationCode)
        .where(EmailVerificationCode.email == email.lower())
        .order_by(EmailVerificationCode.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def count_since(session: AsyncSession, *, email: str, since: datetime) -> int:
    stmt = (
        select(func.count())
        .select_from(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == email.lower(),
            EmailVerificationCode.created_at >= since,
        )
    )
    return int((await session.execute(stmt)).scalar_one())


async def get(session: AsyncSession, code_id: UUID) -> EmailVerificationCode | None:
    return await session.get(EmailVerificationCode, code_id)
