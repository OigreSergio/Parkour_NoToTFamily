from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.models.user import User
from app.schemas.auth import (
    GuestLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import UserOut
from app.services import auth_service

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
