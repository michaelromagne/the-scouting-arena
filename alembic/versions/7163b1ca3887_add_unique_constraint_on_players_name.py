"""Add unique constraint on players.name

Revision ID: 7163b1ca3887
Revises: 0ce606996162
Create Date: 2025-09-15 18:00:17.714279

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "7163b1ca3887"
down_revision = "0ce606996162"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unique constraint on players.name
    op.create_unique_constraint("uq_player_name", "players", ["name"])


def downgrade() -> None:
    # Drop unique constraint on players.name
    op.drop_constraint("uq_player_name", "players", type_="unique")
