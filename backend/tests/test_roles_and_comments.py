from uuid import uuid4

import pytest

from app.core.exceptions import Forbidden
from app.models.spot import Spot, SpotStatus
from app.models.user import User, UserRole
from app.services import spot_service, user_service


def _user(role: UserRole = UserRole.user) -> User:
    return User(
        id=uuid4(),
        email="a@b.c",
        password_hash="x",
        display_name="T",
        role=role,
    )


def _spot(status: SpotStatus) -> Spot:
    return Spot(
        id=uuid4(),
        name="Colle Oppio",
        description="",
        location="SRID=4326;POINT(12.4966 41.8925)",
        photo_urls=[],
        difficulty=2,
        status=status,
    )


# --- roles -----------------------------------------------------------------


def test_new_accounts_start_equal() -> None:
    # The model default is `user`: nobody is born instructor or admin.
    assert User(display_name="X").role in (None, UserRole.user)  # default applied on flush
    assert UserRole("user") == UserRole.user  # value stays stable for clients


def test_admin_can_qualify_and_revoke_instructor() -> None:
    member = _user()
    user_service.change_role(member, UserRole.instructor)
    assert member.role == UserRole.instructor
    user_service.change_role(member, UserRole.user)
    assert member.role == UserRole.user


def test_admin_role_cannot_be_granted_via_api() -> None:
    member = _user()
    with pytest.raises(Forbidden):
        user_service.change_role(member, UserRole.admin)
    assert member.role == UserRole.user


def test_admin_accounts_cannot_be_touched_via_api() -> None:
    boss = _user(UserRole.admin)
    with pytest.raises(Forbidden):
        user_service.change_role(boss, UserRole.user)
    assert boss.role == UserRole.admin


def test_grantable_roles_exclude_admin() -> None:
    assert user_service.can_grant(UserRole.user)
    assert user_service.can_grant(UserRole.instructor)
    assert not user_service.can_grant(UserRole.admin)


# --- spot comments ---------------------------------------------------------


def test_comments_allowed_on_verified_spots_only() -> None:
    assert spot_service.can_discuss(_spot(SpotStatus.verified))
    assert not spot_service.can_discuss(_spot(SpotStatus.pending))
    assert not spot_service.can_discuss(_spot(SpotStatus.rejected))
