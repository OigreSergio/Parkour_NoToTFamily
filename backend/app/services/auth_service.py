import hashlib
import hmac
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
from app.data import guest_names
from app.models.profile import PractitionerType
from app.models.user import RefreshToken, User
from app.repositories import profiles as profiles_repo
from app.repositories import users as users_repo
from app.schemas.auth import (
    GuestLoginRequest,
    GuestSession,
    LoginRequest,
    RegisterRequest,
    TokenPair,
)

#: Prefix on every guest key, so one is recognisable in a bug report or a
#: support message without anybody having to guess what they are looking at.
GUEST_KEY_PREFIX = "pkg_"

#: Tries at finding an unused generated name before widening the suffix.
_NAME_ATTEMPTS = 5


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_guest_key(raw_key: str) -> str:
    """HMAC of a guest key, keyed with the server secret.

    Same reasoning as the email codes: the key is a bearer credential with no
    password behind it, so a database dump must not hand anyone else's guest
    account over. Deterministic because it is also the lookup key.
    """
    settings = get_settings()
    return hmac.new(settings.jwt_secret.encode(), raw_key.encode(), hashlib.sha256).hexdigest()


def generate_guest_key() -> str:
    return GUEST_KEY_PREFIX + secrets.token_urlsafe(32)


async def _unused_display_name(session: AsyncSession) -> str:
    """A generated name nobody is using yet.

    Collisions are cosmetic — the account is identified by its key, not its
    name — but two `Cornicione-7K4Q` in the same comment thread is exactly the
    kind of overlap a guest has no way to resolve, so it is worth five queries.
    """
    for _ in range(_NAME_ATTEMPTS):
        name = guest_names.generate()
        if not await users_repo.display_name_taken(session, name):
            return name
    # Still colliding after five tries means the short suffix is crowded;
    # widening it is cheaper than looping.
    return guest_names.generate(suffix_length=8)


async def login_guest(
    session: AsyncSession,
    data: GuestLoginRequest,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> GuestSession:
    """Create an anonymous account: no email, no chosen name, its own key.

    A guest gets the same questions as everybody else — date of birth, how long
    they have been training, the vault game — because they get the same spots
    and the same tutorials, and the age and experience filters have to have
    something to work with. What they do not get is an identity: the name is
    generated, and the key returned here is the only thread back to the
    account.

    The one branch closed to a guest is the instructor one. Qualifying means
    sending a certificate and an identity document to a human reviewer, which
    is the opposite of staying anonymous — so the profile is created as an
    athlete and the question is never asked.
    """
    from app.services import legal_service, onboarding_service

    missing = legal_service.missing_required(data.accepted_documents, is_minor=False)
    if missing:
        raise ValidationFailed(
            "these notices must be accepted before the account can be created: "
            + ", ".join(missing)
        )

    raw_key = generate_guest_key()
    user = await users_repo.create(
        session,
        email=None,
        password_hash=None,
        display_name=await _unused_display_name(session),
        is_guest=True,
        is_email_verified=False,
        guest_key_hash=hash_guest_key(raw_key),
    )
    profile = await profiles_repo.get_or_create(session, user.id)
    profile.practitioner_type = PractitionerType.athlete

    if data.accepted_documents:
        await legal_service.record(
            session,
            user_id=user.id,
            documents=data.accepted_documents,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    await session.commit()

    tokens = await issue_tokens(session, user)
    return GuestSession(
        tokens=tokens,
        display_name=user.display_name,
        guest_key=raw_key,
        created=True,
        next_step=await onboarding_service.next_step(session, user, profile),
    )


async def resume_guest(session: AsyncSession, raw_key: str) -> GuestSession:
    """Sign back into a guest account with its key.

    This is what makes progress on an anonymous account worth anything: the
    answers, the game result and the levels they unlocked survive a closed tab
    or a new device, without ever asking for an email.
    """
    from app.services import onboarding_service

    user = await users_repo.get_by_guest_key_hash(session, hash_guest_key(raw_key))
    if user is None or not user.is_guest:
        raise Unauthorized("invalid guest key")
    if not user.is_active:
        raise Unauthorized("account disabled")

    profile = await profiles_repo.get_or_create(session, user.id)
    if profile.practitioner_type is None:
        profile.practitioner_type = PractitionerType.athlete
    await session.commit()

    tokens = await issue_tokens(session, user)
    return GuestSession(
        tokens=tokens,
        display_name=user.display_name,
        guest_key=None,
        created=False,
        next_step=await onboarding_service.next_step(session, user, profile),
    )


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
