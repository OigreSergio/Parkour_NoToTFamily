"""spot photo credits and survey flag

Revision ID: 0003_spot_photo_credits
Revises: 0002_guest_tutorials
Create Date: 2026-08-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_spot_photo_credits"
down_revision: Union[str, None] = "0002_guest_tutorials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # photo_urls resta la lista piatta usata da chi vuole solo mostrare le foto;
    # photos porta accanto a ogni URL autore, licenza e pagina di origine, che
    # CC BY / CC BY-SA impongono di mostrare insieme all'immagine.
    op.add_column(
        "spots",
        sa.Column(
            "photos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    # Uno spot può stare in mappa prima che qualcuno ne abbia censito gli
    # ostacoli sul posto: l'app lo segnala invece di far finta che sia completo.
    op.add_column(
        "spots",
        sa.Column(
            "surveyed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("spots", "surveyed")
    op.drop_column("spots", "photos")
