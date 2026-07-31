"""Membership levels.

Every account starts at the same level (`user`): the community is made of
peers. The only progression is a *qualification*:

- `instructor` — granted (and revocable) by an admin to members who qualify
  to teach. It unlocks nothing destructive; it is a recognised status.
- `admin` — reserved. It is the only role that can operate the web admin
  (moderation queue, verify/reject, role grants). No API call can assign it:
  the first admin is seeded server-side and further admins are promoted
  manually at the database level, exactly like before.
"""

from app.core.exceptions import Forbidden
from app.models.user import User, UserRole

#: Roles an admin may assign through the API. `admin` is deliberately absent.
GRANTABLE_ROLES = frozenset({UserRole.user, UserRole.instructor})


def can_grant(new_role: UserRole) -> bool:
    """Whether the API is allowed to hand out ``new_role`` at all."""
    return new_role in GRANTABLE_ROLES


def change_role(target: User, new_role: UserRole) -> User:
    """Apply a qualification change, enforcing the reserved-admin rule.

    - ``user`` → ``instructor``: qualify a member as instructor.
    - ``instructor`` → ``user``: revoke the qualification.
    - anything involving ``admin`` (granting it, or demoting an admin) is
      refused: the admin level is managed outside the API.
    """
    if not can_grant(new_role):
        raise Forbidden("the admin role cannot be granted through the API")
    if target.role == UserRole.admin:
        raise Forbidden("admin accounts cannot be modified through the API")
    target.role = new_role
    return target
