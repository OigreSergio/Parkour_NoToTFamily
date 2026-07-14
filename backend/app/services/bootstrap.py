"""Startup seeding: guarantee an administrator account exists.

Set ``INITIAL_ADMIN_EMAIL`` and ``INITIAL_ADMIN_PASSWORD`` in the environment
(or ``.env``) and the account is created — or an existing account with that
email is promoted to admin — when the API boots. This is the only supported
way to obtain the first admin; there is deliberately no self-service
"become admin" endpoint.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import log
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories import users as users_repo


async def ensure_initial_admin(session: AsyncSession) -> User | None:
    settings = get_settings()
    email = settings.initial_admin_email
    password = settings.initial_admin_password
    if not email or not password:
        return None

    user = await users_repo.get_by_email(session, email)
    if user is None:
        user = await users_repo.create(
            session,
            email=email,
            password_hash=hash_password(password),
            display_name="Admin",
            role=UserRole.admin,
            is_email_verified=True,
        )
        log.info("initial_admin_created", email=email)
    elif user.role != UserRole.admin:
        user.role = UserRole.admin
        log.info("initial_admin_promoted", email=email)
    await session.commit()
    return user
