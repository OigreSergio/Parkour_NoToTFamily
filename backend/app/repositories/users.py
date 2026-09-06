from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email.lower())
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_by_guest_key_hash(session: AsyncSession, key_hash: str) -> User | None:
    stmt = select(User).where(User.guest_key_hash == key_hash)
    return (await session.execute(stmt)).scalar_one_or_none()


async def display_name_taken(session: AsyncSession, display_name: str) -> bool:
    stmt = select(User.id).where(User.display_name == display_name).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def create(session: AsyncSession, **fields: object) -> User:
    if "email" in fields and isinstance(fields["email"], str):
        fields["email"] = fields["email"].lower()
    user = User(**fields)  # type: ignore[arg-type]
    session.add(user)
    await session.flush()
    return user
