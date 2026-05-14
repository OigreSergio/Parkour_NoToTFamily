from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User, UserRole
from app.repositories import users as users_repo


async def db_session() -> AsyncIterator[AsyncSession]:
    async for s in get_session():
        yield s


async def current_user(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(db_session),
) -> User:
    if not authorization.lower().startswith("bearer "):
        raise Unauthorized("missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise Unauthorized("invalid token") from e
    if payload.get("type") != "access":
        raise Unauthorized("wrong token type")
    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as e:
        raise Unauthorized("malformed token") from e
    user = await users_repo.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("user not found")
    return user


async def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.admin:
        raise Forbidden("admin role required")
    return user
