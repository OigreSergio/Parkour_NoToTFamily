"""guest access and tutorial fields

Revision ID: 0002_guest_tutorials
Revises: 0001_initial
Create Date: 2026-07-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_guest_tutorials"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guest accounts sign in without an email/password, so both become nullable.
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.add_column(
        "users",
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users",
        sa.Column("is_subscribed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    trick_category = sa.Enum(
        "flips",
        "basics",
        "vaults",
        "wall_tricks",
        "bar_tricks",
        "ground_tricks",
        "other",
        name="trick_category",
    )
    trick_category.create(op.get_bind(), checkfirst=True)
    op.add_column("videos", sa.Column("trick_category", trick_category, nullable=True))
    op.create_index("ix_videos_trick_category", "videos", ["trick_category"])
    op.add_column(
        "videos",
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("videos", "difficulty")
    op.drop_index("ix_videos_trick_category", table_name="videos")
    op.drop_column("videos", "trick_category")
    op.execute("DROP TYPE IF EXISTS trick_category")
    op.drop_column("users", "is_subscribed")
    op.drop_column("users", "is_guest")
    op.execute("DELETE FROM users WHERE email IS NULL")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
