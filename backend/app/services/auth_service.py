import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import Conflict, Unauthorized
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.repositories import users as users_repo
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def register(session: AsyncSession, data: RegisterRequest) -> User:
    existing = await users_repo.get_by_email(session, data.email)
    if existing:
        raise Conflict("email already registered")
    user = await users_repo.create(
        session,
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
    )
    await session.commit()
    return user


async def issue_tokens(session: AsyncSession, user: User) -> TokenPair:
    settings = get_settings()
    access = create_access_token(user.id, extra={"role": user.role.value})
    raw_refresh = secrets.token_urlsafe(48)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=_hash_refresh(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_ttl_days),
    )
    session.add(rt)
    await session.commit()
    return TokenPair(access_token=access, refresh_token=raw_refresh)


async def login(session: AsyncSession, data: LoginRequest) -> TokenPair:
    user = await users_repo.get_by_email(session, data.email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise Unauthorized("invalid credentials")
    if not user.is_active:
        raise Unauthorized("account disabled")
    return await issue_tokens(session, user)


async def refresh(session: AsyncSession, raw_refresh_token: str) -> TokenPair:
    token_hash = _hash_refresh(raw_refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    rt = (await session.execute(stmt)).scalar_one_or_none()
    if rt is None or rt.revoked_at is not None:
        raise Unauthorized("invalid refresh token")
    if rt.expires_at < datetime.now(timezone.utc):
        raise Unauthorized("refresh token expired")

    rt.revoked_at = datetime.now(timezone.utc)
    user = await users_repo.get_by_id(session, rt.user_id)
    if user is None or not user.is_active:
        raise Unauthorized("account disabled")
    return await issue_tokens(session, user)


async def revoke_all_user_tokens(session: AsyncSession, user_id: UUID) -> None:
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    )
    for rt in (await session.execute(stmt)).scalars():
        rt.revoked_at = datetime.now(timezone.utc)
    await session.commit()
