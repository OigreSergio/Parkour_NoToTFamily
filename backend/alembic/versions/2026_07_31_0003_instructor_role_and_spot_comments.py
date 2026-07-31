"""instructor role and spot comments

Revision ID: 0003_instructor_comments
Revises: 0002_guest_tutorials
Create Date: 2026-07-31

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0003_instructor_comments"
down_revision: str | None = "0002_guest_tutorials"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # New qualification between user and admin. Enum values are append-only.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'instructor'")

    op.create_table(
        "spot_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "spot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("spots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("spot_comments_spot_id_idx", "spot_comments", ["spot_id"])


def downgrade() -> None:
    op.drop_index("spot_comments_spot_id_idx", table_name="spot_comments")
    op.drop_table("spot_comments")
    # Postgres cannot remove a value from an enum; leaving 'instructor' in
    # place is harmless.
