"""Add birth_date to player_seasons table

Revision ID: b6f3g4h5i6j7
Revises: c8d4e5f6g7h8
Create Date: 2025-12-19 10:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b6f3g4h5i6j7"
down_revision = "c8d4e5f6g7h8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add birth_date column to player_seasons table
    op.add_column("player_seasons", sa.Column("birth_date", sa.Date(), nullable=True))

    # Migrate existing born_year to birth_date (assuming January 1st as default)
    # This converts born_year to a date format
    op.execute("""
        UPDATE player_seasons
        SET birth_date = MAKE_DATE(born_year, 1, 1)
        WHERE born_year IS NOT NULL
    """)


def downgrade() -> None:
    # Remove birth_date column from player_seasons table
    op.drop_column("player_seasons", "birth_date")
