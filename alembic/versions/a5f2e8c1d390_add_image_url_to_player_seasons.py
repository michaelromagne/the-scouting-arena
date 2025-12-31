"""Add image_url to player_seasons table

Revision ID: a5f2e8c1d390
Revises: 7163b1ca3887
Create Date: 2025-12-18 14:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a5f2e8c1d390"
down_revision = "7163b1ca3887"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add image_url column to player_seasons table
    op.add_column("player_seasons", sa.Column("image_url", sa.String(), nullable=True))

    # Migrate existing image_url from players table to player_seasons
    # This copies the image_url from players to all associated player_seasons
    op.execute("""
        UPDATE player_seasons ps
        SET image_url = p.image_url
        FROM players p
        WHERE ps.player_id = p.id AND p.image_url IS NOT NULL
    """)


def downgrade() -> None:
    # Remove image_url column from player_seasons table
    op.drop_column("player_seasons", "image_url")
