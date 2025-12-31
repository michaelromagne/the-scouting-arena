"""Add market_value_eur to player_seasons

Revision ID: 0171c651af65
Revises:
Create Date: 2025-08-23 10:59:01.466337

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0171c651af65"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add market_value_eur column to player_seasons table
    op.add_column(
        "player_seasons", sa.Column("market_value_eur", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    # Remove market_value_eur column from player_seasons table
    op.drop_column("player_seasons", "market_value_eur")
