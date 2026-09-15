from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.models.user import User
from app.schemas.onboarding import MemberProfile
from app.schemas.user import UserOut
from app.services import onboarding_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/me/profile", response_model=MemberProfile)
async def my_profile(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(db_session),
) -> MemberProfile:
    """Everything the app needs about the person signed in, in one call.

    This is what a returning member costs: one request. Whether the address is
    verified, what they answered during onboarding, what the vault game
    settled, and what they have put on the map — their pending and rejected
    spots included, since those are theirs to follow.

    What is never here is the date of birth or the content ceiling it produces:
    the catalogue is already filtered server-side, and a client that cannot
    know somebody is a minor cannot show it.
    """
    return await onboarding_service.member_profile(session, user)
