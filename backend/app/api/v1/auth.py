from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.models.user import User
from app.schemas.auth import (
    EmailCodeRequest,
    EmailCodeResult,
    EmailCodeSent,
    EmailCodeVerifyRequest,
    GuestLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import UserOut
from app.services import auth_service, email_verification_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, session: AsyncSession = Depends(db_session)) -> User:
    return await auth_service.register(session, data)


@router.post("/guest", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def login_guest(
    data: GuestLoginRequest | None = None,
    session: AsyncSession = Depends(db_session),
) -> TokenPair:
    """Sign in without an email: creates a guest account and returns tokens."""
    return await auth_service.login_guest(session, data or GuestLoginRequest())


@router.post("/login", response_model=TokenPair)
async def login(data: LoginRequest, session: AsyncSession = Depends(db_session)) -> TokenPair:
    return await auth_service.login(session, data)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, session: AsyncSession = Depends(db_session)) -> TokenPair:
    return await auth_service.refresh(session, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> None:
    await auth_service.revoke_all_user_tokens(session, user.id)


# --- email code sign-in ------------------------------------------------------
#
# The primary way in. No password: the address is the account. Both endpoints
# answer identically whether or not the address is already registered — see
# `app.services.email_verification_service`.


@router.post("/email/request-code", response_model=EmailCodeSent)
async def request_email_code(
    data: EmailCodeRequest,
    session: AsyncSession = Depends(db_session),
) -> EmailCodeSent:
    """Generate a code now and mail it from the no-reply sender.

    Per-address throttling lives in the service (one code per minute, five per
    hour): flooding somebody else's inbox costs the sender nothing, so the
    limit has to follow the address, not the IP.
    """
    return await email_verification_service.request_code(session, email=str(data.email))


@router.post("/email/verify-code", response_model=EmailCodeResult)
async def verify_email_code(
    data: EmailCodeVerifyRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> EmailCodeResult:
    """Check the code: sign in, or create the account and save its profile.

    Creating an account requires the risk notice to be accepted at its current
    version — `accepted_documents` carries what the pop-up showed.
    """
    tokens, created, next_step = await email_verification_service.verify_code(
        session,
        data,
        ip_address=request.headers.get("x-forwarded-for") or (
            request.client.host if request.client else None
        ),
        user_agent=request.headers.get("user-agent"),
    )
    return EmailCodeResult(tokens=tokens, created=created, next_step=next_step)
