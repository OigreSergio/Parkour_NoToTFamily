"""email code sign-in, member profiles, legal acceptances, vault quiz

Revision ID: 0004_auth_profiles
Revises: 0003_instructor_comments
Create Date: 2026-09-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "0004_auth_profiles"
down_revision: str | None = "0003_instructor_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum types are created explicitly (and once): `experience_band` is shared by
# three columns across two tables, and letting create_table emit CREATE TYPE
# would make the second table fail.
_VERIFICATION_PURPOSE = postgresql.ENUM(
    "email_login", "email_change", name="verification_purpose", create_type=False
)
_PRACTITIONER_TYPE = postgresql.ENUM(
    "athlete", "instructor", name="practitioner_type", create_type=False
)
_EXPERIENCE_BAND = postgresql.ENUM(
    "less_than_month",
    "few_months",
    "six_months",
    "one_year",
    "couple_years",
    "over_5_years",
    "over_10_years",
    name="experience_band",
    create_type=False,
)
_CERTIFICATION_STATUS = postgresql.ENUM(
    "pending", "approved", "rejected", name="certification_status", create_type=False
)

_ENUMS = (
    _VERIFICATION_PURPOSE,
    _PRACTITIONER_TYPE,
    _EXPERIENCE_BAND,
    _CERTIFICATION_STATUS,
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum in _ENUMS:
        enum.create(bind, checkfirst=True)

    # --- one-time codes mailed from the no-reply sender ---------------------
    op.create_table(
        "email_verification_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        # HMAC of the code, keyed with the server secret: a dump of this table
        # does not let anyone replay a live code.
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("purpose", _VERIFICATION_PURPOSE, nullable=False, server_default="email_login"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )
    op.create_index("ix_email_verification_codes_email", "email_verification_codes", ["email"])
    op.create_index(
        "email_verification_codes_email_created_idx",
        "email_verification_codes",
        ["email", "created_at"],
    )

    # --- profile: everything the app needs to pick the right exercises ------
    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("practitioner_type", _PRACTITIONER_TYPE, nullable=True),
        sa.Column("experience_band", _EXPERIENCE_BAND, nullable=True),
        sa.Column("verified_band", _EXPERIENCE_BAND, nullable=True),
        sa.Column("quiz_passed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quiz_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )

    # --- instructor dossiers: metadata only, never the files ----------------
    op.create_table(
        "instructor_certifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("issuing_body", sa.String(160), nullable=False),
        sa.Column("certificate_filename", sa.String(255), nullable=False),
        sa.Column("certificate_sha256", sa.String(64), nullable=False),
        sa.Column("identity_filename", sa.String(255), nullable=False),
        sa.Column("identity_sha256", sa.String(64), nullable=False),
        sa.Column("status", _CERTIFICATION_STATUS, nullable=False, server_default="pending"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index(
        "ix_instructor_certifications_user_id", "instructor_certifications", ["user_id"]
    )

    # --- proof that a notice was shown, at the version it was shown at ------
    op.create_table(
        "legal_acceptances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_legal_acceptances_user_id", "legal_acceptances", ["user_id"])
    op.create_index(
        "legal_acceptances_user_doc_idx",
        "legal_acceptances",
        ["user_id", "document_id", "document_version"],
        unique=True,
    )

    # --- vault-naming game --------------------------------------------------
    op.create_table(
        "experience_quiz_attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claimed_band", _EXPERIENCE_BAND, nullable=True),
        # The answer key. Kept server-side so a client cannot read the answers
        # out of its own traffic.
        sa.Column("questions", JSONB, nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("granted_band", _EXPERIENCE_BAND, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_experience_quiz_attempts_user_id", "experience_quiz_attempts", ["user_id"])


def downgrade() -> None:
    op.drop_table("experience_quiz_attempts")
    op.drop_table("legal_acceptances")
    op.drop_table("instructor_certifications")
    op.drop_table("user_profiles")
    op.drop_table("email_verification_codes")
    bind = op.get_bind()
    for enum in _ENUMS:
        enum.drop(bind, checkfirst=True)
