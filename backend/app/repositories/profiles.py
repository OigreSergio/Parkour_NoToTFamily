from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import (
    CertificationStatus,
    InstructorCertification,
    LegalAcceptance,
    UserProfile,
)


async def get(session: AsyncSession, user_id: UUID) -> UserProfile | None:
    return await session.get(UserProfile, user_id)


async def get_or_create(session: AsyncSession, user_id: UUID) -> UserProfile:
    profile = await session.get(UserProfile, user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
        session.add(profile)
        await session.flush()
    return profile


async def latest_certification(
    session: AsyncSession, user_id: UUID
) -> InstructorCertification | None:
    stmt = (
        select(InstructorCertification)
        .where(InstructorCertification.user_id == user_id)
        .order_by(InstructorCertification.created_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def has_approved_certification(session: AsyncSession, user_id: UUID) -> bool:
    cert = await latest_certification(session, user_id)
    return cert is not None and cert.status is CertificationStatus.approved


async def list_acceptances(session: AsyncSession, user_id: UUID) -> list[LegalAcceptance]:
    stmt = select(LegalAcceptance).where(LegalAcceptance.user_id == user_id)
    return list((await session.execute(stmt)).scalars())
