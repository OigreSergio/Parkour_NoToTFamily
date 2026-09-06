"""durable key on guest accounts

Revision ID: 0005_guest_keys
Revises: 0004_auth_profiles
Create Date: 2026-09-06

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_guest_keys"
down_revision: str | None = "0004_auth_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A guest has no email to come back to. This is what makes their answers,
    # their game result and the levels they unlocked survive a closed tab —
    # and the unique index is what guarantees two guests never land on the same
    # account. Only the HMAC is stored; the key itself is shown once, at
    # sign-up, and never again.
    op.add_column("users", sa.Column("guest_key_hash", sa.String(64), nullable=True))
    # Postgres allows any number of NULLs under a unique index, so guest rows
    # created before this migration stay valid (and simply cannot be resumed).
    op.create_index("ix_users_guest_key_hash", "users", ["guest_key_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_guest_key_hash", table_name="users")
    op.drop_column("users", "guest_key_hash")
