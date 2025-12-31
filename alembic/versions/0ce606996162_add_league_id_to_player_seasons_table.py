"""Add league_id to player_seasons table

Revision ID: 0ce606996162
Revises: 164bb115a3cc
Create Date: 2025-09-15 12:22:51.813271

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0ce606996162"
down_revision = "164bb115a3cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add league_id column
    op.add_column("player_seasons", sa.Column("league_id", sa.Integer(), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_player_seasons_league_id",
        "player_seasons",
        "leagues",
        ["league_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Drop old unique constraint
    op.drop_constraint("uq_player_team_season", "player_seasons", type_="unique")

    # Add new unique constraint with league_id
    op.create_unique_constraint(
        "uq_player_team_season_league",
        "player_seasons",
        ["player_id", "season_id", "team_id", "league_id"],
    )


def downgrade() -> None:
    # Drop new unique constraint
    op.drop_constraint("uq_player_team_season_league", "player_seasons", type_="unique")

    # Add back old unique constraint
    op.create_unique_constraint(
        "uq_player_team_season", "player_seasons", ["player_id", "season_id", "team_id"]
    )

    # Drop foreign key constraint
    op.drop_constraint(
        "fk_player_seasons_league_id", "player_seasons", type_="foreignkey"
    )

    # Drop league_id column
    op.drop_column("player_seasons", "league_id")
