import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import Conflict, Unauthorized, ValidationFailed
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.repositories import users as users_repo
from app.schemas.auth import GuestLoginRequest, LoginRequest, RegisterRequest, TokenPair
from app.services import display_name_policy


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _checked_display_name(name: str) -> str:
    """Nome pubblico ripulito, o 422 con il motivo da mostrare all'utente."""
    try:
        return display_name_policy.check(name)
    except display_name_policy.DisplayNameRejected as rejected:
        raise ValidationFailed(str(rejected)) from rejected


async def login_guest(session: AsyncSession, data: GuestLoginRequest) -> TokenPair:
    """Create a device-only guest account (no email) and issue tokens.

    Guests can browse the app and watch beginner tutorials; premium levels
    stay locked until they subscribe (which requires a full account).
    """
    display_name = (
        _checked_display_name(data.display_name)
        if data.display_name
        else f"Guest-{secrets.token_hex(3)}"
    )
    user = await users_repo.create(
        session,
        email=None,
        password_hash=None,
        display_name=display_name,
        is_guest=True,
    )
    await session.commit()
    return await issue_tokens(session, user)


async def register(session: AsyncSession, data: RegisterRequest) -> User:
    """Crea un account con email e nome scelto da chi si iscrive.

    Il nome passa dalla policy pubblica (`display_name_policy`): chi si
    registra sceglie come farsi chiamare, ma non può prendersi un insulto o
    fingersi lo staff.
    """
    display_name = _checked_display_name(data.display_name)
    existing = await users_repo.get_by_email(session, data.email)
    if existing:
        raise Conflict("email already registered")
    user = await users_repo.create(
        session,
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=display_name,
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
    if (
        user is None
        or user.password_hash is None
        or not verify_password(data.password, user.password_hash)
    ):
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
